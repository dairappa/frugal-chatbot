# frugal-chatbot

Companion repository for the article **"The Frugal Chatbot"**
(current title in `article-final.md`: *"$120, $60, $3… Where Does the Chatbot Bill Stop?"*).

The article walks an AWS support chatbot down the model shelf, from Claude Opus 5.5 on
Amazon Bedrock to a small model running in the visitor's browser with WebGPU. At each
step it asks what the bot costs and whether it still does its job. This repository holds
the article drafts and the code and data behind every number in the article.

## Contents

| Path | What it is |
|---|---|
| `article-final.md` | The article as it stands now, with the Bedrock evaluation results. |
| `editor-notes.md` | Editing notes for `article-final.md`: headline options, method notes, and verification status. Not part of the article. |
| `article.md` | An earlier draft (Step 1–7 structure). Kept for reference. |
| `review.md` | Review notes on the draft (Japanese). |
| `demo/faq.md` | The shared system prompt and FAQ that every stage and every eval uses. |
| `demo/stage1/` | Stage 1 backend: a Lambda handler that calls Bedrock Converse, with offline tests. |
| `demo/stage5/` | Stage 5: a static WebLLM page that runs the model in the browser, plus a smoke-test log. |
| `demo/cost/` | The cost calculator that recomputes every dollar figure in the article. |
| `demo/eval/` | The 30-question "floor" eval, its results, and live Bedrock behaviour checks. |
| `figures/` | Figures for the article: the eval chart and the generated header image. |
| `demo/pricing/` | Raw AWS Price List API dumps (us-east-1) that `demo/cost/prices.json` was checked against. |

## Requirements

- Python 3.11 or later.
- `boto3` for the Bedrock scripts, and `pytest` for the Stage 1 tests:

  ```sh
  python3 -m venv .venv && . .venv/bin/activate
  pip install boto3 pytest
  ```

- AWS credentials with Bedrock access, only for the scripts marked "needs AWS" below.
- [Ollama](https://ollama.com/), only for the local eval backend.

## The checks

### Stage 1: Lambda handler (`demo/stage1/`)

`handler.py` is the Stage 1 backend. It caps the request size before any token is spent,
trims the history so that it starts with a user turn, and enforces a daily quota in DynamoDB.
`test_handler.py` checks it offline. botocore's `Stubber` validates every request against the
real Bedrock Runtime and DynamoDB API schemas, so no AWS credentials are needed.

```sh
cd demo/stage1
pytest -q
```

### Cost figures (`demo/cost/`)

`prices.json` holds the per-token prices (USD per 1M tokens, us-east-1 on-demand).
`calc.py` recomputes every dollar figure in the article from those prices and writes
`figures.json`. `check_article.py` lists every `$` amount in `article-final.md` and reports
any amount that `calc.py` did not produce.

```sh
cd demo/cost
python3 calc.py
python3 check_article.py   # exits 1 if any $ amount in the article is unmatched
```

### Floor eval (`demo/eval/`)

`questions.json` has 30 fixed questions: FAQ answers, out-of-scope requests, tone,
multi-turn follow-ups, and Japanese. `run_eval.py` sends them to one model with the same system prompt
and FAQ, auto-grades the answers, and writes them to `results/*.jsonl`. `grades.md` has the
hand grades and explains where the auto-grader is too generous.

```sh
cd demo/eval
# Local model through Ollama (a proxy for the in-browser rung)
python3 run_eval.py ollama llama3.2:1b-instruct-q4_K_M --seed=1

# Bedrock (needs AWS). --dry-run prints the estimated cost and exits.
python3 run_eval.py bedrock us.amazon.nova-micro-v1:0 --dry-run
python3 run_eval.py bedrock us.amazon.nova-micro-v1:0 --budget=0.60
```

`behavior_checks.py` (needs AWS) makes live Converse calls to check the API behaviours the
article depends on, and prints the token usage of every call. The results are in
`behavior_results.json`. `ledger.json` records what the live Bedrock calls cost.

```sh
python3 behavior_checks.py
```

### Stage 5: model in the browser (`demo/stage5/`)

A static chat page that loads a small model with [WebLLM](https://github.com/mlc-ai/web-llm)
and runs it on the visitor's GPU through WebGPU. `serve.py` serves the page and appends the
page's progress events to `smoke.log`.

```sh
cd demo/stage5
python3 serve.py 8765
# open http://127.0.0.1:8765/  (optional: ?model=<WebLLM model id>, ?autotest=<question>)
```

`SMOKE.md` records the smoke test on one machine. The model loaded, but that GPU never
produced an answer.

## Notes

- Prices and model IDs were checked on 2026-11-19. Check them again for your Region before
  you rely on them.
- The eval grades were made by an AI assistant, as `grades.md` explains. Spot-check them
  before you reuse the numbers.

## License

MIT. See `LICENSE`.
