# WhisperSync S3 Trigger Workflow

## Overview

WhisperSync uses S3 ObjectCreated events as the primary trigger for processing voice transcripts. When a new transcript file is uploaded to the `transcripts/` prefix, it automatically triggers the intelligent routing system.

## S3 Event Configuration

### Trigger Setup (CDK)
```python
bucket.add_event_notification(
    s3.EventType.OBJECT_CREATED,
    notification,
    s3.NotificationKeyFilter(
        prefix="transcripts/",  # All transcripts go under this prefix
        suffix=".txt"          # Only process text files
    )
)
```

### Event Types Covered
- `s3:ObjectCreated:Put` - Direct uploads
- `s3:ObjectCreated:Post` - Form POST uploads  
- `s3:ObjectCreated:CompleteMultipartUpload` - Large file uploads
- `s3:ObjectCreated:Copy` - Copied transcripts

## Workflow Steps

### 1. Upload Transcript
Any method that creates an object in S3 triggers the workflow:

```bash
# AWS CLI upload
aws s3 cp voice_memo.txt s3://voice-mcp/transcripts/2024/01/15/memo_123.txt

# Python SDK upload
s3_client.put_object(
    Bucket='voice-mcp',
    Key='transcripts/2024/01/15/memo_123.txt',
    Body=transcript_text,
    Metadata={
        'source': 'iphone',
        'duration': '45',
        'user_id': 'user123'
    }
)
```

### 2. S3 Event Generation
S3 automatically generates an event:

```json
{
    "Records": [{
        "eventVersion": "2.1",
        "eventSource": "aws:s3",
        "eventName": "ObjectCreated:Put",
        "eventTime": "2024-01-15T12:30:45.000Z",
        "s3": {
            "bucket": {
                "name": "voice-mcp",
                "arn": "arn:aws:s3:::voice-mcp"
            },
            "object": {
                "key": "transcripts/2024/01/15/memo_123.txt",
                "size": 1024,
                "eTag": "d41d8cd98f00b204e9800998ecf8427e"
            }
        }
    }]
}
```

### 3. Lambda Invocation
The configured Lambda function (`intelligent_router.lambda_handler`) is invoked with the S3 event.

### 4. Content Processing
```python
# Lambda handler workflow
1. Validate event structure
2. Verify ObjectCreated event type
3. Check prefix matches configuration
4. Download transcript from S3
5. Classify content with AI
6. Route to appropriate agent(s)
7. Store results
```

### 5. Results Storage
Processing results are stored back to S3:

```
s3://voice-mcp/
├── transcripts/2024/01/15/memo_123.txt        # Original
├── outputs/2024/01/15/memo_123_result.json    # Processed result
├── review_needed/2024/01/15/memo_123_review.json  # If low confidence
└── analytics/routing/2024/01/15/{correlation_id}.json  # Analytics
```

## Key Patterns

### Flexible Path Structure
The system only cares about the `transcripts/` prefix. You can organize within it however you want:

```
✓ transcripts/audio_123.txt
✓ transcripts/2024/01/15/morning_thoughts.txt
✓ transcripts/user123/personal/memory.txt
✓ transcripts/raw/unprocessed/voice_note.txt
```

### Content-Based Routing
Unlike the old system, the path structure doesn't determine routing:

```
# All of these could route to the same agent based on content:
transcripts/work/idea.txt → Could go to GitHub agent if it's a project idea
transcripts/personal/meeting.txt → Could go to Work agent if it's about work
transcripts/random/thought.txt → Classified by content, not path
```

### Metadata Support
Use S3 object metadata for additional context:

```python
s3_client.put_object(
    Bucket='voice-mcp',
    Key='transcripts/2024/01/15/memo.txt',
    Body=transcript,
    Metadata={
        'source_device': 'iphone_14_pro',
        'audio_duration_seconds': '120',
        'original_filename': 'Voice Memo 42.m4a',
        'whisper_model': 'large-v3',
        'language': 'en',
        'user_timezone': 'America/New_York'
    }
)
```

## Environment Variables

