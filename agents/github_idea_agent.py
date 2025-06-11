"""GitHub Idea Agent.

This module implements an agent that converts a spoken idea into a new
GitHub repository.  It retrieves a personal access token from AWS
Secrets Manager, creates a repository via the PyGithub library, and logs
metadata about the action back to S3.
"""
from __future__ import annotations

from typing import Any, Dict

from strands import tool

import json
import logging
import os
import time

try:
    import boto3
except Exception:  # pragma: no cover - optional for local testing
    boto3 = None
try:
    from github import Github
except Exception:  # pragma: no cover - optional for local testing
    Github = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3") if boto3 else None
sm = boto3.client("secretsmanager") if boto3 else None

SECRET_NAME = os.environ.get("GITHUB_SECRET_NAME", "github/personal_token")


def get_token() -> str:
    """Retrieve the GitHub token from Secrets Manager."""
    if sm is None:
        raise RuntimeError("boto3 is required for github_idea_agent")
    response = sm.get_secret_value(SecretId=SECRET_NAME)
    return response.get("SecretString", "")


@tool
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub repository from a voice memo.

    Parameters
    ----------
    payload : dict
        Expect keys ``transcript`` with the spoken idea text,
        ``bucket`` for the destination S3 bucket and ``source_s3_key`` for
        logging purposes.

    Returns
    -------
    dict
        Metadata about the created repository including the full repo
        name and the source transcript key.  A dry-run dictionary is
        returned when required dependencies are not available.
    """
    transcript = payload.get("transcript", "")
    bucket = payload.get("bucket")
    s3_key = payload.get("source_s3_key")
    if s3 is None or sm is None:
        logger.warning("boto3 unavailable; returning dry-run response")
        return {"repo": "dry-run"}

    if Github is None:
        logger.warning("PyGithub unavailable; returning dry-run response")
        return {"repo": "dry-run"}
    token = get_token()
    gh = Github(token)
    user = gh.get_user()

    repo_name = f"voice-idea-{int(time.time())}"
    logger.info("Creating repo %s", repo_name)
    repo = user.create_repo(repo_name, description="Created from voice memo")

    readme_content = f"# {repo_name}\n\n{transcript}\n"
    repo.create_file("README.md", "Initial commit", readme_content)

    metadata = {
        "repo": repo.full_name,
        "s3_source": s3_key,
    }

    history_key = "github/history.jsonl"
    logger.info("Appending repo metadata to %s", history_key)
    s3.put_object(Bucket=bucket, Key=history_key, Body=(json.dumps(metadata) + "\n").encode("utf-8"),
                  ContentType="application/json")

    return metadata
