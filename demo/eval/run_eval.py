#!/usr/bin/env python3
"""Floor eval for the Frugal Chatbot: 30 fixed questions, same system prompt + FAQ on every rung.

Backends:
  ollama   -- local model via http://localhost:11434 (used as a proxy for the in-browser rung)
  bedrock  -- Amazon Bedrock Converse (needs credentials; `--dry-run` prints the estimated cost and exits)

Usage:
  python3 run_eval.py ollama llama3.2:1b-instruct-q4_K_M
  python3 run_eval.py bedrock moonshotai.kimi-k2.5 --dry-run
"""
import json, sys, time, pathlib, re, urllib.request

HERE = pathlib.Path(__file__).parent
_SYS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--system=")), None)
SYSTEM = pathlib.Path(_SYS).read_text() if _SYS else (HERE.parent / "faq.md").read_text()
TAG = ("-" + pathlib.Path(_SYS).stem) if _SYS else ""
QUESTIONS = json.loads((HERE / "questions.json").read_text())
REFUSAL_MARKERS = ["don't know", "do not know", "not sure", "don't have", "do not have",
                   "no information", "not in the faq", "not covered", "ticket", "unable to",
                   "can't help", "cannot help", "can't assist", "cannot assist", "not able to",
                   "only help", "only answer", "support@example.com", "outside"]
SEED = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--seed=")), "1"))
# USD per 1M tokens, keyed by Bedrock model ID (one source of truth: ../cost/prices.json)
_P = json.loads((HERE.parent / "cost" / "prices.json").read_text())
PRICES = {m["bedrock"]: m for m in _P["open"].values()}
PRICES.update({m["regional"]["bedrock"]: m["regional"] for m in _P["open"].values() if "regional" in m})


def usage_usd(u, p):
    """Cost of one call. Some models (Kimi K3) cache the prompt on their own; inputTokens then excludes it."""
    return (u["inputTokens"] * p["in"] + u["outputTokens"] * p["out"]
            + u.get("cacheReadInputTokens", 0) * p.get("cr", p["in"])
            + u.get("cacheWriteInputTokens", 0) * p.get("cw", p["in"])) / 1e6
LEDGER = HERE / "ledger.json"   # one running total across every paid call in this project


def build_messages(item):
    msgs = [{"role": r, "text": t} for r, t in item.get("history", [])]
    msgs.append({"role": "user", "text": item["q"]})
    return msgs


def call_ollama(model, msgs):
    # Llama 3.2's own generation defaults (temperature 0.6, top_p 0.9), which WebLLM also uses
    opts = {"num_predict": 400, "temperature": 0.6, "top_p": 0.9, "seed": SEED}
    body = {"model": model, "stream": False, "options": opts,
            "messages": [{"role": "system", "content": SYSTEM}] +
                        [{"role": m["role"], "content": m["text"]} for m in msgs]}
    req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode())
    t = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=600))
    return r["message"]["content"], r.get("prompt_eval_count", 0), r.get("eval_count", 0), time.time() - t


# Stop when the project-wide ledger passes this total (USD). Required for the bedrock backend.
BUDGET_USD = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--budget=")), "0"))
SPENT = 0.0  # this run


