#!/bin/sh
# Three runs of the 30-question eval on every open-weight model in ../cost/prices.json (needs AWS).
# BUDGET is the project-wide ledger total (USD) at which every run stops.
BUDGET=${BUDGET:?set BUDGET}
for id in $(python3 -c 'import json;print(" ".join(m["bedrock"] for m in json.load(open("../cost/prices.json"))["open"].values()))'); do
  ( for seed in 1 2 3; do
      uv run --no-project --with boto3 python3 run_eval.py bedrock "$id" --seed=$seed --budget=$BUDGET > "logs/$id-seed$seed.log" 2>&1
    done ) &
done
wait
