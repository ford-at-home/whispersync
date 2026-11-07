# WhisperSync API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Agent Interfaces](#agent-interfaces)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Usage Examples](#usage-examples)
7. [Rate Limits](#rate-limits)
8. [Webhooks](#webhooks)

## Overview

WhisperSync provides a voice-to-action AI platform through multiple interfaces:
- **S3 Event-driven Processing**: Automatic processing of uploaded transcripts
- **Direct Agent Invocation**: Programmatic access to individual agents
- **Health Check Endpoints**: System monitoring and status
- **Configuration API**: Runtime configuration management

### Base Architecture

```
Client → S3 Upload → Lambda Router → Agent Processing → S3 Output
      ↳ Direct API → Agent Function → Response
```

## Authentication

### AWS IAM Authentication
All API calls use AWS IAM authentication with appropriate permissions.

#### Required Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:s3:::voice-mcp-*/*",
                "arn:aws:lambda:*:*:function:whispersync-*"
            ]
        }
    ]
}
```

### API Keys (Future Enhancement)
For external integrations, API key authentication will be supported:

```http
Authorization: Bearer YOUR_API_KEY
X-WhisperSync-Client-ID: your-client-id
```

## Agent Interfaces

### Orchestrator Agent

The orchestrator agent routes transcripts to appropriate specialized agents based on content analysis.

#### `route_transcript`

Routes a transcript to the most appropriate agent(s).

**Endpoint**: `POST /agents/orchestrator/route`

**Parameters**:
```python
{
    "transcript": str,           # Required. Voice transcript text
    "source_key": str,          # Optional. S3 key hint for routing
    "force_agent": str,         # Optional. Force specific agent
    "correlation_id": str       # Optional. Request tracking ID
}
```

**Response**:
```python
{
    "routing_decision": {
        "primary_agent": str,           # Main agent selected
        "secondary_agents": List[str],  # Additional agents for complex content
        "confidence": float,            # Routing confidence (0.0-1.0)
        "reasoning": str,               # Human-readable explanation
        "processing_time_ms": float     # Time taken for routing decision
    },
    "processing_results": {
        "work": {...},         # Results from work agent (if used)
        "memory": {...},       # Results from memory agent (if used)
        "github": {...}        # Results from github agent (if used)
    },
    "metadata": {
        "timestamp": str,      # ISO 8601 timestamp
        "version": str,        # API version
        "correlation_id": str  # Request tracking ID
    }
}
```

**Example**:
```python
import boto3

lambda_client = boto3.client('lambda')

response = lambda_client.invoke(
    FunctionName='whispersync-orchestrator-production',
    Payload=json.dumps({
        'transcript': 'I completed the user authentication feature today.',
        'correlation_id': 'req-12345'
    })
)

