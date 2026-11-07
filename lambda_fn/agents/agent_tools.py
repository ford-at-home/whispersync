"""Mock implementations of agent tools for WhisperSync.

These mock implementations allow the orchestrator to function without the Strands SDK.
They simulate the expected behavior of each specialized agent.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def work_journal_tool(
    transcript: str, 
    timestamp: Optional[str] = None,
    bucket: Optional[str] = None
) -> Dict[str, Any]:
    """Mock work journal agent tool.
    
    Simulates the work journal agent by creating a structured log entry.
    """
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    
    logger.info(f"Mock work journal tool processing transcript: {transcript[:100]}...")
    
    # Simulate work journal processing
    result = {
        "status": "success",
        "agent": "work_journal",
        "timestamp": timestamp,
        "entry": {
            "date": timestamp.split("T")[0],
            "time": timestamp.split("T")[1].split(".")[0],
            "content": transcript,
            "word_count": len(transcript.split()),
            "mock": True
        },
        "file_path": f"work/weekly_logs/{datetime.utcnow().strftime('%Y-W%U')}.md",
        "message": "Work journal entry created (mock)"
    }
    
    logger.info(f"Mock work journal result: {result}")
    return result


def memory_tool(
    transcript: str,
    timestamp: Optional[str] = None,
    bucket: Optional[str] = None
) -> Dict[str, Any]:
    """Mock memory archive agent tool.
    
    Simulates the memory agent by creating a structured memory entry.
    """
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    
    logger.info(f"Mock memory tool processing transcript: {transcript[:100]}...")
    
    # Simulate memory processing
    result = {
        "status": "success",
        "agent": "memory_archive",
        "timestamp": timestamp,
        "memory": {
            "content": transcript,
            "themes": ["mock_theme"],  # In real version, would extract themes
            "sentiment": "neutral",    # In real version, would analyze sentiment
            "people": [],             # In real version, would extract people mentioned
            "mock": True
        },
        "file_path": f"memories/{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl",
        "message": "Memory archived (mock)"
    }
    
    logger.info(f"Mock memory result: {result}")
    return result


def github_tool(
    transcript: str,
    timestamp: Optional[str] = None,
    bucket: Optional[str] = None
) -> Dict[str, Any]:
    """Mock GitHub idea agent tool.
    
    Simulates the GitHub agent by creating a repository concept.
    """
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    
    logger.info(f"Mock GitHub tool processing transcript: {transcript[:100]}...")
    
    # Simulate GitHub processing
    # Extract a simple repo name from the transcript
    words = transcript.split()[:5]
    repo_name = "-".join(word.lower() for word in words if word.isalnum())[:50]
    
    result = {
        "status": "success",
        "agent": "github_idea",
        "timestamp": timestamp,
        "repository": {
            "name": repo_name or "voice-idea",
            "description": transcript[:200] + "..." if len(transcript) > 200 else transcript,
            "visibility": "public",
            "mock": True,
            "url": f"https://github.com/mock/{repo_name or 'voice-idea'}"
        },
        "message": "GitHub repository concept created (mock)"
    }
    
    logger.info(f"Mock GitHub result: {result}")
    return result


# Mock implementations for when Strands SDK is not available
def get_mock_agent_tools():
    """Return mock agent tools for testing without Strands SDK."""
    return {
        "work_journal_tool": work_journal_tool,
        "memory_tool": memory_tool,
        "github_tool": github_tool
    }