#!/usr/bin/env python3
"""Draw the article's data figures as SVG + PNG.

Reads only demo/cost/figures.json (written by demo/cost/calc.py) and
demo/eval/questions.json. Never runs calc.py.

    python3 figures/make_figures.py      # writes figures/ladder.{svg,png}, figures/eval30.{svg,png}

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
FIG = json.loads((ROOT / "demo/cost/figures.json").read_text())
QUESTIONS = json.loads((ROOT / "demo/eval/questions.json").read_text())

# Palette: dataviz skill reference instance (light mode).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES_1 = "#2a78d6"
GOOD, CRITICAL, NEUTRAL = "#0ca30c", "#d03b3b", "#8a8984"

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
    "text.parse_math": False,   # "$117 of $120" is money, not math
})


def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, metadata={"Date": None} if ext == "svg" else {"Software": None},
                    bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"wrote figures/{name}.svg, figures/{name}.png")


def tidy(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def money(v):
    return f"${v:,.0f}" if v >= 10 else f"${v:,.2f}"


# --- Figure 1: the price ladder (Stage 2 of the article) ----------------------
LADDER = ["Claude Opus 5.5", "Claude Sonnet 5.5", "Claude Haiku 5.5", "Amazon Nova Lite", "Amazon Nova Micro"]


def ladder():
    vals = [FIG[f"ladder.{m}"] for m in LADDER]
    labels = [m.replace("Claude ", "").replace("Amazon ", "") for m in LADDER]
    saved = FIG["ladder.saved_first_two_rungs"]

    fig, (ax, zoom) = plt.subplots(1, 2, figsize=(9.6, 4.2), gridspec_kw={"width_ratios": [5, 3], "wspace": 0.28})

    # Main panel: linear, so the drop is shown at its true size.
    x = range(len(vals))
    ax.bar(x, vals, width=0.96, color=SERIES_1, edgecolor=SURFACE, linewidth=2)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, money(v), ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 140)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}")
    ax.set_title("Model cost per month, 10,000 chats", loc="left", fontsize=12, fontweight="bold", pad=22)
    ax.text(0, 1.03, "1,000 input + 400 output tokens per chat, Bedrock on-demand list prices",
            transform=ax.transAxes, fontsize=9, color=INK_2)
    ax.annotate("", xy=(2, vals[2] + 14), xytext=(0, vals[0] + 14),
                arrowprops=dict(arrowstyle="->", color=INK_2, lw=1.2, connectionstyle="arc3,rad=-0.25"))
    ax.text(1.35, 108, f"First two steps down\nsave ${saved:.0f} of ${vals[0]:.0f}",
            ha="left", va="center", fontsize=10, color=INK)
    tidy(ax)

    # Zoom panel: the bottom three rungs, invisible at the main panel's scale.
    zx = range(3)
    zoom.bar(zx, vals[2:], width=0.96, color=SERIES_1, edgecolor=SURFACE, linewidth=2)
    for i, v in enumerate(vals[2:]):
        zoom.text(i, v + 0.06, money(v), ha="center", va="bottom", fontsize=11, fontweight="bold")
    zoom.set_xticks(list(zx), labels[2:])
    zoom.set_ylim(0, 3.5)
    zoom.set_yticks([0, 1, 2, 3])
    zoom.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}")
    zoom.set_title("Zoom: the bottom three rungs", loc="left", fontsize=10, color=INK_2, pad=22)
    tidy(zoom)

    fig.text(0.01, -0.04, "Source: demo/cost/calc.py → figures.json. gpt-oss-20b ($1.90) is not on the ladder.",
             fontsize=8, color=INK_2)
    save(fig, "ladder")


# --- Figure 2: the 30-question floor test (hand grades) ------------------------
# Copied from demo/eval/grades.md, "Results" table (hand-graded, seed 1).
# Every question not listed is a pass. Only these two models have hand grades;
# the Bedrock runs have only the auto-grader, which grades.md says is too generous.
HAND = {
    "Llama 3.2 1B": {
        "wrong": "A06 A09 A10 A14 A16 A17 B03 C02 C03 C04 D01".split(),
        "other": "A04 A05 A12 A18 B05 D02".split(),
        "expect": (13, 11, 6),   # article-final.md table
    },
    "Llama 3.2 3B": {
        "wrong": "A10 B03 D01".split(),
        "other": "A06 A14 C01 D02".split(),
        "expect": (23, 3, 4),
    },
}
KINDS = [("pass", "Correct", GOOD, "✓"), ("wrong", "Confidently wrong", CRITICAL, "✗"),
         ("other", "Other failure", NEUTRAL, "–")]


def grade(model, qid):
    g = HAND[model]
    return "wrong" if qid in g["wrong"] else "other" if qid in g["other"] else "pass"


def eval30():
    ids = [q["id"] for q in QUESTIONS]
    models = list(HAND)
    for m in models:
        counts = tuple(sum(grade(m, q) == k for q in ids) for k, *_ in KINDS)
        assert counts == HAND[m]["expect"], (m, counts)

    fig, (bars, grid) = plt.subplots(2, 1, figsize=(9.6, 4.6), gridspec_kw={"height_ratios": [1.1, 1], "hspace": 0.75})

    # Top: stacked bars, counts labelled inside each segment.
    for row, m in enumerate(models):
        left = 0
        for k, name, color, _ in KINDS:
            n = sum(grade(m, q) == k for q in ids)
            bars.barh(row, n, left=left, height=0.62, color=color, edgecolor=SURFACE, linewidth=2,
                      label=name if row == 0 else None)
            if n:
                bars.text(left + n / 2, row, str(n), ha="center", va="center", color="white", fontsize=11,
                          fontweight="bold")
            left += n
    bars.set_yticks(range(len(models)), models, fontsize=10, color=INK)
    bars.invert_yaxis()
    bars.set_xlim(0, 30)
    bars.set_xticks([0, 10, 20, 30])
    bars.set_title("30-question floor test, graded by hand against the FAQ", loc="left", fontsize=12,
                   fontweight="bold", pad=26)
    bars.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=9,
                handlelength=1.2, borderaxespad=0.2)
    for s in ("top", "right", "left", "bottom"):
        bars.spines[s].set_visible(False)
    bars.tick_params(length=0)

    # Bottom: one cell per question, glyph + color so it reads without color.
    for row, m in enumerate(models):
        for col, q in enumerate(ids):
            k = grade(m, q)
            _, _, color, glyph = next(t for t in KINDS if t[0] == k)
            grid.add_patch(Rectangle((col + 0.06, row + 0.08), 0.88, 0.84, color=color, linewidth=0))
            grid.text(col + 0.5, row + 0.5, glyph, ha="center", va="center", color="white", fontsize=9,
                      fontweight="bold")
    grid.set_xlim(0, len(ids))
    grid.set_ylim(len(models), 0)
    grid.set_yticks([r + 0.5 for r in range(len(models))], models, fontsize=9, color=INK)
    grid.set_xticks([c + 0.5 for c in range(len(ids))], ids, rotation=90, fontsize=7)
    groups = [("A: in the FAQ", "A"), ("B: out of scope", "B"), ("C: follow-up", "C"), ("D: JA / tone", "D")]
    for label, p in groups:
        cols = [c for c, q in enumerate(ids) if q.startswith(p)]
        grid.text((cols[0] + cols[-1] + 1) / 2, -0.25, label, ha="center", va="bottom", fontsize=8, color=INK_2)
    for s in grid.spines.values():
        s.set_visible(False)
    grid.tick_params(length=0)

    fig.text(0.01, -0.06, "Source: demo/eval/grades.md (Ollama, Q4_K_M, seed 1). D01 = Japanese, D02 = tone.",
             fontsize=8, color=INK_2)
    save(fig, "eval30")


if __name__ == "__main__":
    ladder()
    eval30()
