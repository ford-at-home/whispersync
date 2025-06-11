"""AWS Lambda entry point for dispatching transcripts.

The function triggered by S3 events loads the appropriate agent module
and invokes it directly. Results are
written back to S3 under the ``outputs/`` prefix.
"""
import json
import logging
import os
from importlib import import_module
from typing import AsyncIterator

try:
    import boto3
except Exception:  # pragma: no cover - optional for local testing
    boto3 = None

try:
    from strands import Agent
except Exception:  # pragma: no cover - library may not be installed
    Agent = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3") if boto3 else None

AGENT_MODULES = {
    "work": "agents.work_journal_agent",
    "memories": "agents.memory_agent",
    "github_ideas": "agents.github_idea_agent",
}


def load_agent(agent_name: str):
    """Dynamically import a local agent implementation."""
    module_path = AGENT_MODULES.get(agent_name)
    if not module_path:
        raise ValueError(f"Unknown agent: {agent_name}")
    module = import_module(module_path)
    return module


def invoke_agent(agent_name: str, payload: dict) -> dict:
    """Invoke agent using the Strands SDK when available."""
    module = load_agent(agent_name)

    if Agent and hasattr(module, "handle"):
        strands_agent = Agent(tools=[module.handle])
        try:
            return strands_agent(payload.get("transcript", ""))
        except Exception:
            logger.exception("Strands agent execution failed")

    if hasattr(module, "handle"):
        return module.handle(**payload)

    raise AttributeError(f"Agent {agent_name} missing handle()")


async def stream_agent_async(
    agent_name: str,
    payload: dict,
    callback_handler=None,
) -> AsyncIterator[dict]:
    """Stream agent events asynchronously using ``stream_async``.

    Parameters
    ----------
    agent_name : str
        Which registered agent to invoke.
    payload : dict
        Payload dictionary containing at minimum ``transcript``.
    callback_handler : callable, optional
        Callback handler function to forward events to.

    Yields
    ------
    dict
        Event dictionaries from ``stream_async``.
    """
    module = load_agent(agent_name)
    if not (Agent and hasattr(module, "handle")):
        # Fallback to normal invocation if Strands is unavailable
        result = invoke_agent(agent_name, payload)
        yield {"data": result, "complete": True}
        return

    strands_agent = Agent(tools=[module.handle], callback_handler=callback_handler)
    async for event in strands_agent.stream_async(payload.get("transcript", "")):
        yield event


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
