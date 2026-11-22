# frugal-chatbot

Companion repository for the article **"The Frugal Chatbot"**
(current title in `article.md`: *"$90, $18, $3.90… Where Does the Chatbot Bill Stop?"*).

The article walks an AWS support chatbot down the open-weight model shelf on Amazon Bedrock,
from Kimi K3 to Gemma 3 4B, and then to a small model running in the visitor's browser with
WebGPU. Every price is a list price with no free tier subtracted. At each step it asks what the
bot costs and whether it still does its job. This repository holds the article drafts and the
code and data behind every number in the article.

## Contents

| Path | What it is |
|---|---|
| `article.md` | The article (open-weight edition). Earlier editions and drafts are in git history. |
| `editor-notes.md` | Editing notes for `article.md`: headline options, method notes, and verification status. Not part of the article. |
| `review.md` | Review notes on an early draft of the first (Claude) edition (Japanese). That draft is `article.md` at commit `1da2204`. |
| `humanize-check.md` | How the English of the current edition was edited, and with which tools. |
| `demo/faq.md` | The shared system prompt and FAQ that every stage and every eval uses. |
| `demo/stage1/` | Stage 1 backend: a Lambda handler that calls Bedrock Converse, with offline tests. |
| `demo/stage4/` | Stage 4: a static WebLLM page that runs the model in the browser, plus a smoke-test log. |
| `demo/cost/` | The cost calculator that recomputes every dollar figure in the article. |
| `demo/eval/` | The 30-question "floor" eval, its results and hand grades, and live Bedrock behaviour checks. |
| `figures/` | The article's three figures (two charts and an architecture diagram), generated from the same data. |
| `demo/pricing/` | AWS Price List API dumps and a filtered extract (us-east-1), plus the external prices and licenses read from provider pages. |

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

`prices.json` holds the list prices (USD per 1M tokens, us-east-1 on-demand; AWS infrastructure
per unit). `calc.py` recomputes every dollar figure in the article from those prices and the
measured token counts in `../eval/results/`, and writes `figures.json`. `render_tables.py`
writes the article's tables from `figures.json` and `../eval/scores.json`. `check_article.py`
fails if a `$` amount is neither a list price nor a `calc.py` figure, if a score doesn't match
`scores.json`, if a table is stale, or if a sentence announces "three things" and lists four.

```sh
cd demo/cost
python3 calc.py
python3 render_tables.py
python3 check_article.py   # exits 1 on any mismatch
```

### Floor eval (`demo/eval/`)

`questions.json` has 30 fixed questions: FAQ answers, out-of-scope requests, tone,
multi-turn follow-ups, and Japanese. `run_eval.py` sends them to one model with the same system prompt
and FAQ, auto-grades the answers with keywords (a first filter only), and writes them to
`results/*.jsonl`. Run 1 of every model is hand-graded in `graded.json` against the rubric in
`grades.md`; `score.py` turns that into `scores.json`. `grade_view.py` prints every model's
answer to the same question side by side, which is how the grading was done.

```sh
cd demo/eval
# Local model through Ollama (a proxy for the in-browser rung)
python3 run_eval.py ollama llama3.2:1b-instruct-q4_K_M --seed=1

# Bedrock (needs AWS). --dry-run prints the estimated cost and exits.
# --budget is the project-wide ledger total (USD) at which the run stops.
python3 run_eval.py bedrock moonshotai.kimi-k2.5 --dry-run
python3 run_eval.py bedrock moonshotai.kimi-k2.5 --budget=2.00
BUDGET=2.00 ./run_all.sh          # every open-weight model in prices.json, three runs each
python3 score.py
```

`probe_models.py` makes one call per model. `behavior_checks.py` (needs AWS) checks
assistant-first history, `temperature`, and `outputConfig.effort` on five models; results are
in `behavior_results.json`. `ledger.json` records what every live Bedrock call cost.

```sh
python3 behavior_checks.py
```

### Stage 4: model in the browser (`demo/stage4/`)

A static chat page that loads a small model with [WebLLM](https://github.com/mlc-ai/web-llm)
and runs it on the visitor's GPU through WebGPU. `serve.py` serves the page and appends the
page's progress events to `smoke.log`.

```sh
cd demo/stage4
python3 serve.py 8765
# open http://127.0.0.1:8765/  (optional: ?model=<WebLLM model id>, ?autotest=<question>)
```

`SMOKE.md` records the smoke test on one machine. The model loaded, but that GPU never
produced an answer.

## Notes

- Prices, model IDs, and lifecycle status were checked on 2026-11-19/20. Check them again for
  your Region before you rely on them; Llama 4 Maverick went Legacy during the test.
- The eval grades were made by an AI assistant, as `grades.md` explains. Spot-check them
  before you reuse the numbers.

## License

MIT. See `LICENSE`.
