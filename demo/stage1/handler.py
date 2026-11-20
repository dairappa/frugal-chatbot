"""Stage 1 backend for the Frugal Chatbot: one Lambda function behind a function URL.

Changes from the first draft of the article:
- no `temperature` (a FAQ bot gains nothing from sampling tweaks, and some models reject them)
- the history is trimmed so that it always starts with a user turn (Converse requirement)
- request size is capped *before* any token is spent
- a daily quota in DynamoDB is the cost brake; AWS Budgets is only the alarm
"""
import datetime
import json
import os
import pathlib

import boto3

MODEL_ID = os.environ.get("MODEL_ID", "global.moonshotai.kimi-k3")  # verify the ID in your Region
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))   # leaves room for reasoning tokens
MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES", "7"))  # 3 exchanges + the new question
MAX_CHARS_PER_MESSAGE = 2_000
MAX_BODY_BYTES = 16_000
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "500"))
TABLE = os.environ.get("TABLE")  # unset -> no quota (local tests only)
EFFORT = os.environ.get("EFFORT", "")  # only for models that accept outputConfig.effort; most reject it

SYSTEM_PROMPT = (pathlib.Path(__file__).with_name("faq.md")).read_text() \
    if pathlib.Path(__file__).with_name("faq.md").exists() else os.environ.get("SYSTEM_PROMPT", "")

_bedrock = None
_ddb = None


def bedrock():
    global _bedrock
    _bedrock = _bedrock or boto3.client("bedrock-runtime")
    return _bedrock


def ddb():
    global _ddb
    _ddb = _ddb or boto3.client("dynamodb")
    return _ddb


class BadRequest(Exception):
    pass


def trim_history(history, max_messages=MAX_MESSAGES):
    """Keep the last `max_messages` turns, starting with a user turn, ending with a user turn."""
    clean = []
    for m in history:
        if m.get("role") not in ("user", "assistant") or not isinstance(m.get("text"), str):
            raise BadRequest("each message needs role user|assistant and a text string")
        if len(m["text"]) > MAX_CHARS_PER_MESSAGE:
            raise BadRequest(f"message longer than {MAX_CHARS_PER_MESSAGE} characters")
        clean.append(m)
    trimmed = clean[-max_messages:]
    while trimmed and trimmed[0]["role"] != "user":
        trimmed = trimmed[1:]
    if not trimmed or trimmed[-1]["role"] != "user":
        raise BadRequest("the last message must come from the user")
    return trimmed


def take_quota(today=None):
    """Atomically count today's chats. Returns False once DAILY_LIMIT is reached."""
    if not TABLE:
        return True
    day = today or datetime.date.today().isoformat()
    try:
        ddb().update_item(
            TableName=TABLE,
            Key={"pk": {"S": f"quota#{day}"}},
            UpdateExpression="ADD n :one",
            ConditionExpression="attribute_not_exists(n) OR n < :max",
            ExpressionAttributeValues={":one": {"N": "1"}, ":max": {"N": str(DAILY_LIMIT)}},
        )
        return True
    except ddb().exceptions.ConditionalCheckFailedException:
        return False


def build_request(messages):
    req = dict(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": m["role"], "content": [{"text": m["text"]}]} for m in messages],
        inferenceConfig={"maxTokens": MAX_TOKENS},
    )
    if EFFORT:
        req["outputConfig"] = {"effort": EFFORT}
    return req


def reply(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)}


def handler(event, context):
    raw = event.get("body") or "{}"
    if len(raw.encode()) > MAX_BODY_BYTES:
        return reply(413, {"error": "request too large"})
    try:
        messages = trim_history(json.loads(raw).get("messages", []))
    except (BadRequest, ValueError, AttributeError) as e:
        return reply(400, {"error": str(e)})
    if not take_quota():
        return reply(429, {"error": "daily chat limit reached, please try again tomorrow"})

    response = bedrock().converse(**build_request(messages))
    text = "".join(b.get("text", "") for b in response["output"]["message"]["content"])
    # usage is the meter for this system: log it from day one
    print(json.dumps({"usage": response["usage"], "stopReason": response.get("stopReason")}))
    return reply(200, {"answer": text, "usage": response["usage"]})
