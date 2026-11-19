# The Frugal Chatbot

*How cheap can an AI chatbot on AWS get? I start with the most expensive model available and step down until only the CloudFront bill remains. At each step I ask two questions: what did we give up, and does the bot still do its job?*

---

## The question

At re:Invent 2023, Werner Vogels introduced [The Frugal Architect](https://thefrugalarchitect.com/), seven laws for building systems that are cost-aware by design. The first law is *Make Cost a Non-functional Requirement*. In other words, decide what a system should cost while you design it, not after the first bill arrives.

So I gave myself a challenge: **what is the cheapest way to build an AI chatbot with today's AWS stack?**

Many teams start a new AI feature with the best model available, because nobody wants to explain why the demo failed. I start there too, with Claude Opus 5.5 on Amazon Bedrock, and then move down the price ladder one step at a time. At each step, I check one thing: **does the bot still meet its minimum requirements?** Spoiler: the last step deletes the server.

### The job: what "good enough" means

You cannot be frugal without a definition of "enough." Our example bot is a support assistant for a fictional company, Example Co. It must:

1. **Answer from the FAQ.** It answers product questions correctly from the FAQ text in its system prompt, and it says "I don't know" when the FAQ does not cover the question.
2. **Stay on topic.** It politely declines unrelated requests.
3. **Respond quickly.** The first useful text appears within a few seconds.
4. **Have a known cost limit.** Someone can say what the worst-case monthly bill is.

It does **not** need to write code, reason through multi-step problems, read images, or plan agent workflows. Remember this list. Every step down the ladder is judged against it.

### Ground rules (please read)

- **The numbers are estimates, not measurements.** I did not build a demo or run a load test. Each cost figure comes from published on-demand list prices multiplied by the workload below. Your bill will differ.
- **Workload:** 10,000 chats per month. One chat is one request and response: **1,000 input tokens** (system prompt plus history plus the user's message) and **400 output tokens**.
- **Claude prices** are Anthropic's published list prices for global endpoints. Amazon Bedrock sets its own prices for Claude, and regional endpoints cost 10% more than global ones. Check the Bedrock pricing page for your Region before you copy these numbers into a budget.
- **Amazon Nova and AWS service prices** are on-demand prices for US East (N. Virginia).
- **Thinking tokens are not included.** Current Claude models can use extended "thinking," which is billed as output tokens. My 400-token output assumption does not include those tokens. I discuss this in Step 1.
- **Scope:** I count only model inference and serving infrastructure. I do not count your time, and your time is often the largest cost of all.

---

## Step 1: Start at the top, Claude Opus 5.5 (about $120 per month)

The architecture is the same for every model step: one Lambda function that calls the Bedrock [Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html). It has no API Gateway, no containers, and no vector database. The browser sends the conversation, and Lambda returns the next message. Converse uses the same request format for every model, so changing the model is a configuration change, not a code change.

```js
// index.mjs — Node.js 22 runtime, AWS SDK for JavaScript v3
import {
  BedrockRuntimeClient,
  ConverseCommand,
} from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({});
// Model or inference profile ID, copied from the Bedrock console.
// The whole ladder in this article is a change to this one variable.
const MODEL_ID = process.env.MODEL_ID;

const SYSTEM = [
  { text: "You are a concise support assistant for Example Co. Answer only from the FAQ below. If the FAQ does not cover the question, say so. Answer in 3 sentences or fewer.\n\n<FAQ>...</FAQ>" },
];

export const handler = async (event) => {
  const { messages } = JSON.parse(event.body ?? "{}");
  // messages: [{ role: "user", content: [{ text: "Hi" }] }, ...]

  const res = await client.send(
    new ConverseCommand({
      modelId: MODEL_ID,
      system: SYSTEM,
      messages,
      inferenceConfig: { maxTokens: 400 },
    }),
  );

  return {
    statusCode: 200,
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      reply: res.output.message.content.find((b) => b.text)?.text ?? "",
      usage: res.usage, // inputTokens / outputTokens: log these, they ARE your bill
    }),
  };
};
```

Two details in this code matter for cost:

- `maxTokens: 400` sets a hard limit on output. Output tokens cost about five times as much as input tokens on Claude models, so this limit is a cost control, not only a style choice.
- `usage` is returned so that you can log it. Law IV says *Unobserved Systems Lead to Unknown Costs*. Token counts are the meter for this system, so record them from the first day.

The function's execution role needs `bedrock:InvokeModel` on the model or inference profile ARN.

**Cost (Claude Opus 5.5, $4 input / $20 output per 1M tokens):**

| Item | Tokens per month | Price per 1M | Cost |
|---|---|---|---|
| Input | 10,000 × 1,000 = 10M | $4.00 | $40.00 |
| Output | 10,000 × 400 = 4M | $20.00 | $80.00 |
| **Total** | | | **$120.00** |

**What we give up:** nothing. This is the starting point.

**Minimum requirements:** all met, with a large margin. Opus 5.5 can do everything on our list and much more that the list does not ask for: long multi-step reasoning, agentic coding, analysis of large documents. We pay for all of that capability on every FAQ answer.

**One hidden cost.** Opus 5.5 always uses adaptive thinking, and you cannot turn it off. You can only lower the effort level. Thinking tokens are billed as output, at $20 per 1M. They also count toward `maxTokens`, so with a 400-token limit, a long thinking pass can cut off the visible answer. For a FAQ bot, use the lowest effort level and measure real `outputTokens` before you trust the $120 figure. The real number is probably higher.

---

## Step 2: Claude Sonnet 5.5 (about $60 per month)

| Item | Tokens | Price per 1M | Cost |
|---|---|---|---|
| Input | 10M | $2.00 | $20.00 |
| Output | 4M | $10.00 | $40.00 |
| **Total** | | | **$60.00** |

**What we give up:** the top level of reasoning depth. On the hardest multi-step problems, Sonnet is less capable than Opus. Our bot never gets those problems.

**Minimum requirements:** all met. Answering from a FAQ, staying on topic, and keeping a polite tone are easy tasks for Sonnet. Sonnet 5.5 also lets you turn off thinking between tool calls, so the "thinking tax" from Step 1 is easier to control.

Half the cost, and the users see no difference. This is often where teams stop, because the bill "looks reasonable." We continue.

---

## Step 3: Claude Haiku 5.5 (about $3.00 per month)

| Item | Tokens | Price per 1M | Cost |
|---|---|---|---|
| Input | 10M | $0.10 | $1.00 |
| Output | 4M | $0.50 | $2.00 |
| **Total** | | | **$3.00** |

This is the biggest drop on the whole ladder: **95% less than Sonnet and 97.5% less than Opus**. It is not a clever technique. We simply answered the question "how much model does this job need?"

**What we give up:** more reasoning depth and some precision in long or ambiguous instructions. Haiku also has a pricing trap: prompts over 100,000 tokens cost five times more ($0.50 input / $2.50 output). If you add a full product manual to every request, the price jumps. Our 1,000-token prompt stays far below that limit.

**Minimum requirements:** probably met, but now you must *verify* it. Collect 20–30 real customer questions, including some that the FAQ does not cover and some that are off topic. Run them through Sonnet and Haiku, and read the answers. Check requirement 1 most carefully: does Haiku say "I don't know," or does it invent an answer? A cheap model that invents answers costs you support tickets, and support tickets cost more than tokens.

Law III says *Architecting is a Series of Trade-offs*. Steps 1–3 show that the most valuable trade-off is usually the first one: choosing the model.

---

## Step 4: Change model families, Amazon Nova Lite and Nova Micro (about $1.56 and $0.91 per month)

Haiku is the smallest Claude model. To go lower, we must change to a different model family. Amazon Nova models are AWS's own models on Bedrock, and they are cheaper again.

**Nova Lite** (multimodal):

| Item | Tokens | Price per 1M | Cost |
|---|---|---|---|
| Input | 10M | $0.06 | $0.60 |
| Output | 4M | $0.24 | $0.96 |
| **Total** | | | **$1.56** |

**Nova Micro** (text only, smaller context window):

| Item | Tokens | Price per 1M | Cost |
|---|---|---|---|
| Input | 10M | $0.035 | $0.35 |
| Output | 4M | $0.14 | $0.56 |
| **Total** | | | **$0.91** |

Because we used the Converse API, the change is one environment variable:

```bash
aws lambda update-function-configuration \
  --function-name frugal-chat \
  --environment "Variables={MODEL_ID=amazon.nova-micro-v1:0}"
```

**What we give up:** the model family. This is a bigger change than moving from Sonnet to Haiku. Prompts that worked well on Claude can produce a different tone, format, or refusal behavior on Nova. You must test the prompt again, not only the model. Nova Micro also cannot read images and has a smaller context window.

**Minimum requirements:** you must test again. A short, well-structured FAQ bot can usually meet the bar on Nova Lite. Nova Micro is the "cheapest that might still work" option. Use the same 20–30 question test from Step 3. If Micro fails requirement 1, Nova Lite at $1.56 is the frugal choice, even though Micro costs less.

From here, we save less money with each step. Moving from Haiku to Micro saves about $2 per month, while moving from Sonnet to Haiku saved $57. Remember this when you decide how much engineering time to spend on the next steps.

---

## Step 5: Levers on the token bill

The model is chosen. The bill is now tokens × price, and there are two more ways to reduce the tokens.

### Lever 1: Prompt caching (about $1.29 per month on Nova Lite)

Every request sends the same system prompt again. With [prompt caching](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html), Bedrock can bill a repeated prefix at the cache-read rate. For Nova Lite, that rate is $0.015 per 1M tokens, which is one quarter of the normal input price.

Add a cache checkpoint after the static part of the prompt:

```js
const SYSTEM = [
  { text: LONG_STATIC_INSTRUCTIONS_AND_FAQ }, // must be >= 1K tokens to be cacheable on Nova
  { cachePoint: { type: "default" } },
];
// After each call, check res.usage.cacheReadInputTokens / cacheWriteInputTokens
```

If 60% of each request's input (6M of the 10M tokens) is a cache read, the Nova Lite bill becomes:

| Item | Tokens | Price per 1M | Cost |
|---|---|---|---|
| Input, cache read | 6M | $0.015 | $0.09 |
| Input, uncached | 4M | $0.06 | $0.24 |
| Output | 4M | $0.24 | $0.96 |
| **Total** | | | **$1.29** |

That saves 17%. Before you count on it, check two conditions that a price table does not show:

1. **Minimum prefix size.** For Nova models, a cache checkpoint is used only when the prefix before it is at least **1K tokens**. In our 1,000-token example, a 600-token system prompt would *not* be cached. Caching helps when you have a large static prompt, such as a 2,000-token FAQ. It does not help with a short instruction. Treat $1.29 as the result for a workload with a large shared prefix, not as a free discount.
2. **Cache lifetime and traffic.** The cache lasts 5 minutes after the last use. 10,000 chats per month is about 14 per hour on average, so at night the cache will often expire between requests. Your cache hit rate depends on your traffic pattern, not only on your code.

Caching matters more at the top of the ladder. Claude Opus 5.5 and Sonnet 5.5 bill cache reads at 5% of the input price, but input is only one third of their bill in our workload. On every model in this article, **output is the larger part of the bill**. Caching alone cannot fix that.

**What we give up:** some simplicity. Caching adds a prompt structure that you must keep stable. **Minimum requirements:** not affected.

### Lever 2: Trim the conversation history

This lever does not have a single number because it prevents growth instead of reducing a fixed cost. The Converse API is stateless: each turn you send the *whole* conversation again. Without a limit, input tokens grow quadratically with conversation length.

Example: a 300-token system prompt, 100-token user messages, and 400-token answers.

- **No limit:** a 10-turn conversation bills about **26,500** input tokens in total.
- **Keep only the last 2 exchanges:** the same conversation bills about **12,500**.

Our 1,000-token average holds only if something enforces it. A few lines of code do that:

```js
const MAX_MESSAGES = 4; // last 2 user/assistant exchanges
let trimmed = messages.slice(-MAX_MESSAGES);
// Converse requires the first message to come from the user
while (trimmed.length && trimmed[0].role !== "user") trimmed = trimmed.slice(1);
```

Also reject oversized requests (for example, `event.body.length > 8_000`) before you call Bedrock. Otherwise, your token budget is controlled by whoever writes the longest message.

**What we give up:** long-term memory. The bot forgets what the user said six messages ago. **Minimum requirements:** still met. FAQ questions rarely depend on distant context.

**Total after Step 5:** Nova Micro with a history limit costs about **$0.91 per month**, with a known maximum number of tokens per request.

---

## Step 6: Design to fit in the free tier

The model costs less than a dollar now. What about the infrastructure around it?

| Service | Always-free allowance (per month) | Our usage |
|---|---|---|
| AWS Lambda | 1M requests + 400,000 GB-seconds | 10,000 requests; 10,000 × 2 s × 0.125 GB = 2,500 GB-s |
| Amazon DynamoDB | 25 GB storage, 25 provisioned RCU + 25 WCU | One small counter item per day |
| Lambda function URL | No extra charge (normal Lambda pricing applies) | Replaces API Gateway |

The design choices:

- **Use a Lambda function URL instead of API Gateway.** This gives you one HTTPS endpoint without another service to pay for. If you want it on your own domain, put CloudFront in front of it with origin access control.
- **Use DynamoDB in provisioned mode** at 1–5 RCU/WCU, because the always-free allowance applies to provisioned capacity, not to on-demand capacity.
- **Use 128 MB of memory.** The function only waits for a network call, so more memory does not make it faster.

The infrastructure costs **$0.00**. The bill is now only Bedrock tokens: **about $0.91**.

### Calculate the worst case, not only the expected case

Requirement 4 says that someone must know the worst-case bill. A function URL with `AuthType: NONE` is a public endpoint. The expected case is 10,000 chats. What is the *worst* case?

Set **reserved concurrency to 2**. If each call takes about 2 seconds, the function can run at most about 1 request per second:

- Maximum requests per month: 1 × 2,678,400 s (31 days) ≈ **2.68M**
- Bedrock (Nova Micro, $0.000091 per chat with input capped): **≈ $244**
- Lambda above the free tier: about 1.68M extra requests × $0.20/M + about 270,000 extra GB-s × $0.0000166667 ≈ **$4.83**

So the limit is about **$249 per month**. That is a real limit, but it is too high to ignore. Concurrency limits Lambda. It does not limit Bedrock spend enough.

Compare this with the top of the ladder. With Claude Opus 5.5 at $0.012 per chat, the same 2.68M requests cost about **$32,000**. The model you choose sets your worst-case bill as well as your expected bill.

Law V says *Cost Aware Architectures Implement Cost Controls*. So add a control that limits *chats*, not CPU. Use a daily quota counter in DynamoDB:

```js
import { DynamoDBClient, UpdateItemCommand } from "@aws-sdk/client-dynamodb";
const ddb = new DynamoDBClient({});
const DAILY_LIMIT = 500;

async function takeQuota() {
  const day = new Date().toISOString().slice(0, 10);
  try {
    await ddb.send(new UpdateItemCommand({
      TableName: process.env.TABLE,
      Key: { pk: { S: `quota#${day}` } },
      UpdateExpression: "ADD n :one",
      ConditionExpression: "attribute_not_exists(n) OR n < :max",
      ExpressionAttributeValues: { ":one": { N: "1" }, ":max": { N: String(DAILY_LIMIT) } },
    }));
    return true;
  } catch (e) {
    if (e.name === "ConditionalCheckFailedException") return false; // return 429 to the caller
    throw e;
  }
}
```

Now the worst case is 500 × 31 = 15,500 chats × $0.000091 ≈ **$1.41** of Bedrock spend, plus the same Lambda limit of about $4.83 for rejected requests. The worst-case bill is about **$6 per month**, and you can calculate it before you deploy. (With the same quota, Opus 5.5 would have a worst case of about $191. The quota protects you on any model.)

Finally, create an **AWS Budgets** cost budget, for example $5 per month, with email alerts at 80% of actual spend and 100% of forecasted spend. Note that Budgets is an **alarm, not a brake**. Billing data can arrive hours late, and a budget alert does not stop anything by itself. The quota counter is the brake. The budget tells you when your assumptions were wrong (Law VII: *Unchallenged Success Leads to Assumptions*).

**What we give up:** availability. On a busy day, user number 501 gets a "try again tomorrow" message. **Minimum requirements:** requirement 4 is now fully met for the first time. Requirements 1–3 still hold for the first 500 users each day. Whether 500 is the right number is a business decision, not a technical one (Law II: *Systems that Last Align Cost to Business*).

---

## Step 7: Delete the server (CloudFront is the only bill)

Every step so far still pays for tokens. The last step removes tokens from the bill completely: **run the model in the visitor's browser.**

[WebLLM](https://github.com/mlc-ai/web-llm) (`@mlc-ai/web-llm`) runs quantized open-weight models on the GPU through WebGPU. It provides an OpenAI-style chat API. The whole "backend" is a static site:

```js
import { CreateMLCEngine } from "@mlc-ai/web-llm";

