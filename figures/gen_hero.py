#!/usr/bin/env python3
"""Generate one hero-image candidate with a Stability AI model on Bedrock (us-west-2).

    python3 figures/gen_hero.py core   # Stable Image Core, $0.04/image list price
    python3 figures/gen_hero.py sd35   # SD3.5 Large,       $0.08/image list price

Writes figures/hero-<model>.png and appends the request + result to figures/hero_log.jsonl.
Each run is one billed image. Prompt and seed are fixed so a rerun asks for the same image.
"""
import base64
import json
import pathlib
import sys
import time

import boto3

OUT = pathlib.Path(__file__).resolve().parent
MODELS = {
    "core": ("stability.stable-image-core-v1:1", 0.04),
    "sd35": ("stability.sd3-5-large-v1:0", 0.08),
}
# Asks for rendered text on purpose, to test whether the model can draw the ladder's numbers.
PROMPT = (
    "Flat vector editorial illustration for a tech blog header: a friendly small chatbot robot "
    "walking down a wide staircase of five steps. Each step is labeled with a price in large bold "
    "numbers, from top to bottom: \"$120\", \"$60\", \"$3\", \"$1.56\", \"$0.91\". "
    "Soft blue and orange palette, clean white background, minimal, no other text."
)
SEED = 20261119

key = sys.argv[1]
model_id, list_price = MODELS[key]
body = {"prompt": PROMPT, "aspect_ratio": "16:9", "output_format": "png", "seed": SEED}

client = boto3.client("bedrock-runtime", region_name="us-west-2")
t0 = time.time()
resp = client.invoke_model(modelId=model_id, body=json.dumps(body))
sec = round(time.time() - t0, 1)
out = json.loads(resp["body"].read())

finish = out.get("finish_reasons")
images = out.get("images", [])
files = []
for i, b64 in enumerate(images):
    f = OUT / f"hero-{key}{'' if i == 0 else f'-{i}'}.png"
    f.write_bytes(base64.b64decode(b64))
    files.append(f.name)

entry = {
    "date": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model_id, "seed": SEED, "request": body,
    "response_keys": sorted(out), "finish_reasons": finish, "seeds": out.get("seeds"),
    "files": files, "seconds": sec, "list_price_usd": list_price * len(images),
}
with open(OUT / "hero_log.jsonl", "a") as fh:
    fh.write(json.dumps(entry) + "\n")
print(json.dumps(entry, indent=1))
