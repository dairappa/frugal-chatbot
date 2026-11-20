#!/usr/bin/env python3
"""Filter raw AWS Price List dumps down to the rows the article uses.

    aws pricing get-products --region us-east-1 --service-code AmazonBedrock > /tmp/all-AmazonBedrock.json
    (same for AWSLambda, AmazonDynamoDB, AmazonCloudFront with a us-east-1 / United States filter)
    python3 extract.py /tmp/all-AmazonBedrock.json /tmp/p-AWSLambda.json ... > extract-2026-11-20.json

Keeps us-east-1 (or "United States" for CloudFront) standard on-demand rows only:
no batch, flex, priority, or long-TTL cache rows.
"""
import json, re, sys

KEEP_USAGE = re.compile(
    r"(?i)^(USE1-.*(kimi|deepseek|qwen|glm|gpt-oss|gemma|llama4|nemotron|minimax|ministral).*(input|output|cache-read)-tokens.*"
    r"|Lambda-GB-Second|Request|USE1-ReadRequestUnits|USE1-WriteRequestUnits|ReadRequestUnits|WriteRequestUnits|TimedStorage-ByteHrs"
    r"|US-DataTransfer-Out-Bytes|US-Requests-Tier2-HTTPS)$")
SKIP = re.compile(r"(?i)batch|flex|priority|30m|1h|latency")

rows = []
for path in sys.argv[1:]:
    for s in json.load(open(path))["PriceList"]:
        p = json.loads(s)
        a = p["product"]["attributes"]
        u = a.get("usagetype", "")
        if a.get("regionCode", "us-east-1") != "us-east-1" and a.get("fromLocation") != "United States":
            continue
        if not KEEP_USAGE.match(u) or SKIP.search(u + a.get("inferenceType", "")):
            continue
        for t in p["terms"].get("OnDemand", {}).values():
            for d in t["priceDimensions"].values():
                rows.append({"service": p["serviceCode"], "model": a.get("model"), "usagetype": u,
                             "unit": d["unit"], "usd": float(d["pricePerUnit"]["USD"]),
                             "begin": d["beginRange"], "end": d["endRange"], "desc": d["description"],
                             "effective": t["effectiveDate"][:10], "publication": p.get("publicationDate", "")[:10]})
rows.sort(key=lambda r: (r["service"], r["usagetype"], float(r["begin"])))
json.dump(rows, sys.stdout, indent=1)