def ledger_add(usd, note):
    import fcntl   # several eval runs may append at once
    with open(HERE / ".ledger.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        led = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"total_usd": 0.0, "entries": []}
        led["total_usd"] = round(led["total_usd"] + usd, 6)
        led["entries"].append({"usd": round(usd, 6), "note": note, "date": time.strftime("%Y-%m-%d")})
        LEDGER.write_text(json.dumps(led, indent=1))
        return led["total_usd"]
_client = None


def price_for(model):
    return PRICES[model]   # KeyError before any paid call if the model isn't priced


def call_bedrock(model, msgs):
    """Same request shape as the Stage 1 handler: no temperature, no effort, maxTokens 1024."""
    global _client, SPENT
    import boto3  # only needed for this backend
    p = price_for(model)
    _client = _client or boto3.client("bedrock-runtime", region_name="us-east-1")
    req = dict(modelId=model, system=[{"text": SYSTEM}],
               messages=[{"role": m["role"], "content": [{"text": m["text"]}]} for m in msgs],
               inferenceConfig={"maxTokens": 1024})
    t = time.time()
    r = _client.converse(**req)
    content = r["output"]["message"]["content"]
    text = "".join(b.get("text", "") for b in content)
    call_bedrock.last_reasoning_chars = sum(
        len(b["reasoningContent"].get("reasoningText", {}).get("text", "")) for b in content if "reasoningContent" in b)
    u = r["usage"]
    usd = usage_usd(u, p)
    SPENT += usd
    call_bedrock.last_cache = (u.get("cacheReadInputTokens", 0), u.get("cacheWriteInputTokens", 0))
    total = ledger_add(usd, f"eval {model}")
    if total > BUDGET_USD:
        raise SystemExit(f"project budget ${BUDGET_USD} exceeded (ledger ${total:.4f}); stopping")
    call_bedrock.last_stop = r.get("stopReason")
    return text, u["inputTokens"], u["outputTokens"], time.time() - t


def grade(item, answer):
    a = answer.lower().replace("\u202f", " ").replace("\u2011", "-")
    if item.get("refuse"):
        ok = any(m in a for m in REFUSAL_MARKERS)
        return ok, "refused" if ok else "did not refuse"
    for group in item.get("must", []):
        if not any(k.lower() in a for k in group):
            return False, f"missing one of {group}"
    for f in item.get("forbid", []):
        if f.lower() in a:
            return False, f"contains forbidden '{f}'"
    if item.get("japanese") and not re.search(r"[぀-ヿ]", answer):
        return False, "not answered in Japanese"
    return True, "ok"


def main():
    backend, model = sys.argv[1], sys.argv[2]
    dry = "--dry-run" in sys.argv
    if dry:
        # ~4 chars/token is a rough estimate; the real meter is the usage block.
        tin = sum((len(SYSTEM) + sum(len(m["text"]) for m in build_messages(i))) / 4 for i in QUESTIONS)
        tout = 400 * len(QUESTIONS)  # worst case at our cap, thinking tokens excluded
        p = price_for(model)
        print(f"{len(QUESTIONS)} calls, ~{tin:,.0f} input tokens, <= {tout:,} output tokens")
        if p:
            print(f"estimated cost <= ${tin/1e6*p['in'] + tout/1e6*p['out']:.4f}")
        return
    if backend == "bedrock":
        price_for(model)
        if not BUDGET_USD:
            raise SystemExit("pass --budget=<ledger total in USD at which to stop>")
    call = {"ollama": call_ollama, "bedrock": call_bedrock}[backend]
    out = HERE / "results" / f"{backend}-{re.sub(r'[^A-Za-z0-9.-]', '_', model)}-seed{SEED}{TAG}.jsonl"
    out.parent.mkdir(exist_ok=True)
    passed, tin, tout = 0, 0, 0
    with out.open("w") as f:
        for item in QUESTIONS:
            ans, i_tok, o_tok, sec = call(model, build_messages(item))
            ok, why = grade(item, ans)
            passed += ok; tin += i_tok; tout += o_tok
            f.write(json.dumps({"id": item["id"], "cat": item["cat"], "q": item["q"], "answer": ans,
                                "auto_pass": ok, "auto_reason": why, "in": i_tok, "out": o_tok,
                                "stop": getattr(call, "last_stop", None),
                                "reasoning_chars": getattr(call, "last_reasoning_chars", None),
                                "cache_read": getattr(call, "last_cache", (0, 0))[0],
                                "cache_write": getattr(call, "last_cache", (0, 0))[1],
                                "sec": round(sec, 2)}, ensure_ascii=False) + "\n")
            print(f"{item['id']} {'PASS' if ok else 'FAIL'} ({why}) {sec:.1f}s")
    print(f"\nauto-graded: {passed}/{len(QUESTIONS)}  tokens in={tin} out={tout}  cost=${SPENT:.4f}  -> {out}")


if __name__ == "__main__":
    main()
