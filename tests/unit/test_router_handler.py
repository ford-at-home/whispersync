"""Unit tests for Lambda router handler."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Import the handler function
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from lambda_fn.router_handler import lambda_handler


class TestRouterHandler:
    """Test cases for Lambda router handler."""

    def test_lambda_handler_with_valid_event(self):
        """Test lambda_handler function with valid S3 event."""
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "transcripts/work/test.txt"}
                }
            }]
        }
        
        with patch('lambda_fn.router_handler.Agent') as mock_agent_class:
            with patch('boto3.client') as mock_boto3:
                # Mock S3 operations
                mock_s3 = Mock()
                mock_boto3.return_value = mock_s3
                mock_s3.get_object.return_value = {
                    "Body": Mock(read=lambda: b"Today I worked on the project")
                }
                
                # Mock Agent
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                mock_agent.return_value = {"log_key": "work_journal/2024-W01.txt", "summary": "Logged work entry"}
                
                result = lambda_handler(event, None)
                
                assert result["status"] == "ok"
                assert "output_key" in result
                assert result["output_key"] == "outputs/work/test_response.json"
                
                # Verify S3 operations
                mock_s3.get_object.assert_called_once_with(
                    Bucket="test-bucket",
                    Key="transcripts/work/test.txt"
                )
                mock_s3.put_object.assert_called_once()
                
                # Verify Agent invocation with tools parameter
                mock_agent_class.assert_called_once()
                assert "tools" in mock_agent_class.call_args[1]
                mock_agent.assert_called_once()

    def test_lambda_handler_with_agent_json_response(self):
        """Test lambda_handler function with Agent returning JSON string."""
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "transcripts/memories/test.txt"}
                }
            }]
        }
        
        with patch('lambda_fn.router_handler.Agent') as mock_agent_class:
            with patch('boto3.client') as mock_boto3:
                mock_s3 = Mock()
                mock_boto3.return_value = mock_s3
                mock_s3.get_object.return_value = {
                    "Body": Mock(read=lambda: b"Test memory")
                }
                
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                mock_agent.return_value = '{"memory_key": "memories/test.jsonl"}'
                
                result = lambda_handler(event, None)
                
                assert result["status"] == "ok"
                # Verify the JSON string was parsed
                mock_s3.put_object.assert_called_once()
                call_args = mock_s3.put_object.call_args
                body_content = call_args[1]["Body"].decode("utf-8")
                assert "memory_key" in body_content

    def test_lambda_handler_with_agent_plain_response(self):
        """Test lambda_handler function with Agent returning plain text."""
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "transcripts/github_ideas/test.txt"}
                }
            }]
        }
        
        with patch('lambda_fn.router_handler.Agent') as mock_agent_class:
            with patch('boto3.client') as mock_boto3:
                mock_s3 = Mock()
                mock_boto3.return_value = mock_s3
                mock_s3.get_object.return_value = {
                    "Body": Mock(read=lambda: b"Test idea")
                }
                
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                mock_agent.return_value = "plain text response"
                
                result = lambda_handler(event, None)
                
                assert result["status"] == "ok"
                # Verify plain text was handled correctly
                mock_s3.put_object.assert_called_once()
                call_args = mock_s3.put_object.call_args
                body_content = call_args[1]["Body"].decode("utf-8")
                assert body_content == '"plain text response"'

    def test_lambda_handler_with_agent_invocation_error(self):
        """Test lambda_handler function when agent invocation fails."""
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "transcripts/work/test.txt"}
                }
            }]
        }
        
        with patch('lambda_fn.router_handler.Agent') as mock_agent_class:
            with patch('boto3.client') as mock_boto3:
                mock_s3 = Mock()
                mock_boto3.return_value = mock_s3
                mock_s3.get_object.return_value = {
                    "Body": Mock(read=lambda: b"Test transcript")
                }
                
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                mock_agent.side_effect = Exception("Agent failed")
                
                with pytest.raises(Exception, match="Agent failed"):
                    lambda_handler(event, None)

    def test_lambda_handler_with_different_agent_types(self):
        """Test lambda_handler function with different agent types."""
        test_cases = [
            ("transcripts/memories/test.txt", "memories"),
            ("transcripts/github_ideas/test.txt", "github_ideas"),
        ]
        
        for s3_key, expected_agent in test_cases:
            event = {
                "Records": [{
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": s3_key}
                    }
                }]
            }
            
            with patch('lambda_fn.router_handler.Agent') as mock_agent_class:
                with patch('boto3.client') as mock_boto3:
                    mock_s3 = Mock()
                    mock_boto3.return_value = mock_s3
                    mock_s3.get_object.return_value = {
                        "Body": Mock(read=lambda: b"Test transcript")
                    }
                    
                    mock_agent = Mock()
                    mock_agent_class.return_value = mock_agent
                    mock_agent.return_value = {"result": "success"}
                    
                    result = lambda_handler(event, None)
                    
                    assert result["status"] == "ok"
                    mock_agent_class.assert_called_once()
                    # Verify tools parameter is used instead of name
                    assert "tools" in mock_agent_class.call_args[1] 