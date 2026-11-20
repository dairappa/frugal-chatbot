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
    fig.text(0.01, -0.08, "Bedrock on-demand list prices, us-east-1, log scale. Floor test = hand-graded run 1. "
             "Source: demo/cost/calc.py, demo/eval/score.py.", fontsize=8, color=INK_2)
    save(fig, "shelf")


# --- Figure 2: every model, every question (hand grades) -----------------------
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
    grid.set_title("30-question floor test, run 1, graded by hand against the FAQ", loc="left", fontsize=12,
                   fontweight="bold", pad=34)
    fig.text(0.01, -0.03, "Source: demo/eval/graded.json. Bedrock models in us-east-1; Llama 3.2 on Ollama (Q4_K_M). "
             "D01 = Japanese, D02 = angry customer.", fontsize=8, color=INK_2)
    save(fig, "eval30")


if __name__ == "__main__":
    shelf()
    eval30()
