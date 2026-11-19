#!/usr/bin/env python3
"""Live checks of the Converse behaviours the article depends on. Prints usage for every call."""
import json, pathlib, boto3, botocore
c = boto3.client("bedrock-runtime", region_name="us-east-1")
SYSTEM = (pathlib.Path(__file__).parent.parent / "faq.md").read_text()
OUT = {}

def run(name, **req):
    req.setdefault("inferenceConfig", {}).setdefault("maxTokens", 200)
    try:
        r = c.converse(**req)
        u = r["usage"]
        text = "".join(b.get("text", "") for b in r["output"]["message"]["content"])
        OUT[name] = {"ok": True, "usage": u, "stop": r["stopReason"], "text": text[:160]}
    except botocore.exceptions.ClientError as e:
        OUT[name] = {"ok": False, "error": e.response["Error"]["Code"], "message": e.response["Error"]["Message"][:300]}
    print(name, json.dumps(OUT[name], ensure_ascii=False))

U = lambda t: {"role": "user", "content": [{"text": t}]}
A = lambda t: {"role": "assistant", "content": [{"text": t}]}
CLAUDE = {"opus": "global.anthropic.claude-opus-5-5", "haiku": "global.anthropic.claude-haiku-5-5"}

# 1. temperature on Claude 5.5 (Haiku first: cheapest)
for k, m in (("haiku", CLAUDE["haiku"]), ("opus", CLAUDE["opus"])):
    run(f"temperature0.7.{k}", modelId=m, messages=[U("Say OK.")], inferenceConfig={"maxTokens": 50, "temperature": 0.7})
run("temperature0.7.nova-micro", modelId="us.amazon.nova-micro-v1:0", messages=[U("Say OK.")], inferenceConfig={"maxTokens": 50, "temperature": 0.7})

# 2. assistant-first history (what history[-6:] produces from turn 4 on)
hist = [A("a1"), U("q2"), A("a2"), U("q3"), A("a3"), U("How do I reset my password?")]
for k, m in (("haiku", CLAUDE["haiku"]), ("nova-micro", "us.amazon.nova-micro-v1:0")):
    run(f"assistant_first.{k}", modelId=m, system=[{"text": SYSTEM}], messages=hist)

# 3. effort low accepted? and thinking tokens visible in usage
run("effort_low.haiku", modelId=CLAUDE["haiku"], system=[{"text": SYSTEM}], messages=[U("How do I reset my password?")],
    outputConfig={"effort": "low"}, inferenceConfig={"maxTokens": 400})
run("effort_default.haiku", modelId=CLAUDE["haiku"], system=[{"text": SYSTEM}], messages=[U("How do I reset my password?")],
    inferenceConfig={"maxTokens": 400})
run("effort_low.nova-micro", modelId="us.amazon.nova-micro-v1:0", messages=[U("Say OK.")], outputConfig={"effort": "low"})

# 4. caching: our ~600-token prompt vs a >1K prompt, called twice each
big = SYSTEM + "\n" + ("Additional policy note: this paragraph exists only to make the cached prefix longer. " * 60)
for label, sysp in (("small", SYSTEM), ("big", big)):
    for m_label, m in (("nova-micro", "us.amazon.nova-micro-v1:0"), ("haiku", CLAUDE["haiku"])):
        for i in (1, 2):
            run(f"cache.{label}.{m_label}.{i}", modelId=m, system=[{"text": sysp}, {"cachePoint": {"type": "default"}}],
                messages=[U("How do I reset my password?")], inferenceConfig={"maxTokens": 60})

pathlib.Path(__file__).with_name("behavior_results.json").write_text(json.dumps(OUT, indent=1, ensure_ascii=False))