const engine = await CreateMLCEngine("Llama-3.2-1B-Instruct-q4f16_1-MLC", {
  initProgressCallback: (p) => (status.textContent = p.text), // the first load takes a while
});

const messages = [
  { role: "system", content: "You are a concise support assistant for Example Co." },
  { role: "user", content: input.value },
];

const stream = await engine.chat.completions.create({ messages, stream: true, max_tokens: 400 });
let reply = "";
for await (const chunk of stream) {
  reply += chunk.choices[0]?.delta?.content ?? "";
  output.textContent = reply;
}
```

Build the site, upload the `dist/` folder to a private S3 bucket, and serve it through CloudFront with origin access control. That is the whole architecture.

**Cost:** assume 2,000 visitors produce our 10,000 chats, and the page plus JavaScript bundle is about 5 MB. That is about 10 GB of transfer and a few thousand requests. The CloudFront always-free tier is 1 TB of data transfer out and 10M requests per month, and transfer from S3 to CloudFront is free. S3 storage for a few MB costs a fraction of a cent.

**Estimated monthly bill: $0.00 to a few cents.** No Lambda, no Bedrock, no DynamoDB. CloudFront is the only line item.

### The honest trick

The 5 MB figure is a little misleading, and you should know why.

The page is 5 MB, but the model is not. With WebLLM's default configuration, **the model weights download from Hugging Face's CDN, and the compiled WebGPU library downloads from GitHub.** They do not pass through your CloudFront distribution. Your bill is close to zero partly because someone else pays for most of the transfer.

If you want to host everything yourself, for control, availability, or policy reasons, add a custom `appConfig` that points `model` and `model_lib` to your own distribution:

```js
const appConfig = {
  model_list: [{
    model_id: "Llama-3.2-1B-Instruct-q4f16_1-MLC",
    model: "https://chat.example.com/models/Llama-3.2-1B-Instruct-q4f16_1-MLC/",
    model_lib: "https://chat.example.com/libs/<the matching .wasm from prebuiltAppConfig>",
  }],
};
const engine = await CreateMLCEngine("Llama-3.2-1B-Instruct-q4f16_1-MLC", { appConfig });
```

Then calculate again. 2,000 first-time visitors × about 0.7 GB = **about 1.4 TB**. The first 1 TB is free. The remaining 0.4 TB at $0.085/GB costs **about $34 per month**. That is more than Haiku 5.5 and much more than Nova Micro.

The browser caches the weights after the first load, so returning visitors cost nothing. However, the cost now depends on the number of *new visitors*, not the number of *chats*. That is a different cost model, and it is worse for a public site with many one-time visitors.

**What we give up:** almost everything that the earlier steps protected. See the next section.

**Minimum requirements:** requirement 4 is met in the most extreme way, because the server-side cost limit is about zero. Requirement 1 is at risk: a 1B-parameter model invents answers far more often than any model above it. Requirement 3 fails on the first visit, because nobody waits for a 700 MB download to get a FAQ answer.

---

## The honest limits

Step 7 is cheap for you, but the user pays in other ways:

- **The first load is about 700 MB.** On mobile data, that is unacceptable. On a slow connection, the first answer can take minutes. Show a progress bar and an honest explanation.
- **WebGPU support is not universal.** Recent desktop Chromium browsers support it. Safari and Firefox support has improved but is still uneven, and many phones and older laptops cannot run the model well. You need a fallback, and the obvious fallback is Step 6.
- **Quality.** A 4-bit 1B-parameter model is in a different class from even the smallest Bedrock model in this article. It can handle short, guided answers. It makes mistakes with facts, multi-step reasoning, and languages other than English. For support, where a wrong answer costs money, this may not be acceptable.
- **Battery and heat.** Inference runs on the visitor's GPU. Generating a few hundred tokens on a laptop is fine. Generating for a long time on a phone is not.
- **Control and observability.** You cannot see token usage, you cannot update the model for everyone at once, and anyone who opens DevTools can read your system prompt.

---

## Conclusion: the order is the lesson

| Step | Setup | Estimated cost per month | Minimum requirements |
|---|---|---|---|
| 1 | Claude Opus 5.5 | $120.00 (plus thinking tokens) | Met, with far more capability than needed |
| 2 | Claude Sonnet 5.5 | $60.00 | Met |
| 3 | Claude Haiku 5.5 | $3.00 | Probably met. Test it. |
| 4 | Nova Lite / Nova Micro | $1.56 / $0.91 | Test again with the new model family |
| 5 | + caching (large prefix) and history limit | $1.29 (Lite) / $0.91 (Micro) | Met, with less memory |
| 6 | + free tier, quota, budget alarm | $0.91, worst case about $6 | All four met, including cost limit |
| 7 | WebLLM in the browser, S3 + CloudFront | about $0 / about $34 if self-hosted | Accuracy and speed at risk |

The final $0 is not the interesting part. The order is.

- **The largest saving was a decision, not engineering.** Moving from Opus to Haiku removed 97.5% of the bill and needed one environment variable. Everything after Step 3 saved about $2 per month in total.
- **Each step changed what we gave up.** First we gave up capability we did not need. Then we gave up the model family that we had tested. Then we gave up unlimited availability in exchange for a known worst case. Finally, we moved compute to our users' devices and bandwidth to other companies' CDNs.
- **"Enough" must be written down.** Without the four requirements, every step would be an opinion. With them, every step is a test that passes or fails.
- **Cheap is not the same as frugal.** A frugal architecture is not the one with the smallest bill. It is the one where you know what you pay, why you pay it, and the maximum you can pay. Step 6, with a $6 worst case, is more frugal than Step 7, with a "$0" that depends on someone else's CDN and a $34 surprise if you host the weights yourself. Step 6 is also more frugal than Step 1 with no quota, which has an expected bill of $120 and a worst case of $32,000.

For most real chatbots, I would stop at Step 6: the cheapest model that passes your question set (Haiku 5.5, Nova Lite, or Nova Micro), a history limit, a quota counter, and a budget alarm. It costs a few dollars at most, the maximum is calculated, and you can still see your system working. Use Step 7 when privacy or offline use is a feature, not only because it is cheap.

Start with the requirement, not the model. Make cost a requirement and design for it.

---

<!--
EDITORIAL NOTES (delete before publishing)

- All figures are calculated from list prices, not measured. The ground rules section says this; keep it.
- PRICE VERIFICATION (checked 2026-11-19):
  - CONFIRMED (Anthropic official pricing page, platform.claude.com/docs/en/about-claude/pricing, first-party API list prices):
    Claude Opus 5.5 $4 input / $20 output / $0.20 cache hit per MTok.
    Claude Sonnet 5.5 $2 / $10 / $0.10.
    Claude Haiku 5.5 $0.10 / $0.50 / $0.01 for prompts up to 100K tokens; $0.50 / $2.50 above 100K.
    Cache hits on Opus 5.5 and Sonnet 5.5 are 0.05x the input price. The same page says Bedrock has independent pricing and that regional endpoints cost 10% more than global endpoints.
  - NOT CONFIRMED: Claude prices *on Amazon Bedrock*. The article uses Anthropic's list prices as a proxy and says so in the ground rules. Secondary sources match for Sonnet 5.5 ($2/$10) and Haiku 5.5 ($0.10/$0.50) on Bedrock, but they disagree for Opus 5.5 (one lists $4.40/$22; another says Opus 5.5 on Bedrock is billed through AWS Marketplace). Check the Bedrock pricing page in a browser. If Bedrock prices differ, recalculate Steps 1–3, the Opus worst case ($32,000 = 2,678,400 × $0.012), and the Opus quota worst case ($191 = 15,500 × $0.012 + $4.83, rounded).
  - NOT CONFIRMED: Bedrock model or inference profile IDs for Claude Opus/Sonnet/Haiku 5.5. The code reads the ID from MODEL_ID on purpose. Do not publish a guessed ID.
  - NOT CONFIRMED: How to set Claude effort / thinking options through the Converse API (probably additionalModelRequestFields). The article describes this in prose only. Add code only after you check the Bedrock documentation.
  - CONFIRMED on official pages: Lambda free tier (1M requests + 400,000 GB-s/month), $0.20/1M requests, $0.0000166667/GB-s (aws.amazon.com/lambda/pricing/). CloudFront always-free tier: 1 TB transfer out + 10,000,000 requests/month; the next 9 TB in US/MX/CA costs $0.085/GB (aws.amazon.com/cloudfront/pricing/pay-as-you-go/). Nova prompt caching: 1K-token minimum per checkpoint, 5-minute TTL (docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html). Law titles match thefrugalarchitect.com/laws/.
  - NOT CONFIRMED: Nova Pro/Lite/Micro input/output prices and the Nova Lite cache-read price ($0.015/1M). The Bedrock pricing page loads its tables with JavaScript, and the Nova tables did not appear in the fetched content. The input/output prices match an older AWS blog post (secondary source, possibly outdated).
  - NOT CONFIRMED: DynamoDB always-free allowance (25 GB, 25 RCU/WCU), that Lambda function URLs have no extra charge, and whether Budgets without actions are free.
  - Note: CloudFront's new flat-rate "Free plan" (1M requests, 100 GB) is a different offer from the 1 TB always-free tier on pay-as-you-go. The article uses pay-as-you-go.
- The prompt caching example ($1.29) assumes 60% of input tokens are cache reads. Under Nova's 1K-token minimum per checkpoint, this requires a shared prefix of at least 1K tokens, which is more than our 1,000-token average request. The article states this caveat explicitly.
- The ~700 MB download size for Llama-3.2-1B-Instruct-q4f16_1-MLC comes from secondary sources (about 695 MB). Confirm it in WebLLM's prebuiltAppConfig (src/config.ts) before publishing.
- The "5 MB bundle" figure is an assumption. Check it with a real `vite build` if possible.
- New AWS accounts created after 2025-07-15 use the new Free Tier (credits + Free/Paid plans). Confirm that the Lambda and DynamoDB always-free allowances still apply to the target audience's account type.
- The model quality statements ("probably met", "test again") are not measured. They are framed as things the reader must verify. Keep that framing unless you run the 20–30 question test yourself.
-->
