#!/usr/bin/env python3
"""List every $ amount in article-final.md and whether calc.py produced it (to the cent or rounded)."""
import json, re, pathlib, sys
HERE = pathlib.Path(__file__).parent
figs = json.loads((HERE / "figures.json").read_text()).values()
text = (HERE.parent.parent / "article-final.md").read_text()
text = text.split("### Editor's notes")[0]
# prices per 1M tokens and per-chat unit costs are inputs, not outputs
INPUTS = {4.0, 20.0, 2.0, 10.0, 0.10, 0.50, 2.50, 0.06, 0.24, 0.035, 0.14, 0.20, 0.01, 0.015, 8.0, 40.0,
          0.012, 0.006, 0.0003, 0.000091, 5.0, 0.0,
          0.31, 0.07, 0.30, 0.00019, 0.25, 0.0, 4.40, 22.00, 150.0, 90.0, 30.0}  # 0.31 = eval run_eval.py --dry-run for Opus, not calc.py
def matches(v):
    for f in figs:
        for cand in (f, round(f, 2), round(f), round(f, 1)):
            if abs(cand - v) < 0.006 or (v >= 1000 and abs(cand - v) / v < 0.001):
                return True
    return False
bad = []
for m in re.finditer(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)", text):
    v = float(m.group(1).replace(",", ""))
    status = "input" if v in INPUTS else ("ok" if matches(v) else "UNMATCHED")
    if status == "UNMATCHED":
        bad.append(m.group(0))
    line = text[:m.start()].count("\n") + 1
    print(f"{status:<9} line {line:<4} {m.group(0)}")
print("\nunmatched:", sorted(set(bad)) or "none")
sys.exit(1 if bad else 0)
