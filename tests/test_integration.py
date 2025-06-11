import asyncio
import importlib
import sys
import types
from pathlib import Path
import pytest

# Provide a minimal stub for the ``strands`` package so agent modules can load
strands_stub = types.ModuleType("strands")
def _tool(**_kwargs):
    def decorator(func):
        return func
    return decorator
strands_stub.tool = _tool
sys.modules.setdefault("strands", strands_stub)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
router_handler = importlib.import_module("lambda.router_handler")

invoke_agent = router_handler.invoke_agent
stream_agent_async = router_handler.stream_agent_async

@pytest.mark.parametrize(
    "agent,transcript,expected_field",
    [
        ("work", "Today I worked on the project.", "log_key"),
        ("memories", "A happy day at the park.", "memory_key"),
        ("github_ideas", "An idea to build an AI-powered plant watering system.", "repo"),
    ],
)
def test_invoke_agent(agent, transcript, expected_field):
    payload = {
        "transcript": transcript,
        "bucket": "test-bucket",
    }
    if agent == "github_ideas":
        payload["source_s3_key"] = f"transcripts/{agent}/test.txt"
    result = invoke_agent(agent, payload)
    assert result["status"] == "success"
    assert expected_field in result["content"][0]["json"]


def test_stream_agent_async_fallback():
    payload = {
        "transcript": "Streaming integration test",
        "bucket": "test-bucket",
    }

    async def collect():
        events = []
        async for event in stream_agent_async("work", payload):
            events.append(event)
        return events

    events = asyncio.run(collect())
    assert events[-1]["complete"] is True
    assert events[-1]["data"]["status"] == "success"
