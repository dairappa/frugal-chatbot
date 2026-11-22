#!/usr/bin/env python3
"""Generate the article's tables from prices.json, figures.json and ../eval/scores.json.

    python3 render_tables.py           # rewrite every <!-- table:NAME --> ... <!-- /table --> block
    python3 render_tables.py --check   # exit 1 if any block in the article is stale
"""
import json, pathlib, re, sys

HERE = pathlib.Path(__file__).parent
ARTICLE = HERE.parent.parent / "article.md"
P = json.loads((HERE / "prices.json").read_text())
F = json.loads((HERE / "figures.json").read_text())["usd"]
S = json.loads((HERE.parent / "eval" / "scores.json").read_text())["models"]

usd = lambda v: f"${v:,.2f}" if v < 1000 else f"${v:,.0f}"


def rate(v):
    """A per-1M-token price with at least two decimals: $0.30, $1.125, $15.00."""
    whole, frac = f"{v:.3f}".rstrip("0").split(".")
    return f"${whole}.{frac.ljust(2, '0')}"

# What went wrong, per model, in run 1 (details in ../eval/graded.json)
WHAT = {
    "kimi_k3": "nothing",
    "kimi_k25": "one answer in French",
    "kimi_k2_thinking": "reasoning text shown on all four follow-ups; one empty answer at the 1,024-token cap",
    "deepseek_v32": "\"Yes, you can get a full refund\" after three weeks; sent a user to Export to recover notes; two answers in Spanish and French",
    "glm47": "said it didn't know the Android requirement",
    "qwen3_next": "invented a no-student-discount policy and an Evernote workaround; promised help \"immediately\"; said in Japanese that the reset link arrives within 30 minutes",
    "llama4_maverick": "nothing (but see below)",
    "gpt_oss_120b": "said in Japanese that the reset link arrives within 30 minutes",
    "glm47_flash": "told a user their note from yesterday was gone; two false refusals",
    "gemma3_27b": "nothing",
    "gpt_oss_20b": "escalated the angry customer without mentioning Trash",
    "gemma3_4b": "\"Yes\" to a refund after three weeks; four false refusals",
}


def shelf():
    rows = ["| Model | $/month at the budget (1,000 in / 400 out) | $/month with measured output | Floor test | Confidently wrong | What went wrong |",
            "|---|---|---|---|---|---|"]
    for k in sorted(P["open"], key=lambda k: -F[f"ladder.{k}"]):   # most expensive first
        s = S[k]
        rows.append(f"| {s['name']} | {usd(F[f'ladder.{k}'])} | {usd(F[f'measured_ladder.{k}'])} | "
                    f"{s['pass']}/30 | {s['wrong']} | {WHAT[k]} |")
    return rows


def yardsticks():
    rows = ["| Proprietary model (list price) | $ per 1M tokens in / out | $/month at the budget |",
            "|---|---|---|"]
    for k, m in P["yardsticks"].items():
        if not k.startswith("_"):
            rows.append(f"| {m['name']} | {rate(m['in'])} / {rate(m['out'])} | {usd(F[f'ladder.{k}'])} |")
    return rows


def external():
    e = P["external"]
    k26, ds = e["kimi_k26_moonshot"], e["deepseek_flash"]
    return ["| Model, where | $ per 1M tokens in / out | $/month at the budget | What you need |",
            "|---|---|---|---|",
            f"| {k26['name']} | {rate(k26['in'])} / {rate(k26['out'])} | {usd(F['ladder.kimi_k26_moonshot'])} | {k26['key']} |",
            f"| DeepSeek V4.1-Flash, DeepSeek API, peak | {rate(ds['in'])} / {rate(ds['out'])} | {usd(F['ladder.deepseek_flash'])} | {ds['key']} |",
            f"| DeepSeek V4.1-Flash, DeepSeek API, off-peak | {rate(ds['offpeak']['in'])} / {rate(ds['offpeak']['out'])} | "
            f"{usd(F['ladder.deepseek_flash_offpeak'])} | {ds['key']} |"]


def scale():
    keys = ("kimi_k3", "kimi_k25", "gpt_oss_120b", "gpt_oss_20b", "gemma3_4b")
    names = {k: S[k]["name"] for k in keys}
    rows = ["| Chats per month | " + " | ".join(names[k] for k in keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for n, pre in ((10_000, "ladder"), (100_000, "scale100000"), (1_000_000, "scale1000000")):
        rows.append(f"| {n:,} | " + " | ".join(usd(F[f"{pre}.{k}"]) for k in keys) + " |")
    return rows


def worst():
    keys = ("gpt_oss_20b", "kimi_k25", "kimi_k3")
    head = " | ".join(S[k]["name"] for k in keys)
    return [f"| Concurrency 2, one call every 3 s per slot, all month | {head} |", "|---|---|---|---|",
            "| Average chats (1,000 in / 400 out) | " + " | ".join(usd(F[f"ceiling.avg.{k}"]) for k in keys) + " |",
            "| Chats at the handler's caps (~4,700 in / 1,024 out) | " + " | ".join(usd(F[f"ceiling.capped.{k}"]) for k in keys) + " |",
            "| With a 500-chat daily quota, average chats | " + " | ".join(usd(F[f"quota.avg.{k}"]) for k in keys) + " |",
            "| With a 500-chat daily quota, every chat at the caps | " + " | ".join(usd(F[f"quota.capped.{k}"]) for k in keys) + " |"]


def browser():
    rows = ["| Model | Floor test | Confidently wrong | Other failures (false refusals, off-topic answers, no answer) |",
            "|---|---|---|---|"]
    for k in ("gemma3_4b", "llama32_3b", "llama32_1b"):
        s = S[k]
        where = " (Bedrock)" if k == "gemma3_4b" else " (local)"
        rows.append(f"| {s['name']}{where} | {s['pass']}/30 | {s['wrong']} | {s['other']} |")
    return rows


TABLES = {"shelf": shelf, "yardsticks": yardsticks, "external": external, "scale": scale, "worst": worst, "browser": browser}

if __name__ == "__main__":
    text = ARTICLE.read_text()
    def sub(m):
        return f"<!-- table:{m.group(1)} -->\n" + "\n".join(TABLES[m.group(1)]()) + "\n<!-- /table -->"
    new = re.sub(r"<!-- table:(\w+) -->.*?<!-- /table -->", sub, text, flags=re.S)
    if "--check" in sys.argv:
        stale = new != text
        print("tables: stale, run render_tables.py" if stale else "tables: up to date")
        sys.exit(1 if stale else 0)
    ARTICLE.write_text(new)
    print("tables rendered:", ", ".join(re.findall(r"<!-- table:(\w+) -->", new)))
