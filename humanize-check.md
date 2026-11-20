# Humanize check for article-final.md (2026-11-20)

## Tools

- **pstack:unslop** is installed as a Claude Code skill: `~/.claude/plugins/cache/pstack-claude/pstack/0.9.111/skills/unslop/SKILL.md`. It is a checklist of numbered rules covering content, vocabulary, style, filler, and plain speech.
- **blader/humanizer** exists: https://github.com/blader/humanizer, "Agent skill that removes signs of AI-generated writing from text". It is MIT-licensed. On 2026-11-20 it had 71,477 stars and its last push was 2026-11-19 (checked with `gh api repos/blader/humanizer`). It is not installed here and was not used.

## Starting point

An earlier humanize review (separate session) concluded that the vocabulary was already clean, with no em dashes and no stock AI words. The problems were rhythm and density: stacked one-line punchlines, rhetorical self-questions, steering phrases (Notice, Let's), and too much bold. It also said to keep the human parts: admitted mistakes, measured values, verbatim error messages, predictions that turned out wrong, and explicit statements of what wasn't tested.

## How unslop was used

I did not run it over the article. I loaded it as a checklist, scanned the draft with grep for the mechanical tells, and made the edits by hand.

**Scan results on the new draft:**

- 0 em dashes
- 0 "Notice" / "Let's"
- 0 words from rule 7's list
- 0 rhetorical questions in prose
- 48 bold spans

**Hand edits:**

- **Bold, rule 15.** I went from 48 bold spans to 14.
  - Removed: bold dollar amounts in prose, and the bold-label-plus-colon list items (rule 16).
  - Kept: bold lead-ins that end in a period and are followed by new detail, which rule 16 allows.
- **Stacked punchlines, rule 32.** I removed or merged aphorisms where two closers sat back to back:
  - "A descent needs a floor, or it's just falling."
  - "The quota is the brake." It followed "Budgets is an alarm, not a brake".
  - "The last rung is free in inference and expensive in bytes." It followed a sentence that already made the point with numbers.
  - The four-sentence chain in the worst-case section, which is now two sentences.
  - The Maverick paragraph's two closing sentences, now merged into one.
- **Steering and framing.** "Be clear about what that buys:", "a trick worth stating out loud", "A ladder you only climb down in the sales brochure is marketing", and "the order is the frugal part" became plain statements.
- **Headings.** The first edition's "Does the floor hold? I measured this one" and "Will it even run?" were self-questions. They are now "The floor test on the last rung" and "Running it on my machine".

## Kept on purpose

- My harness priced Kimi K3 wrong at first (auto-cached tokens weren't logged), and I threw those runs away.
- "I expected price to predict the score, and it didn't" / "DeepSeek V3.2 is where my expectations broke".
- Verbatim errors: the Claude 5.5 `AccessDeniedException`, Gemma's "Conversation roles must alternate" rejection, Kimi K3's `temperature` rejection, Maverick's Legacy message, Gemma 4's invalid model identifier.
- Model answers quoted as they came back, including the wrong ones ("$48 if you choose annual billing").
- What wasn't run: Claude 5.5, Kimi K2.6, DeepSeek V4.1-Flash, Gemma 4, and the browser on a machine with GPU acceleration on.

## Structural errors guarded by code

The first edition had two structural errors: "Three things" followed by four items, and a caveat paragraph that split a bullet list. `demo/cost/check_article.py` now fails on both. Run against the first edition, it reports both, at lines 208 and 32. The new article passes. A paragraph sitting between two separate bullet lists is printed as REVIEW for a human to decide.
