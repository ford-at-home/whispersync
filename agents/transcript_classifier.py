"""TranscriptClassifier - Intelligent S3 object tagging for agent routing.

This Lambda function is triggered by S3 ObjectCreated events and:
1. Analyzes transcript content with Claude 3.5
2. Assigns 1-3 category tags (biased toward single tag)
3. Updates S3 object metadata with tags
4. Sends messages to appropriate SQS queues

Categories:
- OvernightMVP: Project ideas and technical innovations
- ExecutiveAssistant: Professional tasks and work updates
- SpiritualAdvisor: Personal reflections and life events
"""

import json
import logging
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime
import asyncio

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
secrets_client = boto3.client('secretsmanager')

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Queue URLs from environment
QUEUE_URLS = {
    'OvernightMVP': os.environ.get('OVERNIGHT_MVP_QUEUE_URL'),
    'ExecutiveAssistant': os.environ.get('EXECUTIVE_ASSISTANT_QUEUE_URL'),
    'SpiritualAdvisor': os.environ.get('SPIRITUAL_ADVISOR_QUEUE_URL')
}

# Category definitions for classification
CATEGORIES = {
    'OvernightMVP': {
        'description': 'Project ideas, technical innovations, creative solutions',
        'keywords': ['idea', 'build', 'create', 'app', 'tool', 'project', 'what if', 
                    'solution', 'innovation', 'startup', 'mvp', 'prototype'],
        'patterns': [
            r'(i have|what if we|we could) (an idea|build|create)',
            r'(new|cool|interesting) (app|tool|project|product)',
            r'mvp for',
            r'prototype'
        ],
        'weight': 1.0  # No bias
    },
    'ExecutiveAssistant': {
        'description': 'Work tasks, meetings, professional updates, career',
        'keywords': ['meeting', 'deadline', 'client', 'team', 'project', 'work',
                    'task', 'boss', 'colleague', 'presentation', 'review', 'goal'],
        'patterns': [
            r'meeting (with|about)',
            r'(finish|complete|done with) (the|my)',
            r'(client|customer) (wants|needs|said)',
            r'(boss|manager|supervisor)',
            r'deadline (for|on)'
        ],
        'weight': 1.1  # Slight bias toward work
    },
    'SpiritualAdvisor': {
        'description': 'Personal reflections, emotions, life events, memories',
        'keywords': ['feel', 'felt', 'remember', 'realized', 'grateful', 'love',
                    'family', 'friend', 'struggling', 'happy', 'sad', 'proud'],
        'patterns': [
            r'i (feel|felt|am feeling)',
            r'(made me|makes me) (think|feel|realize)',
            r'(grateful|thankful) (for|that)',
            r'(family|friend|loved one)',
            r'reminds me of'
        ],
        'weight': 0.9  # Slight bias against (prefer specific categories)
    }
}


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager."""
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve Anthropic API key: {e}")
        raise


async def classify_transcript(transcript: str) -> List[str]:
    """Classify transcript into 1-3 categories using Claude.
    
    Args:
        transcript: The voice transcript text
        
    Returns:
        List of 1-3 category tags, ordered by confidence
    """
    try:
        # Import here to handle Lambda layer loading
        from anthropic import Anthropic
        
        api_key = get_anthropic_api_key()
        anthropic = Anthropic(api_key=api_key)
        
        prompt = f"""Analyze this voice transcript and classify it into 1-3 categories.

Categories:
1. OvernightMVP - Project ideas, technical innovations, app/tool concepts
2. ExecutiveAssistant - Work tasks, meetings, professional updates, career matters
3. SpiritualAdvisor - Personal reflections, emotions, life events, memories

Transcript: "{transcript}"

Rules:
- Choose 1-3 categories that apply
- STRONGLY prefer assigning just 1 category unless the transcript clearly spans multiple
- Order by relevance (most relevant first)
- Focus on the primary intent/content