result = json.loads(response['Payload'].read())
```

### Work Journal Agent

Processes work-related transcripts and maintains professional activity logs.

#### `append_work_log`

Adds a work entry to the weekly journal.

**Parameters**:
```python
{
    "transcript": str,           # Work-related transcript
    "categories": List[str],     # Optional. Work categories override
    "correlation_id": str        # Optional. Request tracking ID
}
```

**Response**:
```python
{
    "status": "success",
    "log_key": str,             # S3 key where log was stored
    "summary": str,             # AI-generated summary
    "categories": List[str],    # Detected work categories
    "key_points": List[str],    # Extracted key points
    "sentiment": str,           # Work sentiment analysis
    "action_items": List[str],  # Extracted action items
    "estimated_time": str,      # Estimated time investment
    "week": str,               # Week identifier (YYYY-WXX)
    "processing_time": float    # Processing duration in seconds
}
```

#### `generate_weekly_summary`

Creates AI-powered summary of week's work activities.

**Parameters**:
```python
{
    "week": int,                # Optional. Week number (default: current)
    "year": int,                # Optional. Year (default: current)
    "include_metrics": bool     # Optional. Include productivity metrics
}
```

**Response**:
```python
{
    "status": "success",
    "summary": str,             # Generated weekly summary
    "key_accomplishments": List[str],  # Major achievements
    "challenges": List[str],    # Challenges encountered
    "metrics": {
        "total_entries": int,
        "categories": Dict[str, int],
        "sentiment_distribution": Dict[str, float]
    },
    "recommendations": List[str]  # AI recommendations for next week
}
```

### Memory Agent

Processes personal memories and experiences with emotional context.

#### `preserve_memory`

Stores a personal memory with AI-enhanced metadata.

**Parameters**:
```python
{
    "transcript": str,           # Memory transcript
    "correlation_id": str        # Optional. Request tracking ID
}
```

**Response**:
```python
{
    "status": "success",
    "memory_id": str,           # Unique memory identifier
    "summary": str,             # AI-generated memory summary
    "themes": List[str],        # Extracted themes
    "sentiment": str,           # Emotional sentiment
    "people_mentioned": List[str],  # People in the memory
    "location": str,            # Extracted location
    "time_period": str,         # Time period classification
    "emotional_tags": List[str], # Emotional classification
    "storage_location": str,    # S3 storage path
    "processing_time": float    # Processing duration
}
```

#### `search_memories`

Search stored memories by themes, people, or sentiment.

**Parameters**:
```python
{
    "query": str,               # Search query
    "themes": List[str],        # Optional. Filter by themes
    "sentiment": str,           # Optional. Filter by sentiment
    "date_range": {             # Optional. Date range filter
        "start": str,           # ISO 8601 date
        "end": str              # ISO 8601 date
    },
    "limit": int               # Optional. Max results (default: 10)
}
```

**Response**:
```python
{
    "status": "success",
    "memories": List[{
        "memory_id": str,
        "summary": str,
        "relevance_score": float,
        "themes": List[str],
        "timestamp": str
    }],
    "total_matches": int,
    "search_time_ms": float
}
```

### GitHub Agent

Creates GitHub repositories from project ideas with AI-generated structure.

#### `create_project_repo`

Creates a GitHub repository from a project idea transcript.

**Parameters**:
```python
{
    "transcript": str,           # Project idea transcript
    "visibility": str,           # Optional. "public" or "private"
    "license": str,             # Optional. License type
    "correlation_id": str        # Optional. Request tracking ID
}
```

**Response**:
```python
{
    "status": "success",
    "repo_name": str,           # Generated repository name
    "repo_url": str,            # GitHub repository URL
    "description": str,         # AI-generated description
    "tech_stack": List[str],    # Identified technologies
    "initial_issues": List[{    # Created GitHub issues
        "title": str,
        "body": str,
        "labels": List[str]
    }],
    "readme_generated": bool,   # Whether README was created
    "license": str,             # Applied license
    "processing_time": float    # Processing duration
}
```

#### `update_project_history`

Updates project development history based on progress transcripts.

**Parameters**:
```python
{
    "repo_name": str,           # Repository name
    "transcript": str,          # Progress update transcript
    "correlation_id": str       # Optional. Request tracking ID
}
```

**Response**:
```python
{
    "status": "success",
    "updates_applied": List[str],  # Applied updates
    "new_issues": List[str],       # New issues created
    "closed_issues": List[str],    # Issues marked complete
    "milestone_progress": float,   # Project completion estimate
    "next_recommendations": List[str]  # AI recommendations
}
```

## Data Models

### Transcript
```python
@dataclass
class Transcript:
    content: str                    # Transcript text
    timestamp: datetime.datetime    # When recorded
    source: str                     # Source identifier
    language: str = "en"           # Language code
    confidence: float = 1.0        # Transcription confidence
    metadata: Dict[str, Any] = None # Additional metadata
```

### AgentResult
```python
@dataclass 
class AgentResult:
    status: str                     # "success", "failure", "partial"
    data: Dict[str, Any]           # Agent-specific result data
    metrics: ProcessingMetrics      # Performance metrics
    timestamp: str                  # ISO 8601 timestamp
    agent_type: str                # Agent that processed
    correlation_id: str = None     # Request tracking ID
```

### ProcessingMetrics
```python
@dataclass
class ProcessingMetrics:
    agent_type: str                # Agent identifier
    processing_time_ms: float      # Total processing time
    transcript_length: int         # Character count
    confidence_score: float        # Processing confidence
    tokens_used: int = 0          # AI tokens consumed
    api_calls_made: int = 0       # External API calls
    success: bool = True          # Success indicator
    error_type: str = None        # Error classification
```

### RoutingDecision
```python
@dataclass
class RoutingDecision:
    primary_agent: str             # Main agent selected
    secondary_agents: List[str]    # Additional agents
    confidence: float              # Routing confidence
    reasoning: str                 # Explanation
    segments: Dict[str, str]      # Agent-specific content
