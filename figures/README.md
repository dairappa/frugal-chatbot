# figures/: tests for adding figures to the article (2026-11-19)

## Route 1: code-generated (Claude Code only)

    python3 figures/make_figures.py

- `ladder.svg` / `ladder.png`: the price ladder ($120 → $60 → $3 → $1.56 → $0.91) with a zoom panel for the bottom three rungs. Reads `demo/cost/figures.json` (calc.py output).
- `eval30.svg` / `eval30.png`: the 30-question floor test. Hand grades for Llama 3.2 1B and 3B (the same figures as the article table), with one cell per question. Data is copied from `demo/eval/grades.md`, and an assert checks the totals against the article (13/11/6 and 23/3/4).
- Reruns produce identical bytes. SVG text is drawn as paths, so the reader needs no fonts.

## Route 2: Bedrock image generation (Stability AI, us-west-2)

    uv run --no-project --with boto3 python3 figures/gen_hero.py core   # $0.04
    uv run --no-project --with boto3 python3 figures/gen_hero.py sd35   # $0.08

- `hero-core.png`: Stable Image Core, 2016x1152, 3.6 s.
- `hero-sd35.png`: SD3.5 Large, 1344x768, 7.3 s.
- Same prompt and seed for both (see `hero_log.jsonl`). The prompt deliberately asks for the prices to be drawn on the steps.
- Cost: 2 images × list price = $0.12. The list prices were confirmed with the Price List API (AWS Marketplace usage, us-west-2). This is not yet a billed amount.
