#!/usr/bin/env python3
"""Draw the article's data figures as SVG + PNG.

Reads demo/cost/figures.json and prices.json (written and kept by demo/cost/), demo/eval/scores.json,
demo/eval/graded.json and demo/eval/questions.json. Never runs calc.py or score.py.

    python3 figures/make_figures.py      # writes figures/shelf.{svg,png}, figures/eval30.{svg,png}

Output is byte-stable across runs (fixed SVG hash salt, no date metadata).
"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "figures"
FIG = json.loads((ROOT / "demo/cost/figures.json").read_text())["usd"]
PRICES = json.loads((ROOT / "demo/cost/prices.json").read_text())
SCORES = json.loads((ROOT / "demo/eval/scores.json").read_text())["models"]
GRADED = json.loads((ROOT / "demo/eval/graded.json").read_text())["models"]
QUESTIONS = json.loads((ROOT / "demo/eval/questions.json").read_text())

# Palette: dataviz skill reference instance (light mode).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES_1 = "#2a78d6"
GOOD, CRITICAL, WARNING, NEUTRAL = "#0ca30c", "#d03b3b", "#c27a00", "#8a8984"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "svg.fonttype": "path",   # portable: no font needed on the reader's side
    "svg.hashsalt": "frugal-chatbot",
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "text.color": INK,
    "text.parse_math": False,   # "$90" is money, not math
})


def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, metadata={"Date": None} if ext == "svg" else {"Software": None},
                    bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"wrote figures/{name}.svg, figures/{name}.png")


def money(v):
    return f"${v:,.0f}" if v >= 10 else f"${v:,.2f}"


# --- Figure 1: the open-weight shelf, price against the floor test (Stage 2) ----
def shelf():
    keys = sorted(PRICES["open"], key=lambda k: -FIG[f"ladder.{k}"])
    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    for row, k in enumerate(keys):
        budget, measured = FIG[f"ladder.{k}"], FIG[f"measured_ladder.{k}"]
        ax.plot([min(budget, measured), max(budget, measured)], [row, row], color=AXIS, lw=2, zorder=1)
        ax.scatter([budget], [row], s=54, facecolor=SURFACE, edgecolor=SERIES_1, linewidth=1.8, zorder=3,
                   label="At the budget (1,000 in / 400 out)" if row == 0 else None)
        ax.scatter([measured], [row], s=54, color=SERIES_1, zorder=3,
                   label="With the output each model actually wrote" if row == 0 else None)
        s = SCORES[k]
        color = GOOD if s["pass"] == 30 else CRITICAL if s["wrong"] else INK_2
        ax.text(260, row, f"{s['pass']}/30", ha="left", va="center", fontsize=10, fontweight="bold", color=color)
        ax.text(420, row, f"{s['wrong']} confidently wrong" if s["wrong"] else "", ha="left", va="center",
                fontsize=9, color=CRITICAL)
    for k, label in (("haiku55", "Claude Haiku 5.5"), ("opus55", "Claude Opus 5.5")):
        v = FIG[f"ladder.{k}"]
        ax.axvline(v, color=NEUTRAL, lw=1, ls=(0, (3, 3)), zorder=0)
        ax.text(v, -0.9, f"{label}\n{money(v)} (price only)", ha="center", va="bottom", fontsize=8, color=INK_2)
    ax.set_yticks(range(len(keys)), [SCORES[k]["name"] for k in keys], fontsize=10, color=INK)
    ax.set_ylim(len(keys) - 0.5, -1.2)
    ax.set_xscale("log")
    ax.set_xlim(0.3, 200)
    ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50, 100], ["$0.50", "$1", "$2", "$5", "$10", "$20", "$50", "$100"])
    ax.minorticks_off()
    ax.text(260, -1.0, "Floor test", ha="left", va="center", fontsize=9, color=INK_2)
    ax.set_title("Model cost per month for 10,000 chats, and the 30-question floor test", loc="left",
                 fontsize=12, fontweight="bold", pad=14)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=2, frameon=False, fontsize=9, borderaxespad=0.3)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, -0.08, "Bedrock on-demand list prices, us-east-1, log scale. Floor test = run 1, AI-graded, spot-checked by the author. "
             "Source: demo/cost/calc.py, demo/eval/score.py.", fontsize=8, color=INK_2)
    save(fig, "shelf")


# --- Figure 2: every model, every question (run-1 grades) -----------------------
KINDS = [("pass", "Correct", GOOD, "✓"), ("wrong", "Confidently wrong", CRITICAL, "✗"),
         ("lang", "Wrong language", WARNING, "L"), ("other", "Other failure", NEUTRAL, "–")]


def grade(model, qid):
    return GRADED[model].get(qid, ["pass"])[0]


def eval30():
    ids = [q["id"] for q in QUESTIONS]
    models = sorted(SCORES, key=lambda k: (-SCORES[k]["pass"], SCORES[k]["wrong"]))
    for m in models:   # the grid must agree with scores.json
        s = SCORES[m]
        assert [sum(grade(m, q) == k for q in ids) for k in ("pass", "wrong", "lang", "other")] == \
               [s["pass"], s["wrong"], s["lang"], s["other"]], m

    fig, grid = plt.subplots(figsize=(9.6, 5.8))
    for row, m in enumerate(models):
        for col, q in enumerate(ids):
            k = grade(m, q)
            _, _, color, glyph = next(t for t in KINDS if t[0] == k)
            grid.add_patch(Rectangle((col + 0.06, row + 0.08), 0.88, 0.84, color=color, linewidth=0))
            grid.text(col + 0.5, row + 0.52, glyph, ha="center", va="center", color="white", fontsize=8,
                      fontweight="bold")
        grid.text(len(ids) + 0.4, row + 0.5, f"{SCORES[m]['pass']}/30", ha="left", va="center", fontsize=9,
                  fontweight="bold", color=INK)
    grid.set_xlim(0, len(ids) + 2.2)
    grid.set_ylim(len(models), -0.9)
    where = {"llama32_3b": " (local)", "llama32_1b": " (local)"}
    grid.set_yticks([r + 0.5 for r in range(len(models))],
                    [SCORES[m]["name"] + where.get(m, "") for m in models], fontsize=9, color=INK)
    grid.set_xticks([c + 0.5 for c in range(len(ids))], ids, rotation=90, fontsize=7)
    for label, p in (("A: in the FAQ", "A"), ("B: out of scope", "B"), ("C: follow-up", "C"), ("D: JA / tone", "D")):
        cols = [c for c, q in enumerate(ids) if q.startswith(p)]
        grid.text((cols[0] + cols[-1] + 1) / 2, -0.2, label, ha="center", va="bottom", fontsize=8, color=INK_2)
    for s in grid.spines.values():
        s.set_visible(False)
    grid.tick_params(length=0)
    handles = [Rectangle((0, 0), 1, 1, color=c) for _, _, c, _ in KINDS]
    grid.legend(handles, [f"{g} {n}" for _, n, _, g in KINDS], loc="lower left", bbox_to_anchor=(0, 1.04),
                ncol=4, frameon=False, fontsize=9, handlelength=1.0, borderaxespad=0.2)
    grid.set_title("30-question floor test, run 1, AI-graded against the FAQ, spot-checked by the author", loc="left", fontsize=12,
                   fontweight="bold", pad=34)
    fig.text(0.01, -0.03, "Source: demo/eval/graded.json. Bedrock models in us-east-1; Llama 3.2 on Ollama (Q4_K_M). "
             "D01 = Japanese, D02 = angry customer.", fontsize=8, color=INK_2)
    save(fig, "eval30")


# --- Figure 3: the architecture, and who pays for each part ---------------------
OTHER = json.loads((ROOT / "demo/cost/figures.json").read_text())["other"]
PAYERS = [("you", "You, priced in this article", SERIES_1), ("unpriced", "You, not priced here", WARNING),
          ("visitor", "The visitor", GOOD), ("third", "Someone else", NEUTRAL)]
WEIGHTS_1B_MB = 705   # WebLLM 0.2.89 model list (article, Stage 4); calc.py uses the same 0.705 GB


def usd(v, nd=2):
    """Dollars at the precision the article prints them: $119.85, $0.0873."""
    return f"${v:,.{nd}f}"


def architecture():
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    color = dict((k, c) for k, _, c in PAYERS)
    open_keys = list(PRICES["open"])
    lo, hi = min(FIG[f"ladder.{k}"] for k in open_keys), max(FIG[f"ladder.{k}"] for k in open_keys)
    quota = [FIG[f"quota.capped.{k}"] for k in ("gpt_oss_20b", "kimi_k3")]

    fig, ax = plt.subplots(figsize=(11, 7.4))
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 66.5)
    ax.axis("off")

    def box(x, y, w, h, title, lines, edge=AXIS):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", facecolor="white",
                                    edgecolor=edge, linewidth=1.4))
        ax.text(x + 1.2, y + h - 1.4, title, ha="left", va="top", fontsize=10, fontweight="bold", color=INK)
        for i, (payer, text) in enumerate(lines):
            ty = y + h - 5.0 - i * 2.9
            ax.add_patch(Rectangle((x + 1.2, ty - 0.9), 1.4, 1.8, color=color[payer], linewidth=0))
            ax.text(x + 3.4, ty, text, ha="left", va="center", fontsize=8.2, color=INK if payer == "you" else INK_2)

    def arrow(a, b, text="", style="-|>", ls="-", tx=None, ty=None, ha="center"):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=12, color=INK_2, lw=1.2, linestyle=ls))
        if text:
            ax.text(tx if tx is not None else (a[0] + b[0]) / 2, ty if ty is not None else (a[1] + b[1]) / 2 + 1.2,
                    text, ha=ha, va="bottom", fontsize=8, color=INK_2)

    # Browser
    box(1, 36, 30, 28, "Visitor's browser", [
        ("visitor", "Stage 4: WebLLM runs the model"),
        ("visitor", "  on the visitor's GPU"),
        ("visitor", f"First load: {WEIGHTS_1B_MB} MB (Llama 3.2 1B)"),
        ("visitor", "Battery, GPU memory, waiting"),
        ("visitor", "Older devices: fail or crawl"),
        ("unpriced", "No server-side logs or guardrails"),
        ("unpriced", "System prompt is public"),
        ("unpriced", f"Confidently wrong: {SCORES['llama32_1b']['wrong']} of 30 (1B)"),
    ])
    # Static delivery
    box(42, 49, 30, 15, "CloudFront + S3 (static)", [
        ("you", "Page, script, FAQ"),
        ("you", f"Browser path: {usd(FIG['static.10000_visits'])}/month"),
        ("you", "  (10,000 visits, 3 requests each)"),
    ])
    # Weights
    box(80, 42, 29, 22, "Model weights", [
        ("third", "WebLLM default: Hugging Face"),
        ("third", "  and GitHub pay the transfer"),
        ("you", "On your CloudFront instead:"),
        ("you", f"  {usd(FIG['selfhost.1b.2000'])} to {usd(FIG['selfhost.1b.10000'])}/month (1B,"),
        ("you", "  2,000 to 10,000 new visitors)"),
    ])
    # Server path
    box(42, 18, 30, 21, "CloudFront + OAC → Lambda", [
        ("you", "Stages 1–3, or the fallback"),
        ("you", f"Lambda 256 MB: {usd(FIG['infra.kimi_k3.lambda'], 4)}/month"),
        ("you", f"  (Kimi K3, {OTHER['measured.kimi_k3.sec']:.1f} s per call)"),
        ("you", f"CloudFront: {usd(FIG['infra.kimi_k3.cloudfront'], 3)}/month"),
        ("you", "  (4 requests per chat)"),
        ("unpriced", "Logs of usage: not priced here"),
    ])
    box(80, 22, 29, 17, "Amazon Bedrock", [
        ("you", f"Model: {usd(lo)} to {usd(hi)}/month"),
        ("you", "  (12 models, at the budget)"),
        ("unpriced", "Re-testing when a model"),
        ("unpriced", "  goes Legacy or is retired"),
    ])
    box(42, 1, 30, 13, "DynamoDB: daily quota", [
        ("you", f"Counter: {usd(FIG['infra.kimi_k3.ddb'], 4)}/month"),
        ("you", f"Worst month at 500/day: {usd(quota[0])}"),
        ("you", f"  to {usd(quota[1])}"),
    ])
    box(80, 1, 29, 16, "Off the request path", [
        ("unpriced", "AWS Budgets alert (alarms only)"),
        ("unpriced", "AI grading, human spot-checks"),
        ("unpriced", "Visitor 501 turned away"),
        ("unpriced", "Humans behind the ticket"),
    ])

    arrow((31.5, 58), (41.5, 58), "page", ty=58.6)
    arrow((31.5, 44), (79.5, 44), "weights, once", ty=44.6, tx=78, ha="right")
    arrow((31.5, 37), (41.5, 37), "fallback /", ty=37.6)
    ax.text(36.5, 36.4, "Stages 1–3", ha="center", va="top", fontsize=8, color=INK_2)
    arrow((72.5, 31), (79.5, 31), "Converse", ty=31.6)
    arrow((57, 17.5), (57, 14.5))

    handles = [Rectangle((0, 0), 1, 1, color=c) for _, _, c in PAYERS]
    ax.legend(handles, [n for _, n, _ in PAYERS], title="Who pays", loc="lower left", bbox_to_anchor=(0.0, 0.0),
              ncol=1, frameon=False, fontsize=9, title_fontsize=9, handlelength=1.0, alignment="left")
    ax.set_title("The architecture, and who pays for each part", loc="left", fontsize=12, fontweight="bold", pad=6)
    fig.text(0.01, 0.0, "10,000 chats (or visits) a month, 1,000 in / 400 out. List prices, us-east-1, no free tier. Browser path and server path are alternatives, "
             "not a sum. Source: demo/cost/calc.py.", fontsize=8, color=INK_2)
    save(fig, "architecture")


if __name__ == "__main__":
    shelf()
    eval30()
    architecture()
