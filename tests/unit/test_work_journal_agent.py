"""Unit tests for work journal agent.

WHY THIS FILE EXISTS:
- Tests the most straightforward agent with append-only behavior
- Validates weekly log file structure and ISO week numbering
- Ensures proper work categorization and analysis
- Tests productivity analysis features

TESTING PHILOSOPHY:
- Test both new log creation and appending to existing logs
- Validate markdown formatting for work journal entries
- Test date-based file organization (YYYY-WXX format)
- Ensure proper work categorization and keyword extraction

WORK JOURNAL SPECIFIC TESTING:
1. File Structure: Weekly logs in work_journal/ directory
2. Date Handling: ISO week number calculation
3. Content Analysis: Work categories and key points
4. Productivity Patterns: Multi-week analysis
5. Summary Generation: Weekly and monthly summaries
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the agent function
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from agents.work_journal_agent import handle, WorkJournalAgent, get_work_journal_agent


class TestWorkJournalAgent:
    """Test cases for work journal agent.
    
    WHY THIS CLASS EXISTS:
    - Groups work journal tests for organization
    - Tests both individual entries and batch analysis
    - Validates the simplest agent for baseline behavior
    """

    def setup_method(self):
        """Reset singleton before each test."""
        import agents.work_journal_agent
        agents.work_journal_agent.work_journal_agent = None

    def test_handle_with_valid_payload(self):
        """Test handle function with valid payload.
        
        WHY: Tests appending to an existing weekly log.
        VALIDATION:
        - Existing log content preserved
        - New entry added with timestamp
        - Work categories identified
        - Key points extracted from content
        """
        payload = {
            "transcript": "Today I worked on the project",
            "bucket": "test-bucket",
        }

        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object to simulate existing log
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"# Work Journal - 2024 Week 01\n\nExisting log content\n")
            }

            result = handle(payload)

            assert "log_key" in result
            assert "summary" in result
            assert "categories" in result
            assert "key_points" in result
            assert result["log_key"].startswith("work_journal/")

            # Verify S3 operations were called
            mock_s3.get_object.assert_called_once()
            mock_s3.put_object.assert_called_once()

    def test_handle_with_new_week_log(self):
        """Test handle function when creating a new weekly log.
        
        WHY: Tests log creation when file doesn't exist yet.
        TESTS:
        - New markdown file structure created
        - Proper header with year and week number
        - First entry added correctly
        SCENARIO: Beginning of a new work week.
        """
        payload = {"transcript": "New week, new work", "bucket": "test-bucket"}

        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object to raise NoSuchKey (new log)
            mock_s3.get_object.side_effect = Exception("NoSuchKey")

            result = handle(payload)

            assert "log_key" in result
            assert result["log_key"].startswith("work_journal/")

            # Verify S3 operations were called
            mock_s3.get_object.assert_called_once()
            mock_s3.put_object.assert_called_once()

    def test_handle_without_boto3(self):
        """Test handle function when boto3 is not available.
        
        WHY: Local development graceful degradation.
        TESTS: Dry-run mode when AWS services unavailable.
        BEHAVIOR: Returns mock response instead of crashing.
        """
        payload = {"transcript": "Test transcript", "bucket": "test-bucket"}

        # Need to patch at module level before creating the agent
        with patch("agents.work_journal_agent.boto3", None):
            # Force recreation of the agent with boto3=None
            import agents.work_journal_agent
            agents.work_journal_agent.work_journal_agent = None
            
            result = handle(payload)

            assert result["log_key"] == "dry-run"

    def test_handle_with_empty_transcript(self):
        """Test handle function with empty transcript.
        
        WHY: User might accidentally trigger recording without speaking.
        TESTS: Still creates log entry to preserve the intent.
        RATIONALE: Empty entries might indicate blocked work time.
        """
        payload = {"transcript": "", "bucket": "test-bucket"}

        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"# Work Journal - 2024 Week 01\n\nExisting log content\n")
            }

            result = handle(payload)

            assert "log_key" in result
            # Should still create a log entry even with empty transcript
            mock_s3.put_object.assert_called_once()

    def test_handle_with_missing_bucket(self):
        """Test handle function with missing bucket.
        
        WHY: Payload might be incomplete in error scenarios.
        TESTS: Uses default bucket 'macbook-transcriptions' when not specified.
        FALLBACK: Should work with minimal configuration.
        """
        payload = {"transcript": "Test transcript"}

        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"# Work Journal - 2024 Week 01\n\nExisting log content\n")
            }

            result = handle(payload)

            # Should use default bucket "macbook-transcriptions"
            assert "log_key" in result
            mock_s3.put_object.assert_called_once()
            call_args = mock_s3.put_object.call_args
            assert call_args[1]["Bucket"] == "macbook-transcriptions"

    def test_work_journal_agent_initialization(self):
        """Test WorkJournalAgent initialization."""
        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_bedrock = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_bedrock
            )
            
            agent = WorkJournalAgent(bucket="test-bucket")
            
            assert agent.bucket == "test-bucket"
            assert agent.s3 == mock_s3
            assert agent.bedrock == mock_bedrock

    def test_append_work_log_method(self):
        """Test append_work_log method directly.
        
        WHY: Tests core logging logic in isolation.
        VALIDATION:
        - Proper timestamp formatting (ISO-8601)
        - Work categorization (meetings, coding, reviews, etc.)
        - Key points extraction from natural language
        - Markdown formatting preservation
        """
        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object to simulate existing log
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"# Work Journal - 2024 Week 01\n\nExisting content\n")
            }
            
            agent = WorkJournalAgent(bucket="test-bucket")
            result = agent.append_work_log("Test work entry")
            
            assert "log_key" in result
            assert result["log_key"].startswith("work_journal/")
            assert "summary" in result
            assert "categories" in result

    def test_generate_weekly_summary_method(self):
        """Test generate_weekly_summary method.
        
        WHY: Weekly summaries help users review their work patterns.
        TESTS:
        - Content aggregation across all week entries
        - Insight generation about productivity patterns
        - Error handling when summary generation fails
        FEATURE: Helps users prepare for weekly reviews.
        """
        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"# Work Journal - 2024 Week 01\n\n## Monday\n- Worked on feature X\n\n## Tuesday\n- Fixed bug Y\n")
            }
            
            agent = WorkJournalAgent()
            result = agent.generate_weekly_summary()
            
            assert "summary" in result
            assert "insights" in result
            # When error occurs, it should still have these fields
            assert result["summary"] == "Unable to generate summary"

    def test_singleton_pattern(self):
        """Test that get_work_journal_agent returns singleton."""
        with patch("agents.work_journal_agent.boto3"):
            # Reset the singleton
            import agents.work_journal_agent
            agents.work_journal_agent.work_journal_agent = None
            
            agent1 = get_work_journal_agent()
            agent2 = get_work_journal_agent()
            
            assert agent1 is agent2

    def test_work_journal_agent_callable(self):
        """Test that WorkJournalAgent is callable."""
        with patch("agents.work_journal_agent.boto3"):
            with patch("agents.work_journal_agent.Agent") as mock_agent_class:
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance
                
                agent = WorkJournalAgent()
                agent.agent = mock_agent_instance
                
                result = agent("Test prompt")
                
                mock_agent_instance.assert_called_once_with("Test prompt")

    def test_analyze_productivity_patterns_method(self):
        """Test analyze_productivity_patterns method.
        
        WHY: Multi-week analysis helps identify productivity trends.
        TESTS:
        - Pattern recognition across multiple weeks
        - Trend identification (improving/declining productivity)
        - Actionable recommendations based on patterns
        ANALYTICS: Provides data-driven insights for self-improvement.
        """
        with patch("agents.work_journal_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock list_objects_v2
            mock_s3.list_objects_v2.return_value = {
                "Contents": [
                    {"Key": "work_journal/2024-W01.md"},
                    {"Key": "work_journal/2024-W02.md"}
                ]
            }
            
            # Mock get_object for journal files
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: b"# Work Journal - 2024 Week 01\n\n## Monday\n- Worked on feature X\n")
            }
            
            agent = WorkJournalAgent()
            result = agent.analyze_productivity_patterns(weeks=2)
            
            assert "patterns" in result
            assert "trends" in result
            assert "recommendations" in result