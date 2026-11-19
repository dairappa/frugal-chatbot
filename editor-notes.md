# Editor's notes for article-final.md

These notes were moved out of `article-final.md` so the article can be published as is.

**Headline:** chosen from review §5, option 3. Alternatives:

- "The Frugal Chatbot: Starting at $120 a Month and Taking the Stairs Down"
- "How Low Can a Chatbot Go? Pricing the Same AWS Bot from Opus Down"
- "Start With the Best Model, Then Ask What It Buys You"
- "The Downhill Chatbot: What You Lose (and Don't) Leaving the Flagship"

The title, subtitle, intro list, and section headings intentionally don't reveal the Stage 5 approach.

**Method note (2026-11-19):** Bedrock calls ran in us-east-1. The Claude 5.5 models (and Opus 5 / 4.7 / 4.8) returned `AccessDeniedException`; `get-foundation-model-availability` shows `agreementAvailability: NOT_AVAILABLE`. I did not accept any Marketplace agreement on the account. Claude rungs were measured with Opus 4.6, Sonnet 4.6, and Haiku 4.5. **Total Bedrock spend: $0.25**, computed as logged usage × Price List rates; this is not a billed figure (see `demo/eval/cost_summary.json` and `ledger.json`). The following were run on 2026-11-19:

- `demo/cost/calc.py`, which produces every dollar figure; `figures.json` is its output.
- `demo/stage1/test_handler.py`: 20 offline tests, all passing.
- `demo/eval/`: the 30-question floor test.
  - Bedrock: Opus 4.6, Sonnet 4.6, and Haiku 4.5 ×1 each; gpt-oss-20b, Nova Lite, and Nova Micro ×3 each; two prompt variants on Micro ×3 and on Lite and gpt-oss ×1.
  - Local Ollama: Llama 3.2 1B and 3B.
  - Grades in `grades.md` were assigned by the AI assistant, not by the author. **Spot-check them before publishing**, because the article reports them in the author's voice. Only the first run of each Bedrock model was hand-graded; the language counts for the repeat runs come from a word-list check.
- `demo/eval/behavior_checks.py` and `behavior_results.json` record the live checks: assistant-first history, `temperature`, `outputConfig`, and caching in-Region versus through the `us.*` profile.
- `demo/stage5/`: served locally and smoke-tested three times in headless Chrome with forced WebGPU on an Intel integrated GPU; see `SMOKE.md`. Per the author, this machine is a Mac running Linux with an unstable GPU, and Chrome's hardware acceleration is turned off on it, so the failures there are machine-specific. Retesting on a machine with GPU acceleration on would replace the "no answer" result with real speed numbers.

**Verification status:**

- **All model prices: verified against the AWS Price List API, 2026-11-19** (raw dumps in `demo/pricing/`).
  - Claude 5.5, global endpoints: Opus $4/$20, Sonnet $2/$10, Haiku $0.10/$0.50 ($0.50 input above 100K). Cache reads $0.20/$0.10/$0.01; cache writes $5.00/$2.50/$0.125.
  - Regional endpoints cost +10%. Fable 5.2 is $8/$40.
  - Nova Lite $0.06/$0.24, cache read $0.015. Nova Micro $0.035/$0.14, cache read $0.00875. Nova cache writes are listed at $0.00; it isn't clear whether written tokens are then billed as regular input, so calc.py bills them at the input price as an upper bound.
  - gpt-oss-20b $0.07/$0.30.
- **Cache minimums (Nova 1K, Claude 5.5 512) and the default 5-minute TTL:** AWS Bedrock prompt-caching page, read 2026-11-19. **Measured contradiction:** Nova Micro and Lite cached a ~540-token prefix. The usage fields reported it; billing was not observed. That page lists Claude Fable 5.2 on Bedrock, which supports the "more expensive tier" sentence; Fable's $8/$40 is Anthropic's list price.
- **1.25× Claude write premium:** confirmed by the Price List.
- **Thinking billed as output, and the sampling-parameter rejection on Claude 5.5:** from Anthropic's documentation for its own API. Not testable here (no 5.5 access). Haiku 4.5 accepted `temperature`.
- **Converse `outputConfig.effort` and `cachePoint`:** present in the botocore 1.44.6 Bedrock Runtime API model (schema only).
- **Converse first-message rule:** measured. Nova Micro rejects it with `ValidationException: A conversation must start with a user message`; Haiku 4.5 accepted it. `outputConfig` on Nova is rejected with "This model doesn't support the outputConfig field".
- **WebLLM sizes and VRAM:** web-llm 0.2.89 `prebuiltAppConfig` and Hugging Face file listings, 2026-11-19.
- **Safari 26 WebGPU:** secondary coverage; check Apple's release notes. Firefox 141 on Windows and Chrome/Edge 113+ are not re-verified.
- **CORS on function URLs and the OAC `x-amz-content-sha256` requirement for POST:** from memory of AWS docs, not re-checked this session.
- **The "companion repository":** now public at https://github.com/dairappa/frugal-chatbot. The article still refers to it only as "the companion repository (`demo/`)"; add the link before posting.
- **Lambda, DynamoDB, CloudFront free tiers and the $0.0000166667/GB-s rate:** official pages, 2026-11-18/19. The $0.085/GB CloudFront rate after the free tier is not re-verified.
- **The Frugal Architect:** "Make Cost a Non-functional Requirement" is law I. The frugal-vs-cheap framing is the author's paraphrase, not a quotation.
