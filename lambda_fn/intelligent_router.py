"""Intelligent Lambda router for WhisperSync with AI-powered classification.

This replaces the legacy folder-based routing with intelligent content analysis
that determines which memory bucket a transcript belongs to:
- Cool New Ideas → GitHub repository creation
- Tactical Reflections → Work journal tracking
- Personal Memories → Emotionally-aware diary

DESIGN PHILOSOPHY:
- Content determines routing, not folder structure
- AI-powered understanding of context and intent
- Graceful fallback when confidence is low
- Learning from user corrections
"""

import json
import logging
import os
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

# Initialize AWS services
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Import our intelligent classifier
try:
    import sys
    sys.path.insert(0, '/opt/python')  # Lambda layer path
    from agents.memory_classifier import (
        MemoryClassifier, MemoryRouter, MemoryBucket, ClassificationResult
    )
    from agents.diary_processor import DiaryProcessor
    CLASSIFIER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Failed to import memory_classifier: {e}")
    CLASSIFIER_AVAILABLE = False

# Agent Lambda function ARNs (configured via environment variables)
AGENT_FUNCTIONS = {
    'github_agent': os.environ.get('GITHUB_AGENT_ARN'),
    'work_agent': os.environ.get('WORK_AGENT_ARN'),
    'diary_agent': os.environ.get('DIARY_AGENT_ARN')
}


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager.
    
    Returns:
        API key string
        
    Raises:
        Exception if key cannot be retrieved
    """
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve Anthropic API key: {e}")
        raise


async def classify_transcript(
    transcript: str, 
    s3_key: Optional[str] = None
) -> ClassificationResult:
    """Classify a transcript using AI.
    
    Args:
        transcript: The voice transcript text
        s3_key: Optional S3 key for fallback hints
        
    Returns:
        Classification result with confidence scores
    """
    if not CLASSIFIER_AVAILABLE:
        # Fallback to simple keyword matching
        return fallback_classification(transcript, s3_key)
    
    try:
        api_key = get_anthropic_api_key()
        classifier = MemoryClassifier(anthropic_api_key=api_key)
        result = await classifier.classify(transcript)
        
        # Log classification for monitoring
        logger.info(
            f"Classified transcript: {result.primary_bucket.value} "
            f"(confidence: {result.confidence:.2f})"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return fallback_classification(transcript, s3_key)


def fallback_classification(
    transcript: str, 
    s3_key: Optional[str] = None
) -> ClassificationResult:
    """Simple fallback classification when AI is unavailable.
    
    Args:
        transcript: The voice transcript
        s3_key: Optional S3 key for folder-based hints
        
    Returns:
        Basic classification result
    """
    from agents.memory_classifier import ClassificationResult, MemoryBucket
    
    # Check S3 key for folder hints
    if s3_key:
        if 'github' in s3_key.lower() or 'ideas' in s3_key.lower():
            bucket = MemoryBucket.COOL_IDEAS
        elif 'work' in s3_key.lower():
            bucket = MemoryBucket.TACTICAL
        elif 'memor' in s3_key.lower() or 'personal' in s3_key.lower():
            bucket = MemoryBucket.PERSONAL
        else:
            bucket = MemoryBucket.PERSONAL  # Default
        
        return ClassificationResult(
            primary_bucket=bucket,
            confidence=0.6,  # Low confidence for fallback
            secondary_buckets=[],
            reasoning="Classified based on S3 folder structure (fallback mode)",
            key_indicators=[f"S3 path: {s3_key}"],
            suggested_tags=[]
        )
    
    # Simple keyword matching
    transcript_lower = transcript.lower()
    
    if any(word in transcript_lower for word in ['build', 'app', 'idea', 'project']):
        bucket = MemoryBucket.COOL_IDEAS
    elif any(word in transcript_lower for word in ['work', 'meeting', 'task', 'completed']):
        bucket = MemoryBucket.TACTICAL
    else:
        bucket = MemoryBucket.PERSONAL
    
    return ClassificationResult(
        primary_bucket=bucket,
        confidence=0.5,  # Very low confidence
        secondary_buckets=[],
        reasoning="Classified using simple keyword matching (AI unavailable)",
        key_indicators=[],
        suggested_tags=[]
    )


async def invoke_agent(
    agent_name: str,
    transcript: str,
    classification: ClassificationResult,
    s3_bucket: str,
    s3_key: str
) -> Dict[str, Any]:
    """Invoke the appropriate agent Lambda function.
    
    Args:
        agent_name: Name of the agent to invoke
        transcript: Voice transcript
        classification: Classification result with metadata
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        
    Returns:
        Agent processing result
    """
    # Special handling for diary agent (direct processing)
    if agent_name == 'diary_agent' and CLASSIFIER_AVAILABLE:
        try:
            api_key = get_anthropic_api_key()
            processor = DiaryProcessor(
                anthropic_api_key=api_key,
                s3_bucket=s3_bucket
            )
            
            diary_entry = await processor.process_transcript(
                transcript=transcript,
                source_metadata={
                    's3_key': s3_key,
                    'classification': classification.to_dict()
                }
            )
            
            return {
                'status': 'success',
                'agent': 'diary',
                'entry': diary_entry.to_json(),
                'storage_location': f"diary/{diary_entry.date}"
            }
            
        except Exception as e:
            logger.error(f"Diary processing failed: {e}")
            return {
                'status': 'error',
                'agent': 'diary',
                'error': str(e)
            }
    
    # For other agents, invoke Lambda functions
    function_arn = AGENT_FUNCTIONS.get(agent_name)
    if not function_arn:
        logger.error(f"No Lambda function configured for agent: {agent_name}")
        return {
            'status': 'error',
            'agent': agent_name,
            'error': 'Agent Lambda function not configured'
        }
    
    try:
        lambda_client = boto3.client('lambda')
        
        payload = {
            'transcript': transcript,
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'classification': classification.to_dict()
        }
        
        response = lambda_client.invoke(
            FunctionName=function_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        return result
        
    except Exception as e:
        logger.error(f"Failed to invoke {agent_name}: {e}")
        return {
            'status': 'error',
            'agent': agent_name,
            'error': str(e)
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for S3 ObjectCreated events.
    
    Triggered by S3 ObjectCreated events within configured prefix (e.g., 'transcripts/').
    The intelligent routing system analyzes content to determine the appropriate
    memory bucket, regardless of the specific S3 path structure.
    
    Args:
        event: S3 ObjectCreated event with format:
               {
                   "Records": [{
                       "eventName": "ObjectCreated:Put",
                       "s3": {
                           "bucket": {"name": "voice-mcp"},
                           "object": {"key": "transcripts/2024/01/15/audio_123.txt"}
                       }
                   }]
               }
        context: Lambda context with request_id, function_name, etc.
        
    Returns:
        Processing result with routing decisions
    """
    try:
        # Validate S3 event structure
        if 'Records' not in event or not event['Records']:
            logger.error("Invalid S3 event structure")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid S3 event structure'})
            }
        
        # Process first record (S3 sends one record per event)
        record = event['Records'][0]
        
        # Verify this is an ObjectCreated event
        event_name = record.get('eventName', '')
        if not event_name.startswith('ObjectCreated'):
            logger.warning(f"Ignoring non-ObjectCreated event: {event_name}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': f'Ignored event: {event_name}'})
            }
        
        # Extract S3 information
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Check if this is within our configured prefix
        configured_prefix = os.environ.get('TRANSCRIPT_PREFIX', 'transcripts/')
        if not key.startswith(configured_prefix):
            logger.warning(f"Object {key} is not within configured prefix {configured_prefix}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': f'Ignored object outside prefix: {key}'})
            }
        
        logger.info(f"Processing new transcript from s3://{bucket}/{key}")
        
        # Download transcript
        try:
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            transcript = obj['Body'].read().decode('utf-8')
            
            # Get object metadata if available
            object_metadata = obj.get('Metadata', {})
            
            logger.info(
                f"Downloaded transcript: {len(transcript)} characters, "
                f"metadata: {object_metadata}"
            )
        except Exception as e:
            logger.error(f"Failed to download transcript: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to download transcript',
                    'details': str(e)
                })
            }
        
        # Run async classification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Classify the transcript
            classification = loop.run_until_complete(
                classify_transcript(transcript, key)
            )
            
            # Map classification to agent
            agent_mapping = {
                MemoryBucket.COOL_IDEAS: 'github_agent',
                MemoryBucket.TACTICAL: 'work_agent',
                MemoryBucket.PERSONAL: 'diary_agent'
            }
            
            target_agent = agent_mapping[classification.primary_bucket]
            
            # Invoke the appropriate agent
            agent_result = loop.run_until_complete(
                invoke_agent(
                    agent_name=target_agent,
                    transcript=transcript,
                    classification=classification,
                    s3_bucket=bucket,
                    s3_key=key
                )
            )
            
            # Prepare output
            output_data = {
                'source_key': key,
                'processed_at': datetime.utcnow().isoformat(),
                'classification': classification.to_dict(),
                'agent_result': agent_result,
                'request_id': context.request_id
            }
            
            # Store results
            output_key = key.replace('transcripts/', 'outputs/').replace('.txt', '_result.json')
            
            s3_client.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=json.dumps(output_data, indent=2),
                ContentType='application/json',
                Metadata={
                    'source_transcript': key,
                    'memory_bucket': classification.primary_bucket.value,
                    'confidence': str(classification.confidence),
                    'agent': target_agent
                }
            )
            
            logger.info(f"Stored results at s3://{bucket}/{output_key}")
            
            # Handle low confidence classifications
            if classification.needs_user_confirmation():
                # Store for review
                review_key = key.replace('transcripts/', 'review_needed/').replace('.txt', '_review.json')
                s3_client.put_object(
                    Bucket=bucket,
                    Key=review_key,
                    Body=json.dumps({
                        'transcript': transcript,
                        'classification': classification.to_dict(),
                        'suggested_alternatives': [
                            {
                                'bucket': b.value,
                                'confidence': c,
                                'agent': agent_mapping[b]
                            }
                            for b, c in classification.secondary_buckets
                        ],
                        'timestamp': datetime.utcnow().isoformat()
                    }, indent=2),
                    ContentType='application/json'
                )
                logger.info(f"Low confidence - marked for review: {review_key}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Transcript processed successfully',
                    'classification': {
                        'bucket': classification.primary_bucket.value,
                        'confidence': classification.confidence
                    },
                    'agent': target_agent,
                    'output_key': output_key,
                    'needs_review': classification.needs_user_confirmation()
                })
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        
        # Store error for debugging
        if 'bucket' in locals() and 'key' in locals():
            error_key = key.replace('transcripts/', 'errors/').replace('.txt', '_error.json')
            try:
                s3_client.put_object(
                    Bucket=bucket,
                    Key=error_key,
                    Body=json.dumps({
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'source_key': key,
                        'timestamp': datetime.utcnow().isoformat(),
                        'request_id': context.request_id
                    }, indent=2),
                    ContentType='application/json'
                )
            except:
                pass  # Don't fail on error logging
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Processing failed',
                'details': str(e)
            })
        }


def feedback_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user feedback on classifications to improve the system.
    
    This allows users to correct misclassifications, which can be used
    to improve the classifier over time.
    
    Args:
        event: Contains transcript, original classification, and correction
        context: Lambda context
        
    Returns:
        Feedback processing result
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        transcript = body.get('transcript')
        original_classification = body.get('original_classification')
        correct_bucket = body.get('correct_bucket')
        user_notes = body.get('notes', '')
        
        if not all([transcript, original_classification, correct_bucket]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields: transcript, original_classification, correct_bucket'
                })
            }
        
        # Store feedback for future training
        feedback_data = {
            'transcript': transcript,
            'original_classification': original_classification,
            'correct_bucket': correct_bucket,
            'user_notes': user_notes,
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': context.request_id
        }
        
        bucket = os.environ.get('BUCKET_NAME', 'voice-mcp')
        feedback_key = f"feedback/{datetime.utcnow().strftime('%Y/%m/%d')}/{context.request_id}.json"
        
        s3_client.put_object(
            Bucket=bucket,
            Key=feedback_key,
            Body=json.dumps(feedback_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Stored classification feedback: {feedback_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Feedback recorded successfully',
                'feedback_id': context.request_id
            })
        }
        
    except Exception as e:
        logger.error(f"Feedback processing failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process feedback',
                'details': str(e)
            })
        }


