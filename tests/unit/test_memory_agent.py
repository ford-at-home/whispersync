"""Unit tests for memory agent.

WHY THIS FILE EXISTS:
- Tests the memory agent's complex data analysis capabilities
- Validates JSONL storage format for memories
- Ensures proper sentiment analysis and theme extraction
- Tests memory search and relationship finding

TESTING PHILOSOPHY:
- Mock S3 operations to test storage logic without AWS
- Test emotional analysis with realistic memory content
- Validate JSON serialization of memory objects
- Test search and indexing functionality

MEMORY-SPECIFIC TESTING:
1. Sentiment Analysis: Ensure emotions are properly categorized
2. Theme Extraction: Test keyword and topic identification
3. Significance Scoring: Validate importance ratings (1-10)
4. Temporal Organization: Test date-based storage structure
5. Related Memory Finding: Test similarity algorithms
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the agent function
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from agents.memory_agent import handle, MemoryAgent, get_memory_agent


class TestMemoryAgent:
    """Test cases for memory agent.
    
    WHY THIS CLASS EXISTS:
    - Groups memory agent tests for organization
    - Provides singleton reset for clean test isolation
    - Tests both storage and retrieval operations
    """

    def setup_method(self):
        """Reset singleton before each test."""
        import agents.memory_agent
        agents.memory_agent.memory_agent = None

    def test_handle_with_valid_payload(self):
        """Test handle function with valid payload.
        
        WHY: Tests the main workflow for storing a memory.
        VALIDATION:
        - Memory stored in JSONL format
        - Sentiment analysis performed
        - Timestamp added correctly
        - S3 operations called with correct parameters
        """
        payload = {
            "transcript": "I remember when I first learned to code",
            "bucket": "test-bucket",
        }

        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object to simulate no existing content
            def get_object_side_effect(*args, **kwargs):
                # Always return NoSuchKey for any get_object call
                raise Exception("NoSuchKey")
            
            mock_s3.get_object.side_effect = get_object_side_effect
            
            # Mock S3 list_objects_v2 for search_memories
            mock_s3.list_objects_v2.return_value = {"Contents": []}
            
            with patch("agents.memory_agent.datetime") as mock_datetime:
                # Mock datetime to return a fixed timestamp
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_now.strftime.return_value = "2024-01-01"
                mock_datetime.datetime.utcnow.return_value = mock_now

                result = handle(payload)

                assert "memory_key" in result
                assert result["memory_key"] == "memories/2024-01-01.jsonl"

                # Verify S3 put_object was called with correct data
                mock_s3.put_object.assert_called()
                put_calls = [call for call in mock_s3.put_object.call_args_list]
                
                # Find the memory file write (not the theme index)
                memory_call = None
                for call in put_calls:
                    if call[1]["Key"] == "memories/2024-01-01.jsonl":
                        memory_call = call
                        break
                
                assert memory_call is not None
                assert memory_call[1]["Bucket"] == "test-bucket"
                
                # Verify the JSON content
                body_content = memory_call[1]["Body"].decode("utf-8")
                record = json.loads(body_content.strip())
                assert record["content"] == "I remember when I first learned to code"
                assert record["sentiment"] == "neutral"
                assert record["timestamp"] == "2024-01-01T12:00:00"

    def test_handle_without_boto3(self):
        """Test handle function when boto3 is not available.
        
        WHY: Local development graceful degradation.
        TESTS: Returns dry-run mode instead of crashing.
        DESIGN: Allows testing memory logic without AWS.
        """
        payload = {"transcript": "Test memory", "bucket": "test-bucket"}

        # Need to patch at module level before creating the agent
        with patch("agents.memory_agent.boto3", None):
            # Force recreation of the agent with boto3=None
            import agents.memory_agent
            agents.memory_agent.memory_agent = None
            
            result = handle(payload)

            assert result["memory_key"] == "dry-run"

    def test_handle_with_empty_transcript(self):
        """Test handle function with empty transcript.
        
        WHY: Voice recognition might produce empty results.
        TESTS: Still creates memory entry with empty content.
        RATIONALE: User intended to record something, so preserve the attempt.
        """
        payload = {"transcript": "", "bucket": "test-bucket"}

        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object to simulate no existing content
            def get_object_side_effect(*args, **kwargs):
                # Always return NoSuchKey for any get_object call
                raise Exception("NoSuchKey")
            
            mock_s3.get_object.side_effect = get_object_side_effect
            
            # Mock S3 list_objects_v2
            mock_s3.list_objects_v2.return_value = {"Contents": []}
            
            with patch("agents.memory_agent.datetime") as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_now.strftime.return_value = "2024-01-01"
                mock_datetime.datetime.utcnow.return_value = mock_now

                result = handle(payload)

                assert "memory_key" in result
                # Should still create a memory record even with empty transcript
                mock_s3.put_object.assert_called()

                # Find the memory file write
                put_calls = [call for call in mock_s3.put_object.call_args_list]
                memory_call = None
                for call in put_calls:
                    if call[1]["Key"] == "memories/2024-01-01.jsonl":
                        memory_call = call
                        break
                
                assert memory_call is not None
                body_content = memory_call[1]["Body"].decode("utf-8")
                record = json.loads(body_content.strip())
                assert record["content"] == ""

    def test_handle_with_missing_bucket(self):
        """Test handle function with missing bucket.
        
        WHY: Payload might be incomplete in error scenarios.
        TESTS: Uses default bucket 'voice-mcp' when not specified.
        ROBUSTNESS: Should work with minimal input.
        """
        payload = {"transcript": "Test memory"}

        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object to simulate no existing content
            def get_object_side_effect(*args, **kwargs):
                # Always return NoSuchKey for any get_object call
                raise Exception("NoSuchKey")
            
            mock_s3.get_object.side_effect = get_object_side_effect
            
            # Mock S3 list_objects_v2
            mock_s3.list_objects_v2.return_value = {"Contents": []}
            
            with patch("agents.memory_agent.datetime") as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_now.strftime.return_value = "2024-01-01"
                mock_datetime.datetime.utcnow.return_value = mock_now

                result = handle(payload)

                # Should use default bucket "voice-mcp"
                assert "memory_key" in result
                mock_s3.put_object.assert_called()
                
                # Find the memory file write
                put_calls = [call for call in mock_s3.put_object.call_args_list]
                memory_call = None
                for call in put_calls:
                    if call[1]["Key"] == "memories/2024-01-01.jsonl":
                        memory_call = call
                        break
                
                assert memory_call is not None
                assert memory_call[1]["Bucket"] == "voice-mcp"

    def test_handle_with_missing_transcript(self):
        """Test handle function with missing transcript.
        
        WHY: Validates handling of malformed payloads.
        TESTS: Uses empty string as default for missing transcript.
        ERROR HANDLING: Graceful handling of incomplete data.
        """
        payload = {"bucket": "test-bucket"}

        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object to simulate no existing content
            def get_object_side_effect(*args, **kwargs):
                # Always return NoSuchKey for any get_object call
                raise Exception("NoSuchKey")
            
            mock_s3.get_object.side_effect = get_object_side_effect
            
            # Mock S3 list_objects_v2
            mock_s3.list_objects_v2.return_value = {"Contents": []}
            
            with patch("agents.memory_agent.datetime") as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_now.strftime.return_value = "2024-01-01"
                mock_datetime.datetime.utcnow.return_value = mock_now

                result = handle(payload)

                assert "memory_key" in result
                # Should use empty string as default
                mock_s3.put_object.assert_called()
                
                # Find the memory file write
                put_calls = [call for call in mock_s3.put_object.call_args_list]
                memory_call = None
                for call in put_calls:
                    if call[1]["Key"] == "memories/2024-01-01.jsonl":
                        memory_call = call
                        break
                
                assert memory_call is not None
                body_content = memory_call[1]["Body"].decode("utf-8")
                record = json.loads(body_content.strip())
                assert record["content"] == ""

    def test_memory_agent_initialization(self):
        """Test MemoryAgent initialization."""
        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_bedrock = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_bedrock
            )
            
            agent = MemoryAgent(bucket="test-bucket")
            
            assert agent.bucket == "test-bucket"
            assert agent.s3 == mock_s3
            assert agent.bedrock == mock_bedrock

    def test_store_memory_method(self):
        """Test store_memory method directly.
        
        WHY: Tests core memory storage logic in isolation.
        VALIDATION:
        - Memory ID generation
        - Analysis structure (sentiment, themes, significance)
        - Related memory search integration
        - Proper JSONL formatting
        """
        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_bedrock = Mock()
            mock_boto3.client.side_effect = lambda service: (
                mock_s3 if service == "s3" else mock_bedrock
            )
            
            # Mock S3 get_object to simulate no existing content
            def get_object_side_effect(*args, **kwargs):
                # Always return NoSuchKey for any get_object call
                raise Exception("NoSuchKey")
            
            mock_s3.get_object.side_effect = get_object_side_effect
            
            # Mock S3 list_objects_v2
            mock_s3.list_objects_v2.return_value = {"Contents": []}
            
            with patch("agents.memory_agent.datetime") as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_now.strftime.return_value = "2024-01-01"
                mock_datetime.datetime.utcnow.return_value = mock_now
                
                agent = MemoryAgent(bucket="test-bucket")
                result = agent.store_memory("Test memory content")
                
                assert result["memory_key"] == "memories/2024-01-01.jsonl"
                assert result["analysis"]["sentiment"] == "neutral"
                assert "memory_id" in result
                assert "related_memories" in result

    def test_search_memories_method(self):
        """Test search_memories method.
        
        WHY: Search is critical for finding related memories.
        TESTS:
        - Keyword matching in memory content
        - Result formatting and preview generation
        - S3 object listing and content retrieval
        SEARCH STRATEGY: Simple keyword matching for now.
        """
        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 list_objects_v2
            mock_s3.list_objects_v2.return_value = {
                "Contents": [{"Key": "memories/2024-01-01.jsonl"}]
            }
            
            # Mock S3 get_object
            memory_data = {
                "id": "test-id",
                "timestamp": "2024-01-01T12:00:00",
                "content": "I learned Python programming today",
                "sentiment": "positive",
                "themes": ["learning", "programming"],
                "people": [],
                "significance": 7
            }
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: json.dumps(memory_data).encode() + b"\n")
            }
            
            agent = MemoryAgent()
            results = agent.search_memories("Python")
            
            assert len(results) > 0
            assert results[0]["memory_id"] == "test-id"
            assert "Python" in results[0]["preview"]

    def test_analyze_memory_themes_method(self):
        """Test analyze_memory_themes method.
        
        WHY: Theme analysis helps identify patterns over time.
        TESTS:
        - Theme indexing and counting
        - Time period filtering (week/month/year)
        - Insight generation based on theme patterns
        ANALYTICS: Provides user insights into their thinking patterns.
        """
        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock theme index
            mock_s3.get_object.side_effect = [
                # First call for themes index
                {"Body": Mock(read=lambda: json.dumps({"learning": ["id1", "id2"]}).encode())},
                # Second call for memory file
                {
                    "Body": Mock(read=lambda: json.dumps({
                        "id": "id1",
                        "timestamp": datetime.utcnow().isoformat(),
                        "content": "Learning memory content",
                        "themes": ["learning"],
                        "emotions": ["excited"],
                        "sentiment": "positive",
                        "significance": 8
                    }).encode() + b"\n")
                }
            ]
            
            # Mock list_objects_v2
            mock_s3.list_objects_v2.return_value = {
                "Contents": [{"Key": "memories/2024-01-01.jsonl"}]
            }
            
            agent = MemoryAgent()
            result = agent.analyze_memory_themes("week")
            
            assert result["time_period"] == "week"
            assert result["total_memories"] == 1
            assert "theme_counts" in result
            assert "insights" in result

    def test_singleton_pattern(self):
        """Test that get_memory_agent returns singleton."""
        with patch("agents.memory_agent.boto3"):
            # Reset the singleton
            import agents.memory_agent
            agents.memory_agent.memory_agent = None
            
            agent1 = get_memory_agent()
            agent2 = get_memory_agent()
            
            assert agent1 is agent2

    def test_memory_agent_callable(self):
        """Test that MemoryAgent is callable."""
        with patch("agents.memory_agent.boto3"):
            with patch("agents.memory_agent.Agent") as mock_agent_class:
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance
                
                agent = MemoryAgent()
                agent.agent = mock_agent_instance
                
                result = agent("Test prompt")
                
                mock_agent_instance.assert_called_once_with("Test prompt")

    def test_get_memory_timeline_method(self):
        """Test get_memory_timeline method.
        
        WHY: Timeline view helps users see memory patterns over time.
        TESTS:
        - Date range filtering
        - Memory counting per day
        - Chronological organization
        USER EXPERIENCE: Enables 'memory lane' browsing.
        """
        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock S3 get_object for a specific date
            memory_data = {
                "id": "test-id",
                "timestamp": "2024-01-01T12:00:00",
                "content": "Test memory for timeline",
                "sentiment": "positive",
                "themes": ["test"],
                "significance": 5
            }
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: json.dumps(memory_data).encode() + b"\n")
            }
            
            agent = MemoryAgent()
            result = agent.get_memory_timeline(
                start_date="2024-01-01",
                end_date="2024-01-01"
            )
            
            assert len(result) > 0
            assert result[0]["date"] == "2024-01-01"
            assert result[0]["memory_count"] == 1

    def test_find_related_memories_method(self):
        """Test find_related_memories method.
        
        WHY: Related memories help surface connections between experiences.
        TESTS:
        - Similarity scoring based on themes, people, emotions
        - Relationship type identification
        - Relevance ranking
        ALGORITHM: Multi-factor similarity (themes + people + sentiment).
        """
        with patch("agents.memory_agent.boto3") as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.client.return_value = mock_s3
            
            # Mock list_objects_v2
            mock_s3.list_objects_v2.return_value = {
                "Contents": [{"Key": "memories/2024-01-01.jsonl"}]
            }
            
            # Mock S3 get_object with two memories
            memory1 = {
                "id": "memory1",
                "timestamp": "2024-01-01T12:00:00",
                "content": "Learning Python",
                "themes": ["learning", "programming"],
                "people": ["John"],
                "emotions": ["excited"],
                "sentiment": "positive"
            }
            memory2 = {
                "id": "memory2",
                "timestamp": "2024-01-01T13:00:00",
                "content": "Teaching Python to John",
                "themes": ["teaching", "programming"],
                "people": ["John"],
                "emotions": ["happy"],
                "sentiment": "positive"
            }
            memories_content = (
                json.dumps(memory1) + "\n" +
                json.dumps(memory2) + "\n"
            )
            mock_s3.get_object.return_value = {
                "Body": Mock(read=lambda: memories_content.encode())
            }
            
            agent = MemoryAgent()
            results = agent.find_related_memories("memory1")
            
            assert len(results) > 0
            assert results[0]["memory_id"] == "memory2"
            assert "relationship" in results[0]