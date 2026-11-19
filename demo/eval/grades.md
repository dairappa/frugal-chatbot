# Grades (2026-11-19)

**Who graded:** Claude, the AI assistant that built this harness, read the answers against the rubric below. The article's author has not spot-checked these grades yet. Do that before you publish the numbers. Raw answers are in `results/*.jsonl`.

## Rubric

**Rubric v1** (Llama rows, graded first): pass = correct per the FAQ and *invents nothing*, not even plausible extra detail.

**Rubric v2** (Bedrock rows): pass = correct per the FAQ, in the user's language, with no invented policy or feature and no contradiction. A plausible inference passes but is noted, for example "your account reverts to Free" or "Team may suit more devices". Under v2, the Llama 3B A10 answer (invented export options) would still fail. The Llama rows were not re-graded under v2.

All hand-graded Bedrock answers were re-read in full, not truncated, on 2026-11-19. The first pass had printed only the first 170 to 260 characters.

Notes from the full read:

- Sonnet A18 ("If you need more, the Team plan may be worth considering!") and Haiku A18 ("Plus and Team plans offer more flexibility across multiple devices") hint that Team allows more devices. The FAQ is silent on that, so both count as inferences and pass. Haiku B03 failed under the same rubric because it implies a feature, an Evernote import process, that the FAQ never mentions.
- gpt-oss A14 and Haiku A14 say the account "reverts to Free" after cancelling. That is an inference and passes.
- Nova Micro run 2, A14, links to an invented URL (`https://example.com/faq/cancel-subscription`). I found it while reading the out-of-scope and refund rows of runs 2 and 3, which were not otherwise graded. Those rows contained no invented policies.
- **Out-of-scope questions (B\*):** pass = declines and invents nothing.
- **Confidently wrong:** a fluent answer that contradicts the FAQ, or one that invents a policy, feature, or step. This is the dangerous failure.
- **Wrong language:** an English question answered in another language, or the Japanese question (D01) answered in English.
- **Other failure:** a false refusal (the FAQ had the answer), complying with an off-topic request, or not answering.

## Setup

- System prompt: `../faq.md`, the same on every model unless a variant is named. Same request shape as the Stage 1 handler: no temperature, `maxTokens` 1024. `effort: low` would apply to Claude 5.5 only, and no 5.5 model ran.
- Bedrock models ran in us-east-1. Claude ran through `global.*` inference profiles; Nova and gpt-oss ran with in-region model IDs.
- **The Claude 5.5 models could not be run.** The account has no Marketplace agreement for them: `agreementAvailability: NOT_AVAILABLE`, and calls return `AccessDeniedException`. Opus 5 and Opus 4.7/4.8 are also unavailable. **Previous-generation models stand in as proxies:** Opus 4.6, Sonnet 4.6, and Haiku 4.5.
- Local models ran on Ollama with Q4_K_M quantization and Llama defaults (temperature 0.6, top_p 0.9).

## Results: original prompt, hand-graded run

| Model | Where | Pass | Confidently wrong | Wrong language | Other |
|---|---|---|---|---|---|
| Claude Opus 4.6 *(stand-in for Opus 5.5; $150/month at this workload, vs $120)* | Bedrock | **30/30** | 0 | 0 | 0 |
| Claude Sonnet 4.6 *(stand-in for Sonnet 5.5; $90 vs $60)* | Bedrock | **30/30** | 0 | 0 | 0 |
| Claude Haiku 4.5 *(stand-in for Haiku 5.5; $30 vs $3)* | Bedrock | **28/30** | 2 (A06 "Yes, you can!" for a refund past 14 days; B03 "they'll help you with the import process") | 0 | 0 |
| gpt-oss-20b | Bedrock | **29/30** | 0 | 0 | 1 (D02: no mention of Trash) |
| Nova Lite | Bedrock | **28/30** | 0 | 1 (A05 in Spanish) | 1 (D02) |
| Nova Micro | Bedrock | **20/30** | 0 | **10** (German ×9, Dutch ×1; one of them, D02, also didn't answer) | 0 |
| Llama 3.2 3B | local | **23/30** | 3 | 0 | 4 |
| Llama 3.2 1B | local | **13/30** | **11** | 1 (D01 counted as wrong content) | 6 |

### Repeat runs

- **Nova Micro:** answered English questions in another language 10, 8, and 6 times in three runs.
- **Nova Lite:** 1, 0, and 0 times.
- **gpt-oss-20b:** 0, 0, and 0 times.

Detected with a word-list check; only the first run was hand-graded.

## Results: prompt variants (Nova Micro's language problem)

The original prompt line is "Reply in the same language as the user."

| Variant | Model | Result |
|---|---|---|
| `faq-langfix.md`: "Reply in English. If the user writes in another language, reply in that language." | Nova Micro ×3 | 0 wrong-language answers to English questions, but **D01 (Japanese) answered in English in all 3 runs** |
| `faq-langfix2.md`: "Detect the language of the user's latest message and reply in exactly that language (English questions get English answers)." | Nova Micro ×3 | 0 wrong-language answers; D01 in Japanese in all 3. Hand-graded run: **29/30**, 1 confidently wrong (B01: "we don't offer student discounts") |
| `faq-langfix2.md` | Nova Lite ×1 | **D01 now answered in English** (it was Japanese with the original prompt). Not fully hand-graded. |
| `faq-langfix2.md` | gpt-oss-20b ×1 | D02 still fails; the rest looks fine. Not fully hand-graded. |

**Lesson:** a prompt fix is model-specific. The line that fixed Micro broke Lite's Japanese. Re-run the eval after every prompt change.

## Auto-grader notes

- It was too generous on Llama 1B: it passed wrong answers that contained the right keyword.
- It was too strict on gpt-oss: that model writes "14 days" with a narrow no-break space. Fixed in `run_eval.py` after these runs.
- It can't see the language problem unless a keyword is missing.

## Live handler check (2026-11-19)

`stage1/handler.py` was invoked with a five-message conversation. Sliced naively, that conversation starts with an assistant turn.

| Model | `EFFORT` | Result |
|---|---|---|
| `amazon.nova-micro-v1:0` | `""` | 200, correct answer (Trash, then Restore) |
| `global.anthropic.claude-haiku-4-5-20251001-v1:0` | `""` | 200, correct answer |
| `global.anthropic.claude-haiku-4-5-20251001-v1:0` | `low` (the handler's default) | **ValidationException: "This model does not support the effort parameter"**. The handler doesn't catch this error, so Lambda would return a 500. |

`EFFORT=low` is meant for the Claude 5.5 models only, and those models could not be tested on this account.

The DynamoDB quota path was **not** run live. Only the Stubber test covers it.
