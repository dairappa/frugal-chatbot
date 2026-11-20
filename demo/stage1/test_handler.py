"""Offline checks for the Stage 1 handler. No AWS credentials needed: botocore's Stubber
validates every request against the real Bedrock Runtime / DynamoDB API schemas."""
import json
import os

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

import boto3
import pytest
from botocore.stub import Stubber
from botocore.exceptions import ParamValidationError

import handler


def conversation(turns):
    """turns user messages and turns-1 assistant replies, ending with the user: odd length."""
    msgs = []
    for i in range(turns):
        msgs.append({"role": "user", "text": f"q{i}"})
        if i < turns - 1:
            msgs.append({"role": "assistant", "text": f"a{i}"})
    return msgs


# --- the bug in the first draft -------------------------------------------------------

@pytest.mark.parametrize("turns", [4, 5, 10])
def test_draft_slice_starts_with_assistant(turns):
    """The draft used history[-6:]. The client always sends an odd number of messages
    (it ends with the user's new question), so from turn 4 on the slice starts with an
    assistant message. (Whether Bedrock rejects that is not verified live.)"""
    sliced = conversation(turns)[-6:]
    assert sliced[0]["role"] == "assistant"


@pytest.mark.parametrize("turns", range(1, 12))
def test_trim_history_always_starts_and_ends_with_user(turns):
    t = handler.trim_history(conversation(turns))
    assert t[0]["role"] == "user" and t[-1]["role"] == "user"
    assert len(t) <= handler.MAX_MESSAGES


def test_oversized_message_rejected_before_any_tokens_are_spent():
    with pytest.raises(handler.BadRequest):
        handler.trim_history([{"role": "user", "text": "x" * 50_000}])


def test_oversized_body_returns_413():
    r = handler.handler({"body": json.dumps({"messages": [{"role": "user", "text": "x" * 20_000}]})}, None)
    assert r["statusCode"] == 413


# --- request shapes against the real API schema ---------------------------------------

def stubbed_bedrock():
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return client, Stubber(client)


def test_fixed_request_matches_converse_schema():
    client, stub = stubbed_bedrock()
    req = handler.build_request(handler.trim_history(conversation(5)))
    stub.add_response("converse", {
        "output": {"message": {"role": "assistant", "content": [{"text": "ok"}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        "metrics": {"latencyMs": 1},
    }, req)
    with stub:
        client.converse(**req)
    assert "temperature" not in req["inferenceConfig"]
    assert "outputConfig" not in req   # EFFORT is off by default


def test_schema_alone_does_not_catch_the_draft_bugs():
    """Honesty check: the draft's request (temperature 0.7, assistant-first history) is
    *schema-valid*. Whether Bedrock rejects it is a service-side rule that only a live call
    shows -- this test documents that limit of offline validation."""
    client, stub = stubbed_bedrock()
    msgs = conversation(5)[-6:]
    req = dict(modelId="moonshotai.kimi-k2.5", system=[{"text": "s"}],
               messages=[{"role": m["role"], "content": [{"text": m["text"]}]} for m in msgs],
               inferenceConfig={"maxTokens": 512, "temperature": 0.7})
    stub.add_response("converse", {
        "output": {"message": {"role": "assistant", "content": [{"text": "ok"}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        "metrics": {"latencyMs": 1},
    }, req)
    with stub:
        client.converse(**req)  # no ParamValidationError


def test_schema_catches_a_real_shape_error():
    client, _ = stubbed_bedrock()
    with pytest.raises(ParamValidationError):
        client.converse(modelId="m", messages=[{"role": "user", "content": "plain string"}])


# --- the cost brake ------------------------------------------------------------------

def test_quota_returns_429_when_limit_reached(monkeypatch):
    client = boto3.client("dynamodb", region_name="us-east-1")
    stub = Stubber(client)
    monkeypatch.setattr(handler, "TABLE", "chat-quota")
    monkeypatch.setattr(handler, "_ddb", client)
    stub.add_client_error("update_item", "ConditionalCheckFailedException",
                          expected_params={
                              "TableName": "chat-quota",
                              "Key": {"pk": {"S": "quota#2026-11-19"}},
                              "UpdateExpression": "ADD n :one",
                              "ConditionExpression": "attribute_not_exists(n) OR n < :max",
                              "ExpressionAttributeValues": {":one": {"N": "1"}, ":max": {"N": "500"}},
                          })
    with stub:
        assert handler.take_quota("2026-11-19") is False