Configure the Lambda function with:

```bash
# Required
ANTHROPIC_SECRET_NAME=anthropic/api_key
BUCKET_NAME=voice-mcp
TRANSCRIPT_PREFIX=transcripts/  # Can be customized

# Optional
LOG_LEVEL=INFO
CONFIDENCE_THRESHOLD=0.7
ENABLE_MULTI_AGENT=true
```

## Error Handling

### Resilient Design
- Failed classifications fall back to keyword matching
- Errors are logged to `errors/` prefix for debugging
- Original transcripts are never modified or deleted
- Partial results are better than no results

### Retry Logic
S3 events have built-in retry with exponential backoff:
- First retry: ~1 minute
- Second retry: ~2 minutes  
- Third retry: ~4 minutes

### Dead Letter Queue
Configure DLQ for events that fail all retries:

```python
dead_letter_queue = sqs.Queue(
    self, "DeadLetterQueue",
    retention_period=Duration.days(14)
)

lambda_fn.add_event_source(
    S3EventSource(
        bucket,
        # ... other config ...
        on_failure=lambda_destinations.SqsDestination(dead_letter_queue)
    )
)
```

## Monitoring

### CloudWatch Metrics
- `S3EventsReceived` - Count of S3 events
- `TranscriptsProcessed` - Successfully processed
- `ClassificationConfidence` - Average confidence scores
- `RoutingDistribution` - Which agents are used

### Example Queries
```sql
-- Find low confidence classifications
SELECT * FROM cloudwatch_logs
WHERE confidence < 0.7
AND timestamp > NOW() - INTERVAL '24 hours'

-- Track routing patterns
SELECT 
    primary_bucket,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM routing_analytics
GROUP BY primary_bucket
```

## Testing S3 Triggers

### Local Testing
```python
# Simulate S3 event locally
test_event = {
    "Records": [{
        "eventName": "ObjectCreated:Put",
        "s3": {
            "bucket": {"name": "voice-mcp"},
            "object": {"key": "transcripts/test.txt"}
        }
    }]
}

# Invoke handler
from lambda_fn.intelligent_router import lambda_handler
result = lambda_handler(test_event, {})
```

### Integration Testing
```bash
# Upload test file and verify processing
echo "I have an idea for a new app" > test.txt
aws s3 cp test.txt s3://voice-mcp/transcripts/test.txt

# Wait for processing
sleep 5

# Check results
aws s3 cp s3://voice-mcp/outputs/test_result.json - | jq .
```

## Best Practices

1. **Consistent Naming**: Use timestamps in filenames for easy sorting
   ```
   transcripts/2024/01/15/20240115_123045.txt
   ```

2. **Idempotency**: Ensure reprocessing the same file is safe
   - Use correlation IDs
   - Check if output already exists

3. **Size Limits**: Lambda has a 6MB response limit
   - Stream large results directly to S3
   - Return S3 location instead of full content

4. **Cost Optimization**:
   - Use S3 lifecycle policies to archive old transcripts
   - Consider S3 Intelligent-Tiering for automatic optimization

5. **Security**:
   - Enable S3 bucket versioning
   - Use bucket policies to restrict access
   - Enable CloudTrail for audit logging

## Migration from Folder-Based System

If you have existing transcripts in the old folder structure:

```python
# Migration script
import boto3

s3 = boto3.client('s3')

# Old structure
old_prefixes = ['work/', 'memories/', 'github_ideas/']

for prefix in old_prefixes:
    # List objects in old structure
    response = s3.list_objects_v2(
        Bucket='voice-mcp',
        Prefix=f'transcripts/{prefix}'
    )
    
    for obj in response.get('Contents', []):
        # Copy to new structure (flat under transcripts/)
        new_key = obj['Key'].replace(prefix, '')
        
        s3.copy_object(
            Bucket='voice-mcp',
            CopySource={'Bucket': 'voice-mcp', 'Key': obj['Key']},
            Key=new_key
        )
```

The beauty of the new system is that it doesn't matter where the files are within `transcripts/` - the AI will figure out where they belong based on content!