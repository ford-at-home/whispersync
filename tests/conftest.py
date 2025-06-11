"""Pytest configuration and fixtures."""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def mock_s3():
    """Mock S3 client for testing."""
    with patch('boto3.client') as mock_client:
        mock_s3 = Mock()
        mock_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def mock_secrets_manager():
    """Mock Secrets Manager client for testing."""
    with patch('boto3.client') as mock_client:
        mock_sm = Mock()
        mock_client.return_value = mock_sm
        yield mock_sm


@pytest.fixture
def mock_github():
    """Mock GitHub client for testing."""
    with patch('github.Github') as mock_github_class:
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        yield mock_github


@pytest.fixture
def temp_transcript_file():
    """Create a temporary transcript file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
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
    """Sample work transcript for testing."""
    return "Today I worked on implementing the new feature and reviewed three pull requests."


@pytest.fixture
def sample_memory_transcript():
    """Sample memory transcript for testing."""
    return "I remember when I first learned to code. It was in college and I was so excited."


@pytest.fixture
def sample_github_idea_transcript():
    """Sample GitHub idea transcript for testing."""
    return "I want to create a new project for automated voice memo processing with AI."


@pytest.fixture
def mock_strands_client():
    """Mock Strands client for testing."""
    with patch('strands_sdk.StrandsClient') as mock_strands_class:
        mock_strands = Mock()
        mock_strands_class.return_value = mock_strands
        yield mock_strands


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment variables
    os.environ['GITHUB_SECRET_NAME'] = 'test/github_token'
    os.environ['STRANDS_REGION'] = 'us-east-1'
    
    yield
    
    # Cleanup
    os.environ.pop('GITHUB_SECRET_NAME', None)
    os.environ.pop('STRANDS_REGION', None) 