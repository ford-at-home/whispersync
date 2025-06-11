"""Local test runner to mimic Lambda invocation.

This utility imports the Lambda router and executes a selected agent on
a transcript file.  It is useful for verifying agent behavior without
deploying any AWS resources.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from importlib import import_module

logging.basicConfig(level=logging.INFO)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
router = import_module("lambda.router_handler")
invoke_agent = router.invoke_agent
stream_agent_async = router.stream_agent_async


async def run_stream(
    agent_name: str, payload: dict, use_callback: bool = False
) -> None:
    """Stream events from the agent asynchronously."""

    def cb_handler(**kwargs):
        if "data" in kwargs:
            print(f"CALLBACK: {kwargs['data']}")

    async for event in stream_agent_async(
        agent_name,
        payload,
        cb_handler if use_callback else None,
    ):
        print(json.dumps(event))


def main(path: str, bucket: str = "local-bucket", stream: bool = False, use_callback: bool = False) -> None:
    """Execute the selected agent with a local transcript file.

    Parameters
    ----------
    path : str
        Path to the transcript text file.
    bucket : str, optional
        Name of the mock S3 bucket to pass to the agent.
    """
    path_obj = Path(path)
    key = str(path_obj)
    parts = path_obj.parts
    if "transcripts" in parts:
        agent_name = parts[parts.index("transcripts") + 1]
    else:
        agent_name = path_obj.parent.name

    with open(path, "r") as f:
        transcript = f.read()

    payload = {
        "transcript": transcript,
        "bucket": bucket,
        "source_s3_key": key,
    }

    if stream:
        asyncio.run(run_stream(agent_name, payload, use_callback))
    else:
        result = invoke_agent(agent_name, payload)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a local agent test")
    parser.add_argument("path", help="Path to transcript text file")
    parser.add_argument("--bucket", default="local-bucket", help="Mock bucket name")
    parser.add_argument("--stream", action="store_true", help="Use async streaming")
    parser.add_argument("--callback", action="store_true", help="Use demo callback handler")
    args = parser.parse_args()

    main(args.path, bucket=args.bucket, stream=args.stream, use_callback=args.callback)
