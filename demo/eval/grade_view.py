#!/usr/bin/env python3
"""Print every model's run-1 answer to the same question, side by side, for hand grading.

    python3 grade_view.py A06 B01      # selected questions
    python3 grade_view.py              # all 30
Models and result files are listed in MODELS (graded.json uses the same keys).
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).parent
MODELS = {
    "kimi_k3": "bedrock-global.moonshotai.kimi-k3",
    "kimi_k25": "bedrock-moonshotai.kimi-k2.5",
    "kimi_k2_thinking": "bedrock-moonshot.kimi-k2-thinking",
    "deepseek_v32": "bedrock-deepseek.v3.2",
    "glm47": "bedrock-zai.glm-4.7",
    "qwen3_next": "bedrock-qwen.qwen3-next-80b-a3b",
    "llama4_maverick": "bedrock-us.meta.llama4-maverick-17b-instruct-v1_0",
    "gpt_oss_120b": "bedrock-openai.gpt-oss-120b-1_0",
    "glm47_flash": "bedrock-zai.glm-4.7-flash",
    "gemma3_27b": "bedrock-google.gemma-3-27b-it",
    "gpt_oss_20b": "bedrock-openai.gpt-oss-20b-1_0",
    "gemma3_4b": "bedrock-google.gemma-3-4b-it",
    "llama32_3b": "ollama-llama3.2_3b-instruct-q4_K_M",
    "llama32_1b": "ollama-llama3.2_1b-instruct-q4_K_M",
}


def load(key, seed=1):
    path = HERE / "results" / f"{MODELS[key]}-seed{seed}.jsonl"
    return {r["id"]: r for r in map(json.loads, path.read_text().splitlines())}


if __name__ == "__main__":
    runs = {k: load(k) for k in MODELS}
    questions = json.loads((HERE / "questions.json").read_text())
    wanted = set(sys.argv[1:])
    for q in questions:
        if wanted and q["id"] not in wanted:
            continue
        print(f"\n######## {q['id']} {q['q']}")
        for k, run in runs.items():
            r = run[q["id"]]
            flag = "" if r["auto_pass"] else f"  [auto: {r['auto_reason']}]"
            stop = "" if r.get("stop") in (None, "end_turn", "stop") else f"  [stop: {r['stop']}]"
            print(f"-- {k}{flag}{stop}: {' '.join(r['answer'].split())}")
