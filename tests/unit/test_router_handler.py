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
from urllib.parse import quote_plus

# Import the handler function
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lambda_fn.router_handler import lambda_handler, process_single_transcript

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
            assert body["message"] == "All transcripts processed successfully"
            assert body["processed"] == 1
            assert body["total"] == 1
            assert "results" in body
            assert len(body["results"]) == 1
            assert body["results"][0]["success"] is True

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
            assert body["message"] == "All transcripts processed successfully"
            assert body["processed"] == 1
            assert body["total"] == 1
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
            assert body["message"] == "All transcripts processed successfully"
            assert body["processed"] == 1
            assert body["total"] == 1
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
            assert "All records failed to process" in body["error"]

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
                assert body["message"] == "All transcripts processed successfully"
                assert body["processed"] == 1
                assert body["total"] == 1
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
            assert body["message"] == "All transcripts processed successfully"
            assert body["processed"] == 1
            assert body["total"] == 1
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

        assert result["statusCode"] == 400  # Bad request for missing Records
        body = json.loads(result["body"])
        assert "error" in body
        assert "Missing 'Records' field" in body["details"]

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
            assert body["message"] == "All transcripts processed successfully"
            assert body["processed"] == 1
            assert body["total"] == 1
            # Should still process even with empty transcript
            mock_route.assert_called_once_with(
                transcript="",
                source_key="transcripts/work/empty.txt",
                bucket="test-bucket"
            )

    def test_lambda_handler_with_url_encoded_keys(self):
        """Test lambda_handler with URL-encoded S3 keys.
        
        WHY: S3 event notifications URL-encode object keys.
        TESTS: Proper decoding of spaces and special characters.
        EXAMPLES: 
        - Spaces can be encoded as '+' or '%20'
        - Special chars like '&' become '%26'
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/work/my+voice+memo+2024-01-01.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"Test transcript with spaces")
        }

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {
                    "primary_agent": "work",
                    "secondary_agents": [],
                    "confidence": 0.95,
                    "reasoning": "Work-related content"
                },
                "processing_results": {
                    "work": {"result": "success"}
                }
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            
            # Verify S3 was called with decoded key
            mock_s3.get_object.assert_called_once_with(
                Bucket="test-bucket", 
                Key="transcripts/work/my voice memo 2024-01-01.txt"  # Decoded
            )
            
            # Verify orchestrator received decoded key
            mock_route.assert_called_once()
            call_args = mock_route.call_args[1]
            assert call_args["source_key"] == "transcripts/work/my voice memo 2024-01-01.txt"

    def test_lambda_handler_with_multi_record_event(self):
        """Test lambda_handler with multiple S3 records.
        
        WHY: S3 can batch multiple object notifications.
        TESTS: All records are processed correctly.
        VALIDATION: Each record gets its own processing.
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/work/memo1.txt"},
                    }
                },
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/memories/memo2.txt"},
                    }
                },
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/github_ideas/memo3.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        
        # Return different content for each file
        mock_s3.get_object.side_effect = [
            {"Body": Mock(read=lambda: b"Work transcript")},
            {"Body": Mock(read=lambda: b"Memory transcript")},
            {"Body": Mock(read=lambda: b"GitHub idea transcript")}
        ]

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            # Return different results for each agent
            mock_route.side_effect = [
                {
                    "routing_decision": {"primary_agent": "work"},
                    "processing_results": {"work": {"result": "work success"}}
                },
                {
                    "routing_decision": {"primary_agent": "memory"},
                    "processing_results": {"memory": {"result": "memory success"}}
                },
                {
                    "routing_decision": {"primary_agent": "github"},
                    "processing_results": {"github": {"result": "github success"}}
                }
            ]

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "All transcripts processed successfully"
            assert body["processed"] == 3
            assert body["total"] == 3
            assert len(body["results"]) == 3
            
            # Verify all S3 operations
            assert mock_s3.get_object.call_count == 3
            assert mock_s3.put_object.call_count == 3
            
            # Verify all orchestrator invocations
            assert mock_route.call_count == 3

    def test_lambda_handler_with_partial_failure(self):
        """Test lambda_handler when some records fail.
        
        WHY: Need to handle partial failures gracefully.
        TESTS: Multi-status response with error details.
        VALIDATION: Successful records still processed.
        """
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/work/good.txt"},
                    }
                },
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "transcripts/work/bad.txt"},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        
        # First succeeds, second fails
        mock_s3.get_object.side_effect = [
            {"Body": Mock(read=lambda: b"Good transcript")},
            Exception("S3 GetObject failed")
        ]

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {"primary_agent": "work"},
                "processing_results": {"work": {"result": "success"}}
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 207  # Multi-status
            body = json.loads(result["body"])
            assert body["message"] == "Partial success"
            assert body["processed"] == 1
            assert body["total"] == 2
            assert len(body["errors"]) == 1
            assert body["errors"][0]["error"] == "Failed to download transcript"

    def test_lambda_handler_with_invalid_event(self):
        """Test lambda_handler with various invalid event formats.
        
        WHY: Lambda should handle malformed events gracefully.
        TESTS: Various invalid event structures.
        VALIDATION: Appropriate error responses.
        """
        test_cases = [
            (None, "Invalid event format"),
            ({}, "Missing 'Records' field"),
            ({"Records": []}, "No records to process"),
            ({"Records": [{}]}, "Missing 's3' field"),
            ({"Records": [{"s3": {}}]}, "Incomplete S3 information"),
        ]

        for event, expected_error in test_cases:
            result = lambda_handler(event, None)
            
            if event is None or "Records" not in (event or {}):
                assert result["statusCode"] == 400
            elif not event.get("Records"):
                assert result["statusCode"] == 200
            else:
                assert result["statusCode"] == 500
                
            body = json.loads(result["body"])
            if "error" in body:
                # Check in main error message or details
                found = (expected_error in body["error"] or 
                        expected_error in body.get("details", "") or
                        any(expected_error in str(err) for err in body.get("errors", [])))
                assert found, f"Expected '{expected_error}' not found in response: {body}"
            else:
                assert expected_error in body.get("message", "")

    def test_lambda_handler_with_special_characters(self):
        """Test lambda_handler with special characters in S3 keys.
        
        WHY: File names can contain various special characters.
        TESTS: Proper handling of percent-encoded characters.
        EXAMPLES: &, =, ?, #, etc.
        """
        # Test with various encoded special characters
        encoded_key = "transcripts/work/memo%26notes%3D2024%2D01%2D01%2Etxt"
        expected_key = "transcripts/work/memo&notes=2024-01-01.txt"
        
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": encoded_key},
                    }
                }
            ]
        }

        # Mock S3 operations
        mock_s3 = Mock()
        lambda_fn.router_handler.s3 = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=lambda: b"Test with special chars")
        }

        with patch("lambda_fn.router_handler.route_to_agent") as mock_route:
            mock_route.return_value = {
                "routing_decision": {"primary_agent": "work"},
                "processing_results": {"work": {"result": "success"}}
            }

            # Create mock context
            mock_context = Mock()
            mock_context.request_id = "test-request-id"

            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            
            # Verify S3 was called with properly decoded key
            mock_s3.get_object.assert_called_once_with(
                Bucket="test-bucket", 
                Key=expected_key
            )