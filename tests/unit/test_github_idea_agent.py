"""Unit tests for GitHub idea agent."""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock

# Import the agent function
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from agents.github_idea_agent import handle, get_token


class TestGitHubIdeaAgent:
    """Test cases for GitHub idea agent."""

    def test_get_token_with_valid_secret(self):
        """Test get_token function with valid secret."""
        with patch('agents.github_idea_agent.sm') as mock_sm:
            mock_sm.get_secret_value.return_value = {
                "SecretString": "test-token-123"
            }
            
            token = get_token()
            
            assert token == "test-token-123"
            mock_sm.get_secret_value.assert_called_once_with(
                SecretId="github/personal_token"
            )

    def test_get_token_with_custom_secret_name(self):
        """Test get_token function with custom secret name."""
        with patch('agents.github_idea_agent.sm') as mock_sm:
            with patch('agents.github_idea_agent.SECRET_NAME', 'custom/secret'):
                mock_sm.get_secret_value.return_value = {
                    "SecretString": "custom-token"
                }
                
                token = get_token()
                
                assert token == "custom-token"
                mock_sm.get_secret_value.assert_called_once_with(
                    SecretId="custom/secret"
                )

    def test_get_token_without_boto3(self):
        """Test get_token function when boto3 is not available."""
        with patch('agents.github_idea_agent.sm', None):
            with pytest.raises(RuntimeError, match="boto3 is required"):
                get_token()

    def test_handle_with_valid_payload(self):
        """Test handle function with valid payload."""
        payload = {
            "transcript": "I want to create a new project for voice processing",
            "bucket": "test-bucket",
            "source_s3_key": "transcripts/github_ideas/test.txt"
        }
        
        with patch('agents.github_idea_agent.s3') as mock_s3:
            with patch('agents.github_idea_agent.sm') as mock_sm:
                with patch('agents.github_idea_agent.Github') as mock_github_class:
                    with patch('agents.github_idea_agent.time') as mock_time:
                        # Mock time.time to return fixed timestamp
                        mock_time.time.return_value = 1234567890
                        
                        # Mock secrets manager
                        mock_sm.get_secret_value.return_value = {
                            "SecretString": "test-token"
                        }
                        
                        # Mock GitHub API
                        mock_github = Mock()
                        mock_github_class.return_value = mock_github
                        mock_user = Mock()
                        mock_github.get_user.return_value = mock_user
                        mock_repo = Mock()
                        mock_user.create_repo.return_value = mock_repo
                        mock_repo.full_name = "testuser/voice-idea-1234567890"
                        
                        result = handle(payload)
                        
                        assert "repo" in result
                        assert "s3_source" in result
                        assert result["repo"] == "testuser/voice-idea-1234567890"
                        assert result["s3_source"] == "transcripts/github_ideas/test.txt"
                        
                        # Verify GitHub operations
                        mock_github_class.assert_called_once_with("test-token")
                        mock_github.get_user.assert_called_once()
                        mock_user.create_repo.assert_called_once_with(
                            "voice-idea-1234567890",
                            description="Created from voice memo"
                        )
                        
                        # Verify S3 operations
                        mock_s3.put_object.assert_called_once()
                        call_args = mock_s3.put_object.call_args
                        assert call_args[1]["Bucket"] == "test-bucket"
                        assert call_args[1]["Key"] == "github/history.jsonl"

    def test_handle_without_boto3(self):
        """Test handle function when boto3 is not available."""
        payload = {
            "transcript": "Test idea",
            "bucket": "test-bucket"
        }
        
        with patch('agents.github_idea_agent.boto3', None):
            with patch('agents.github_idea_agent.s3', None):
                with patch('agents.github_idea_agent.sm', None):
                    result = handle(payload)
                    
                    assert result["repo"] == "dry-run"

    def test_handle_without_pygithub(self):
        """Test handle function when PyGithub is not available."""
        payload = {
            "transcript": "Test idea",
            "bucket": "test-bucket"
        }
        
        with patch('agents.github_idea_agent.s3') as mock_s3:
            with patch('agents.github_idea_agent.sm') as mock_sm:
                with patch('agents.github_idea_agent.Github', None):
                    result = handle(payload)
                    
                    assert result["repo"] == "dry-run"

    def test_handle_with_empty_transcript(self):
        """Test handle function with empty transcript."""
        payload = {
            "transcript": "",
            "bucket": "test-bucket",
            "source_s3_key": "transcripts/github_ideas/empty.txt"
        }
        
        with patch('agents.github_idea_agent.s3') as mock_s3:
            with patch('agents.github_idea_agent.sm') as mock_sm:
                with patch('agents.github_idea_agent.Github') as mock_github_class:
                    with patch('agents.github_idea_agent.time') as mock_time:
                        mock_time.time.return_value = 1234567890
                        mock_sm.get_secret_value.return_value = {
                            "SecretString": "test-token"
                        }
                        mock_github = Mock()
                        mock_github_class.return_value = mock_github
                        mock_user = Mock()
                        mock_github.get_user.return_value = mock_user
                        mock_repo = Mock()
                        mock_user.create_repo.return_value = mock_repo
                        mock_repo.full_name = "testuser/voice-idea-1234567890"
                        
                        result = handle(payload)
                        
                        assert "repo" in result
                        # Should still create a repo even with empty transcript
                        mock_user.create_repo.assert_called_once()

    def test_handle_with_missing_optional_fields(self):
        """Test handle function with missing optional fields."""
        payload = {
            "transcript": "Test idea"
        }
        
        with patch('agents.github_idea_agent.s3') as mock_s3:
            with patch('agents.github_idea_agent.sm') as mock_sm:
                with patch('agents.github_idea_agent.Github') as mock_github_class:
                    with patch('agents.github_idea_agent.time') as mock_time:
                        mock_time.time.return_value = 1234567890
                        mock_sm.get_secret_value.return_value = {
                            "SecretString": "test-token"
                        }
                        mock_github = Mock()
                        mock_github_class.return_value = mock_github
                        mock_user = Mock()
                        mock_github.get_user.return_value = mock_user
                        mock_repo = Mock()
                        mock_user.create_repo.return_value = mock_repo
                        mock_repo.full_name = "testuser/voice-idea-1234567890"
                        
                        result = handle(payload)
                        
                        assert "repo" in result
                        assert result["s3_source"] == ""
                        # Should still work with missing optional fields
                        mock_user.create_repo.assert_called_once() 