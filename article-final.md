# $120, $60, $3… Where Does the Chatbot Bill Stop?

*Walking an AWS support bot down the model shelf, starting from the flagship, and keeping score of what each dollar was really buying.*

---

## Introduction: the scary part was never the token price

Every team that adds a chatbot to a product has the same nightmare: a user pastes an entire wiki into the chat window at 3 a.m., the conversation history grows without bound, and the monthly bill arrives like a phone number.

[The Frugal Architect](https://thefrugalarchitect.com/), Werner Vogels' collection of laws for building cost-aware systems, is a good lens for this. The first law is *Make Cost a Non-functional Requirement*. I read the laws as drawing a line between frugal and cheap. Cheap means cutting corners and hoping nobody notices. Frugal means knowing what each design decision costs, and spending only where it buys something real.

Nobody begins with the cheapest model. You begin with the *best* model, the flagship, because you want to see what "good" looks like before you start trading it away. Then the first bill arrives, and the real engineering begins: how far down the shelf can you walk before the chatbot stops being good enough?

We will build the same chatbot five times, walking down a ladder:

1. **Stage 1:** the flagship, Claude Opus 5.5 on Amazon Bedrock, behind a Lambda function.
2. **Stage 2:** the same architecture, walking down the model shelf: Sonnet, then Haiku, then Amazon's own Nova models.
3. **Stage 3:** the same architecture, with three cost levers pulled.
4. **Stage 4:** the same architecture, squeezed inside the AWS Free Tier, with a worst-case bill you can name.
5. **Stage 5:** one more step down, where the question stops being "which model?"

### What I ran, and what I didn't

The monthly prices are **calculations** from list prices, and every list price was checked against the AWS Price List API. The floor checks are **measurements**. The code is in the companion repository (`demo/`):

- **A cost script** (`demo/cost/calc.py`) that produces every dollar figure in this article from one price file. If you change the prices or the traffic, the article's tables change with them.
- **Offline tests for the Stage 1 handler** (`demo/stage1/`). They use botocore's `Stubber`, which validates each request against the real Converse and DynamoDB API schemas without calling AWS.
- **A 30-question floor test** (`demo/eval/`) with the same system prompt and FAQ on every rung. It ran on Amazon Bedrock against Nova Lite, Nova Micro, and gpt-oss-20b, and against Claude models (see the caveat below). It also ran on the last rung's model. Every answer was graded by reading it against a written rubric. All the Bedrock calls behind this article, including the experiments, cost **$0.25**, computed from the logged token counts at list prices.
- **Live checks of the Converse behaviors the code relies on:** history that starts with an assistant turn, `temperature`, `outputConfig`, and prompt caching.

**One caveat.** The Claude 5.5 models were not enabled on my AWS account (its Marketplace agreement status was `NOT_AVAILABLE`). So the Claude rungs were measured with older-generation stand-ins: **Opus 4.6, Sonnet 4.6, and Haiku 4.5**. The prices in this article are the 5.5 prices. The floor results for those rungs come from older models that cost more at this workload ($150, $90, and $30 a month); they are not measurements of the 5.5 models.
- **A minimal implementation of the last rung** (`demo/stage5/`), served locally and smoke-tested.

### The unit of comparison

- **10,000 chats per month.**
- **Each chat is 1,000 input tokens and 400 output tokens.** The input is the system prompt with the FAQ, a trimmed slice of history, and the user's question. The demo FAQ is 515 tokens with Llama's tokenizer. Other tokenizers count differently; Anthropic says Claude Haiku 5.5's tokenizer counts about 30% more tokens for the same text. Use one fixed budget for comparison, and measure your own.
- **List prices, US East (N. Virginia), on demand**, checked against the AWS Price List API on 2026-11-19. For Claude, these are the *global* endpoint rates. Regional endpoints (`us.*` profiles) cost 10% more; the Price List shows $4.40/$22.00 for Opus 5.5.
- **The budget is conservative.** In the measured runs, a single-turn FAQ answer used 550 to 610 input tokens. Output was 22 to 47 tokens on Nova and the Claude stand-ins, and 111 on gpt-oss-20b, whose count includes its reasoning. Real answers came in far under 400 output tokens; thinking on the 5.5 models is the unknown.
- **Thinking tokens are not included.** The Claude 5.5 models think by default, and thinking is billed as output. Stage 1 shows what that does to the bill.
- The master formula, per chat: `input_tokens/1M × input_price + output_tokens/1M × output_price`, times 10,000.

### The floor: what "minimum viable" means

A descent needs a floor, or it's just falling. Before we price anything, define the least a support chatbot must do to deserve the name:

- Answer questions **from the context you give it** (your FAQ, your docs), accurately and in the user's language.
- **Admit ignorance** and offer a ticket or a human when the answer isn't in the context, instead of improvising.
- Hold **a few turns of context**, so "and how do I undo that?" works.
- Stay polite, on-topic, and concise.

The 30 questions in `demo/eval/questions.json` map to this list:

- 18 answerable from the FAQ
- 6 out of scope: a student discount, HIPAA, Evernote import, a Linux release date, a Python script, the weather
- 4 follow-ups that need history
- 1 question in Japanese
- 1 angry customer

Every rung below gets the same question: *what do we give up here, and does the floor still hold?* Each rung now has a measured answer, from a stand-in model on the Claude rungs. Thirty questions is a smoke test, not a benchmark, so run the harness against your own FAQ before you trust mine.

## Stage 1: Start at the top, Claude Opus 5.5 behind Lambda

The architecture is small: a static chat page, one Lambda function with a function URL, Amazon Bedrock for the model, and a DynamoDB table that we will need in Stage 4. There are no servers to patch and no GPU to feed. You pay per token, plus fractions of a cent of compute.

The model choice is the flagship of Claude's Opus line. (Bedrock offers an even more expensive tier, Claude Fable 5.2 at $8/$40, but that tier is aimed at long-horizon agent work, not support chat.) Claude Opus 5.5 costs **$4.00 per 1M input tokens and $20.00 per 1M output tokens**. Per chat: `0.001 × $4.00 + 0.0004 × $20.00 = $0.012`. Times 10,000 chats: **$120/month in model costs.**

Here is the backend, using the Bedrock Converse API from Lambda (Python). The full file and its tests are in `demo/stage1/`:

```python
import json, os, boto3

bedrock = boto3.client("bedrock-runtime")
MODEL_ID = os.environ["MODEL_ID"]            # e.g. a global.* inference profile ID for Opus 5.5
EFFORT = os.environ.get("EFFORT", "low")     # Claude 5.5 only; set to "" for Nova
SYSTEM_PROMPT = open("faq.md").read()        # instructions + the FAQ, ~600 tokens
MAX_MESSAGES = 7                             # 3 exchanges + the new question
MAX_CHARS_PER_MESSAGE, MAX_BODY_BYTES = 2_000, 16_000

def trim_history(history):
    if any(len(m["text"]) > MAX_CHARS_PER_MESSAGE for m in history):
        raise ValueError("message too long")
    trimmed = history[-MAX_MESSAGES:]
    while trimmed and trimmed[0]["role"] != "user":   # always open with a user turn
        trimmed = trimmed[1:]
    if not trimmed or trimmed[-1]["role"] != "user":
        raise ValueError("the last message must come from the user")
    return trimmed

def handler(event, context):
    body = event.get("body") or "{}"
    if len(body.encode()) > MAX_BODY_BYTES:
        return {"statusCode": 413, "body": "request too large"}
    try:
        messages = trim_history(json.loads(body).get("messages", []))
    except (ValueError, KeyError, TypeError) as e:
        return {"statusCode": 400, "body": str(e)}

    request = dict(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": m["role"], "content": [{"text": m["text"]}]} for m in messages],
        inferenceConfig={"maxTokens": 1024},
    )
    if EFFORT:   # Claude 5.5: thinking can be turned down, not off
        request["outputConfig"] = {"effort": EFFORT}
    response = bedrock.converse(**request)
    answer = "".join(b.get("text", "") for b in response["output"]["message"]["content"])
    print(json.dumps({"usage": response["usage"]}))   # the meter for this system
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"answer": answer, "usage": response["usage"]})}
```

Four details in this snippet do quiet financial or correctness work:

- **The history is trimmed so that it starts with a user turn.** My first draft used `history[-6:]`. The client always sends an odd number of messages, because the list ends with the user's new question. So from the fourth turn on, that slice *starts with an assistant message*. What happens next depends on the model. Nova Micro rejects the call with `ValidationException: A conversation must start with a user message`. Haiku 4.5 accepted it. A chatbot that breaks on turn four for some models and not others is the worst kind of bug, so the handler never sends one. A unit test in `demo/stage1/` reproduces the bad slice.
- **Size is checked before any token is spent.** The 3 a.m. wiki paste now gets a 413 and costs nothing.
- **No `temperature`.** On Anthropic's API, the Claude 5.5 models reject non-default sampling parameters. Nova Micro and Haiku 4.5 accepted `temperature: 0.7` on Bedrock. I couldn't test the 5.5 models. A FAQ bot gains nothing from it anyway.
- **`outputConfig.effort` is `low` and `maxTokens` is 1,024, not 400.** Opus 5.5 always thinks, and thinking tokens count toward `maxTokens`, so a tight cap can cut off the visible answer. Send `effort` only to the Claude 5.5 models. Nova rejects the whole request with `This model doesn't support the outputConfig field`, and Haiku 4.5 rejects it with `This model does not support the effort parameter`. I ran this handler live against Nova Micro and Haiku 4.5 with `EFFORT=""`, and both answered a five-message conversation correctly.

That last point changes the bill. The $120 assumes 400 output tokens per chat. If each chat also thinks for 200 tokens, the bill becomes **$160**; at 1,000 thinking tokens it becomes **$320**. Log `usage.outputTokens` from day one, because it is the only number that tells you which of these you are paying.

The execution role needs `bedrock:InvokeModel` on the inference profile and the models it routes to. Raise the Lambda timeout from its 3-second default to 30 seconds. In the test runs, the slowest Opus 4.6 answer took 5.5 seconds, and a thinking model will be slower.

What does $120/month buy? Excellent answers. The Opus stand-in passed **30 of 30**. It calmed the angry customer before it told them where Trash is, and it declined all six out-of-scope questions without inventing anything. Opus handles the ambiguous question, the question that needs three facts combined, and the annoyed customer who needs calming before instructions. If your chatbot does legal triage or complex troubleshooting, stop here: this is your stage, and $120/month for it is not much.

But watch a flagship model answer "How do I reset my password?" a few hundred times and a suspicion forms: you are paying for reasoning depth that FAQ traffic never touches. Let's walk down.

**Stage 1 total: ≈ $120/month** (model, before thinking tokens) + Lambda and DynamoDB charges, which Stage 4 takes to zero.

## Stage 2: Walk down the model shelf

Same code, same architecture. The only thing that changes is configuration (`MODEL_ID`, plus `EFFORT=""` for any model outside the Claude 5.5 family), and the question we ask at each rung.

### Rung 1: Claude Sonnet 5.5 ($60/month)

**$2.00 per 1M input tokens, $10.00 per 1M output tokens** → `0.001 × $2.00 + 0.0004 × $10.00 = $0.006` per chat → **$60/month**. The first step down halves the bill.

What you give up: the deepest reasoning, the multi-step edge cases, the subtlest reading of a convoluted question. None of that showed up in a FAQ test. The Sonnet stand-in also passed **30 of 30**. For most chatbots this rung is *still* overkill, just less flamboyantly so.

### Rung 2: Claude Haiku 5.5 ($3/month)

**$0.10 per 1M input tokens, $0.50 per 1M output tokens** for prompts up to 100K tokens; above that, $0.50/$2.50. Ours are 1,000. → `0.001 × $0.10 + 0.0004 × $0.50 = $0.0003` per chat → **$3/month**. This is the rung where the character of the exercise changes: we are no longer trimming a bill, we have divided it by forty.

What you give up: nuance, and it shows up as the first wrong answers. The Haiku stand-in (Haiku 4.5, which costs ten times as much at this workload) passed **28 of 30**. Both failures were the dangerous kind. To a customer who bought three weeks ago, it opened with "Yes, you can!", then explained that the 14-day refund window had passed. And it promised that support would "help you with the import process" for an Evernote import feature the FAQ never mentions. The floor holds, with cracks you would want a human to review. For FAQ traffic this is the first rung that feels *designed* for the job, and $3/month is close to the point where further savings stop mattering in dollars and start mattering as a design exercise. We continue anyway.

### Rung 2½: an open-weight model, gpt-oss-20b ($1.90/month)

Bedrock also serves open-weight models on demand. OpenAI's gpt-oss-20b costs **$0.07/$0.30 per 1M tokens** → **$1.90/month**. Its list price is above Nova Lite's, and it also reasons before it answers. In my runs it averaged about 111 output tokens per answer, against Nova's 22 to 29, and the extra tokens appear to be its reasoning. So its real bill per answer runs higher than Nova's too. It passed **29 of 30**, in the right language every time across three runs. Its only failure was the angry customer: it escalated without mentioning Trash.

### Rung 3: Amazon Nova Lite and Nova Micro ($1.56 and $0.91/month)

The last step on the shelf is Amazon's own Nova family. Nova Lite costs **$0.06/$0.24 per 1M tokens** → **$1.56/month**. Nova Micro costs **$0.035/$0.14** → `0.001 × $0.035 + 0.0004 × $0.14 = $0.000091` per chat → **$0.91/month**.

I expected Nova to fail by inventing answers. Mostly it didn't. In the hand-graded runs, neither model invented a policy, and both declined all six out-of-scope questions in all three runs. One repeat run did invent a help-page URL. Nova Lite passed **28 of 30**, but one refund answer came back in Spanish.

Nova Micro failed differently. It answered **10 of 30 English questions in another language**, nine in German and one in Dutch, and passed **20 of 30**. Nine of those ten were factually right, just in the wrong language. Across three runs, Micro switched language on 10, 8, and 6 questions. The trigger was the prompt line "Reply in the same language as the user." Micro apparently read that as an invitation to pick a language.

The fixes taught me more than the failure did:

- "Reply in English. If the user writes in another language, reply in that language." This stopped the German, and it also made Micro answer the Japanese question in English, three runs out of three.
- "Detect the language of the user's latest message and reply in exactly that language (English questions get English answers)." This fixed Micro: **29 of 30**, with English for English and Japanese for Japanese. The same line then made **Nova Lite** answer the Japanese question in English.

A prompt fix is model-specific. Whenever you change the prompt or the model, rerun the floor test. (The demo's `faq.md` keeps the original line, so every rung in the table below saw the same prompt.)

At this altitude, **routing** becomes attractive: send the easy majority to Micro, and escalate to Haiku when the question is complex. How you route matters:

- **A router decides first** (a cheap classifier or rules), and 20% of chats go to Haiku: **$1.33/month**.
- **Micro answers first**, and 20% are re-asked to Haiku when the answer looks unsure: **$1.51/month**, because escalated chats pay for both models.

Here is the whole shelf, measured with the same 30 questions:

| Rung | $/month | Model tested | Floor test | Confidently wrong | What went wrong |
|---|---|---|---|---|---|
| Opus 5.5 | $120 | Opus 4.6 ($150 at this workload) | 30/30 | 0 | nothing |
| Sonnet 5.5 | $60 | Sonnet 4.6 ($90) | 30/30 | 0 | nothing (one mild hint that Team allows more devices) |
| Haiku 5.5 | $3.00 | Haiku 4.5 ($30) | 28/30 | 2 | a contradictory refund answer; an implied import feature |
| gpt-oss-20b | $1.90 | same | 29/30 | 0 | escalated the angry customer without mentioning Trash |
| Nova Lite | $1.56 | same | 28/30 | 0 | one answer in Spanish; the angry customer again |
| Nova Micro | $0.91 | same | 20/30 → **29/30** after a one-line prompt fix | 0 → 1 | German answers, then one invented "we don't offer student discounts" |

**Stage 2 total: $120 → $60 → $3 → $1.56 → $0.91/month**, depending on where you stop. Notice the shape: the first two rungs saved $117 of the $120. Model selection is not one lever among many; it is *the* lever.

The shape holds at any scale, but the absolute numbers decide whether the rest of this article matters to you:

| Chats per month | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 | Nova Lite | Nova Micro |
|---|---|---|---|---|---|
| 10,000 | $120 | $60 | $3.00 | $1.56 | $0.91 |
| 100,000 | $1,200 | $600 | $30 | $15.60 | $9.10 |
| 1,000,000 | $12,000 | $6,000 | $300 | $156 | $91 |

## Stage 3: Three levers that cost nothing to pull

Before changing any architecture, pull the levers that are pure configuration. They multiply whatever rung you're standing on. They are worth most at the top of the ladder, so the examples start there.

### Lever 1: Stop paying full price for the prompt you send every time

Your system prompt and FAQ are identical on every request. Bedrock prompt caching bills a repeated prefix at a cache-read rate: **$0.20 per 1M tokens on Opus 5.5** (5% of its input price), **$0.10 on Sonnet 5.5**, **$0.01 on Haiku 5.5**, and **$0.015 on Nova Lite**. In the Converse API, you mark the end of the cacheable prefix with a `cachePoint`:

```python
system=[
    {"text": SYSTEM_PROMPT},
    {"cachePoint": {"type": "default"}},   # everything above is cached
],
```

Three things a price table does not show:

1. **Measure the minimum; don't trust it.** AWS documents a minimum of 1K tokens per cache checkpoint for Nova. In my runs, Nova Micro and Nova Lite both cached our **~540-token** prefix: the first call reported it in `cacheWriteInputTokens` and the next calls in `cacheReadInputTokens`. If that holds for you, Nova Lite with a cached 600-token prefix drops from $1.56 to **$1.29/month** at a perfect hit rate. For the Claude 5.5 models, the documented minimum is 512 tokens. If the prompt caches there too, Opus drops from $120 to **$97.20/month** at a perfect hit rate, or **$100 to $106** at the realistic hit rates below.
2. **Cross-region profiles split the cache.** A `us.*` inference profile can route consecutive calls to different Regions, and each Region keeps its own cache. Called through `us.amazon.nova-micro-v1:0`, only 2 of 4 repeat calls read the cache; the others wrote it again. With the in-Region model ID, 4 of 4 hit. (That is a handful of calls, not a study, but it is easy to check in your own `usage` logs.)
3. **Writes may cost extra, and entries expire.** On Claude, a cache write costs 1.25× the input price; the Price List shows $5.00 per 1M for Opus 5.5. For Nova, it lists cache writes at $0.00. An entry lives 5 minutes after its last use. 10,000 chats a month is one every **4.3 minutes** on average. If arrivals are random, the next chat arrives within 5 minutes only **69%** of the time. If all traffic falls in 12 waking hours, that rises to **90%**. A 100% hit rate is not a free assumption.
4. **Check that it works.** After each call, read `usage.cacheReadInputTokens`. If it stays at zero, your prefix isn't stable, isn't long enough, or is landing in a different Region each time.

With a bigger FAQ (a 2,000-token cached prefix plus 400 tokens of question and history), caching earns its keep. The table uses the hit rates above and the write premium. For Nova, the table bills writes at the input price, which makes its Nova figures an upper bound:

| 2,400 input / 400 output | No cache | 69% hits | 90% hits |
|---|---|---|---|
| Opus 5.5 | $176.00 | $130.17 | $109.48 |
| Haiku 5.5 | $4.40 | $3.32 | $2.83 |
| Nova Lite | $2.40 | $1.78 | $1.59 |

The trade-off is design discipline: the cacheable prefix has to be byte-for-byte static, so per-user data goes *after* the cache point, never inside it.

### Lever 2: Trim the history, summarize the rest

Lever 2 is Stage 1's `trim_history` taken seriously. A chat that replays a 40-message history on every turn can multiply its input tokens fivefold by the end of a long session. Under our assumptions, that takes Nova Lite from $1.56 to **$3.96** for the same answers, and Opus from $120 to **$280**. Keep the last few exchanges verbatim, replace everything older with a short running summary, and your input cost per chat stays flat no matter how long the conversation runs.

### Lever 3: Cap the output, and turn the thinking down

Output tokens cost 4 to 5 times as much as input tokens on every model on the shelf, so a chatbot that writes essays when a paragraph would do pays essay prices. Ask for concision in the system prompt ("3 sentences or fewer"), and on the Claude 5.5 models set `effort` to `low`. Keep `maxTokens` as a safety net, not as the main control. On a thinking model, a tight cap truncates answers instead of shortening them.

**Stage 3 total: ≈ $0.75 to $1.51/month** at the bottom rungs, depending on how you route and whether the cache holds. Nova Micro with a cached prefix comes to $0.75 to $0.80. The levers matter more at the top: Opus can drop from $120 to about $100 to $106 with caching alone.

## Stage 4: Fit the whole thing inside the free tier

Now for the supporting cast. At 10,000 chats a month, the compute and storage around the model are small enough that AWS's **always-free** allowances cover them. These are not the 12-month trial; they don't expire.

- **Lambda:** 1 million requests and 400,000 GB-seconds per month are free. Even at 10 seconds per call at 256 MB, 10,000 calls use 25,000 GB-seconds, about 6% of the allowance. Cost: **$0**.
- **DynamoDB:** 25 GB of storage plus 25 read and 25 write capacity units. The allowance covers **provisioned** capacity, so create the table in provisioned mode with 1 to 5 units. Our quota counter writes one small item per day. Cost: **$0**.
- **The API layer:** a **Lambda function URL** is an HTTPS endpoint with no per-request charge of its own. What you give up is API Gateway's toolbox (usage plans, request validation, WAF attachment). A function URL with auth type `NONE` is a public endpoint, so put CloudFront in front of it with origin access control. Two details trip people up here. If the chat page is served from another origin, configure CORS on the function URL. And with origin access control, POST requests must carry an `x-amz-content-sha256` header with the body's SHA-256 hash, which the page computes before sending. But be clear about what that buys. It hides the raw endpoint; it does not stop anyone who opens your chat page from sending as many messages as they like. On a public chatbot, every visitor is a legitimate client.

### Put a ceiling on the worst case

Frugal design means the failure mode is priced too. My first draft capped the Lambda function at 2 concurrent executions and called the result a ceiling: two slots busy 24/7 for 30 days at 256 MB come to **about $15/month of compute, maximum**. That figure is correct and almost irrelevant. It caps the *compute*, not the *tokens*.

Two slots answering one chat every 3 seconds each make **1.73 million calls a month**. In tokens, that is:

| 24/7 abuse at concurrency 2, one call every 3 s per slot | Nova Micro | Haiku 5.5 | Opus 5.5 |
|---|---|---|---|
| Average chats (1,000 in / 400 out) | $157 | $518 | $20,736 |
| Chats at the handler's caps (~4,700 in / 1,024 out) | $532 | $1,697 | $67,876 |

An abuser won't send average chats. They will send the largest body you accept, and the model will use the output cap.

The model you choose sets your worst-case bill as well as your expected bill. Concurrency limits Lambda; it doesn't limit Bedrock spend enough. So the brake has to count **chats**. A daily quota in DynamoDB does it in one conditional write (the full function, with a test that it returns 429 at the limit, is in `demo/stage1/handler.py`):

```python
ddb.update_item(
    TableName=TABLE,
    Key={"pk": {"S": f"quota#{today}"}},
    UpdateExpression="ADD n :one",
    ConditionExpression="attribute_not_exists(n) OR n < :max",
    ExpressionAttributeValues={":one": {"N": "1"}, ":max": {"N": "500"}},
)   # ConditionalCheckFailedException -> return 429 "try again tomorrow"
```

With 500 chats a day, a month of average chats costs $1.37 on Nova Micro, $4.50 on Haiku, and $180 on Opus. If every chat hits the caps, the worst month is **$4.62 on Nova Micro, $14.73 on Haiku, and $589 on Opus**, plus the Lambda compute ceiling for rejected requests. That is a number you can state before you deploy. On Opus it is also a reason to lower the quota or the caps. Then add **an AWS Budgets alert** at an amount that would make you raise an eyebrow. $5 is a fine eyebrow. Budgets is an **alarm, not a brake**: billing data can arrive hours late, and an alert stops nothing by itself. The quota is the brake. The alarm tells you your assumptions were wrong.

What you give up: on a busy day, user number 501 gets "try again tomorrow." Whether 500 is the right number is a business decision, not a technical one.

**Stage 4 total: ≈ $0.91/month** (Nova Micro; everything else is inside free allowances at this volume), with a worst case you can state before you deploy.

We have optimized diligently. The model still costs money on every chat. There is one rung left.

## Stage 5: The last rung

If per-token pricing is the problem, remove the token meter. Modern browsers can run small language models on the visitor's own GPU through WebGPU. [WebLLM](https://github.com/mlc-ai/web-llm) (`@mlc-ai/web-llm`) packages this up. It downloads a quantized model into the browser, caches it, and exposes an OpenAI-style `chat.completions` API, entirely client-side.

To keep this the *same chatbot*, the page loads the same `faq.md` system prompt and uses the same trimming rule as the Lambda version. It also checks the GPU before it commits to a 700 MB download. The full page is in `demo/stage5/`:

```js
import { CreateMLCEngine } from "https://esm.run/@mlc-ai/web-llm@0.2.89";

const system = await (await fetch("./faq.md")).text();   // same prompt as the server

async function startLocal() {
  const adapter = await navigator.gpu?.requestAdapter();
  if (!adapter) throw new Error("no WebGPU");
  // The default q4f16 builds need the shader-f16 feature; pick a q4f32 build otherwise.
  const model = adapter.features.has("shader-f16")
    ? "Llama-3.2-1B-Instruct-q4f16_1-MLC" : "Llama-3.2-1B-Instruct-q4f32_1-MLC";
  const engine = await CreateMLCEngine(model, {
    initProgressCallback: (p) => { status.textContent = p.text; },
  });
  return async (messages, onToken) => {
    const chunks = await engine.chat.completions.create({
      messages: [{ role: "system", content: system }, ...trim(messages)],
      stream: true, max_tokens: 400,
    });
    let out = "";
    for await (const c of chunks) { out += c.choices[0]?.delta?.content ?? ""; onToken(out); }
    return out;
  };
}
// Load on intent (first click on "Start chat"), not on page load.
// If startLocal() fails, fall back to the Stage 4 function URL.
```

That's the whole chatbot. There is no API key, no backend, and no per-token anything. From WebLLM 0.2.89's model list and the Hugging Face file listings:

| Model | Download | GPU memory |
|---|---|---|
| Llama 3.2 1B (q4f16) | 705 MB | 879 MB |
| Llama 3.2 3B (q4f16) | 1.8 GB | 2.3 GB |
| Qwen3 0.6B (q4f16) | 352 MB | 1.4 GB |

Note that Qwen3 0.6B is smaller to download than Llama 1B but needs more GPU memory. All of these models run with a 4K-token context window.

### Does the floor hold? I measured this one

I ran the 30-question floor test on Llama 3.2 1B and 3B: same system prompt, same FAQ, 4-bit quantization, Llama's default sampling. I ran them locally with Ollama as a stand-in for the in-browser runtime. The quantization formats differ, so treat the numbers as indicative. Every answer was graded by reading it against a written rubric: a pass must be correct per the FAQ and invent nothing. The rubric and per-question grades are in `demo/eval/grades.md`.

| Model | Correct | **Confidently wrong** | Other failures (false refusals, off-topic answers, no answer) |
|---|---|---|---|
| Llama 3.2 1B | 13/30 | **11** | 6 |
| Llama 3.2 3B | 23/30 | **3** | 4 |

For a support bot, the middle column is the one that matters. A wrong answer delivered fluently is worse than "I don't know." Some of the 1B model's answers:

- It told a customer they had "already used your 30-day money-back guarantee." The FAQ says 14 days.
- It said there was no discount for paying yearly. The FAQ says annual billing saves 20%.
- It invented an Evernote import feature, with directions to "the import settings."
- It said the web app works offline. The FAQ says it needs a connection.

The 1B model **does not hold the floor**. It fails the floor item small models lose first: knowing what it doesn't know. The 3B model comes much closer: 23 of 30, with three confidently wrong answers. One of them is a mistranslation in Japanese. It costs 2.6 times the download.

Put that next to the Bedrock rungs. The cheapest model on the shelf, Nova Micro at $0.91 a month, gave one invented answer in 30 once its prompt was fixed. The 1B model gave 11, and its AWS bill is zero. At this traffic, the gap between them is less than a dollar a month.

An automatic keyword grader, by the way, scored the 1B model at 19 to 22 out of 30 across three runs. It passed five answers that put the right keyword next to an invented claim. Read your outputs.

### Will it even run?

I loaded the page in headless Chrome on a Linux PC with an Intel integrated GPU (the adapter reports "gen-7"). Read what follows with that machine in mind. It is a Mac running Linux, its GPU driver is unstable, and Chrome's hardware acceleration is turned off on it for that reason. WebGPU had to be forced on with `--enable-unsafe-webgpu` and Vulkan flags. This is not a normal user's setup. The page loaded and found an adapter. The default 1B build then failed to compile, because this GPU lacks the `shader-f16` feature that the q4f16 build needs. With the feature check above, the page picked the q4f32 build instead. The first load took 93 seconds, and a repeat load from the browser cache took 4 seconds. On an otherwise idle machine, it still produced **no answer within nine minutes**.

**The compile failure and the missing answer are this machine's problem, not a limit of WebLLM.** With hardware acceleration off, the browser was not really using the GPU. Most readers will run Chrome, Edge, or Safari with GPU acceleration on. That is the default, and it is the setup WebLLM targets. I couldn't measure that setup here, so I have no speed numbers for it, good or bad. What the test does show is the shape of the failure on a machine like mine: "WebGPU is available" is not the same as "the model answers." Visitors with machines like that exist, so the fallback needs a timeout, not only a feature check. I did not test a machine with GPU acceleration on, Safari, Firefox, or a phone.

### What's left on the bill

What remains on your AWS bill is the delivery of a static site: an HTML file, a script, and the FAQ.

```bash
aws s3 sync ./dist s3://your-chatbot-bucket --delete
# CloudFront in front of the bucket (origin access control), index.html as
# the default root object, long cache TTLs on hashed assets.
```

At 10,000 visits a month, that traffic sits comfortably inside CloudFront's always-free allowance (1 TB of transfer and 10 million requests per month), and S3 storage for a few files rounds to zero. **The chatbot's AWS bill is now effectively zero.**

The trick behind that number deserves to be stated out loud. WebLLM fetches the model weights from Hugging Face and the compiled GPU code from GitHub by default, so the one heavy asset never crosses your CloudFront bill. By the definition at the top of this article, that is close to *cheap*: someone else is paying for the transfer, and it depends on a service you don't control. If you self-host the weights, the delivery bill follows the number of *new visitors*, not chats:

- 2,000 first-time visitors × 0.7 GB = 1.4 TB → **about $32/month** after the free terabyte.
- 10,000 first-time visitors = 7 TB → **about $508/month**, which is more than Haiku would have cost for a year.

**Stage 5 total: $0 in inference and compute, and static delivery inside the free tier.** But the model that fits the budget does not hold the floor.

## The limits

A ladder you only climb down in the sales brochure is marketing, so here is what Stage 5 costs in the currencies that aren't dollars:

- **The first visit is heavy.** 705 MB for the 1B model, 1.8 GB for the 3B model that actually held the floor. It's cached afterwards, but a drive-by visitor may never finish loading. Load on intent, show progress, and prefer small models.
- **Browser support is broad, not universal.** WebGPU ships in Chrome and Edge, in Safari 26, and in Firefox on Windows. Older devices, many phones, GPUs without `shader-f16`, and browsers with hardware acceleration turned off will fail or crawl. My own test machine was in that last group (see "Will it even run?"), so its result says little about a typical visitor with GPU acceleration on. The best escape hatch is a **hybrid**: try the local model, and if WebGPU is missing or too slow, quietly fall back to your Stage 4 endpoint. The expensive path then serves only the visitors the free path can't.
- **Small models are confidently wrong.** The measurement above is the whole argument. For support triage with a human behind it, a 3B model may be acceptable. For refunds, billing, medical, legal, or financial answers, a 1B model is not.
- **You lose the server-side view.** You get no central logs of what users asked (unless you add analytics, carefully and with consent), no instant model upgrades, and no server-side guardrails. Anyone who opens DevTools can read your system prompt.
- **The user's battery is now your compute budget.** Inference is free to *you* because the visitor's GPU does the work. On a plugged-in laptop that's a fine trade. On a phone at 12% battery, be polite: small models, short answers, and no warm GPU when the tab is idle.

## Conclusion: the order is the lesson

Notice what we did *not* do. We didn't start with the last rung, and we didn't start with the cheapest model either. The ladder has an order, and the order is the frugal part:

1. **Start at the top** (Stage 1). Learn what "good" looks like for your traffic, and log `usage` from the first request.
2. **Walk down one rung at a time** (Stage 2), with a fixed question set, and stop at the first rung where the floor cracks for *your* questions; then step back up one. In my test, the floor held all the way down the Bedrock shelf, with cracks. The Haiku stand-in gave a contradictory refund answer, Nova Lite replied once in Spanish, and Nova Micro switched languages until a one-line prompt change fixed it. Nova Lite and gpt-oss-20b passed 28 and 29 of 30 for under $2 a month. Rerun the test every time you change the prompt, because the fix for one model broke another.
3. **Pull the free levers, and price the worst case** (Stages 3 and 4). Cache what is static, trim what grows, cap what is long, and put a quota in front of the token meter.

Most products should stop at Stage 2 or 3. A few dollars a month for a correct, logged, upgradeable chatbot is one of the great bargains in modern infrastructure. Stage 5 is for cases where something other than money is the constraint: no API key in the client, data that must not leave the device, offline use. Even then, my measurement says to choose the model by the floor, not by the download size.

Your homework, in the spirit of The Frugal Architect: take the formula from the introduction, plug in *your* chat count and *your* token counts, and run 30 of *your* questions down the ladder. The ladder is only useful if you know your rung.
