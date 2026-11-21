# Grades (2026-11-20)

**Who graded:** Claude, the AI assistant that built this harness. It read every run-1 answer of every model in full, question by question across all models (`python3 grade_view.py`), against the rubric below. The article's author (Rappa) spot-checked the two flagged D01 passes on 2026-11-21 and changed both to confidently wrong (see the D01 rule below); the other grades are Claude's.

- Hand grades: `graded.json`. Scores: `scores.json`, written by `score.py`. Raw answers: `results/*.jsonl`.
- `score.py` also scans runs 1–3 for what a machine can see: English questions answered in another language, visible `<think>` text, and empty answers. On run 1 its language counts match the hand grades for every model.

## Rubric (one rubric for every model)

Pass means the answer is correct per the FAQ, in the user's language, invents no policy, feature, option, step, URL, or number, and contradicts nothing in the FAQ.

**Out-of-scope questions (B\*):** pass means the model declines and invents nothing. "We don't offer student discounts" invents a policy, so it fails.

**Failure classes:**

- **Confidently wrong:** a fluent answer that contradicts the FAQ or invents something.
- **Wrong language:** an English question answered in another language, or the Japanese question (D01) answered in English.
- **Other:**
  - a false refusal, when the FAQ had the answer
  - complying with an off-topic request
  - missing the key fact (D02 must mention Trash)
  - an empty answer
  - reasoning text shown to the user

**Tie-break rules, written down after the first pass so that every model gets the same call:**

- A plausible inference passes, with a note. Examples:
  - "your account reverts to Free" after cancelling
  - "Linux users can use the web app" read as "yes"
  - "recover the note to its original location"
- An invented option, step, or feature that a user would try, and fail, to use is confidently wrong. Example: "export selected notes or a specific folder".
- Response times:
  - An explicit promise that contradicts "we reply within one business day" ("we'll help immediately") is confidently wrong.
  - Implying that email is faster ("if you need immediate help, email us") passes, with a note.
- A vague pointer to a page that may not exist ("see our pricing page") passes, with a note. An invented URL fails.
- **D01 (Japanese):**
  - The FAQ says the reset link expires after 30 minutes. 「30分で期限切れ」 or 「有効期限は30分」 passes.
  - 「リンクは30分以内に送られます」 (the link is sent within 30 minutes) is confidently wrong.
  - 「30分以内に有効なリセットリンク」 is confidently wrong. Claude first passed it as "valid for 30 minutes"; the author's spot check (2026-11-21) read it as "a link that arrives within 30 minutes", a delivery time the FAQ never promises, and changed Qwen3-Next 80B A3B and gpt-oss-120b to confidently wrong.

## Setup

- System prompt: `../faq.md`, the same for every model. Same request shape as the Stage 1 handler: no `temperature`, no `outputConfig`, `maxTokens` 1,024.
- Bedrock calls ran in us-east-1 on 2026-11-20:
  - Kimi K3 through the `global.*` inference profile
  - Llama 4 Maverick through `us.*`
  - every other model with its in-Region model ID
- Local models ran on Ollama with Q4_K_M quantization and Llama 3.2's default sampling (temperature 0.6, top_p 0.9), as a stand-in for the in-browser runtime.
- Three runs per model. Bedrock has no seed parameter, so a "seed" is only a run label there.
- **Llama 4 Maverick has two full runs, plus three answers of the third.** During run 3, Bedrock started rejecting calls with `ResourceNotFoundException: ... This Model is marked by provider as Legacy and you have not been actively using the model in the last 30 days`. `get-foundation-model` reports `status: LEGACY`, legacy since 2026-09-30, end of life 2027-03-30.
- **Claude 5.5 could not be run.** One Converse call returned `AccessDeniedException: ... is not available for this account`. Claude appears in the article as a price only.

## Results: hand-graded run 1

See `scores.json` (and the article's table, which is generated from it). Repeat-run observations from `score.py`:

| Model | Wrong-language answers, runs 1/2/3 | Visible `<think>`, runs 1/2/3 | Empty answers, runs 1/2/3 |
|---|---|---|---|
| Kimi K2.5 | 1/0/0 (French) | 0/0/0 | 0/0/0 |
| Kimi K2 Thinking | 0/0/0 | 4/4/4 (the four follow-up questions) | 1/0/1 (`max_tokens`) |
| DeepSeek V3.2 | 2/3/3 (Spanish, French, German, Italian, Portuguese) | 0/0/0 | 0/0/0 |
| every other model | 0/0/0 | 0/0/0 | 0/0/0 |

Kimi K2 Thinking's visible reasoning appeared only on the questions that carry history (C01–C04). The `<think>` text came back inside the Converse text block, not as a `reasoningContent` block.

## Auto-grader notes

- The keyword auto-grader in `run_eval.py` is a first filter, not a grade.
  - It passed Llama 3.2 1B answers that put the right keyword next to an invented claim.
  - It failed correct answers that phrase things differently: "20 %" with a space, "does not work offline".
- The first version of the language check in `score.py` was a word list fitted to run 1. Reading every non-ASCII answer in runs 2 and 3 by hand showed that it missed DeepSeek's German, Italian, and Portuguese answers. It now flags any accented Latin, Cyrillic, kana, or CJK letter in an answer to an English question.