Respond with a JSON object:
{{
    "categories": ["Category1", "Category2"],  // 1-3 categories
    "confidence": 0.85,  // Overall confidence (0-1)
    "reasoning": "Brief explanation"
}}"""

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            temperature=0.3,  # Low temperature for consistent classification
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse response
        content = response.content[0].text
        result = json.loads(content)
        
        categories = result.get('categories', [])
        confidence = result.get('confidence', 0.5)
        
        # Apply single-tag bias
        if len(categories) > 1 and confidence < 0.9:
            # Only keep multiple tags if very confident
            categories = categories[:1]
        
        logger.info(f"Classified transcript: {categories} (confidence: {confidence})")
        return categories
        
    except Exception as e:
        logger.error(f"AI classification failed: {e}")
        # Fall back to keyword-based classification
        return fallback_classification(transcript)


def fallback_classification(transcript: str) -> List[str]:
    """Simple keyword-based classification as fallback.
    
    Args:
        transcript: The voice transcript
        
    Returns:
        List of 1-3 category tags based on keyword matching
    """
    scores = {}
    transcript_lower = transcript.lower()
    
    for category, config in CATEGORIES.items():
        score = 0.0
        
        # Check keywords
        for keyword in config['keywords']:
            if keyword in transcript_lower:
                score += 1.0
        
        # Apply weight
        score *= config['weight']
        
        if score > 0:
            scores[category] = score
    
    # Sort by score and return top categories
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Strong bias toward single category
    if sorted_categories:
        if len(sorted_categories) == 1 or sorted_categories[0][1] > sorted_categories[1][1] * 1.5:
            return [sorted_categories[0][0]]
        else:
            # Return up to 2 categories if scores are close
            return [cat[0] for cat in sorted_categories[:2]]
    
    # Default to ExecutiveAssistant if no matches
    return ['ExecutiveAssistant']


def update_s3_metadata(bucket: str, key: str, categories: List[str]) -> None:
    """Update S3 object metadata with category tags.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        categories: List of category tags
    """
    try:
        # Get current object metadata
        response = s3_client.head_object(Bucket=bucket, Key=key)
        current_metadata = response.get('Metadata', {})
        
        # Add category tags
        current_metadata['categories'] = ','.join(categories)
        current_metadata['classified_at'] = datetime.utcnow().isoformat()
        current_metadata['classifier_version'] = '1.0'
        
        # Copy object with updated metadata (S3 doesn't support direct metadata update)
        s3_client.copy_object(
            Bucket=bucket,
            Key=key,
            CopySource={'Bucket': bucket, 'Key': key},
            Metadata=current_metadata,
            MetadataDirective='REPLACE',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Updated S3 metadata for {key} with categories: {categories}")
        
    except Exception as e:
        logger.error(f"Failed to update S3 metadata: {e}")
        raise


def send_to_queues(bucket: str, key: str, transcript: str, categories: List[str]) -> None:
    """Send messages to appropriate SQS queues based on categories.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        transcript: Transcript text
        categories: List of assigned categories
    """
    for category in categories:
        queue_url = QUEUE_URLS.get(category)
        if not queue_url:
            logger.error(f"No queue URL configured for category: {category}")
            continue
        
        message = {
            'bucket': bucket,
            'key': key,
            'transcript': transcript,
            'category': category,
            'is_primary': category == categories[0],  # First category is primary
            'all_categories': categories,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'TranscriptClassifier'
        }
        
        try:
            response = sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'Category': {
                        'StringValue': category,
                        'DataType': 'String'
                    },
                    'S3Bucket': {
                        'StringValue': bucket,
                        'DataType': 'String'
                    },
                    'S3Key': {
                        'StringValue': key,
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Sent message to {category} queue: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Failed to send message to {category} queue: {e}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for S3 ObjectCreated events.
    
    Args:
        event: S3 event
        context: Lambda context
        
    Returns:
        Processing result
    """
    try:
        # Extract S3 information
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing transcript from s3://{bucket}/{key}")
        
        # Download transcript
        try:
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            transcript = obj['Body'].read().decode('utf-8')
            logger.info(f"Downloaded transcript: {len(transcript)} characters")
        except Exception as e:
            logger.error(f"Failed to download transcript: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to download transcript'})
            }
        
        # Run async classification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Classify transcript
            categories = loop.run_until_complete(classify_transcript(transcript))
            
            if not categories:
                logger.error("No categories assigned")
                categories = ['ExecutiveAssistant']  # Default
            
            # Update S3 metadata
            update_s3_metadata(bucket, key, categories)
            
            # Send to SQS queues
            send_to_queues(bucket, key, transcript, categories)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Transcript classified and routed',
                    'categories': categories,
                    'bucket': bucket,
                    'key': key
                })
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }