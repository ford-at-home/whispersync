"""Memory Agent.

This module defines an agent that archives short personal memories.  A
transcript provided by the Lambda router is written to an S3 bucket as a
single JSON Lines record.  A sentiment field is included as a placeholder
for future analysis or enhancement.
"""
from __future__ import annotations

from typing import Dict

from strands import tool

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


@tool(name="memory", description="Archive a memory transcript to S3")
def handle(transcript: str, bucket: str) -> Dict[str, str]:
    """Archive a memory transcript to S3.

    Args:
        transcript: Memory text to store
        bucket: Destination S3 bucket name

    Returns:
        Mapping with the key ``memory_key`` pointing to the stored object.
        When ``boto3`` is unavailable, the value is ``"dry-run"``.
    """
    if s3 is None:
        logger.warning("boto3 unavailable; returning dry-run response")
        return {
            "status": "success",
            "content": [{"json": {"memory_key": "dry-run"}}],
        }
    now = datetime.datetime.utcnow().isoformat()
    record = {
        "timestamp": now,
        "text": transcript,
        "sentiment": "neutral",  # placeholder
    }

    key = f"memories/{now}.jsonl"
    logger.info("Writing memory record to %s", key)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=(json.dumps(record) + "\n").encode("utf-8"),
        ContentType="application/json",
    )
    return {
        "status": "success",
        "content": [{"json": {"memory_key": key}}],
    }
