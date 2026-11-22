# figures/

    python3 figures/make_figures.py

All three figures are generated from the data the article's numbers come from; nothing is typed in by hand.

- `shelf.svg` / `shelf.png`: monthly model cost for 10,000 chats (log scale) for the twelve open-weight models, at the 1,000-in / 400-out budget and at the output each model actually wrote, with the hand-graded floor-test score. Reads `demo/cost/figures.json`, `demo/cost/prices.json` and `demo/eval/scores.json`.
- `eval30.svg` / `eval30.png`: every model, every question, run 1, from `demo/eval/graded.json`. An assert checks that the grid agrees with `scores.json`.
- `architecture.svg` / `architecture.png`: the bot's architecture (browser path and server path), each part colored by who pays. Every dollar amount is read from `demo/cost/figures.json` (`infra.kimi_k3.*`, `static.10000_visits`, `selfhost.1b.*`, `quota.capped.*`, the open-weight `ladder.*` range) and printed at the article's precision; costs with no figure are drawn as labels without numbers. The 705 MB download size is the WebLLM 0.2.89 figure the article quotes.
- Reruns produce identical bytes. SVG text is drawn as paths, so the reader needs no fonts.
- On NixOS, run it with the system `python3` (which has matplotlib); pip wheels of numpy can't find `libstdc++` there.

The generated header images of the first edition (Stable Image Core / SD3.5) were removed: the prices drawn on them were the old Claude ladder.
