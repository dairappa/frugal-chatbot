#!/usr/bin/env python3
"""One Converse call per candidate model (needs AWS): does it answer, and what does one FAQ answer cost?

    python3 probe_models.py            # every model in ../cost/prices.json "open"
    python3 probe_models.py kimi_k25   # just one
Appends each call's cost to ledger.json and writes probe_results.json.
"""
import json, sys, time, pathlib
import boto3
from run_eval import SYSTEM, PRICES, ledger_add, usage_usd

HERE = pathlib.Path(__file__).parent
OPEN = json.loads((HERE.parent / "cost" / "prices.json").read_text())["open"]
keys = sys.argv[1:] or list(OPEN)
brt = boto3.client("bedrock-runtime", region_name="us-east-1")
out_path = HERE / "probe_results.json"
results = json.loads(out_path.read_text()) if out_path.exists() else {}
for k in keys:
    m = OPEN[k]["bedrock"]
    t = time.time()
    try:
        r = brt.converse(modelId=m, system=[{"text": SYSTEM}],
                         messages=[{"role": "user", "content": [{"text": "I bought Plus three weeks ago. Can I still get a refund?"}]}],
                         inferenceConfig={"maxTokens": 1024})
    except Exception as e:
        results[k] = {"model": m, "error": f"{type(e).__name__}: {e}"[:300]}
        print(k, "ERROR", results[k]["error"])
        continue
    c = r["output"]["message"]["content"]
    text = "".join(b.get("text", "") for b in c)
    reasoning = sum(len(b["reasoningContent"].get("reasoningText", {}).get("text", "")) for b in c if "reasoningContent" in b)
    u, p = r["usage"], PRICES[m]
    usd = usage_usd(u, p)
    ledger_add(usd, f"probe {m}")
    results[k] = {"model": m, "in": u["inputTokens"], "out": u["outputTokens"], "stop": r["stopReason"],
                  "reasoning_chars": reasoning, "sec": round(time.time() - t, 2), "usd": round(usd, 6), "answer": text}
    print(f"{k:<16} in={u['inputTokens']:<5} out={u['outputTokens']:<5} stop={r['stopReason']:<10} reasoning={reasoning:<5} {time.time()-t:5.1f}s  {text[:110]!r}")
out_path.write_text(json.dumps(results, indent=1, ensure_ascii=False))
