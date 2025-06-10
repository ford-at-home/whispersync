"""GitHub Idea Agent.

Turns a transcript into a GitHub repository using PyGithub.
"""
from __future__ import annotations

import json
import logging
import os
import time

import boto3
from github import Github

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
sm = boto3.client("secretsmanager")

SECRET_NAME = os.environ.get("GITHUB_SECRET_NAME", "github/personal_token")


def get_token() -> str:
    response = sm.get_secret_value(SecretId=SECRET_NAME)
    return response.get("SecretString", "")


def handle(payload: dict) -> dict:
    """Create a GitHub repository from a voice memo."""
    transcript = payload.get("transcript", "")
    bucket = payload.get("bucket")
    s3_key = payload.get("source_s3_key")

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
