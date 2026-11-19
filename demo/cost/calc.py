#!/usr/bin/env python3
"""Recompute every dollar figure in the Frugal Chatbot article. Writes figures.json."""
import json, math, pathlib
HERE = pathlib.Path(__file__).parent
P = json.loads((HERE / "prices.json").read_text())
M, AWS = P["models"], P["aws"]
OPUS, SONNET, HAIKU, LITE, MICRO, GPTOSS = list(M)
CHATS, IN, OUT = 10_000, 1_000, 400
MONTH_S = 30 * 24 * 3600
F = {}

def per_chat(m, tin=IN, tout=OUT, cached=0, hit=1.0):
    """cached = tokens of static prefix behind a cache point; hit = cache hit rate."""
    p = M[m]
    fresh = tin - cached
    prefix = cached * (hit * p["cr"] + (1 - hit) * p["cw"]) if cached else 0.0
    return (fresh * p["in"] + prefix + tout * p["out"]) / 1e6

def put(key, val, note=""):
    F[key] = round(val, 4)
    print(f"{key:<46} {val:>12,.4f}  {note}")

print("== Ladder (10,000 chats, 1,000 in / 400 out) ==")
for m in M:
    put(f"ladder.{M[m]['name']}", per_chat(m) * CHATS, f"per chat ${per_chat(m):.6f}")
for n in (100_000, 1_000_000):
    for m in M:
        put(f"scale{n}.{M[m]['name']}", per_chat(m) * n)

for k, label in (("anthropic.claude-opus-4-6-v1", "opus46"), ("anthropic.claude-sonnet-4-6", "sonnet46"), ("anthropic.claude-haiku-4-5-20251001-v1:0", "haiku45")):
    pp = P["proxies"][k]
    put(f"proxy.{label}", (IN * pp["in"] + OUT * pp["out"]) / 1e6 * CHATS, "stand-in model at the same workload")
put("ladder.saved_first_two_rungs", (per_chat(OPUS) - per_chat(HAIKU)) * CHATS)
print("\n== Thinking tokens (hidden output) on Opus ==")
for extra in (200, 1000):
    put(f"thinking+{extra}.opus", per_chat(OPUS, tout=OUT + extra) * CHATS)

print("\n== Lever 1: caching ==")
# Our FAQ prompt is ~515-700 tokens: below Nova's 1K checkpoint minimum -> no caching on Nova.
put("cache.draft_claim.nova_lite_600_at_100pct", per_chat(LITE, cached=600) * CHATS, "draft's $1.29 -- not reachable: 600 < 1K minimum")
# Hit rate: Poisson arrivals, entry survives if next request starts within TTL (5 min).
gap_flat = MONTH_S / CHATS / 60
gap_day = gap_flat / 2   # all traffic in 12 waking hours
hit_flat, hit_day = 1 - math.exp(-5 / gap_flat), 1 - math.exp(-5 / gap_day)
put("cache.mean_gap_min", gap_flat); put("cache.hit_flat", hit_flat); put("cache.hit_12h", hit_day)
# Larger-prefix scenario: 2,000-token static FAQ + 400 dynamic tokens = 2,400 input.
BIG, PREFIX = 2_400, 2_000
for m, label in ((OPUS, "opus"), (HAIKU, "haiku"), (LITE, "nova_lite")):
    put(f"bigprefix.{label}.nocache", per_chat(m, tin=BIG) * CHATS)
    put(f"bigprefix.{label}.cache_100", per_chat(m, tin=BIG, cached=PREFIX, hit=1.0) * CHATS)
    put(f"bigprefix.{label}.cache_flat", per_chat(m, tin=BIG, cached=PREFIX, hit=hit_flat) * CHATS)
    put(f"bigprefix.{label}.cache_12h", per_chat(m, tin=BIG, cached=PREFIX, hit=hit_day) * CHATS)
put("cache.opus_600_at_100pct", per_chat(OPUS, cached=600) * CHATS, "Claude 5.5 min on Bedrock: 512")
for m, label in ((LITE, "nova_lite"), (MICRO, "nova_micro")):
    put(f"cache.{label}_600_100pct", per_chat(m, cached=600) * CHATS, "measured: Nova caches a ~540-token prefix in-region")
    put(f"cache.{label}_600_flat_upper", per_chat(m, cached=600, hit=hit_flat) * CHATS, "writes billed at input price = upper bound")
put("cache.opus_600_flat", per_chat(OPUS, cached=600, hit=hit_flat) * CHATS)
put("cache.opus_600_12h", per_chat(OPUS, cached=600, hit=hit_day) * CHATS)

print("\n== Lever 2: history ==")
put("history.nova_lite_5x_input", per_chat(LITE, tin=5 * IN) * CHATS, "draft said 'nearly $8'")
put("history.opus_5x_input", per_chat(OPUS, tin=5 * IN) * CHATS)

print("\n== Routing (80% Micro, 20% escalate to Haiku) ==")
put("routing.classify_first", (0.8 * per_chat(MICRO) + 0.2 * per_chat(HAIKU)) * CHATS, "free, perfect classifier")
put("routing.answer_then_escalate", (per_chat(MICRO) + 0.2 * per_chat(HAIKU)) * CHATS, "escalated chats pay twice")

print("\n== Worst case: reserved concurrency 2, abuse 24/7 ==")
lam = 2 * 0.25 * MONTH_S
put("ceiling.lambda_compute_only", (lam - AWS["lambda_free_gb_s"]) * AWS["lambda_gb_s"], "draft's $15")
for sec in (0.8, 3, 10):
    calls = 2 * MONTH_S / sec
    put(f"ceiling.calls@{sec}s", calls)
    for m, label in ((MICRO, "micro"), (HAIKU, "haiku"), (OPUS, "opus")):
        put(f"ceiling.tokens@{sec}s.{label}", calls * per_chat(m))
# Capped chat: what the Stage 1 handler lets one request cost at most.
# 16,000-byte body (~4 bytes/token for English) + ~700-token system prompt in; maxTokens 1,024 out.
CAP_IN, CAP_OUT = 16_000 // 4 + 700, 1_024
calls = 2 * MONTH_S / 3
for m, label in ((MICRO, "micro"), (HAIKU, "haiku"), (OPUS, "opus")):
    put(f"ceiling.capped@3s.{label}", calls * per_chat(m, CAP_IN, CAP_OUT))
QUOTA = 500
for m, label in ((MICRO, "micro"), (HAIKU, "haiku"), (OPUS, "opus")):
    put(f"quota{QUOTA}.month.{label}", QUOTA * 30 * per_chat(m))
    put(f"quota{QUOTA}.month.capped.{label}", QUOTA * 30 * per_chat(m, CAP_IN, CAP_OUT))

print("\n== Free tier check ==")
for sec in (0.8, 3, 10):
    put(f"lambda.gb_s@{sec}s_256MB", CHATS * sec * 0.25, "free: 400,000")

print("\n== Self-hosted model weights (CloudFront) ==")
for visitors in (2_000, 10_000):
    gb = visitors * 0.7
    put(f"selfhost.{visitors}_visitors_gb", gb)
    put(f"selfhost.{visitors}_visitors_usd", max(0, gb - AWS["cloudfront_free_gb"]) * AWS["cloudfront_per_gb_after"])

(HERE / "figures.json").write_text(json.dumps(F, indent=1))
