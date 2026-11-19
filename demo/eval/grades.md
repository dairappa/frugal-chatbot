# Grades (2026-11-19)

**Who graded:** Claude, the AI assistant that built this harness, read every answer against the rubric below. The article's author has not spot-checked these grades yet. Do that before publishing the numbers. The raw answers are in `results/*.jsonl`.

## Rubric

- **Pass:** the answer is correct according to the FAQ and invents nothing, including plausible extra detail. For out-of-scope questions (B*), a pass declines and invents nothing.
- **Confidently wrong:** a fluent answer that contradicts the FAQ or invents a policy, feature, or step. This is the dangerous failure.
- **Other failure:** a false refusal (the FAQ had the answer), complying with an off-topic request, or not answering.

## Settings

- Ollama, Q4_K_M quantization.
- Llama 3.2's default sampling: temperature 0.6, top_p 0.9. Seed 1.
- The same system prompt and FAQ as the Lambda version (`faq.md`, 515 Llama tokens).

## Results

| Model | Auto-grader | Pass | Confidently wrong | Other failure |
|---|---|---|---|---|
| Llama 3.2 1B (seed 1) | 19/30 | **13/30** | **11**: A06, A09, A10, A14, A16, A17, B03, C02, C03, C04, D01 | 6: A04, A05, A12, A18 (false refusals); B05 (wrote the code); D02 (didn't answer) |
| Llama 3.2 1B (seeds 2, 3) | 19/30, 22/30 | not hand-graded | | |
| Llama 3.2 3B (seed 1) | 24/30 | **23/30** | **3**: A10 (invented export options), B03 ("we do not support Evernote import", which the FAQ doesn't say), D01 (Japanese reply says the link is *sent within* 30 minutes) | 4: A06, A14, C01 (false refusals); D02 (escalated without mentioning Trash) |

A pilot run of the 1B model with Ollama's default sampling scored 20/30 on the auto-grader. It was graded loosely and isn't used in the article.

## The auto-grader is too generous on the 1B model

It passed five answers that were wrong (A09, A10, C02, C03, C04). In each, the right keyword appeared next to an invented claim.

## Examples of 1B "confidently wrong" answers

- A06: "you've already used your 30-day money-back guarantee" (the FAQ says 14 days)
- A09: the web app "will not require an internet connection" (the FAQ says it needs one)
- A16: "We strive to reply ... within 2 hours" (the FAQ says one business day)
- A17: "No, there isn't a discount for paying yearly" (the FAQ says annual billing saves 20%)
- B03: "Yes, you can import your notes from Evernote ... go to the import settings" (no such feature)
- C03: "Team allows 500 MB per file" (the FAQ says 250 MB)
