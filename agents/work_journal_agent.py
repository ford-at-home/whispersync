"""Work Journal Agent.

Appends transcripts to a weekly work log stored in S3 and returns a summary.
"""
from __future__ import annotations

import datetime
import logging

try:
    import boto3
except Exception:  # pragma: no cover - optional for local testing
    boto3 = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3") if boto3 else None


def handle(transcript: str, *, bucket: str, s3_key: str | None = None) -> dict:
    """Append transcript to weekly log and return a short summary."""
    if s3 is None:
        logger.warning("boto3 unavailable; returning dry-run response")
        return {"log_key": "dry-run", "summary": transcript[:50]}

    now = datetime.datetime.utcnow()
    year, week, _ = now.isocalendar()
    log_key = s3_key or f"work_journal/{year}-W{week}.txt"

    logger.info("Appending work log to %s", log_key)
    try:
        existing = s3.get_object(Bucket=bucket, Key=log_key)
        content = existing["Body"].read().decode()
    except s3.exceptions.NoSuchKey:
        content = ""

    content += f"\n[{now.isoformat()}] {transcript}\n"
    s3.put_object(Bucket=bucket, Key=log_key, Body=content.encode("utf-8"))

    summary = f"Logged work entry on {now.date()}"
    return {"log_key": log_key, "summary": summary}
