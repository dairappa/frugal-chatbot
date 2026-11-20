#!/usr/bin/env python3
"""Live checks of the Converse behaviours the Stage 1 handler depends on (needs AWS).

For each model, one call per case:
  assistant_first  history that starts with an assistant turn (what history[-6:] produces on turn 4)
  temperature      inferenceConfig.temperature = 0.7
  effort           outputConfig.effort = "low"
Writes behavior_results.json and adds the cost of every call to ledger.json.
"""
import json, pathlib
import boto3, botocore
from run_eval import SYSTEM, PRICES, ledger_add, usage_usd

HERE = pathlib.Path(__file__).parent
MODELS = ["global.moonshotai.kimi-k3", "moonshotai.kimi-k2.5", "openai.gpt-oss-120b-1:0",
          "google.gemma-3-27b-it", "openai.gpt-oss-20b-1:0"]
U = lambda t: {"role": "user", "content": [{"text": t}]}
A = lambda t: {"role": "assistant", "content": [{"text": t}]}
CASES = {
    "assistant_first": dict(messages=[A("Deleted notes go to Trash."), U("And how do I undo that?")]),
    "temperature": dict(messages=[U("How much is Plus?")], inferenceConfig={"maxTokens": 1024, "temperature": 0.7}),
    "effort": dict(messages=[U("How much is Plus?")], outputConfig={"effort": "low"}),
}
c = boto3.client("bedrock-runtime", region_name="us-east-1")
out = {}
for model in MODELS:
    for case, extra in CASES.items():
        req = {"modelId": model, "system": [{"text": SYSTEM}], "inferenceConfig": {"maxTokens": 1024}, **extra}
        try:
            r = c.converse(**req)
            ledger_add(usage_usd(r["usage"], PRICES[model]), f"behavior_checks {model} {case}")
            text = "".join(b.get("text", "") for b in r["output"]["message"]["content"])
            res = {"ok": True, "stop": r["stopReason"], "text": " ".join(text.split())[:160]}
        except botocore.exceptions.ClientError as e:
            res = {"ok": False, "error": e.response["Error"]["Code"], "message": e.response["Error"]["Message"][:200]}
        out[f"{model} {case}"] = res
        print(f"{model:<32} {case:<16} {json.dumps(res, ensure_ascii=False)[:200]}")
(HERE / "behavior_results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
