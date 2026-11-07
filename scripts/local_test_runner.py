"""Local test runner for WhisperSync agents.

This script allows testing the agent pipeline locally without AWS infrastructure.

WHY THIS SCRIPT EXISTS:
- Enables rapid development feedback without AWS costs or setup complexity
- Simulates the Lambda environment for debugging agent logic
- Provides interactive testing mode for exploring agent behaviors
- Supports both single-file testing and interactive transcript entry
- Bridges the gap between unit tests and full integration tests

DESIGN DECISIONS:
- Falls back gracefully when Strands SDK is unavailable (optional dependency)
- Uses path-based agent routing matching production S3 key structure
- Provides both legacy single-agent and new orchestrator modes
- Includes rich interactive output for better developer experience
- Mimics production data flow while remaining completely local
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
# WHY: Allows importing agents without installing package
# Enables development workflow where scripts can test in-progress changes
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# WHY try/except: Graceful degradation when Strands SDK unavailable
# Allows script to run in environments without full dependencies installed
# Enables CI/CD testing without requiring Strands platform access
try:
    from strands import Agent
    from agents.orchestrator_agent import get_orchestrator_agent, route_to_agent
    from agents.work_journal_agent import append_work_log
    from agents.memory_agent import store_memory
    from agents.github_idea_agent import create_github_repo
except ImportError:  # pragma: no cover - optional for local testing
    Agent = None
    get_orchestrator_agent = None
    route_to_agent = None
    append_work_log = None
    store_memory = None
    create_github_repo = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def process_transcript_locally(
    transcript: str,
    source_key: Optional[str] = None,
    mock_bucket: str = os.environ.get("TRANSCRIPT_BUCKET_NAME", "macbook-transcriptions-local"),
) -> Dict[str, Any]:
    # WHY mock_bucket: Simulates S3 bucket name for agent compatibility
    # WHY source_key Optional: Supports both explicit routing and auto-detection
    # WHY return Dict: Matches Lambda handler return format for consistency
    """Process a transcript locally using the orchestrator.

    Args:
        transcript: The voice transcript to process
        source_key: Optional S3-style key for routing hints
        mock_bucket: Mock bucket name for local testing

    Returns:
        Processing results dictionary
    """
    logger.info(f"Processing transcript locally: {transcript[:50]}...")

    # WHY fallback logic: Supports development during orchestrator transition
    # Enables testing individual agents when orchestrator unavailable
    if route_to_agent is None:
        # Fallback to old single-agent logic
        return process_with_single_agent(transcript, source_key, mock_bucket)

    try:
        # Use the new orchestrator
        result = route_to_agent(
            transcript=transcript, source_key=source_key, bucket=mock_bucket
        )

        logger.info(
            f"Processing complete. Primary agent: "
            f"{result.get('routing_decision', {}).get('primary_agent')}"
        )

        return result

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {"error": str(e), "error_type": type(e).__name__}


def process_with_single_agent(
    transcript: str, source_key: Optional[str], bucket: str
) -> Dict[str, Any]:
    """Legacy single-agent processing.
    
    WHY THIS EXISTS:
    - Maintains backward compatibility during orchestrator rollout
    - Simpler debugging path for individual agent development
    - Reduces dependencies for basic functionality testing
    """
    if Agent is None:
        raise RuntimeError("strands-agents is required for local_test_runner")

    # Determine agent from source key
    # WHY "work" default: Most common use case for voice memo logging
    # WHY path parsing: Matches production S3 key structure (transcripts/{agent}/file)
    agent_name = "work"  # default
    if source_key:
        parts = Path(source_key).parts
        if "transcripts" in parts:
            idx = parts.index("transcripts")
            if idx + 1 < len(parts):
                agent_name = parts[idx + 1]

    # Create agent with appropriate tools
    # WHY tool mapping: Each agent type needs specific capabilities
    # WHY list format: Supports future multi-tool agents
    agent_tools_map = {
        "work": [append_work_log],
        "memories": [store_memory],
        "github_ideas": [create_github_repo],
    }

    if agent_name not in agent_tools_map:
        raise ValueError(f"Unknown agent: {agent_name}")

    tools = agent_tools_map[agent_name]
    agent = Agent(tools=tools)

    # Create prompt
    prompt_map = {
        "work": f"Please log this work transcript to bucket {bucket}: {transcript}",
        "memories": f"Please store this memory in bucket {bucket}: {transcript}",
        "github_ideas": f"Please create a GitHub repository for this idea. Store metadata in bucket {bucket} with source key {source_key}: {transcript}",
    }

    prompt = prompt_map[agent_name]
    result = agent(prompt)

    # Extract result
    if hasattr(result, "message") and hasattr(result.message, "content"):
        content = result.message.content
        if isinstance(content, list) and len(content) > 0:
            result_data = content[0].get("text", str(content[0]))
        else:
            result_data = str(content)
    else:
        result_data = str(result)

    # Try to parse as JSON
    try:
        if isinstance(result_data, str) and result_data.strip().startswith("{"):
            result_data = json.loads(result_data)
    except json.JSONDecodeError:
        pass

    # Return in orchestrator format
    return {
        "routing_decision": {
            "primary_agent": agent_name,
            "secondary_agents": [],
            "confidence": 0.95,
            "reasoning": "Single agent mode",
        },
        "processing_results": {agent_name: result_data},
    }


def process_file(file_path: str) -> Dict[str, Any]:
    """Process a transcript from a file.

    Args:
        file_path: Path to the transcript file

    Returns:
        Processing results dictionary
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return {"error": "File not found"}

    logger.info(f"Processing file: {file_path}")

    # Read transcript
    try:
        transcript = file_path.read_text().strip()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return {"error": f"Failed to read file: {e}"}

    # Extract agent hint from path if available
    source_key = None
    path_parts = file_path.parts

    if "transcripts" in path_parts:
        idx = path_parts.index("transcripts")
        if idx + 1 < len(path_parts):
            agent_type = path_parts[idx + 1]
            source_key = f"transcripts/{agent_type}/{file_path.name}"
            logger.info(f"Detected agent type from path: {agent_type}")

    # Process transcript
    return process_transcript_locally(transcript, source_key)


