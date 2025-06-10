import json
import logging
import os
from importlib import import_module

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

AGENT_MODULES = {
    "work": "agents.work_journal_agent",
    "memories": "agents.memory_agent",
    "gitub_ideas": "agents.github_idea_agent",
}


def load_agent(agent_name):
    module_path = AGENT_MODULES.get(agent_name)
    if not module_path:
        raise ValueError(f"Unknown agent: {agent_name}")
    module = import_module(module_path)
    return module


def invoke_agent(agent_name: str, transcript: str, bucket: str, key: str):
    module = load_agent(agent_name)
    if hasattr(module, "handle"):
        return module.handle(transcript, bucket=bucket, s3_key=key)
    raise AttributeError(f"Agent {agent_name} missing handle()")


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    agent_name = key.split("/")[1]
    logger.info("Parsed agent: %s", agent_name)

    obj = s3.get_object(Bucket=bucket, Key=key)
    transcript = obj["Body"].read().decode()
    logger.info("Transcript downloaded, %d bytes", len(transcript))

    try:
        result = invoke_agent(agent_name, transcript, bucket, key)
    except Exception as exc:
        logger.exception("Agent invocation failed: %s", exc)
        raise

    output_key = key.replace("transcripts", "outputs").replace(".txt", "_response.json")
    s3.put_object(Bucket=bucket, Key=output_key, Body=json.dumps(result).encode("utf-8"))
    logger.info("Wrote response to %s", output_key)

    return {"status": "ok", "output_key": output_key}
