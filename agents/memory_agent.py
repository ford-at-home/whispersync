"""Memory Agent.

This module defines an agent that archives short personal memories.  A
transcript provided by the Lambda router is written to an S3 bucket as a
single JSON Lines record.  A sentiment field is included as a placeholder
for future analysis or enhancement.
"""
from __future__ import annotations

from typing import Any, Dict

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

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Archive a memory transcript to S3.

    Parameters
    ----------
    payload : dict
        Should contain ``transcript`` with the memory text and ``bucket``
        specifying the S3 bucket name.

    Returns
    -------
    dict
        Mapping with the key ``memory_key`` pointing to the stored object
        path.  When ``boto3`` is not available a dry-run value is returned.
    """
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
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=(json.dumps(record) + "\n").encode("utf-8"),
        ContentType="application/json",
    )
    return {"memory_key": key}
