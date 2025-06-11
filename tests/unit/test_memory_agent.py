"""Unit tests for memory agent."""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

# Import the agent function
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from agents.memory_agent import handle


class TestMemoryAgent:
    """Test cases for memory agent."""

    def test_handle_with_valid_payload(self):
        """Test handle function with valid payload."""
        payload = {
            "transcript": "I remember when I first learned to code",
            "bucket": "test-bucket"
        }
        
        with patch('agents.memory_agent.s3') as mock_s3:
            with patch('agents.memory_agent.datetime') as mock_datetime:
                # Mock datetime to return a fixed timestamp
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_datetime.datetime.utcnow.return_value = mock_now
                
                result = handle(payload)
                
                assert "memory_key" in result
                assert result["memory_key"] == "memories/2024-01-01T12:00:00.jsonl"
                
                # Verify S3 put_object was called with correct data
                mock_s3.put_object.assert_called_once()
                call_args = mock_s3.put_object.call_args
                assert call_args[1]["Bucket"] == "test-bucket"
                assert call_args[1]["Key"] == "memories/2024-01-01T12:00:00.jsonl"
                
                # Verify the JSON content
                body_content = call_args[1]["Body"].decode("utf-8")
                record = json.loads(body_content)
                assert record["text"] == "I remember when I first learned to code"
                assert record["sentiment"] == "neutral"
                assert record["timestamp"] == "2024-01-01T12:00:00"

    def test_handle_without_boto3(self):
        """Test handle function when boto3 is not available."""
        payload = {
            "transcript": "Test memory",
            "bucket": "test-bucket"
        }
        
        with patch('agents.memory_agent.boto3', None):
            with patch('agents.memory_agent.s3', None):
                result = handle(payload)
                
                assert result["memory_key"] == "dry-run"

    def test_handle_with_empty_transcript(self):
        """Test handle function with empty transcript."""
        payload = {
            "transcript": "",
            "bucket": "test-bucket"
        }
        
        with patch('agents.memory_agent.s3') as mock_s3:
            with patch('agents.memory_agent.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_datetime.datetime.utcnow.return_value = mock_now
                
                result = handle(payload)
                
                assert "memory_key" in result
                # Should still create a memory record even with empty transcript
                mock_s3.put_object.assert_called_once()
                
                # Verify the JSON content has empty text
                call_args = mock_s3.put_object.call_args
                body_content = call_args[1]["Body"].decode("utf-8")
                record = json.loads(body_content)
                assert record["text"] == ""

    def test_handle_with_missing_bucket(self):
        """Test handle function with missing bucket."""
        payload = {
            "transcript": "Test memory"
        }
        
        with patch('agents.memory_agent.s3') as mock_s3:
            with patch('agents.memory_agent.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_datetime.datetime.utcnow.return_value = mock_now
                
                result = handle(payload)
                
                # Should still work, just use empty string as bucket
                assert "memory_key" in result
                mock_s3.put_object.assert_called_once()
                call_args = mock_s3.put_object.call_args
                assert call_args[1]["Bucket"] == ""

    def test_handle_with_missing_transcript(self):
        """Test handle function with missing transcript."""
        payload = {
            "bucket": "test-bucket"
        }
        
        with patch('agents.memory_agent.s3') as mock_s3:
            with patch('agents.memory_agent.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_datetime.datetime.utcnow.return_value = mock_now
                
                result = handle(payload)
                
                assert "memory_key" in result
                # Should use empty string as default
                mock_s3.put_object.assert_called_once()
                call_args = mock_s3.put_object.call_args
                body_content = call_args[1]["Body"].decode("utf-8")
                record = json.loads(body_content)
                assert record["text"] == "" 