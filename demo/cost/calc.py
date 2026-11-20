#!/usr/bin/env python3
"""Recompute every dollar figure in the Frugal Chatbot article. Writes figures.json.

All prices are list prices from prices.json. No free tier is subtracted anywhere.
Measured token counts come from the eval results (../eval/results/bedrock-<model>-seed{1,2,3}.jsonl).
"""
import json, pathlib, re, statistics

HERE = pathlib.Path(__file__).parent
RESULTS = HERE.parent / "eval" / "results"
P = json.loads((HERE / "prices.json").read_text())
OPEN, YARD, AWS = P["open"], P["yardsticks"], P["aws"]
EXT = {k: v for k, v in P["external"].items() if not k.startswith("_")}
YARD = {k: v for k, v in YARD.items() if not k.startswith("_")}
ALL = {**OPEN, **YARD, **EXT}
CHATS, IN, OUT = 10_000, 1_000, 400
MONTH_S = 30 * 24 * 3600
F = {"usd": {}, "other": {}}   # check_article.py matches $ amounts against "usd" only


def put(key, val, note="", usd=True):
    F["usd" if usd else "other"][key] = round(val, 6)
    print(f"{key:<48} {'$' if usd else ' '}{val:>14,.4f}  {note}")


def per_chat(p, tin=IN, tout=OUT, cached=0, hit=1.0):
    """USD for one chat. cached = static prefix tokens behind a cache point; hit = cache hit rate."""
    prefix = cached * (hit * p["cr"] + (1 - hit) * p["cw"]) if cached else 0.0
    return ((tin - cached) * p["in"] + prefix + tout * p["out"]) / 1e6


def measured(key):
    """Mean tokens and latency per answer over the three eval runs of one model."""
    safe = re.sub(r"[^A-Za-z0-9.-]", "_", OPEN[key]["bedrock"])
    rows = [json.loads(l) for s in (1, 2, 3)
            for l in (RESULTS / f"bedrock-{safe}-seed{s}.jsonl").read_text().splitlines()]
    tin = statistics.mean(r["in"] + r.get("cache_read", 0) + r.get("cache_write", 0) for r in rows)
    return {"n": len(rows), "in": tin, "out": statistics.mean(r["out"] for r in rows),
            "out_max": max(r["out"] for r in rows), "sec": statistics.mean(r["sec"] for r in rows),
            "max_tokens_stops": sum(r["stop"] == "max_tokens" for r in rows)}


print("== List-price ladder (10,000 chats, 1,000 in / 400 out) ==")
for k, p in ALL.items():
    put(f"ladder.{k}", per_chat(p) * CHATS, f"{p['name']}: ${per_chat(p):.6f}/chat")
put("ladder.deepseek_flash_offpeak", per_chat(EXT["deepseek_flash"]["offpeak"]) * CHATS)
for n in (100_000, 1_000_000):
    for k in ("kimi_k3", "kimi_k25", "gpt_oss_120b", "gpt_oss_20b", "gemma3_4b", "opus55", "haiku55"):
        put(f"scale{n}.{k}", per_chat(ALL[k]) * n)

print("\n== Measured tokens per answer (3 runs x 30 questions) ==")
M = {}
for k in OPEN:
    M[k] = m = measured(k)
    put(f"measured.{k}.out", m["out"], f"in {m['in']:.0f}, out max {m['out_max']}, {m['sec']:.1f} s, "
        f"{m['max_tokens_stops']} max_tokens stops, n={m['n']}", usd=False)
    put(f"measured.{k}.in", m["in"], usd=False)
    put(f"measured.{k}.sec", m["sec"], usd=False)
    put(f"measured.{k}.out_max", m["out_max"], usd=False)
    put(f"measured.{k}.n", m["n"], usd=False)
    put(f"measured.{k}.max_tokens_stops", m["max_tokens_stops"], usd=False)
    # The budget's 1,000 input tokens stay (real chats carry history); output is what the model really wrote.
    put(f"measured_ladder.{k}", per_chat(OPEN[k], IN, m["out"]) * CHATS, "1,000 in / measured out")
    put(f"measured.{k}.out_vs_budget", m["out"] / OUT, usd=False)

print("\n== Lever: output tokens (reasoning models write more of them) ==")
for k in ("kimi_k3", "kimi_k2_thinking", "gpt_oss_120b", "gpt_oss_20b", "kimi_k25"):
    put(f"output_share.{k}", 1 - per_chat(OPEN[k], IN, 0) / per_chat(OPEN[k], IN, M[k]["out"]),
        "share of the measured bill that is output tokens", usd=False)

