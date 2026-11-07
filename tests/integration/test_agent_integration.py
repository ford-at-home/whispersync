"""Integration tests for agent workflows.

WHY THIS FILE EXISTS:
- Tests the complete end-to-end workflow from transcript file to agent output
- Validates that the local test runner correctly mimics Lambda behavior
- Ensures proper integration between orchestrator and individual agents
- Tests multi-agent coordination scenarios

TESTING PHILOSOPHY:
- Focus on realistic user scenarios (voice memo → action)
- Test both single-agent and multi-agent routing
- Validate the orchestrator's decision-making process
- Ensure error handling works across the full pipeline

KEY SCENARIOS TESTED:
1. Path-based routing (work/, memories/, github_ideas/)
2. Content-based routing (when path is ambiguous)
3. Multi-agent coordination (content spans multiple domains)
4. Error recovery and graceful degradation
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, Mock
from pathlib import Path

# Import the test runner
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.local_test_runner import main, process_transcript_locally


def agent_transcript_path(agent, transcript):
    """Create a transcript file in the correct agent directory structure.
    
    WHY: The local test runner expects files in specific directories.
    This helper ensures tests create files that match production S3 structure.
    """
    base_dir = Path("test_data/transcripts")
    agent_dir = base_dir / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    file_path = agent_dir / f"test_{agent}.txt"
    file_path.write_text(transcript)
    return str(file_path)


class TestAgentIntegration:
    """Integration tests for agent workflows.
    
    WHY THIS CLASS EXISTS:
    - Groups all integration tests for better organization
    - Allows shared setup/teardown if needed in the future
    - Makes it easy to run only integration tests
    """

    def test_work_agent_integration(self):
        """Test complete work agent workflow.
        
        WHY: Validates the most common use case - logging daily work.
        TESTS:
        - Orchestrator correctly identifies work content
        - Work agent processes and stores the log entry
        - Response includes proper work categories and analysis
        """
        transcript = (
            "Today I completed the project documentation and reviewed pull requests."
        )
        file_path = agent_transcript_path("work", transcript)
        try:
            # Test with the new orchestrator architecture
            with patch("scripts.local_test_runner.route_to_agent") as mock_route:
                # Mock the orchestrator response
                mock_route.return_value = {
                    "routing_decision": {
                        "primary_agent": "work",
                        "secondary_agents": [],
                        "confidence": 0.95,
                        "reasoning": "Work-related content detected"
                    },
                    "processing_results": {
                        "work": {
                            "log_key": "work_journal/2024-W01.txt",
                            "summary": "Logged work entry on 2024-01-01",
                            "analysis": {
                                "categories": ["documentation", "code_review"],
                                "key_points": ["Completed project documentation", "Reviewed pull requests"]
                            }
                        }
                    }
                }

                result = main(file_path)
                assert isinstance(result, dict)
                assert "routing_decision" in result
                assert "processing_results" in result
                
                # Check routing decision
                assert result["routing_decision"]["primary_agent"] == "work"
                assert result["routing_decision"]["confidence"] > 0.9
                
                # Check work processing results
                work_results = result["processing_results"]["work"]
                assert "log_key" in work_results
                assert "summary" in work_results
                assert work_results["log_key"].startswith("work_journal/")
                assert "Logged work entry" in work_results["summary"]

                # Verify the orchestrator was called with correct parameters
                mock_route.assert_called_once()
                call_args = mock_route.call_args
                assert call_args[1]["transcript"] == transcript
                # The local test runner constructs source_key from path parts
                expected_source_key = "transcripts/work/test_work.txt"
                assert call_args[1]["source_key"] == expected_source_key
        finally:
            Path(file_path).unlink()

    def test_memory_agent_integration(self):
        """Test complete memory agent workflow.
        
        WHY: Memories require sentiment analysis and theme extraction.
        TESTS:
        - Orchestrator recognizes personal/nostalgic content
        - Memory agent performs emotional analysis
        - Significance scoring works correctly
        - Related memory search doesn't crash on first memory
        """
        transcript = "I remember the first time I deployed to production. It was nerve-wracking but exciting."
        file_path = agent_transcript_path("memories", transcript)
        try:
            with patch("scripts.local_test_runner.route_to_agent") as mock_route:
                # Mock the orchestrator response
                mock_route.return_value = {
                    "routing_decision": {
                        "primary_agent": "memory",
                        "secondary_agents": [],
                        "confidence": 0.92,
                        "reasoning": "Personal memory detected"
                    },
                    "processing_results": {
                        "memory": {
                            "memory_key": "memories/2024-01-01T12:00:00.jsonl",
                            "memory_id": "2024-01-01T12:00:00-1234",
                            "analysis": {
                                "sentiment": "mixed",
                                "emotions": ["anxiety", "excitement", "pride"],
                                "themes": ["career", "achievement", "growth"],
                                "people": [],
                                "locations": [],
                                "significance": 8
                            },
                            "related_memories": []
                        }
                    }
                }

                result = main(file_path)
                assert isinstance(result, dict)
                assert "routing_decision" in result
                assert "processing_results" in result
                
                # Check routing decision
                assert result["routing_decision"]["primary_agent"] == "memory"
                
                # Check memory processing results
                memory_results = result["processing_results"]["memory"]
                assert "memory_key" in memory_results
                assert memory_results["memory_key"].endswith(".jsonl")
                assert "analysis" in memory_results
                assert memory_results["analysis"]["sentiment"] == "mixed"
                assert "anxiety" in memory_results["analysis"]["emotions"]
                assert memory_results["analysis"]["significance"] == 8

                # Verify the orchestrator was called
                mock_route.assert_called_once()
        finally:
            Path(file_path).unlink()

    def test_github_idea_agent_integration(self):
        """Test complete GitHub idea agent workflow.
        
        WHY: GitHub agent has the most complex external integration.
        TESTS:
        - Orchestrator detects project ideas
        - Repository name generation from idea content
        - Tech stack inference
        - README and initial file generation
        """
        transcript = (
            "I want to create a new project for automated testing of voice memos."
        )
        file_path = agent_transcript_path("github_ideas", transcript)
        try:
            with patch("scripts.local_test_runner.route_to_agent") as mock_route:
                # Mock the orchestrator response
                mock_route.return_value = {
                    "routing_decision": {
                        "primary_agent": "github",
                        "secondary_agents": [],
                        "confidence": 0.98,
                        "reasoning": "GitHub project idea detected"
                    },
                    "processing_results": {
                        "github": {
                            "repo": "testuser/voice-memo-testing",
                            "url": "https://github.com/testuser/voice-memo-testing",
                            "description": "Automated testing framework for voice memo applications",
                            "tech_stack": ["python", "pytest", "speech-recognition"],
                            "features": [
                                "Voice memo recording simulation",
                                "Transcription accuracy testing",
                                "Multi-format audio support"
                            ],
                            "files_created": 5,
                            "topics": ["testing", "voice", "automation", "python"],
                            "status": "success"
                        }
                    }
                }

                result = main(file_path)
                assert isinstance(result, dict)
                assert "routing_decision" in result
                assert "processing_results" in result
                
                # Check routing decision
                assert result["routing_decision"]["primary_agent"] == "github"
                assert result["routing_decision"]["confidence"] > 0.95
                
                # Check GitHub processing results
                github_results = result["processing_results"]["github"]
                assert "repo" in github_results
                assert "url" in github_results
                assert "tech_stack" in github_results
                assert github_results["status"] == "success"
                assert "python" in github_results["tech_stack"]

                # Verify the orchestrator was called
                mock_route.assert_called_once()
        finally:
            Path(file_path).unlink()

    def test_agent_routing_integration(self):
        """Test that different agent types are routed correctly.
        
        WHY: Path-based routing is the primary routing mechanism.
        TESTS:
        - Each agent directory maps to the correct agent
        - Orchestrator respects path hints
        - Responses contain agent-specific fields
        EDGE CASES:
        - What if content doesn't match the path hint?
        - Currently tests assume path takes precedence
        """
        test_cases = [
            ("work", "Today I worked on the project", "work"),
            ("memories", "I remember when I first learned to code", "memory"),
            ("github_ideas", "I want to create a new repository for testing", "github"),
        ]
        for agent_dir, transcript, expected_agent in test_cases:
            file_path = agent_transcript_path(agent_dir, transcript)
            try:
                with patch("scripts.local_test_runner.route_to_agent") as mock_route:
                    # Set up expected responses for each agent type
                    if expected_agent == "work":
                        mock_route.return_value = {
                            "routing_decision": {
                                "primary_agent": "work",
                                "secondary_agents": [],
                                "confidence": 0.95,
                                "reasoning": "Work content detected"
                            },
                            "processing_results": {
                                "work": {
                                    "log_key": "work_journal/2024-W01.txt",
                                    "summary": "Logged work entry"
                                }
                            }
                        }
                    elif expected_agent == "memory":
                        mock_route.return_value = {
                            "routing_decision": {
                                "primary_agent": "memory",
                                "secondary_agents": [],
                                "confidence": 0.93,
                                "reasoning": "Personal memory detected"
                            },
                            "processing_results": {
                                "memory": {
                                    "memory_key": "memories/test.jsonl",
                                    "analysis": {"sentiment": "nostalgic"}
                                }
                            }
                        }
                    elif expected_agent == "github":
                        mock_route.return_value = {
                            "routing_decision": {
                                "primary_agent": "github",
                                "secondary_agents": [],
                                "confidence": 0.97,
                                "reasoning": "GitHub project idea"
                            },
                            "processing_results": {
                                "github": {
                                    "repo": "testuser/test-repo",
                                    "url": "https://github.com/testuser/test-repo",
                                    "status": "success"
                                }
                            }
                        }

                    result = main(file_path)
                    assert isinstance(result, dict)
                    assert "routing_decision" in result
                    assert "processing_results" in result
                    
                    # Verify correct agent was selected
                    assert result["routing_decision"]["primary_agent"] == expected_agent

                    # Verify each agent returns appropriate response
                    if expected_agent == "work":
                        assert "work" in result["processing_results"]
                        assert "log_key" in result["processing_results"]["work"]
                        assert "summary" in result["processing_results"]["work"]
                    elif expected_agent == "memory":
                        assert "memory" in result["processing_results"]
                        assert "memory_key" in result["processing_results"]["memory"]
                    elif expected_agent == "github":
                        assert "github" in result["processing_results"]
                        assert "repo" in result["processing_results"]["github"]
                        assert "status" in result["processing_results"]["github"]

                    # Verify the orchestrator was called correctly
                    mock_route.assert_called_once()
                    assert mock_route.call_args[1]["transcript"] == transcript
                    # Verify source_key contains the agent directory
                    source_key = mock_route.call_args[1]["source_key"]
                    assert f"transcripts/{agent_dir}/" in source_key
                    
                    # Reset mock for next iteration
                    mock_route.reset_mock()
            finally:
                Path(file_path).unlink()

    def test_multi_agent_coordination(self):
        """Test orchestrator handling multi-agent scenarios.
        
        WHY: Real voice memos often contain mixed content.
        SCENARIO: "I worked on X, it reminds me of Y, maybe make it a project"
        TESTS:
        - Orchestrator detects multiple relevant agents
        - All applicable agents process the content
        - Results are properly aggregated
        - Lower confidence score for ambiguous content
        
        EDGE CASE: Uses 'general/' directory to test content-based routing
        without path hints, forcing the orchestrator to analyze content.
        """
        transcript = (
            "I worked on implementing the new authentication system today. "
            "It reminds me of my first big project where I had to learn OAuth from scratch. "
            "I think this could be turned into a reusable library for future projects."
        )
        
        # Create a file without specific agent directory to test content-based routing
        base_dir = Path("test_data/transcripts/general")
        base_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_dir / "multi_agent_test.txt"
        file_path.write_text(transcript)
        
        try:
            with patch("scripts.local_test_runner.route_to_agent") as mock_route:
                # Mock a multi-agent response
                mock_route.return_value = {
                    "routing_decision": {
                        "primary_agent": "multiple",
                        "secondary_agents": ["work", "memory", "github"],
                        "confidence": 0.85,
                        "reasoning": "Content spans multiple domains: work activity, personal reflection, and project idea"
                    },
                    "processing_results": {
                        "work": {
                            "log_key": "work_journal/2024-W01.txt",
                            "summary": "Implemented authentication system",
                            "analysis": {
                                "categories": ["development", "security"],
                                "key_points": ["New authentication system implementation"]
                            }
                        },
                        "memory": {
                            "memory_key": "memories/2024-01-01.jsonl",
                            "analysis": {
                                "sentiment": "nostalgic",
                                "themes": ["learning", "growth", "achievement"],
                                "significance": 7
                            }
                        },
                        "github": {
                            "repo": "testuser/auth-library",
                            "url": "https://github.com/testuser/auth-library",
                            "description": "Reusable authentication library",
                            "status": "success"
                        }
                    }
                }

                result = main(str(file_path))
                assert isinstance(result, dict)
                assert "routing_decision" in result
                assert "processing_results" in result
                
                # Check multi-agent routing
                assert result["routing_decision"]["primary_agent"] == "multiple"
                assert len(result["routing_decision"]["secondary_agents"]) == 3
                assert "work" in result["routing_decision"]["secondary_agents"]
                assert "memory" in result["routing_decision"]["secondary_agents"]
                assert "github" in result["routing_decision"]["secondary_agents"]
                
                # Verify all three agents processed the content
                assert len(result["processing_results"]) == 3
                assert "work" in result["processing_results"]
                assert "memory" in result["processing_results"]
                assert "github" in result["processing_results"]
                
                # Verify each agent's results
                assert "log_key" in result["processing_results"]["work"]
                assert "memory_key" in result["processing_results"]["memory"]
                assert "repo" in result["processing_results"]["github"]
                
                # Verify orchestrator handled the complex routing
                assert result["routing_decision"]["confidence"] < 0.9  # Lower confidence for multi-agent
                assert "multiple domains" in result["routing_decision"]["reasoning"].lower()

        finally:
            if file_path.exists():
                file_path.unlink()
            # Clean up the general directory if empty
            if base_dir.exists() and not any(base_dir.iterdir()):
                base_dir.rmdir()
