"""Pytest configuration and fixtures.

WHY THIS FILE EXISTS:
- Provides shared test fixtures and configuration for all tests
- Centralizes mock object creation to avoid duplication
- Ensures consistent test environment setup across the test suite

TESTING PHILOSOPHY:
- Mock external dependencies (AWS services, GitHub) for unit tests
- Provide realistic sample data for testing agent behaviors
- Use fixtures to reduce test setup boilerplate
- Ensure tests are isolated and reproducible
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def mock_s3():
    """Mock S3 client for testing.
    
    WHY: S3 is the primary storage mechanism for transcripts and outputs.
    We mock it to avoid AWS costs and ensure tests run offline.
    """
    with patch("boto3.client") as mock_client:
        mock_s3 = Mock()
        mock_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def mock_secrets_manager():
    """Mock Secrets Manager client for testing.
    
    WHY: Secrets Manager stores the GitHub PAT token.
    Mocking prevents exposing real credentials in tests.
    """
    with patch("boto3.client") as mock_client:
        mock_sm = Mock()
        mock_client.return_value = mock_sm
        yield mock_sm


@pytest.fixture
def mock_github():
    """Mock GitHub client for testing.
    
    WHY: GitHub API is used to create repositories.
    Mocking prevents creating real repos during tests.
    """
    with patch("github.Github") as mock_github_class:
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        yield mock_github


@pytest.fixture
def temp_transcript_file():
    """Create a temporary transcript file for testing.
    
    WHY: Integration tests need real files to mimic the local test runner.
    This fixture ensures proper cleanup after tests.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test transcript for testing purposes.")
        temp_file = f.name

    yield temp_file

    # Cleanup
    try:
        os.unlink(temp_file)
    except OSError:
        pass


@pytest.fixture
def sample_work_transcript():
    """Sample work transcript for testing.
    
    WHY: Provides consistent work-related content for testing the work agent.
    The content is designed to trigger work-specific behaviors.
    """
    return "Today I worked on implementing the new feature and reviewed three pull requests."


@pytest.fixture
def sample_memory_transcript():
    """Sample memory transcript for testing.
    
    WHY: Provides nostalgic/personal content for testing the memory agent.
    The content includes temporal references and emotions.
    """
    return "I remember when I first learned to code. It was in college and I was so excited."


@pytest.fixture
def sample_github_idea_transcript():
    """Sample GitHub idea transcript for testing.
    
    WHY: Provides project idea content for testing the GitHub agent.
    The content includes keywords that indicate a new project concept.
    """
    return "I want to create a new project for automated voice memo processing with AI."


@pytest.fixture
def mock_strands_client():
    """Mock Strands client for testing.
    
    WHY: Strands SDK is used for agent registration and invocation.
    Mocking allows testing agent logic without real Strands infrastructure.
    """
    with patch("strands_sdk.StrandsClient") as mock_strands_class:
        mock_strands = Mock()
        mock_strands_class.return_value = mock_strands
        yield mock_strands


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables.
    
    WHY: Tests need consistent environment variables for configuration.
    This fixture ensures all tests have required env vars set and cleaned up.
    Using autouse=True ensures this runs for every test automatically.
    """
    # Set test environment variables
    os.environ["GITHUB_SECRET_NAME"] = "test/github_token"
    os.environ["STRANDS_REGION"] = "us-east-1"

    yield

    # Cleanup
    os.environ.pop("GITHUB_SECRET_NAME", None)
    os.environ.pop("STRANDS_REGION", None)