print("\n== Lever: caching. Kimi K3 caches the prompt by itself on Bedrock (measured, see the eval results) ==")
K3 = OPEN["kimi_k3"]
rows = [json.loads(l) for s in (1, 2, 3)
        for l in (RESULTS / f"bedrock-global.moonshotai.kimi-k3-seed{s}.jsonl").read_text().splitlines()]
put("cache.kimi_k3.calls_with_read", sum(r["cache_read"] > 0 for r in rows), usd=False)
put("cache.kimi_k3.calls_with_write", sum(r["cache_write"] > 0 for r in rows), usd=False)
put("cache.kimi_k3.mean_read", statistics.mean(r["cache_read"] for r in rows), usd=False)
put("cache.kimi_k3.calls", len(rows), usd=False)
put("cache.kimi_k3_600.0", per_chat(K3) * CHATS, "no hits")
put("cache.kimi_k3_600.100", per_chat(K3, cached=600, hit=1.0) * CHATS, "600 of 1,000 input tokens read from cache on every chat")

print("\n== Lever: history ==")
for k in ("kimi_k3", "kimi_k25"):
    put(f"history.{k}_5x_input", per_chat(OPEN[k], tin=5 * IN) * CHATS)

print("\n== Supporting cast at list price (10,000 chats) ==")
# Per chat: 1 Lambda invocation (256 MB, as long as the model call), 1 DynamoDB write (the quota counter),
# 4 CloudFront HTTPS requests (page, script, FAQ, API call) and ~0.1 MB of static transfer.
def infra(sec):
    return {"lambda": CHATS * (AWS["lambda_per_request"] + sec * 0.25 * AWS["lambda_gb_s"]),
            "ddb": CHATS * AWS["ddb_write_per_unit"],
            "cloudfront": CHATS * (4 * AWS["cloudfront_per_https_request"] + 0.1 / 1024 * AWS["cloudfront_per_gb"])}
for k in ("kimi_k3", "kimi_k25", "gpt_oss_20b"):
    parts = infra(M[k]["sec"])
    for part, usd in parts.items():
        put(f"infra.{k}.{part}", usd)
    put(f"infra.{k}.total", sum(parts.values()), f"at {M[k]['sec']:.1f} s per call")

print("\n== Worst case: reserved concurrency 2, abuse 24/7, one call every 3 s per slot ==")
calls = 2 * MONTH_S / 3
put("ceiling.calls", calls, usd=False)
put("ceiling.lambda", 2 * 0.25 * MONTH_S * AWS["lambda_gb_s"] + calls * AWS["lambda_per_request"],
    "two slots busy all month, no free tier")
# Capped chat: 16,000-byte body (~4 bytes/token) + ~700-token system prompt in; maxTokens 1,024 out.
CAP_IN, CAP_OUT = 16_000 // 4 + 700, 1_024
WORST = ("kimi_k3", "kimi_k25", "gpt_oss_20b")
for k in WORST:
    put(f"ceiling.avg.{k}", calls * per_chat(OPEN[k]))
    put(f"ceiling.capped.{k}", calls * per_chat(OPEN[k], CAP_IN, CAP_OUT))
QUOTA = 500
put("quota.ddb_month", QUOTA * 30 * AWS["ddb_write_per_unit"])
for k in WORST:
    put(f"quota.avg.{k}", QUOTA * 30 * per_chat(OPEN[k]))
    put(f"quota.capped.{k}", QUOTA * 30 * per_chat(OPEN[k], CAP_IN, CAP_OUT))
# Rejected calls still run Lambda and still attempt the conditional write.
put("quota.rejected_overhead", calls * (AWS["lambda_per_request"] + AWS["ddb_write_per_unit"]
                                        + 0.05 * 0.25 * AWS["lambda_gb_s"]), "50 ms per rejected call")

print("\n== The last rung: static delivery at list price ==")
put("static.10000_visits", CHATS * (3 * AWS["cloudfront_per_https_request"] + 0.1 / 1024 * AWS["cloudfront_per_gb"]),
    "page, script, FAQ; no API call")
for gb, label in ((0.705, "1b"), (1.8, "3b")):
    for visitors in (2_000, 10_000):
        tgb = visitors * gb   # CloudFront: $0.085/GB for the first 10 TB, $0.080/GB for the next 40 TB
        put(f"selfhost.{label}.{visitors}", min(tgb, 10_240) * AWS["cloudfront_per_gb"]
            + max(0, tgb - 10_240) * AWS["cloudfront_per_gb_10tb_to_50tb"])
        put(f"selfhost.{label}.{visitors}.tb", visitors * gb / 1000, usd=False)

(HERE / "figures.json").write_text(json.dumps(F, indent=1) + "\n")
