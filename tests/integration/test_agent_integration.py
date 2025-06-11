"""Integration tests for agent workflows."""
import pytest
import json
import tempfile
import os
from unittest.mock import patch, Mock
from pathlib import Path

# Import the test runner
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.local_test_runner import main


def agent_transcript_path(agent, transcript):
    """Create a transcript file in the correct agent directory structure."""
    base_dir = Path("test_data/transcripts")
    agent_dir = base_dir / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    file_path = agent_dir / f"test_{agent}.txt"
    file_path.write_text(transcript)
    return str(file_path)


class TestAgentIntegration:
    """Integration tests for agent workflows."""

    def test_work_agent_integration(self):
        """Test complete work agent workflow."""
        transcript = "Today I completed the project documentation and reviewed pull requests."
        file_path = agent_transcript_path("work", transcript)
        try:
            # Mock the Agent class and its return value
            with patch('scripts.local_test_runner.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                # Mock the agent's __call__ method to return a structured response
                mock_result = Mock()
                mock_result.message.content = [{"text": '{"log_key": "work_journal/2024-W01.txt", "summary": "Logged work entry on 2024-01-01"}'}]
                mock_agent.return_value = mock_result
                
                result = main(file_path)
                assert isinstance(result, dict)
                assert "log_key" in result
                assert "summary" in result
                assert result["log_key"].startswith("work_journal/")
                assert "Logged work entry" in result["summary"]
                
                # Verify Agent was called with tools
                mock_agent_class.assert_called_once()
                assert "tools" in mock_agent_class.call_args[1]
                mock_agent.assert_called_once()
        finally:
            Path(file_path).unlink()

    def test_memory_agent_integration(self):
        """Test complete memory agent workflow."""
        transcript = "I remember the first time I deployed to production. It was nerve-wracking but exciting."
        file_path = agent_transcript_path("memories", transcript)
        try:
            with patch('scripts.local_test_runner.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                # Mock the agent's __call__ method to return a structured response
                mock_result = Mock()
                mock_result.message.content = [{"text": '{"memory_key": "memories/2024-01-01T12:00:00.jsonl"}'}]
                mock_agent.return_value = mock_result
                
                result = main(file_path)
                assert isinstance(result, dict)
                assert "memory_key" in result
                assert result["memory_key"].endswith(".jsonl")
                
                # Verify Agent was called with tools
                mock_agent_class.assert_called_once()
                assert "tools" in mock_agent_class.call_args[1]
                mock_agent.assert_called_once()
        finally:
            Path(file_path).unlink()

    def test_github_idea_agent_integration(self):
        """Test complete GitHub idea agent workflow."""
        transcript = "I want to create a new project for automated testing of voice memos."
        file_path = agent_transcript_path("github_ideas", transcript)
        try:
            with patch('scripts.local_test_runner.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                # Mock the agent's __call__ method to return a structured response
                mock_result = Mock()
                mock_result.message.content = [{"text": f'{{"repo": "testuser/voice-idea-1234567890", "s3_source": "{file_path}"}}'}]
                mock_agent.return_value = mock_result
                
                result = main(file_path)
                assert isinstance(result, dict)
                assert "repo" in result
                assert "s3_source" in result
                assert result["repo"] == "testuser/voice-idea-1234567890"
                
                # Verify Agent was called with tools
                mock_agent_class.assert_called_once()
                assert "tools" in mock_agent_class.call_args[1]
                mock_agent.assert_called_once()
        finally:
            Path(file_path).unlink()

    def test_agent_routing_integration(self):
        """Test that different agent types are routed correctly."""
        test_cases = [
            ("work", "Today I worked on the project"),
            ("memories", "I remember when I first learned to code"),
            ("github_ideas", "I want to create a new repository for testing"),
        ]
        for agent_type, transcript in test_cases:
            file_path = agent_transcript_path(agent_type, transcript)
            try:
                with patch('scripts.local_test_runner.Agent') as mock_agent_class:
                    mock_agent = Mock()
                    mock_agent_class.return_value = mock_agent
                    
                    # Set up expected responses for each agent type
                    if agent_type == "work":
                        mock_result = Mock()
                        mock_result.message.content = [{"text": '{"log_key": "work_journal/2024-W01.txt", "summary": "Logged work entry"}'}]
                        mock_agent.return_value = mock_result
                    elif agent_type == "memories":
                        mock_result = Mock()
                        mock_result.message.content = [{"text": '{"memory_key": "memories/test.jsonl"}'}]
                        mock_agent.return_value = mock_result
                    elif agent_type == "github_ideas":
                        mock_result = Mock()
                        mock_result.message.content = [{"text": f'{{"repo": "testuser/test-repo", "s3_source": "{file_path}"}}'}]
                        mock_agent.return_value = mock_result
                    
                    result = main(file_path)
                    assert isinstance(result, dict)
                    
                    # Verify each agent returns appropriate response
                    if agent_type == "work":
                        assert "log_key" in result
                        assert "summary" in result
                    elif agent_type == "memories":
                        assert "memory_key" in result
                    elif agent_type == "github_ideas":
                        assert "repo" in result
                        assert "s3_source" in result
                    
                    # Verify the correct agent was called with tools
                    mock_agent_class.assert_called_once()
                    assert "tools" in mock_agent_class.call_args[1]
                    mock_agent.assert_called_once()
            finally:
                Path(file_path).unlink() 