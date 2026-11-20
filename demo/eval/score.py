#!/usr/bin/env python3
"""Turn graded.json (hand grades, run 1) and the raw runs 1-3 into scores.json.

Hand grades give the headline score. Runs 2 and 3 are not hand-graded; for all three runs this script
counts what a machine can see reliably: English questions answered in another language, visible
<think> reasoning, and empty answers.
"""
import json, pathlib, re
from grade_view import MODELS, load

HERE = pathlib.Path(__file__).parent
graded = json.loads((HERE / "graded.json").read_text())["models"]
prices = json.loads((HERE.parent / "cost" / "prices.json").read_text())["open"]
NAMES = {**{k: v["name"] for k, v in prices.items()}, "llama32_3b": "Llama 3.2 3B", "llama32_1b": "Llama 3.2 1B"}
# Letters English answers never need here: accented Latin, Cyrillic, kana, CJK
NON_ENGLISH = re.compile(r"[\u00c0-\u00ff\u0400-\u04ff\u3040-\u30ff\u4e00-\u9fff]")
FOREIGN = re.compile(r"\b(der|und|nicht|ist|wir|ihre|les|vous|votre|pour|cette|merci|est|las|los|por|para|usted|puede|het|een|niet)\b", re.I)


def wrong_language(qid, answer):
    if qid == "D01":
        return not re.search(r"[぀-ヿ]", answer)
    return len(FOREIGN.findall(answer)) >= 2 or bool(NON_ENGLISH.search(answer))


out = {"columns": ["pass", "confidently wrong", "wrong language", "other"], "models": {}}
for key in MODELS:
    g = graded[key]
    counts = {v: sum(1 for x in g.values() if x[0] == v) for v in ("wrong", "lang", "other")}
    runs = {}
    for seed in (1, 2, 3):
        try:
            rows = load(key, seed)
        except FileNotFoundError:
            continue
        runs[seed] = {
            "wrong_language": sorted(q for q, r in rows.items() if wrong_language(q, r["answer"])),
            "think_visible": sorted(q for q, r in rows.items() if "<think>" in r["answer"]),
            "empty": sorted(q for q, r in rows.items() if not r["answer"].strip()),
        }
    hand_lang = sorted(q for q, x in g.items() if x[0] == "lang" or (q == "D01" and x[0] != "pass" and "Japanese" in x[1] and "English" in x[1]))
    if 1 in runs and runs[1]["wrong_language"] != hand_lang:
        print(f"note: {key} run 1 language check {runs[1]['wrong_language']} vs hand grades {hand_lang}")
    out["models"][key] = {"name": NAMES[key], "pass": 30 - sum(counts.values()), "wrong": counts["wrong"],
                          "lang": counts["lang"], "other": counts["other"], "runs": runs}
    r = out["models"][key]
    print(f"{NAMES[key]:<22} {r['pass']:>2}/30  wrong {r['wrong']}  lang {r['lang']}  other {r['other']}  "
          + "  ".join(f"run{s}: lang {len(v['wrong_language'])} think {len(v['think_visible'])} empty {len(v['empty'])}"
                      for s, v in runs.items()))
(HERE / "scores.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
