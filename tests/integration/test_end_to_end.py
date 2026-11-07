"""End-to-end integration tests for WhisperSync pipeline.

WHY THIS TEST EXISTS:
- Validates complete pipeline from S3 upload to agent processing
- Tests real AWS services (S3, Lambda) integration
- Ensures all agent types work correctly in production-like environment
- Validates performance requirements (< 5 seconds processing)
- Tests error handling and edge cases

TESTING PHILOSOPHY:
- Use real AWS services but mock external dependencies (GitHub API)
- Test both happy path and error scenarios
- Validate complete data flow from input to output
- Clean up all resources after tests
- Provide comprehensive assertions with clear error messages

REQUIREMENTS TESTED:
1. Work journal integration (transcript → executive agent → weekly log)
2. Memory preservation (transcript → spiritual agent → JSONL file)
3. GitHub repo creation (transcript → github agent → repo created)
4. Error handling for invalid scenarios
5. Performance measurement (< 5 seconds processing time)
6. Lambda trigger and routing validation
7. S3 output validation
"""

import pytest
import json
import boto3
import time
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, Mock, MagicMock
from moto import mock_aws
import requests
from botocore.exceptions import ClientError

# Test configuration
TEST_BUCKET_NAME = os.environ.get("TEST_BUCKET_NAME", "macbook-transcriptions-test")
TEST_LAMBDA_FUNCTION_NAME = os.environ.get("TEST_LAMBDA_FUNCTION_NAME", "whispersync-router")
TEST_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
TEST_TIMEOUT = 30  # seconds
PERFORMANCE_THRESHOLD = 5.0  # seconds


