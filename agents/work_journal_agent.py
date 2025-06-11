"""Work Journal Agent.

This agent appends a transcript to a week-based journal file stored in S3.
The intent is to capture quick daily notes that can later be summarized.
Only a short confirmation summary is generated here as a placeholder.
"""
from __future__ import annotations

from typing import Any, Dict

from strands import tool

import datetime
import logging
try:
    import boto3
except Exception:  # pragma: no cover - optional for local testing
    boto3 = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3") if boto3 else None

@tool
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append transcript to weekly log and return a short summary.

    Parameters
    ----------
    payload : dict
        Contains ``transcript`` with the work note text and ``bucket`` for
        the S3 location.

    Returns
    -------
    dict
        Path of the log file and a one-line summary string.  In dry-run
        mode the log key is ``"dry-run"``.
    """
    transcript = payload.get("transcript", "")
    bucket = payload.get("bucket")
    if s3 is None:
        logger.warning("boto3 unavailable; returning dry-run response")
        return {"log_key": "dry-run", "summary": transcript[:50]}
    now = datetime.datetime.utcnow()
    year, week, _ = now.isocalendar()
    log_key = f"work_journal/{year}-W{week}.txt"

    logger.info("Appending work log to %s", log_key)
    try:
        existing = s3.get_object(Bucket=bucket, Key=log_key)
        content = existing["Body"].read().decode()
    except s3.exceptions.NoSuchKey:
        content = ""

    content += f"\n[{now.isoformat()}] {transcript}\n"
    s3.put_object(
        Bucket=bucket,
        Key=log_key,
        Body=content.encode("utf-8"),
        ContentType="text/plain",
    )

    # Placeholder summary
    summary = f"Logged work entry on {now.date()}"
    return {"log_key": log_key, "summary": summary}
