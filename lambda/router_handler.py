"""Lambda entry point to route transcripts to Strands agents."""
import json
import logging
import os
from importlib import import_module

try:
    import boto3
except Exception:  # pragma: no cover - optional for local testing
    boto3 = None

try:
    from strands_sdk import StrandsClient
except Exception:  # pragma: no cover - library may not be installed
    StrandsClient = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3") if boto3 else None

AGENT_MODULES = {
    "work": "agents.work_journal_agent",
    "memories": "agents.memory_agent",
    "gitub_ideas": "agents.github_idea_agent",
}


def load_agent(agent_name: str):
    """Dynamically import a local agent implementation."""
    module_path = AGENT_MODULES.get(agent_name)
    if not module_path:
        raise ValueError(f"Unknown agent: {agent_name}")
    module = import_module(module_path)
    return module


def invoke_agent(agent_name: str, payload: dict) -> dict:
    """Invoke agent via Strands SDK if available, else call locally."""
    if StrandsClient:
        strands = StrandsClient(region=os.environ.get("STRANDS_REGION", "us-east-1"))
        response = strands.invoke_agent(
            agent_name=f"{agent_name}_agent",
            input=payload,
        )
        try:
            return json.loads(response)
        except Exception:
            return response

    # Fallback: import the agent locally
    module = load_agent(agent_name)
    if hasattr(module, "handle"):
        return module.handle(payload)
    raise AttributeError(f"Agent {agent_name} missing handle()")


def lambda_handler(event, context):
    """Entry point for AWS Lambda to route transcripts."""
    if s3 is None:
        raise RuntimeError("boto3 is required for lambda_handler")
    logger.info("Received event: %s", json.dumps(event))

    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    agent_name = key.split("/")[1]
    logger.info("Parsed agent: %s", agent_name)

    obj = s3.get_object(Bucket=bucket, Key=key)
    transcript = obj["Body"].read().decode()
    logger.info("Transcript downloaded, %d bytes", len(transcript))

    payload = {
        "transcript": transcript,
        "source_s3_key": key,
        "bucket": bucket,
    }

    try:
        result = invoke_agent(agent_name, payload)
    except Exception as exc:
        logger.exception("Agent invocation failed: %s", exc)
        raise

    output_key = key.replace("transcripts/", "outputs/").replace(".txt", "_response.json")
    body = json.dumps(result).encode("utf-8") if not isinstance(result, (bytes, bytearray)) else result
    s3.put_object(Bucket=bucket, Key=output_key, Body=body)
    logger.info("Wrote response to %s", output_key)

    return {"status": "ok", "output_key": output_key}
