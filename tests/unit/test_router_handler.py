"""Unit tests for Lambda router handler.

WHY THIS FILE EXISTS:
- Tests the Lambda function entry point for the entire system
- Validates S3 event parsing and response formatting
- Ensures proper integration with the orchestrator agent
- Tests error handling for various failure scenarios

TESTING PHILOSOPHY:
- Mock all AWS services to avoid actual Lambda deployment
- Test realistic S3 event payloads
- Validate HTTP response format for API Gateway integration
- Ensure proper error propagation and logging

LAMBDA-SPECIFIC CONCERNS:
1. Event Structure: Test various S3 event formats
2. Context Handling: Validate request ID propagation
3. Response Format: Ensure proper HTTP response structure
4. Error Handling: Test graceful failure scenarios
5. Orchestrator Integration: Test routing to different agents
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Import the handler function
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lambda_fn.router_handler import lambda_handler

# Reset orchestrator singleton before tests
import agents.orchestrator_agent
agents.orchestrator_agent.orchestrator_agent = None

# Mock boto3 at module level to prevent S3 client creation
import lambda_fn.router_handler
lambda_fn.router_handler.s3 = Mock()


class TestRouterHandler:
    """Test cases for Lambda router handler.
    
    WHY THIS CLASS EXISTS:
    - Groups all Lambda handler tests for organization
    - Provides singleton reset for orchestrator agent
    - Tests the main entry point for the voice memo pipeline
    """

    def setup_method(self):
        """Reset singleton before each test."""
        agents.orchestrator_agent.orchestrator_agent = None

    def test_lambda_handler_with_valid_event(self):
        """Test lambda_handler function with valid S3 event.
        
        WHY: Tests the most common success scenario.
        VALIDATION:
        - S3 event properly parsed
        - Transcript downloaded from S3
        - Orchestrator invoked with correct parameters
        - Response stored back to S3
        - HTTP response format correct
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/work/test.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"Today I worked on the project")
        }

        # Mock orchestrator and route_to_agent
        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {
                    "primary_agent": "work",
                    "secondary_agents": [],
                    "confidence": 0.95,
                    "reasoning": "Work-related content"
                },
                "processing_results": {
                    "work": {
                        "log_key": "work_journal/2024-W01.txt",
                        "summary": "Logged work entry",
                    }
                }
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Transcript processed successfully"
            assert "output_key" in body
            assert body["output_key"] == "outputs/work/test_response.json"
            assert body["success"] is True

            # Verify S3 operations
            mock_s3.get_object.assert_called_once_with(
                Bucket="test-bucket", Key="transcripts/work/test.txt"
            )
            assert mock_s3.put_object.call_count == 1

            # Verify orchestrator invocation
            mock_route.assert_called_once_with(
                transcript="Today I worked on the project", 
                source_key="transcripts/work/test.txt",
                bucket="test-bucket"
            )

    def test_lambda_handler_with_memory_agent(self):
        """Test lambda_handler function with memory agent.
        
        WHY: Validates memory-specific routing and response handling.
        TESTS: Different agent types return different response structures.
        VALIDATION: Memory agent response includes sentiment analysis.
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/memories/test.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"Test memory")
        }

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {
                    "primary_agent": "memory",
                    "secondary_agents": [],
                    "confidence": 0.95,
                    "reasoning": "Memory content detected"
                },
                "processing_results": {
                    "memory": {
                        "memory_key": "memories/test.jsonl",
                        "analysis": {
                            "sentiment": "positive",
                            "themes": ["reflection"]
                        }
                    }
                }
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Transcript processed successfully"
            assert "output_key" in body
            assert body["success"] is True
            # Verify the results were stored
            mock_s3.put_object.assert_called_once()
            call_args = mock_s3.put_object.call_args
            body_content = call_args[1]["Body"].decode("utf-8")
            assert "memory_key" in body_content

    def test_lambda_handler_with_github_agent(self):
        """Test lambda_handler function with GitHub agent.
        
        WHY: GitHub agent has unique response format with repo URLs.
        TESTS: Repository creation success is properly reported.
        VALIDATION: Response includes GitHub-specific fields.
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/github_ideas/test.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"Test idea")
        }

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {
                    "primary_agent": "github",
                    "secondary_agents": [],
                    "confidence": 0.95,
                    "reasoning": "GitHub project idea"
                },
                "processing_results": {
                    "github": {
                        "repo": "testuser/test-idea",
                        "url": "https://github.com/testuser/test-idea",
                        "status": "success"
                    }
                }
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Transcript processed successfully"
            assert body["success"] is True
            # Verify results were stored correctly
            mock_s3.put_object.assert_called_once()
            call_args = mock_s3.put_object.call_args
            body_content = call_args[1]["Body"].decode("utf-8")
            assert "repo" in body_content

    def test_lambda_handler_with_orchestrator_error(self):
        """Test lambda_handler function when orchestrator fails.
        
        WHY: Orchestrator might fail due to network/service issues.
        TESTS: Proper HTTP 500 response with error details.
        ERROR HANDLING: User gets meaningful error message.
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/work/test.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"Test transcript")
        }

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.side_effect = Exception("Orchestrator failed")

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            # Should return error response
            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "error" in body
            assert "Processing failed" in body["error"]

    def test_lambda_handler_with_different_agent_types(self):
        """Test lambda_handler function with different agent types.
        
        WHY: Path-based routing is the primary routing mechanism.
        TESTS: All supported S3 key patterns route correctly.
        COVERAGE: Ensures each agent type is tested.
        """
        test_cases = [
            ("transcripts/memories/test.txt", "memory"),
            ("transcripts/github_ideas/test.txt", "github"),
            ("transcripts/work/test.txt", "work"),
        ]

        for s3_key, expected_agent in test_cases:
            # Reset singleton
            agents.orchestrator_agent.orchestrator_agent = None
            
            event = {
                "Records": [
                    {
                        "s3": {
                            "bucket": {"name": "test-bucket"},
                            "object": {"key": s3_key},
                        }
                    }
                ]
            }

            # Mock S3 operations
            mock_s3 = Mock()
            lambda_fn.router_handler.s3 = mock_s3
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"Test transcript")
            }

            with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
                mock_route.return_value = {
                    "routing_decision": {
                        "primary_agent": expected_agent,
                        "secondary_agents": [],
                        "confidence": 0.95,
                        "reasoning": "Path-based routing"
                    },
                    "processing_results": {
                        expected_agent: {"result": "success"}
                    }
                }

                # Create mock context
                mock_context = Mock()
                mock_context.request_id = "test-request-id"

                result = lambda_handler(event, mock_context)

                assert result["statusCode"] == 200
                body = json.loads(result["body"])
                assert body["message"] == "Transcript processed successfully"
                assert body["success"] is True
                # Verify orchestrator was called with correct S3 key
                mock_route.assert_called_once_with(
                    transcript="Test transcript", 
                    source_key=s3_key,
                    bucket="test-bucket"
                )
                
                # Reset mock for next iteration
                mock_route.reset_mock()

    def test_lambda_handler_with_multi_agent_response(self):
        """Test lambda_handler with multiple agents processing.
        
        WHY: Orchestrator might route to multiple agents.
        TESTS:
        - Response aggregation from multiple agents
        - Proper JSON structure for multi-agent results
        - All agent results stored in output
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/general/test.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"I worked on a project and had a great memory")
        }

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {
                    "primary_agent": "multiple",
                    "secondary_agents": ["work", "memory"],
                    "confidence": 0.85,
                    "reasoning": "Mixed content detected"
                },
                "processing_results": {
                    "work": {"log_key": "work_journal/2024-W01.txt"},
                    "memory": {"memory_key": "memories/2024-01-01.jsonl"}
                }
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Transcript processed successfully"
            assert body["success"] is True
            assert "work" in body["agents_used"]
            assert "memory" in body["agents_used"]
            # Verify results contain both agents
            call_args = mock_s3.put_object.call_args
            body_content = call_args[1]["Body"].decode("utf-8")
            parsed_result = json.loads(body_content)
            assert "work" in parsed_result["agent_results"]
            assert "memory" in parsed_result["agent_results"]

    def test_lambda_handler_warmup_event(self):
        """Test lambda_handler handles warmup events correctly.
        
        WHY: Lambda containers need warmup to avoid cold starts.
        CURRENT STATE: Handler doesn't have warmup logic yet.
        TEST EXPECTATION: Should fail with missing Records key.
        TODO: Add proper warmup handling.
        """
        event = {"warmup": True}

        # The lambda handler doesn't have warmup handling in main handler
        # It will fail with missing Records key
        result = lambda_handler(event, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body

    def test_lambda_handler_with_missing_s3_key(self):
        """Test lambda_handler with missing S3 object key.
        
        WHY: S3 events might be malformed or corrupted.
        TESTS: Proper error handling for incomplete events.
        ROBUSTNESS: Lambda shouldn't crash on bad input.
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        # Missing object key
                    }
                }
            ]
        }

        result = lambda_handler(event, None)
        
        # Should return error response
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body

    def test_lambda_handler_with_empty_transcript(self):
        """Test lambda_handler with empty transcript from S3.
        
        WHY: Transcript files might be empty due to processing errors.
        TESTS: Handler still processes empty content gracefully.
        BEHAVIOR: Orchestrator receives empty string and handles it.
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/work/empty.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"")
        }

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {
                    "primary_agent": "unknown",
                    "secondary_agents": [],
                    "confidence": 0.2,
                    "reasoning": "Empty transcript"
                },
                "processing_results": {}
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Transcript processed successfully"
            assert body["success"] is True  # all() returns True for empty sequences
            assert body["agents_used"] == []  # No agents were used
            # Should still process even with empty transcript
            mock_route.assert_called_once_with(
                transcript="",
                source_key="transcripts/work/empty.txt",
                bucket="test-bucket"
            )