# Health check handler
def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Health check for the intelligent router.
    
    Returns:
        Health status including classifier availability
    """
    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'classifier': {
                'available': CLASSIFIER_AVAILABLE,
                'mode': 'AI' if CLASSIFIER_AVAILABLE else 'fallback'
            },
            's3': {'status': 'unknown'},
            'secrets': {'status': 'unknown'}
        }
    }
    
    # Test S3 access
    try:
        bucket = os.environ.get('BUCKET_NAME', 'voice-mcp')
        s3_client.head_bucket(Bucket=bucket)
        health['services']['s3'] = {'status': 'available', 'bucket': bucket}
    except Exception as e:
        health['services']['s3'] = {'status': 'error', 'error': str(e)}
        health['status'] = 'degraded'
    
    # Test Secrets Manager access
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        secrets_client.describe_secret(SecretId=secret_name)
        health['services']['secrets'] = {'status': 'available'}
    except Exception as e:
        health['services']['secrets'] = {'status': 'error', 'error': str(e)}
        if CLASSIFIER_AVAILABLE:
            health['status'] = 'degraded'
    
    status_code = 200 if health['status'] in ['healthy', 'degraded'] else 503
    
    return {
        'statusCode': status_code,
        'body': json.dumps(health, indent=2),
        'headers': {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }
    }