```

## Error Handling

### Error Response Format
```python
{
    "error": {
        "code": str,              # Error code
        "message": str,           # Human-readable message
        "details": Dict[str, Any], # Additional error details
        "timestamp": str,         # ISO 8601 timestamp
        "correlation_id": str,    # Request tracking ID
        "retry_after": int        # Retry delay in seconds (if applicable)
    }
}
```

### Error Codes

| Code | Description | Retry |
|------|-------------|-------|
| `INVALID_INPUT` | Invalid transcript or parameters | No |
| `PROCESSING_TIMEOUT` | Agent processing exceeded timeout | Yes |
| `SERVICE_UNAVAILABLE` | External service temporarily unavailable | Yes |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Yes |
| `AUTHENTICATION_FAILED` | Invalid credentials | No |
| `AUTHORIZATION_DENIED` | Insufficient permissions | No |
| `AGENT_ERROR` | Agent-specific processing error | Maybe |
| `INTERNAL_ERROR` | Unexpected system error | Yes |

### Retry Strategy
```python
import time
import random

def retry_with_backoff(func, max_attempts=3, base_delay=1.0):
    for attempt in range(max_attempts):
        try:
            return func()
        except RetryableError as e:
            if attempt == max_attempts - 1:
                raise e
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

## Usage Examples

### Basic Voice Processing
```python
import boto3
import json

# Initialize AWS Lambda client
lambda_client = boto3.client('lambda', region_name='us-east-1')

# Process work transcript
def process_work_memo(transcript):
    response = lambda_client.invoke(
        FunctionName='whispersync-orchestrator-production',
        Payload=json.dumps({
            'transcript': transcript,
            'force_agent': 'work'  # Force work agent
        })
    )
    
    result = json.loads(response['Payload'].read())
    
    if result.get('routing_decision', {}).get('primary_agent') == 'work':
        work_result = result['processing_results']['work']
        print(f"Work logged: {work_result['summary']}")
        return work_result
    else:
        print("Failed to process as work memo")
        return None

# Example usage
work_result = process_work_memo(
    "I completed the authentication system today. Fixed three bugs "
    "in the login flow and updated the API documentation."
)
```

### Batch Processing
```python
import concurrent.futures
from typing import List, Dict, Any

def process_transcripts_batch(transcripts: List[str]) -> List[Dict[str, Any]]:
    """Process multiple transcripts concurrently."""
    
    def process_single(transcript):
        return lambda_client.invoke(
            FunctionName='whispersync-orchestrator-production',
            Payload=json.dumps({'transcript': transcript})
        )
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single, t) for t in transcripts]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                response = future.result()
                result = json.loads(response['Payload'].read())
                results.append(result)
            except Exception as e:
                print(f"Error processing transcript: {e}")
                results.append({"error": str(e)})
    
    return results
```

### Memory Search Integration
```python
class MemorySearchClient:
    def __init__(self, lambda_function_name):
        self.lambda_client = boto3.client('lambda')
        self.function_name = lambda_function_name
    
    def search_memories(self, query, **filters):
        """Search memories with filters."""
        payload = {
            'action': 'search_memories',
            'query': query,
            **filters
        }
        
        response = self.lambda_client.invoke(
            FunctionName=self.function_name,
            Payload=json.dumps(payload)
        )
        
        return json.loads(response['Payload'].read())
    
    def find_similar_memories(self, memory_text, limit=5):
        """Find memories similar to given text."""
        return self.search_memories(
            query=memory_text,
            limit=limit
        )

# Usage
memory_client = MemorySearchClient('whispersync-memory-agent-production')
similar_memories = memory_client.find_similar_memories(
    "childhood camping trip with family"
)
```

