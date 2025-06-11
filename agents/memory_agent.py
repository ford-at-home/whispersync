"""Memory Agent.

Stores personal memory transcripts as JSON lines in S3 and tags sentiment.
"""
from __future__ import annotations

from typing import Any, Dict

import json
import logging
import datetime
try:
    import boto3
    from strands import tool
except Exception:  # pragma: no cover - optional for local testing
    boto3 = None
    tool = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3") if boto3 else None

@tool
def store_memory(transcript: str, bucket: str) -> Dict[str, Any]:
    """Archive a memory transcript to S3.
    
    Args:
        transcript: The memory transcript to store
        bucket: The S3 bucket name where the memory should be stored
        
    Returns:
        Dictionary containing memory_key
    """
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
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=(json.dumps(record) + "\n").encode("utf-8"),
        ContentType="application/json",
    )
    return {"memory_key": key}

# For backward compatibility with existing tests
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy handler function for backward compatibility."""
    return store_memory(
        transcript=payload.get("transcript", ""),
        bucket=payload.get("bucket", "")
    )
