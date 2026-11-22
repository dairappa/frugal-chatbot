#!/usr/bin/env python3
"""Mechanical checks on article.md. Exits 1 on any failure.

1. Every $ amount is either a list price from prices.json or a figure calc.py produced.
2. Every "N/30" and "N of 30" is a score in ../eval/scores.json.
3. Every table row whose first cell names a graded model shows that model's score in the score columns,
   and every generated table matches render_tables.py.
4. A sentence that announces a count ("Three things ...:", "four details ...:") is followed by
   exactly that many list items, and no paragraph interrupts a list it belongs to.
"""
import json, pathlib, re, sys

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent.parent
figs = list(json.loads((HERE / "figures.json").read_text())["usd"].values())
prices = json.loads((HERE / "prices.json").read_text())
scores = json.loads((HERE.parent / "eval" / "scores.json").read_text())
text = (ROOT / "article.md").read_text()
lines = text.splitlines()
fail = []


def walk(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield float(o)


INPUTS = set(walk({k: v for k, v in prices.items() if k != "aws"}))
INPUTS |= set(walk(prices["aws"])) | {round(x * 1e6, 6) for x in walk(prices["aws"])}   # per unit and per million
# Amounts quoted in the prose that are neither prices nor results, each with where it comes from
QUOTED = {48.0: "gpt-oss-20b's wrong annual price (behavior_results.json)",
          38.40: "the correct annual Plus price: 12 x $4 x 0.8 (faq.md)",
          20.0: "Kimi K3 License ($20 million) revenue threshold (../pricing/external-2026-11-20.md)"}
INPUTS |= set(QUOTED)


def matches(v):
    for f in figs:
        for cand in (f, round(f, 2), round(f), round(f, 1), round(f, 3), round(f, 4)):
            if abs(cand - v) < 0.0006 or (v >= 100 and abs(cand - v) / v < 0.005):
                return True
    return False


# 1. dollar amounts
for m in re.finditer(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)", text):
    v = float(m.group(1).replace(",", ""))
    line = text[:m.start()].count("\n") + 1
    if v in INPUTS:
        status = "input"
    elif matches(v):
        status = "ok"
    else:
        status = "UNMATCHED"
        fail.append(f"line {line}: {m.group(0)} is neither a list price nor a calc.py figure")
    print(f"{status:<9} line {line:<4} {m.group(0)}")

# 2. scores
valid = {s["pass"] for s in scores["models"].values()}
for m in re.finditer(r"\b(\d{1,2})(?:/| of )30\b", text):
    line = text[:m.start()].count("\n") + 1
    if int(m.group(1)) not in valid and "30 questions" not in m.group(0):
        fail.append(f"line {line}: score {m.group(0)} is not in scores.json")

# 3. table rows, by column
names = {s["name"]: s for s in scores["models"].values()}
cells = lambda l: [c.strip().strip("*") for c in l.strip().strip("|").split("|")]
header = []
for i, l in enumerate(lines, 1):
    if not l.startswith("|"):
        header = []
        continue
    if not header:
        header = [h.lower() for h in cells(l)]
        continue
    row = cells(l)
    name = re.sub(r" \((Bedrock|local)\)$", "", row[0])
    if name not in names:
        continue
    s = names[name]
    for col, want in (("floor test", f"{s['pass']}/30"), ("confidently wrong", str(s["wrong"]))):
        if col in header and row[header.index(col)] != want:
            fail.append(f"line {i}: {name}: column '{col}' is {row[header.index(col)]!r}, scores.json says {want!r}")
import subprocess
if subprocess.run([sys.executable, str(HERE / "render_tables.py"), "--check"]).returncode:
    fail.append("a generated table is stale: run render_tables.py")

# 4. announced counts and interrupted lists
WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
is_item = lambda l: bool(re.match(r"\s*(?:[-*]|\d+\.)\s", l))
for i, l in enumerate(lines):
    m = re.search(r"\b(two|three|four|five|six|seven|eight)\b[^.:]*:\s*$", l, re.I)
    if not m:
        continue
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    n = 0
    while j < len(lines) and (is_item(lines[j]) or (lines[j].startswith("  ") and lines[j].strip())):
        n += is_item(lines[j]) and not lines[j].startswith("  ")
        j += 1
    if n and n != WORDS[m.group(1).lower()]:
        fail.append(f"line {i+1}: announces {m.group(1)} items, {n} follow")
for i in range(1, len(lines) - 2):
    # list item, then a plain paragraph line, then a list item again with no blank line in between
    if is_item(lines[i - 1]) and lines[i].strip() and not is_item(lines[i]) and not lines[i].startswith(" ") \
            and is_item(lines[i + 1]):
        fail.append(f"line {i+1}: a paragraph interrupts a list")
    # list item, blank, paragraph glued to the next list item: the list resumes after a stray paragraph
    if i >= 2 and is_item(lines[i - 2]) and not lines[i - 1].strip() and lines[i].strip() \
            and not is_item(lines[i]) and not lines[i].startswith((" ", "#", "|")) and is_item(lines[i + 1]):
        fail.append(f"line {i+1}: a paragraph interrupts a list")
    # list item, blank, paragraph, blank, list item that continues the numbering
    if is_item(lines[i - 1]) and not lines[i].strip() and lines[i + 1].strip() and not is_item(lines[i + 1]) \
            and i + 3 < len(lines) and not lines[i + 2].strip() and re.match(r"\d+\.", lines[i + 3]) \
            and not lines[i + 3].startswith("1."):
        fail.append(f"line {i+2}: a paragraph interrupts a numbered list")
    # same shape for bullets: legitimate (two separate lists) or a stray paragraph; a human decides
    if is_item(lines[i - 1]) and not lines[i].strip() and i + 3 < len(lines) and lines[i + 1].strip() \
            and not is_item(lines[i + 1]) and not lines[i + 1].startswith(("#", "|", "`")) \
            and not lines[i + 2].strip() and re.match(r"[-*]\s", lines[i + 3]):
        print(f"REVIEW    line {i+2}: one paragraph between two bullet lists; is it a separate list?")

print("\n" + ("\n".join(fail) if fail else "all checks passed"))
sys.exit(1 if fail else 0)
