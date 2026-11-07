#!/usr/bin/env python3
"""Example demonstrating the improved S3 event processing in Lambda handler.

This script shows how the Lambda handler now properly handles:
1. URL-encoded S3 keys (spaces and special characters)
2. Multi-record S3 events
3. Proper error handling for malformed events
4. Partial success scenarios
"""

import json
from lambda_fn.router_handler import lambda_handler

# Mock context for testing
class MockContext:
    def __init__(self):
        self.request_id = "test-request-123"
        self.function_name = "mcpAgentRouterLambda"
        self.memory_limit_in_mb = 512
        self.remaining_time_millis = 300000
    
    def get_remaining_time_in_millis(self):
        return self.remaining_time_millis


def demo_url_encoded_keys():
    """Demonstrate handling of URL-encoded S3 keys."""
    print("\n=== URL-Encoded Keys Demo ===")
    
    # S3 encodes spaces as '+' and special chars with percent encoding
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "voice-mcp"},
                    "object": {"key": "transcripts/work/my+voice+memo+2024-01-01.txt"}
                }
            }
        ]
    }
    
    print(f"Input S3 key (encoded): {event['Records'][0]['s3']['object']['key']}")
    print("Expected decoded key: transcripts/work/my voice memo 2024-01-01.txt")
    
    # In real usage, this would process the transcript
    # The handler will decode the key before using it with S3


def demo_multi_record_processing():
    """Demonstrate processing multiple S3 records in one event."""
    print("\n=== Multi-Record Processing Demo ===")
    
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "voice-mcp"},
                    "object": {"key": "transcripts/work/memo1.txt"}
                }
            },
            {
                "s3": {
                    "bucket": {"name": "voice-mcp"},
                    "object": {"key": "transcripts/memories/memo2.txt"}
                }
            },
            {
                "s3": {
                    "bucket": {"name": "voice-mcp"},
                    "object": {"key": "transcripts/github_ideas/memo3.txt"}
                }
            }
        ]
    }
    
    print(f"Processing {len(event['Records'])} records:")
    for i, record in enumerate(event['Records']):
        key = record['s3']['object']['key']
        print(f"  {i+1}. {key}")
    
    # The handler will process all records and return aggregate results


def demo_error_handling():
    """Demonstrate proper error handling for malformed events."""
    print("\n=== Error Handling Demo ===")
    
    test_cases = [
        {
            "name": "Missing Records field",
            "event": {"someOtherField": "value"},
            "expected_status": 400
        },
        {
            "name": "Empty Records array",
            "event": {"Records": []},
            "expected_status": 200
        },
        {
            "name": "Missing S3 field in record",
            "event": {"Records": [{"notS3": "data"}]},
            "expected_status": 500
        },
        {
            "name": "Incomplete S3 information",
            "event": {"Records": [{"s3": {"bucket": {"name": "test"}}}]},
            "expected_status": 500
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Event: {json.dumps(test['event'], indent=2)}")
        print(f"Expected status code: {test['expected_status']}")


def demo_partial_success():
    """Demonstrate handling of partial success scenarios."""
    print("\n=== Partial Success Demo ===")
    
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "voice-mcp"},
                    "object": {"key": "transcripts/work/good.txt"}
                }
            },
            {
                "s3": {
                    "bucket": {"name": "voice-mcp"},
                    "object": {"key": "transcripts/work/nonexistent.txt"}  # Will fail
                }
            },
            {
                "s3": {
                    "bucket": {"name": "voice-mcp"},
                    "object": {"key": "transcripts/work/another_good.txt"}
                }
            }
        ]
    }
    
    print("Processing 3 records where 1 will fail:")
    print("- Record 1: Should succeed")
    print("- Record 2: Will fail (file doesn't exist)")
    print("- Record 3: Should succeed")
    print("\nExpected result: HTTP 207 (Multi-Status) with partial success")


def demo_special_characters():
    """Demonstrate handling of special characters in S3 keys."""
    print("\n=== Special Characters Demo ===")
    
    # Various special characters that get URL-encoded
    special_cases = [
        ("memo&notes.txt", "memo%26notes.txt"),
        ("report=2024.txt", "report%3D2024.txt"),
        ("file name.txt", "file+name.txt"),
        ("data[1].txt", "data%5B1%5D.txt"),
        ("test@file.txt", "test%40file.txt")
    ]
    
    print("Special character encoding examples:")
    for original, encoded in special_cases:
        print(f"  Original: {original}")
        print(f"  Encoded:  {encoded}")
        print(f"  S3 key:   transcripts/work/{encoded}")
        print()


if __name__ == "__main__":
    print("WhisperSync Lambda Handler - S3 Event Processing Examples")
    print("=" * 60)
    
    demo_url_encoded_keys()
    demo_multi_record_processing()
    demo_error_handling()
    demo_partial_success()
    demo_special_characters()
    
    print("\n" + "=" * 60)
    print("These examples demonstrate the improved S3 event processing")
    print("capabilities added in GitHub issue #16.")
    print("\nKey improvements:")
    print("- ✅ URL-encoded key handling (spaces and special chars)")
    print("- ✅ Multi-record event processing")
    print("- ✅ Comprehensive error handling")
    print("- ✅ Partial success reporting (HTTP 207)")
    print("- ✅ Better validation of event structure")