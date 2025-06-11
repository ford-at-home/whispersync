"""Unit tests for work journal agent."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the agent function
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from agents.work_journal_agent import handle


class TestWorkJournalAgent:
    """Test cases for work journal agent."""

    def test_handle_with_valid_payload(self):
        """Test handle function with valid payload."""
        payload = {
            "transcript": "Today I worked on the project",
            "bucket": "test-bucket"
        }
        
        with patch('agents.work_journal_agent.s3') as mock_s3:
            # Mock S3 get_object to simulate existing log
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"Existing log content\n")
            }
            
            result = handle(payload)
            
            assert "log_key" in result
            assert "summary" in result
            assert result["log_key"].startswith("work_journal/")
            assert "Logged work entry" in result["summary"]
            
            # Verify S3 operations were called
            mock_s3.get_object.assert_called_once()
            mock_s3.put_object.assert_called_once()

    def test_handle_with_new_week_log(self):
        """Test handle function when creating a new weekly log."""
        payload = {
            "transcript": "New week, new work",
            "bucket": "test-bucket"
        }
        
        import botocore
        with patch('agents.work_journal_agent.s3') as mock_s3, \
             patch('agents.work_journal_agent.botocore', botocore):
            # Mock S3 get_object to raise NoSuchKey (new log)
            from botocore.exceptions import ClientError
            error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
            mock_s3.get_object.side_effect = ClientError(error_response, 'GetObject')
            
            result = handle(payload)
            
            assert "log_key" in result
            assert "summary" in result
            assert result["log_key"].startswith("work_journal/")
            
            # Verify S3 operations were called
            mock_s3.get_object.assert_called_once()
            mock_s3.put_object.assert_called_once()

    def test_handle_without_boto3(self):
        """Test handle function when boto3 is not available."""
        payload = {
            "transcript": "Test transcript",
            "bucket": "test-bucket"
        }
        
        with patch('agents.work_journal_agent.boto3', None):
            with patch('agents.work_journal_agent.s3', None):
                result = handle(payload)
                
                assert result["log_key"] == "dry-run"
                assert result["summary"] == "Test transcript"[:50]

    def test_handle_with_empty_transcript(self):
        """Test handle function with empty transcript."""
        payload = {
            "transcript": "",
            "bucket": "test-bucket"
        }
        
        with patch('agents.work_journal_agent.s3') as mock_s3:
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"Existing log content\n")
            }
            
            result = handle(payload)
            
            assert "log_key" in result
            assert "summary" in result
            # Should still create a log entry even with empty transcript
            mock_s3.put_object.assert_called_once()

    def test_handle_with_missing_bucket(self):
        """Test handle function with missing bucket."""
        payload = {
            "transcript": "Test transcript"
        }
        
        with patch('agents.work_journal_agent.s3') as mock_s3:
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"Existing log content\n")
            }
            
            result = handle(payload)
            
            # Should still work, just use None as bucket
            assert "log_key" in result
            assert "summary" in result 