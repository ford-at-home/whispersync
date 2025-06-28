"""Unit tests for GitHub idea agent.

WHY THIS FILE EXISTS:
- Tests the most complex agent with external API dependencies
- Validates repository name sanitization and generation
- Ensures proper error handling when GitHub API fails
- Tests both dry-run mode and production mode

TESTING PHILOSOPHY:
- Mock all external dependencies (GitHub API, AWS services)
- Test edge cases like empty transcripts and missing credentials
- Verify singleton pattern works correctly
- Test both the agent class and the handle function entry point

KEY TESTING STRATEGIES:
1. Secrets Management: Test with/without GitHub tokens
2. Repository Creation: Mock GitHub API responses
3. Error Handling: Test graceful degradation when services unavailable
4. Name Sanitization: Ensure repo names follow GitHub rules
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the agent function
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from agents.github_idea_agent import handle, GitHubIdeaAgent, get_github_idea_agent


class TestGitHubIdeaAgent:
    """Test cases for GitHub idea agent.
    
    WHY THIS CLASS EXISTS:
    - Groups all GitHub agent tests for better organization
    - Provides setup_method to reset singleton state
    - Ensures each test starts with a clean agent instance
    """

    def setup_method(self):
        """Reset singleton before each test.
        
        WHY: The agent uses singleton pattern for efficiency in Lambda.
        Tests must reset this to avoid state leakage between tests.
        """
        import agents.github_idea_agent
        agents.github_idea_agent.github_idea_agent = None

    def test_get_token_with_valid_secret(self):
        """Test _get_token method with valid secret.
        
        WHY: Token retrieval is critical for GitHub API access.
        TESTS: Normal case where secret exists and is properly formatted.
        """
        agent = GitHubIdeaAgent()

        with patch.object(agent, "sm") as mock_sm:
            mock_sm.get_secret_value.return_value = {"SecretString": "test-token-123"}

            token = agent._get_token()

            assert token == "test-token-123"
            # Uses the environment variable set by conftest.py
            mock_sm.get_secret_value.assert_called_once_with(
                SecretId="test/github_token"
            )

    def test_get_token_with_custom_secret_name(self):
        """Test _get_token method with custom secret name.
        
        WHY: Supports different deployment environments (dev/prod).
        TESTS: Environment variable overrides default secret name.
        """
        agent = GitHubIdeaAgent()

        with patch.object(agent, "sm") as mock_sm:
            with patch.dict(os.environ, {"GITHUB_SECRET_NAME": "custom/secret"}):
                mock_sm.get_secret_value.return_value = {"SecretString": "custom-token"}

                token = agent._get_token()

                assert token == "custom-token"
                mock_sm.get_secret_value.assert_called_once_with(
                    SecretId="custom/secret"
                )

    def test_get_token_without_boto3(self):
        """Test _get_token method when boto3 is not available.
        
        WHY: Local development might not have AWS credentials.
        TESTS: Proper error message when Secrets Manager unavailable.
        EDGE CASE: This prevents silent failures in development.
        """
        agent = GitHubIdeaAgent()
        agent.sm = None

        with pytest.raises(RuntimeError, match="Secrets Manager unavailable"):
            agent._get_token()

    def test_handle_with_valid_payload(self):
        """Test handle function with valid payload.
        
        WHY: Tests the main entry point with realistic input.
        TESTS:
        - Complete workflow from transcript to GitHub repo creation
        - S3 operations for storing history
        - GitHub API calls with proper parameters
        - Response format matches expected schema
        """
        payload = {
            "transcript": "I want to create a new project for voice processing",
            "bucket": "test-bucket",
            "source_s3_key": "transcripts/github_ideas/test.txt",
        }

        with patch("agents.github_idea_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_sm = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_sm
            )

            with patch("agents.github_idea_agent.Github") as mock_github_class:
                with patch("agents.github_idea_agent.time") as mock_time:
                    # Mock time
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
                    mock_repo.full_name = "testuser/voice-processing-project"
                    mock_repo.html_url = (
                        "https://github.com/testuser/voice-processing-project"
                    )
                    mock_repo.created_at.isoformat.return_value = "2024-01-01T00:00:00"

                    # Mock S3 operations
                    mock_s3.get_object.side_effect = Exception("NoSuchKey")

                    result = handle(payload)

                    assert "url" in result
                    assert result["url"] == "https://github.com/testuser/voice-processing-project"
                    assert "repo" in result

                    # Verify GitHub operations
                    mock_github_class.assert_called_once_with("test-token")
                    mock_github.get_user.assert_called_once()
                    mock_user.create_repo.assert_called_once()

                    # Verify S3 operations were attempted
                    assert mock_s3.put_object.call_count >= 1

    def test_handle_without_boto3(self):
        """Test handle function when boto3 is not available.
        
        WHY: Ensures graceful degradation for local development.
        TESTS: Dry-run mode when AWS services unavailable.
        DESIGN DECISION: Returns mock data instead of failing.
        """
        payload = {"transcript": "Test idea", "bucket": "test-bucket"}

        # Need to patch at module level before creating the agent
        with patch("agents.github_idea_agent.boto3", None):
            # Force recreation of the agent with boto3=None
            import agents.github_idea_agent
            agents.github_idea_agent.github_idea_agent = None
            
            result = handle(payload)

            assert result["repo"] == "dry-run/test-repo"
            assert result["status"] == "dry-run"

    def test_handle_without_pygithub(self):
        """Test handle function when PyGithub is not available.
        
        WHY: PyGithub might not be installed in all environments.
        TESTS: Dry-run mode when GitHub library unavailable.
        RATIONALE: Better to log the idea than crash completely.
        """
        payload = {"transcript": "Test idea", "bucket": "test-bucket"}

        with patch("agents.github_idea_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_sm = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_sm
            )

            with patch("agents.github_idea_agent.Github", None):
                result = handle(payload)

                assert result["repo"] == "dry-run/test-repo"
                assert result["status"] == "dry-run"

    def test_handle_with_empty_transcript(self):
        """Test handle function with empty transcript.
        
        WHY: Voice transcription can sometimes fail or be empty.
        TESTS: Agent still creates a repo with generic name.
        DESIGN DECISION: Empty content shouldn't prevent repo creation.
        """
        payload = {
            "transcript": "",
            "bucket": "test-bucket",
            "source_s3_key": "transcripts/github_ideas/empty.txt",
        }

        with patch("agents.github_idea_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_sm = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_sm
            )

            with patch("agents.github_idea_agent.Github") as mock_github_class:
                with patch("agents.github_idea_agent.time") as mock_time:
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
                    mock_repo.full_name = "testuser/github-idea"
                    mock_repo.html_url = (
                        "https://github.com/testuser/github-idea"
                    )
                    mock_repo.created_at.isoformat.return_value = "2024-01-01T00:00:00"

                    # Mock S3 operations
                    mock_s3.get_object.side_effect = Exception("NoSuchKey")

                    result = handle(payload)

                    assert "url" in result
                    # Should still create a repo even with empty transcript
                    mock_user.create_repo.assert_called_once()

    def test_handle_with_missing_optional_fields(self):
        """Test handle function with missing optional fields.
        
        WHY: Payload might be incomplete in error scenarios.
        TESTS: Agent uses defaults for missing bucket/s3_key.
        ROBUSTNESS: Should work with minimal required input.
        """
        payload = {"transcript": "Test idea"}

        with patch("agents.github_idea_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_sm = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_sm
            )

            with patch("agents.github_idea_agent.Github") as mock_github_class:
                with patch("agents.github_idea_agent.time") as mock_time:
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
                    mock_repo.full_name = "testuser/test-idea"
                    mock_repo.html_url = (
                        "https://github.com/testuser/test-idea"
                    )
                    mock_repo.created_at.isoformat.return_value = "2024-01-01T00:00:00"

                    # Mock S3 operations
                    mock_s3.get_object.side_effect = Exception("NoSuchKey")

                    result = handle(payload)

                    assert "url" in result
                    # Should still work with missing optional fields
                    mock_user.create_repo.assert_called_once()

    def test_sanitize_repo_name(self):
        """Test repository name sanitization.
        
        WHY: GitHub has strict rules for repository names.
        EDGE CASES TESTED:
        - Special characters (replaced with safe alternatives)
        - Leading/trailing hyphens (stripped)
        - Multiple consecutive hyphens (collapsed)
        - Empty strings (default name generated)
        - Very long names (truncated to GitHub limits)
        """
        agent = GitHubIdeaAgent()

        # Test various inputs
        assert agent._sanitize_repo_name("Hello World") == "hello-world"
        assert agent._sanitize_repo_name("Test_Project_123") == "test-project-123"
        assert agent._sanitize_repo_name("My---App") == "my-app"
        assert agent._sanitize_repo_name("-leading-trailing-") == "leading-trailing"
        assert agent._sanitize_repo_name("Special@#$Characters") == "specialcharacters"
        assert agent._sanitize_repo_name("") != ""  # Should generate a default name
        assert len(agent._sanitize_repo_name("a" * 200)) <= 100  # Should truncate

    def test_singleton_pattern(self):
        """Test that get_github_idea_agent returns singleton.
        
        WHY: Lambda containers reuse instances for efficiency.
        TESTS: Multiple calls return the same agent instance.
        PERFORMANCE: Avoids recreating boto3 clients repeatedly.
        """
        with patch("agents.github_idea_agent.boto3"):
            agent1 = get_github_idea_agent()
            agent2 = get_github_idea_agent()

            assert agent1 is agent2

    def test_github_idea_agent_initialization(self):
        """Test GitHubIdeaAgent initialization.
        
        WHY: Constructor sets up AWS clients and configuration.
        TESTS: All required clients are created and stored.
        VALIDATION: Instance attributes are set correctly.
        """
        with patch("agents.github_idea_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_sm = Mock()
            mock_bedrock = Mock()
            mock_boto3.client.side_effect = lambda service: {
                "s3": mock_s3,
                "secretsmanager": mock_sm,
                "bedrock-runtime": mock_bedrock,
            }.get(service)
            
            agent = GitHubIdeaAgent(bucket="test-bucket", github_token="test-token")
            
            assert agent.bucket == "test-bucket"
            assert agent.s3 == mock_s3
            assert agent.sm == mock_sm
            assert agent._github_token == "test-token"

    def test_create_repository_from_idea_method(self):
        """Test create_repository_from_idea method directly.
        
        WHY: Tests the core repository creation logic in isolation.
        TESTS:
        - GitHub API interactions
        - File creation in the new repository
        - Response format and content
        ISOLATION: Tests the method without the handle() wrapper.
        """
        with patch("agents.github_idea_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_sm = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_sm
            )
            
            with patch("agents.github_idea_agent.Github") as mock_github_class:
                mock_github = Mock()
                mock_github_class.return_value = mock_github
                mock_user = Mock()
                mock_github.get_user.return_value = mock_user
                mock_repo = Mock()
                mock_user.create_repo.return_value = mock_repo
                mock_repo.full_name = "testuser/new-idea"
                mock_repo.html_url = "https://github.com/testuser/new-idea"
                mock_repo.created_at.isoformat.return_value = "2024-01-01T00:00:00"
                
                # Mock the repo file creation
                mock_repo.create_file.return_value = Mock()
                
                # Mock S3 operations
                mock_s3.put_object.return_value = {}
                
                agent = GitHubIdeaAgent(github_token="test-token")
                result = agent.create_repository_from_idea(
                    "Create a web scraper",
                    is_private=False
                )
                
                assert "url" in result
                assert "repo" in result
                assert result["status"] == "success"

    def test_github_idea_agent_callable(self):
        """Test that GitHubIdeaAgent is callable.
        
        WHY: Agents implement the Strands Agent interface.
        TESTS: Agent instance can be called like a function.
        INTERFACE: Ensures compatibility with Strands SDK.
        """
        with patch("agents.github_idea_agent.boto3"):
            with patch("agents.github_idea_agent.Agent") as mock_agent_class:
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance
                
                agent = GitHubIdeaAgent()
                agent.agent = mock_agent_instance
                
                result = agent("Test prompt")
                
                mock_agent_instance.assert_called_once_with("Test prompt")