### GitHub Integration Workflow
```python
class ProjectManager:
    def __init__(self, github_agent_function):
        self.lambda_client = boto3.client('lambda')
        self.github_function = github_agent_function
    
    def create_project_from_idea(self, idea_transcript, **options):
        """Create GitHub project from idea transcript."""
        payload = {
            'action': 'create_project_repo',
            'transcript': idea_transcript,
            **options
        }
        
        response = self.lambda_client.invoke(
            FunctionName=self.github_function,
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        return result
    
    def track_project_progress(self, repo_name, progress_transcript):
        """Update project with progress transcript."""
        payload = {
            'action': 'update_project_history',
            'repo_name': repo_name,
            'transcript': progress_transcript
        }
        
        response = self.lambda_client.invoke(
            FunctionName=self.github_function,
            Payload=json.dumps(payload)
        )
        
        return json.loads(response['Payload'].read())

# Usage
project_manager = ProjectManager('whispersync-github-agent-production')

# Create project
project = project_manager.create_project_from_idea(
    "I want to build a personal finance tracker that uses AI to "
    "categorize expenses and provide spending insights.",
    visibility="public",
    license="MIT"
)

print(f"Created project: {project['repo_url']}")

# Later, update with progress
progress = project_manager.track_project_progress(
    project['repo_name'],
    "I implemented the expense categorization algorithm and added "
    "unit tests. Ready to work on the web interface next."
)
```

## Rate Limits

### Current Limits
- **Lambda Invocations**: 1000 concurrent executions per region
- **S3 Requests**: 5,500 GET/PUT requests per second per prefix
- **Bedrock API**: Model-specific limits (typically 20 requests/minute)

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 60
```

### Handling Rate Limits
```python
import time
from botocore.exceptions import ClientError

def handle_rate_limits(func):
    """Decorator to handle rate limit errors."""
    def wrapper(*args, **kwargs):
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                if e.response['Error']['Code'] == 'TooManyRequestsException':
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                raise e
    return wrapper

@handle_rate_limits
def invoke_agent(function_name, payload):
    return lambda_client.invoke(
        FunctionName=function_name,
        Payload=json.dumps(payload)
    )
```

## Webhooks

### Event Notifications
WhisperSync can send webhook notifications for key events:

#### Webhook Payload Format
```python
{
    "event_type": str,          # Event type identifier
    "timestamp": str,           # ISO 8601 timestamp
    "data": Dict[str, Any],     # Event-specific data
    "correlation_id": str,      # Request tracking ID
    "signature": str            # HMAC signature for verification
}
```

#### Supported Events
- `transcript.processed` - Transcript processing completed
- `agent.success` - Agent completed successfully
- `agent.error` - Agent encountered error
- `routing.completed` - Routing decision made
- `memory.created` - New memory stored
- `project.created` - GitHub repository created

#### Webhook Configuration
```python
# Configure webhook endpoint
webhook_config = {
    "url": "https://your-app.com/webhooks/whispersync",
    "secret": "your-webhook-secret",
    "events": ["transcript.processed", "agent.success"],
    "retry_policy": {
        "max_attempts": 3,
        "backoff_multiplier": 2
    }
}
```

#### Webhook Verification
```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    """Verify webhook signature."""
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

# Example webhook handler
def handle_webhook(request):
    signature = request.headers.get('X-WhisperSync-Signature')
    payload = request.body
    
    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        return {"error": "Invalid signature"}, 401
    
    event = json.loads(payload)
    
    if event['event_type'] == 'transcript.processed':
        # Handle processed transcript
        process_completed_transcript(event['data'])
    
    return {"status": "received"}, 200
```

---

## SDK Examples

### Python SDK (Future Enhancement)
```python
from whispersync import WhisperSyncClient

# Initialize client
client = WhisperSyncClient(
    region='us-east-1',
    environment='production'
)

# Process transcript
result = client.process_transcript(
    "I completed the user authentication feature today.",
    agent_preference='work'
)

# Search memories
memories = client.search_memories(
    query="family camping trip",
    sentiment="positive"
)

# Create project
project = client.create_project(
    "I want to build a habit tracking app with gamification.",
    visibility="public"
)
```

### JavaScript SDK (Future Enhancement)
```javascript
import { WhisperSyncClient } from '@whispersync/sdk';

const client = new WhisperSyncClient({
    region: 'us-east-1',
    environment: 'production'
});

// Process transcript
const result = await client.processTranscript({
    transcript: 'I completed the user authentication feature today.',
    agentPreference: 'work'
});

// Search memories
const memories = await client.searchMemories({
    query: 'family camping trip',
    sentiment: 'positive'
});
```

## Support

For API questions or issues:
- **Documentation**: Refer to this guide and code examples
- **GitHub Issues**: Report bugs or request features
- **AWS Support**: For infrastructure and deployment issues

## Changelog

### v1.0.0
- Initial API release
- Core agent functionality
- S3 event processing
- Basic error handling

### v1.1.0 (Planned)
- Webhook support
- Batch processing endpoints
- Enhanced search capabilities
- Performance optimizations