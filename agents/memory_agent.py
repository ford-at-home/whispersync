"""Memory Agent.

Stores personal memory transcripts as JSON lines in S3 and tags sentiment.
"""
from __future__ import annotations

import json
import logging
import datetime
try:
    import boto3
except Exception:  # pragma: no cover - optional for local testing
    boto3 = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3") if boto3 else None
def handle(payload: dict) -> dict:
    """Archive a memory transcript to S3."""
    transcript = payload.get("transcript", "")
    bucket = payload.get("bucket")
    if s3 is None:
        logger.warning("boto3 unavailable; returning dry-run response")
        return {"memory_key": "dry-run"}
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
