"""Local test runner to mimic Lambda invocation."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

try:
    from strands import Agent
    from agents.work_journal_agent import append_work_log
    from agents.memory_agent import store_memory
    from agents.github_idea_agent import create_github_repo
except ImportError:  # pragma: no cover - optional for local testing
    Agent = None
    append_work_log = None
    store_memory = None
    create_github_repo = None

logging.basicConfig(level=logging.INFO)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(path: str, bucket: str = "local-bucket") -> dict:
    """Execute the selected agent with a local transcript file."""
    if Agent is None:
        raise RuntimeError("strands-agents is required for local_test_runner")
        
    path_obj = Path(path)
    key = str(path_obj)
    parts = path_obj.parts
    if "transcripts" in parts:
        agent_name = parts[parts.index("transcripts") + 1]
    else:
        agent_name = path_obj.parent.name

    with open(path, "r") as f:
        transcript = f.read()

    # Create agent with appropriate tools based on agent type
    agent_tools_map = {
        "work": [append_work_log],
        "memories": [store_memory],
        "github_ideas": [create_github_repo],
    }
    
    if agent_name not in agent_tools_map:
        raise ValueError(f"Unknown agent: {agent_name}")
    
    tools = agent_tools_map[agent_name]
    agent = Agent(tools=tools)
    
    # Create a natural language prompt for the agent
    prompt_map = {
        "work": f"Please log this work transcript to bucket {bucket}: {transcript}",
        "memories": f"Please store this memory in bucket {bucket}: {transcript}",
        "github_ideas": f"Please create a GitHub repository for this idea. Store metadata in bucket {bucket} with source key {key}: {transcript}",
    }
    
    prompt = prompt_map[agent_name]
    
    result = agent(prompt)
    
    # Extract the result from the agent response
    if hasattr(result, 'message') and hasattr(result.message, 'content'):
        # The agent returned a structured result
        content = result.message.content
        if isinstance(content, list) and len(content) > 0:
            # Extract text from the first content item
            result_data = content[0].get('text', str(content[0]))
        else:
            result_data = str(content)
    else:
        result_data = str(result)
        
    # Try to parse as JSON if it looks like JSON
    try:
        if isinstance(result_data, str) and result_data.strip().startswith('{'):
            result_data = json.loads(result_data)
    except json.JSONDecodeError:
        pass
    
    print(json.dumps(result_data, indent=2))
    return result_data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python local_test_runner.py <transcript_path>")
        sys.exit(1)
    main(sys.argv[1])