def main(file_path: Optional[str] = None):
    """Main entry point for local testing.

    Args:
        file_path: Optional path to transcript file
    """
    if file_path:
        # Process single file
        result = process_file(file_path)
        print(json.dumps(result, indent=2))
        return result
    else:
        # Interactive mode
        print("\n🎙️  WhisperSync Local Test Runner")
        print("=" * 60)
        print("Enter transcripts to process (type 'quit' to exit)")
        print("For multi-line input, end with a line containing only '---'")
        print("=" * 60 + "\n")

        while True:
            print("\n📝 Enter transcript (or 'quit' to exit):")

            # Collect multi-line input
            lines = []
            while True:
                line = input()
                if line.lower() == "quit":
                    print("\n👋 Goodbye!")
                    return
                if line == "---":
                    break
                lines.append(line)

            transcript = "\n".join(lines).strip()

            if transcript:
                # Ask for optional agent hint
                agent_hint = input(
                    "\n🎯 Agent hint (work/memory/github/none) [none]: "
                ).strip()

                source_key = None
                if agent_hint and agent_hint != "none":
                    source_key = f"transcripts/{agent_hint}/interactive.txt"

                # Process transcript
                print("\n⚙️  Processing...")
                result = process_transcript_locally(transcript, source_key)

                # Display results
                print("\n" + "=" * 60)
                print("RESULTS")
                print("=" * 60)

                # Routing decision
                routing = result.get("routing_decision", {})
                if routing:
                    print(f"\n🎯 Routing Decision:")
                    print(f"   Primary Agent: {routing.get('primary_agent')}")
                    print(f"   Confidence: {routing.get('confidence', 0):.2%}")
                    print(f"   Reasoning: {routing.get('reasoning')}")

                    if routing.get("secondary_agents"):
                        print(
                            f"   Secondary Agents: {', '.join(routing['secondary_agents'])}"
                        )

                # Agent results
                processing_results = result.get("processing_results", {})
                if processing_results:
                    print(f"\n🤖 Agent Results:")
                    for agent_name, agent_result in processing_results.items():
                        print(f"\n   {agent_name.upper()} Agent:")

                        # Display key results based on agent type
                        if agent_name == "work" and isinstance(agent_result, dict):
                            if "summary" in agent_result:
                                print(f"   - Summary: {agent_result['summary']}")
                            if "categories" in agent_result:
                                print(
                                    f"   - Categories: {', '.join(agent_result['categories'])}"
                                )
                            if "key_points" in agent_result:
                                print(
                                    f"   - Key Points: {len(agent_result['key_points'])} extracted"
                                )

                        elif agent_name == "memory" and isinstance(agent_result, dict):
                            if "analysis" in agent_result:
                                analysis = agent_result["analysis"]
                                print(f"   - Sentiment: {analysis.get('sentiment')}")
                                print(
                                    f"   - Significance: {analysis.get('significance')}/10"
                                )
                                if "themes" in analysis:
                                    print(
                                        f"   - Themes: {', '.join(analysis['themes'])}"
                                    )

                        elif agent_name == "github" and isinstance(agent_result, dict):
                            if "repo" in agent_result:
                                print(f"   - Repository: {agent_result['repo']}")
                            if "description" in agent_result:
                                print(
                                    f"   - Description: {agent_result['description']}"
                                )
                            if "tech_stack" in agent_result:
                                print(
                                    f"   - Tech Stack: {', '.join(agent_result['tech_stack'])}"
                                )

                # Errors
                if "error" in result:
                    print(f"\n❌ Error: {result['error']}")

                # Full JSON option
                show_json = (
                    input("\n📄 Show full JSON result? (y/n) [n]: ").strip().lower()
                )
                if show_json == "y":
                    print("\n" + json.dumps(result, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test WhisperSync agents locally")
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to transcript file (optional, interactive mode if not provided)",
    )

    args = parser.parse_args()

    try:
        main(args.file)
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
