# Editor's notes for article.md (open-weight edition, 2026-11-20)

These notes are not part of the article.

## Direction (decided 2026-11-20)

- The article centres on open-weight models; proprietary models appear only as price yardsticks.
- No Claude measurements. Claude 5.5 appears as a list-price yardstick only, and the article does not discuss access to it (author's instruction, 2026-11-22).
- All costs are at list price, with no free tier.
- Structure (author's instruction, 2026-11-22): the browser (WebLLM) rung is Stage 4, right after the model stages, as the punchline. It is followed by the rest of the bill (server path, browser path, the worst-case ceiling) and a closing part with the architecture diagram and the costs the token price leaves out. The title, subtitle, headings, and the introduction's stage list must still not reveal the browser rung.
- Tone (author, 2026-11-22): half a joke, played straight. No false statements and real tests, but trivial details may go. The aim is to show how wide the architecture space is, not to maximise practicality.

## Headline options

Current: **"$90, $18, $3.90… Where Does the Chatbot Bill Stop?"** It continues the first edition's title shape, with the new prices.

Alternatives (none of them reveals the last rung):

- "Open Weights, List Prices: Walking a Support Bot Down the Model Shelf"
- "Twelve Open-Weight Models, Thirty Questions, One Support Bot"
- "The Frugal Chatbot, Open-Weight Edition"
- "Same Bot, Twelve Models: What a Support Chatbot Really Needs to Cost"
- "Price Didn't Predict the Score: Pricing a Support Bot on Open-Weight Models"

## Method and verification status

- **Spend.** Bedrock spend for this edition was $0.87, computed as logged usage × list price (`calc.py` → `spend.this_edition`, from `demo/eval/ledger.json`).
  - This includes an upper-bound correction of $0.18 for Kimi K3 runs whose auto-cached tokens weren't logged. Those runs were thrown away.
  - This is not a billed figure.
- **Prices.** The open-weight Bedrock prices come from the AWS Price List API, us-east-1, read 2026-11-20 (`demo/pricing/extract-2026-11-20.json`).
  - The Claude and Nova yardsticks were read on 2026-11-19 (`demo/pricing/claude-use1-summary.json`).
  - Lambda, DynamoDB, and CloudFront list prices were read on 2026-11-20.
- **External prices and licenses.** These are in `demo/pricing/external-2026-11-20.md`. They were gathered by an AI research assistant from Hugging Face, the Moonshot, DeepSeek, and Z.ai pricing pages, and OpenRouter, and were not re-read by the author.
- **Grades.** Run 1 of all 14 models was graded by Claude (AI assistant) against one rubric (`demo/eval/grades.md`, `graded.json`). The author spot-checked the two flagged Japanese D01 passes on 2026-11-21 and failed both (Qwen3-Next 27→26/30, gpt-oss-120b 30→29/30): 「30分以内に有効なリセットリンク」 reads as a delivery time, not the FAQ's 30-minute expiry. The rest of the grades have not been spot-checked.
- **Llama 4 Maverick.** It went `LEGACY` mid-test, so it has 2 full runs plus 3 answers.
- **Kimi K3's automatic caching.** It was measured: 90/90 calls read about 614 tokens from cache, and no write was reported. Bedrock's retention time for automatic caching is unknown. The calls were seconds apart.
- **Behaviour checks.** These are in `demo/eval/behavior_results.json`, from 5 models, 2026-11-20. The Stage 1 handler was run live once on Gemma 3 27B and returned 200.
- **Stage 5.** The WebLLM smoke test (`demo/stage4/SMOKE.md`, the Stage 5 page of earlier drafts) is unchanged from the first edition. WebLLM sizes come from web-llm 0.2.89 `prebuiltAppConfig`.
- **Unchanged and not re-verified this time:** Safari 26 / Firefox WebGPU support, and CORS / OAC `x-amz-content-sha256` behaviour.
- **The companion repository.** It is https://github.com/dairappa/frugal-chatbot. The article calls it "the companion repository (`demo/`)". Add the link before posting.

## Open decisions

- **Testing Kimi K2.6 and DeepSeek V4.1-Flash** needs a Moonshot (platform.kimi.ai) API key and a DeepSeek API key. Moonshot's notice says the K2 series is closed to newly registered users from 2026-10-31; whether that covers K2.6 isn't stated.
- **Gemma 4 has Bedrock price rows but no Converse model ID.** It may need the OpenAI-compatible endpoint, which was not tried.
- **The Kimi framing.** On this FAQ, the Kimi K2 line is not the best value. Gemma 3 27B scored 30/30 and gpt-oss-120b 29/30 for under $4, against $18 for Kimi K2.5 at 29/30. The article says so.