class WhisperSyncE2ETest:
    """End-to-end integration test suite for WhisperSync pipeline.
    
    This class provides comprehensive testing of the complete pipeline from
    S3 upload through Lambda processing to final output validation.
    """
    
    def __init__(self):
        self.s3_client = boto3.client("s3", region_name=TEST_REGION)
        self.lambda_client = boto3.client("lambda", region_name=TEST_REGION)
        self.test_objects = []  # Track objects for cleanup
        self.test_id = str(uuid.uuid4())[:8]
        
    def cleanup(self):
        """Clean up all test resources."""
        print(f"Cleaning up test resources for test_id: {self.test_id}")
        
        # Delete all test objects from S3
        if self.test_objects:
            try:
                delete_objects = [{"Key": obj} for obj in self.test_objects]
                self.s3_client.delete_objects(
                    Bucket=TEST_BUCKET_NAME,
                    Delete={"Objects": delete_objects}
                )
                print(f"Deleted {len(self.test_objects)} S3 objects")
            except Exception as e:
                print(f"Error cleaning up S3 objects: {e}")
        
        self.test_objects.clear()
    
    def upload_test_transcript(self, agent_type: str, transcript: str, filename: Optional[str] = None) -> str:
        """Upload a test transcript to S3 and return the key."""
        if filename is None:
            filename = f"test_{self.test_id}_{int(time.time())}.txt"
        
        key = f"transcripts/{agent_type}/{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=TEST_BUCKET_NAME,
                Key=key,
                Body=transcript.encode("utf-8"),
                ContentType="text/plain"
            )
            self.test_objects.append(key)
            print(f"Uploaded test transcript: s3://{TEST_BUCKET_NAME}/{key}")
            return key
        except Exception as e:
            raise Exception(f"Failed to upload test transcript: {e}")
    
    def wait_for_processing(self, input_key: str, timeout: int = TEST_TIMEOUT) -> Dict[str, Any]:
        """Wait for Lambda processing to complete and return the output."""
        output_key = input_key.replace("transcripts/", "outputs/").replace(".txt", "_response.json")
        error_key = input_key.replace("transcripts/", "errors/").replace(".txt", "_error.json")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check for successful output
                obj = self.s3_client.get_object(Bucket=TEST_BUCKET_NAME, Key=output_key)
                result = json.loads(obj["Body"].read().decode("utf-8"))
                self.test_objects.append(output_key)
                print(f"Found output: s3://{TEST_BUCKET_NAME}/{output_key}")
                return {"success": True, "result": result, "output_key": output_key}
            except ClientError as e:
                if e.response["Error"]["Code"] != "NoSuchKey":
                    raise
            
            try:
                # Check for error output
                obj = self.s3_client.get_object(Bucket=TEST_BUCKET_NAME, Key=error_key)
                error_result = json.loads(obj["Body"].read().decode("utf-8"))
                self.test_objects.append(error_key)
                print(f"Found error: s3://{TEST_BUCKET_NAME}/{error_key}")
                return {"success": False, "error": error_result, "error_key": error_key}
            except ClientError as e:
                if e.response["Error"]["Code"] != "NoSuchKey":
                    raise
            
            time.sleep(1)
        
        raise TimeoutError(f"Processing did not complete within {timeout} seconds")
    
    def validate_work_agent_output(self, result: Dict[str, Any]) -> None:
        """Validate work agent output structure and content."""
        assert "routing_decision" in result
        assert "agent_results" in result
        
        routing = result["routing_decision"]
        assert routing["primary_agent"] in ["work", "multiple"]
        assert routing["confidence"] > 0.7
        
        # Check work agent results
        work_results = None
        if "work" in result["agent_results"]:
            work_results = result["agent_results"]["work"]
        elif routing["primary_agent"] == "work":
            # Single agent response format
            work_results = result["agent_results"]
        
        assert work_results is not None, "Work agent results not found"
        
        # Validate work agent specific fields
        if isinstance(work_results, dict):
            # Should have either log_key or summary indicating work was logged
            assert any(key in work_results for key in ["log_key", "summary", "work_entry"]), \
                "Work agent should return log_key, summary, or work_entry"
            
            # If analysis is present, validate structure
            if "analysis" in work_results:
                analysis = work_results["analysis"]
                assert "categories" in analysis or "key_points" in analysis, \
                    "Work analysis should include categories or key_points"
    
    def validate_memory_agent_output(self, result: Dict[str, Any]) -> None:
        """Validate memory agent output structure and content."""
        assert "routing_decision" in result
        assert "agent_results" in result
        
        routing = result["routing_decision"]
        assert routing["primary_agent"] in ["memory", "multiple"]
        assert routing["confidence"] > 0.7
        
        # Check memory agent results
        memory_results = None
        if "memory" in result["agent_results"]:
            memory_results = result["agent_results"]["memory"]
        elif routing["primary_agent"] == "memory":
            memory_results = result["agent_results"]
        
        assert memory_results is not None, "Memory agent results not found"
        
        # Validate memory agent specific fields
        if isinstance(memory_results, dict):
            # Should have memory_key or memory_id
            assert any(key in memory_results for key in ["memory_key", "memory_id", "stored_at"]), \
                "Memory agent should return memory_key, memory_id, or stored_at"
            
            # If analysis is present, validate structure
            if "analysis" in memory_results:
                analysis = memory_results["analysis"]
                expected_fields = ["sentiment", "themes", "significance", "emotions"]
                assert any(field in analysis for field in expected_fields), \
                    f"Memory analysis should include one of: {expected_fields}"
    
    def validate_github_agent_output(self, result: Dict[str, Any]) -> None:
        """Validate GitHub agent output structure and content."""
        assert "routing_decision" in result
        assert "agent_results" in result
        
        routing = result["routing_decision"]
        assert routing["primary_agent"] in ["github", "multiple"]
        assert routing["confidence"] > 0.7
        
        # Check GitHub agent results
        github_results = None
        if "github" in result["agent_results"]:
            github_results = result["agent_results"]["github"]
        elif routing["primary_agent"] == "github":
            github_results = result["agent_results"]
        
        assert github_results is not None, "GitHub agent results not found"
        
        # Validate GitHub agent specific fields
        if isinstance(github_results, dict):
            # Should have repo information
            assert any(key in github_results for key in ["repo", "url", "repository", "status"]), \
                "GitHub agent should return repo, url, repository, or status"
            
            # If tech_stack is present, should be a list
            if "tech_stack" in github_results:
                assert isinstance(github_results["tech_stack"], list), \
                    "tech_stack should be a list"
            
            # If status is present, should indicate success or failure
            if "status" in github_results:
                assert github_results["status"] in ["success", "failed", "error"], \
                    "status should be success, failed, or error"


