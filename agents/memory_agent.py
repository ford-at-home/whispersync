"""Memory Agent.

Stores personal memory transcripts as JSON lines in S3 and tags sentiment.
"""
from __future__ import annotations

import json
import logging
import datetime
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
def handle(payload: dict) -> dict:
    """Archive a memory transcript to S3."""
    transcript = payload.get("transcript", "")
    bucket = payload.get("bucket")
    now = datetime.datetime.utcnow().isoformat()
    record = {
        "timestamp": now,
        "text": transcript,
        "sentiment": "neutral",  # placeholder
    }

    key = f"memories/{now}.jsonl"
    logger.info("Writing memory record to %s", key)
    s3.put_object(Bucket=bucket, Key=key, Body=(json.dumps(record) + "\n").encode("utf-8"))
    return {"memory_key": key}