@pytest.fixture
def e2e_test():
    """Fixture to provide E2E test instance with cleanup."""
    test_instance = WhisperSyncE2ETest()
    yield test_instance
    test_instance.cleanup()


class TestEndToEndIntegration:
    """End-to-end integration test cases."""
    
    def test_work_journal_integration(self, e2e_test):
        """Test complete work journal integration pipeline.
        
        SCENARIO: User records work-related voice memo
        PIPELINE: S3 upload → Lambda trigger → Work agent → Weekly log
        VALIDATION: Ensures work entry is logged with proper categorization
        """
        print("\n=== Testing Work Journal Integration ===")
        
        # Test transcript with work-related content
        transcript = (
            "Today I completed the authentication system implementation. "
            "I spent 3 hours debugging the OAuth flow and finally got it working. "
            "The team review went well and we're ready to deploy next week. "
            "Need to update the documentation before release."
        )
        
        # Upload transcript to work folder
        start_time = time.time()
        key = e2e_test.upload_test_transcript("work", transcript)
        
        # Wait for processing
        processing_result = e2e_test.wait_for_processing(key)
        processing_time = time.time() - start_time
        
        # Validate processing succeeded
        assert processing_result["success"], f"Processing failed: {processing_result.get('error')}"
        
        # Validate performance
        assert processing_time < PERFORMANCE_THRESHOLD, \
            f"Processing took {processing_time:.2f}s, exceeds {PERFORMANCE_THRESHOLD}s threshold"
        
        # Validate work agent output
        result = processing_result["result"]
        e2e_test.validate_work_agent_output(result)
        
        # Additional work-specific validations
        if "work" in result["agent_results"]:
            work_results = result["agent_results"]["work"]
            if isinstance(work_results, dict) and "analysis" in work_results:
                analysis = work_results["analysis"]
                if "categories" in analysis:
                    # Should detect development/coding categories
                    categories = analysis["categories"]
                    assert any("develop" in cat.lower() or "code" in cat.lower() 
                             for cat in categories), "Should detect development work"
        
        print(f"✓ Work journal integration test passed in {processing_time:.2f}s")
    
    def test_memory_preservation_integration(self, e2e_test):
        """Test complete memory preservation pipeline.
        
        SCENARIO: User records personal memory or reflection
        PIPELINE: S3 upload → Lambda trigger → Memory agent → JSONL storage
        VALIDATION: Ensures memory is stored with sentiment analysis
        """
        print("\n=== Testing Memory Preservation Integration ===")
        
        # Test transcript with personal/memory content
        transcript = (
            "I was just thinking about my first day at this job five years ago. "
            "I remember being so nervous but excited. The team was incredibly welcoming, "
            "and my manager took me out for coffee to help me feel at ease. "
            "It's amazing how much I've grown since then. That nervous energy has "
            "transformed into confidence and genuine love for what I do."
        )
        
        # Upload transcript to memories folder
        start_time = time.time()
        key = e2e_test.upload_test_transcript("memories", transcript)
        
        # Wait for processing
        processing_result = e2e_test.wait_for_processing(key)
        processing_time = time.time() - start_time
        
        # Validate processing succeeded
        assert processing_result["success"], f"Processing failed: {processing_result.get('error')}"
        
        # Validate performance
        assert processing_time < PERFORMANCE_THRESHOLD, \
            f"Processing took {processing_time:.2f}s, exceeds {PERFORMANCE_THRESHOLD}s threshold"
        
        # Validate memory agent output
        result = processing_result["result"]
        e2e_test.validate_memory_agent_output(result)
        
        # Additional memory-specific validations
        if "memory" in result["agent_results"]:
            memory_results = result["agent_results"]["memory"]
            if isinstance(memory_results, dict) and "analysis" in memory_results:
                analysis = memory_results["analysis"]
                
                # Should have detected emotional content
                if "sentiment" in analysis:
                    assert analysis["sentiment"] in ["positive", "negative", "mixed", "nostalgic"], \
                        f"Unexpected sentiment: {analysis['sentiment']}"
                
                # Should have themes related to career/growth
                if "themes" in analysis:
                    themes = analysis["themes"]
                    assert any("career" in theme.lower() or "growth" in theme.lower() 
                             or "work" in theme.lower() for theme in themes), \
                        "Should detect career/growth themes"
        
        print(f"✓ Memory preservation integration test passed in {processing_time:.2f}s")
    
    @patch('agents.github_idea_agent.PyGithub')
    def test_github_repo_creation_integration(self, mock_github, e2e_test):
        """Test complete GitHub repository creation pipeline.
        
        SCENARIO: User records idea for new project
        PIPELINE: S3 upload → Lambda trigger → GitHub agent → Repository created
        VALIDATION: Ensures repository is created with proper structure
        """
        print("\n=== Testing GitHub Repository Creation Integration ===")
        
        # Mock GitHub API
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_repo.name = "voice-memo-analyzer"
        mock_repo.html_url = "https://github.com/testuser/voice-memo-analyzer"
        mock_repo.description = "AI-powered voice memo analysis tool"
        mock_github_instance.get_user.return_value.create_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        # Test transcript with project idea
        transcript = (
            "I have an idea for a new project. I want to build a voice memo analyzer "
            "that uses AI to automatically categorize and summarize voice recordings. "
            "It should use Python with machine learning libraries like scikit-learn "
            "and maybe integrate with speech recognition APIs. The goal is to help "
            "people organize their thoughts and find patterns in their voice memos."
        )
        
        # Upload transcript to github_ideas folder
        start_time = time.time()
        key = e2e_test.upload_test_transcript("github_ideas", transcript)
        
        # Wait for processing
        processing_result = e2e_test.wait_for_processing(key)
        processing_time = time.time() - start_time
        
        # Validate processing succeeded
        assert processing_result["success"], f"Processing failed: {processing_result.get('error')}"
        
        # Validate performance
        assert processing_time < PERFORMANCE_THRESHOLD, \
            f"Processing took {processing_time:.2f}s, exceeds {PERFORMANCE_THRESHOLD}s threshold"
        
        # Validate GitHub agent output
        result = processing_result["result"]
        e2e_test.validate_github_agent_output(result)
        
        # Additional GitHub-specific validations
        if "github" in result["agent_results"]:
            github_results = result["agent_results"]["github"]
            if isinstance(github_results, dict):
                
                # Should have detected Python as tech stack
                if "tech_stack" in github_results:
                    tech_stack = github_results["tech_stack"]
                    assert "python" in [t.lower() for t in tech_stack], \
                        "Should detect Python in tech stack"
                
                # Should have created repository
                if "status" in github_results:
                    assert github_results["status"] == "success", \
                        "Repository creation should succeed"
        
        print(f"✓ GitHub repository creation integration test passed in {processing_time:.2f}s")
    
    def test_multi_agent_coordination(self, e2e_test):
        """Test multi-agent coordination for complex transcripts.
        
        SCENARIO: User records transcript that spans multiple domains
        PIPELINE: S3 upload → Lambda trigger → Orchestrator → Multiple agents
        VALIDATION: Ensures multiple agents process the same transcript
        """
        print("\n=== Testing Multi-Agent Coordination ===")
        
        # Test transcript with mixed content (work + memory + project idea)
        transcript = (
            "Today I finished implementing the new authentication system at work. "
            "It reminds me of when I first learned about OAuth five years ago - "
            "I was so confused but determined to understand it. Now I'm thinking "
            "this authentication pattern could be turned into a reusable library. "
            "Maybe I should create an open-source project for it. The library could "
            "help other developers avoid the same confusion I went through."
        )
        
        # Upload to general folder to force content-based routing
        start_time = time.time()
        key = e2e_test.upload_test_transcript("general", transcript)
        
        # Wait for processing
        processing_result = e2e_test.wait_for_processing(key)
        processing_time = time.time() - start_time
        
        # Validate processing succeeded
        assert processing_result["success"], f"Processing failed: {processing_result.get('error')}"
        
        # Validate performance (allow extra time for multi-agent processing)
        assert processing_time < PERFORMANCE_THRESHOLD * 2, \
            f"Multi-agent processing took {processing_time:.2f}s, exceeds {PERFORMANCE_THRESHOLD * 2}s threshold"
        
        # Validate multi-agent coordination
        result = processing_result["result"]
        routing = result["routing_decision"]
        
        # Should detect multiple relevant agents
        assert routing["primary_agent"] == "multiple" or len(result["agent_results"]) > 1, \
            "Should detect multiple relevant agents"
        
        # Should have lower confidence for ambiguous content
        assert routing["confidence"] < 0.95, \
            "Should have lower confidence for multi-domain content"
        
        print(f"✓ Multi-agent coordination test passed in {processing_time:.2f}s")
    
    def test_error_handling_invalid_transcript(self, e2e_test):
        """Test error handling for invalid transcript content.
        
        SCENARIO: Upload invalid or problematic transcript
        PIPELINE: S3 upload → Lambda trigger → Error handling
        VALIDATION: Ensures graceful error handling and logging
        """
        print("\n=== Testing Error Handling ===")
        
        # Test with empty transcript
        transcript = ""
        
        start_time = time.time()
        key = e2e_test.upload_test_transcript("work", transcript)
        
        # Wait for processing (should still complete, even with errors)
        processing_result = e2e_test.wait_for_processing(key)
        processing_time = time.time() - start_time
        
        # Should complete processing even with invalid input
        assert processing_result is not None, "Should handle invalid input gracefully"
        
        if not processing_result["success"]:
            # If it failed, should have proper error information
            error = processing_result["error"]
            assert "error" in error, "Error result should contain error field"
            assert "request_id" in error, "Error should include request_id for tracing"
        
        print(f"✓ Error handling test completed in {processing_time:.2f}s")
    
    def test_performance_benchmarks(self, e2e_test):
        """Test performance benchmarks for different transcript types.
        
        SCENARIO: Process various transcript sizes and complexities
        VALIDATION: Ensures all processing completes within performance thresholds
        """
        print("\n=== Testing Performance Benchmarks ===")
        
        test_cases = [
            ("work", "Quick work update.", "short"),
            ("work", "Today I worked on implementing a complex authentication system. " * 10, "medium"),
            ("memories", "I remember when I first started programming. " * 20, "long"),
        ]
        
        performance_results = []
        
        for agent_type, transcript, size in test_cases:
            print(f"Testing {size} transcript for {agent_type} agent...")
            
            start_time = time.time()
            key = e2e_test.upload_test_transcript(agent_type, transcript)
            
            processing_result = e2e_test.wait_for_processing(key)
            processing_time = time.time() - start_time
            
            performance_results.append({
                "agent_type": agent_type,
                "size": size,
                "processing_time": processing_time,
                "success": processing_result["success"]
            })
            
            # Validate performance threshold
            threshold = PERFORMANCE_THRESHOLD * 2 if size == "long" else PERFORMANCE_THRESHOLD
            assert processing_time < threshold, \
                f"{size} transcript took {processing_time:.2f}s, exceeds {threshold}s threshold"
        
        # Report performance results
        print("\nPerformance Results:")
        for result in performance_results:
            print(f"  {result['agent_type']} ({result['size']}): {result['processing_time']:.2f}s")
        
        print("✓ All performance benchmarks passed")
    
    def test_lambda_trigger_validation(self, e2e_test):
        """Test that Lambda is properly triggered by S3 events.
        
        SCENARIO: Validate S3 event configuration and Lambda invocation
        VALIDATION: Ensures Lambda function is invoked for the correct S3 events
        """
        print("\n=== Testing Lambda Trigger Validation ===")
        
        transcript = "Testing Lambda trigger validation."
        
        # Upload transcript and measure how quickly processing starts
        start_time = time.time()
        key = e2e_test.upload_test_transcript("work", transcript)
        
        # Check for processing indicators quickly
        processing_started = False
        for _ in range(10):  # Check for 10 seconds
            time.sleep(1)
            try:
                # Look for any processing artifacts
                output_key = key.replace("transcripts/", "outputs/").replace(".txt", "_response.json")
                error_key = key.replace("transcripts/", "errors/").replace(".txt", "_error.json")
                
                # Check if processing has started (either output or error exists)
                try:
                    e2e_test.s3_client.head_object(Bucket=TEST_BUCKET_NAME, Key=output_key)
                    processing_started = True
                    break
                except ClientError:
                    pass
                
                try:
                    e2e_test.s3_client.head_object(Bucket=TEST_BUCKET_NAME, Key=error_key)
                    processing_started = True
                    break
                except ClientError:
                    pass
            except:
                pass
        
        trigger_time = time.time() - start_time
        
        # Should trigger within reasonable time
        assert trigger_time < 15, f"Lambda trigger took {trigger_time:.2f}s, too slow"
        
        # Wait for complete processing
        processing_result = e2e_test.wait_for_processing(key)
        
        assert processing_result["success"], "Lambda processing should succeed"
        
        print(f"✓ Lambda trigger validation passed (triggered in {trigger_time:.2f}s)")
    
    def test_s3_output_validation(self, e2e_test):
        """Test S3 output structure and metadata validation.
        
        SCENARIO: Validate S3 output files have correct structure and metadata
        VALIDATION: Ensures output files are properly formatted and accessible
        """
        print("\n=== Testing S3 Output Validation ===")
        
        transcript = "Testing S3 output structure and metadata."
        
        key = e2e_test.upload_test_transcript("work", transcript)
        processing_result = e2e_test.wait_for_processing(key)
        
        assert processing_result["success"], "Processing should succeed"
        
        output_key = processing_result["output_key"]
        
        # Validate output file structure
        obj = e2e_test.s3_client.get_object(Bucket=TEST_BUCKET_NAME, Key=output_key)
        output_data = json.loads(obj["Body"].read().decode("utf-8"))
        
        # Validate required fields
        required_fields = ["source_key", "processed_at", "routing_decision", "agent_results"]
        for field in required_fields:
            assert field in output_data, f"Output should contain {field}"
        
        # Validate metadata
        metadata = obj.get("Metadata", {})
        assert "source_transcript" in metadata, "Should have source_transcript metadata"
        assert "primary_agent" in metadata, "Should have primary_agent metadata"
        assert "request_id" in metadata, "Should have request_id metadata"
        
        # Validate content type
        assert obj["ContentType"] == "application/json", "Should have correct content type"
        
        print("✓ S3 output validation passed")


if __name__ == "__main__":
    # Run tests directly for debugging
    import sys
    
    # Check if AWS credentials are available
    try:
        boto3.client("s3").list_buckets()
    except Exception as e:
        print(f"AWS credentials not available: {e}")
        sys.exit(1)
    
    # Check if test bucket exists
    try:
        s3 = boto3.client("s3")
        s3.head_bucket(Bucket=TEST_BUCKET_NAME)
    except Exception as e:
        print(f"Test bucket {TEST_BUCKET_NAME} not accessible: {e}")
        print("Please set TEST_BUCKET_NAME environment variable to an existing bucket")
        sys.exit(1)
    
    # Run a simple test
    test_instance = WhisperSyncE2ETest()
    try:
        print("Running basic end-to-end test...")
        key = test_instance.upload_test_transcript("work", "Test transcript")
        print(f"Successfully uploaded: {key}")
        
        result = test_instance.wait_for_processing(key)
        print(f"Processing result: {result['success']}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        raise
    finally:
        test_instance.cleanup()
    
    print("Basic test completed successfully!")