"""SpiritualAdvisorAgent - Minimal working implementation for Sprint 1 MVP.

Core responsibilities (MVP):
- Create JSON entry with timestamp and content
- Save to daily memory file in S3 (JSONL format)
- Preserve exact transcript verbatim
- Return success response

This is a minimal implementation focused on data preservation without analysis.
"""

import json
import logging
import os
from typing import Dict, Any
from datetime import datetime

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
s3_client = boto3.client('s3')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Minimal working Lambda handler for Spiritual Advisor agent - Sprint 1 MVP.
    
    Processes personal memories with minimal implementation:
    1. Creates JSON entry with timestamp and content
    2. Saves to daily memory file in S3 (JSONL format)
    3. Preserves exact transcript verbatim
    4. Returns success response
    """
    try:
        # Process each record
        for record in event['Records']:
            # Parse message
            message = json.loads(record['body'])
            transcript = message['transcript']
            s3_bucket = message['bucket']
            s3_key = message['key']
            
            logger.info(f"Processing personal memory from {s3_key}")
            
            # Create minimal memory entry
            now = datetime.utcnow()
            memory_entry = {
                "timestamp": now.isoformat(),
                "content": transcript  # Preserve exact transcript verbatim
            }
            
            # Save to daily memory file in S3 (JSONL format)
            date_key = now.strftime("%Y-%m-%d")  # e.g., "2024-01-15"
            memory_key = f"memories/{date_key}.jsonl"  # e.g., "memories/2024-01-15.jsonl"
            
            try:
                # Get existing daily file for appending
                obj = s3_client.get_object(Bucket=s3_bucket, Key=memory_key)
                existing_content = obj['Body'].read().decode('utf-8')
            except s3_client.exceptions.NoSuchKey:
                # First memory of the day - start new file
                existing_content = ""
            except Exception as e:
                logger.warning(f"Error reading existing file: {e}")
                existing_content = ""
            
            # Append new memory to daily file
            updated_content = existing_content + json.dumps(memory_entry) + "\n"
            
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=memory_key,
                Body=updated_content.encode('utf-8'),
                ContentType='application/x-ndjson',  # JSONL MIME type
                Metadata={
                    'date': date_key,
                    'count': str(len(updated_content.strip().split('\n')))
                }
            )
            
            # Create success response
            output = {
                "status": "success",
                "memory_key": memory_key,
                "timestamp": now.isoformat(),
                "content_preserved": True,
                "daily_file_updated": True
            }
            
            # Store simple output
            output_key = s3_key.replace('transcripts/', 'outputs/spiritual_advisor/').replace('.txt', '_response.json')
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=output_key,
                Body=json.dumps(output, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Successfully stored memory in {memory_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Memories processed and stored successfully'})
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# For backward compatibility with existing code that might import functions
def minimal_memory_handler(transcript: str, s3_bucket: str, s3_key: str) -> Dict[str, Any]:
    """Standalone function for processing memories with minimal implementation."""
    # Create minimal memory entry
    now = datetime.utcnow()
    memory_entry = {
        "timestamp": now.isoformat(),
        "content": transcript  # Preserve exact transcript verbatim
    }
    
    # Save to daily memory file in S3 (JSONL format)
    date_key = now.strftime("%Y-%m-%d")  # e.g., "2024-01-15"
    memory_key = f"memories/{date_key}.jsonl"  # e.g., "memories/2024-01-15.jsonl"
    
    try:
        # Get existing daily file for appending
        obj = s3_client.get_object(Bucket=s3_bucket, Key=memory_key)
        existing_content = obj['Body'].read().decode('utf-8')
    except s3_client.exceptions.NoSuchKey:
        # First memory of the day - start new file
        existing_content = ""
    except Exception as e:
        logger.warning(f"Error reading existing file: {e}")
        existing_content = ""
    
    # Append new memory to daily file
    updated_content = existing_content + json.dumps(memory_entry) + "\n"
    
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=memory_key,
        Body=updated_content.encode('utf-8'),
        ContentType='application/x-ndjson',  # JSONL MIME type
        Metadata={
            'date': date_key,
            'count': str(len(updated_content.strip().split('\n')))
        }
    )
    
    # Return success response
    return {
        "status": "success",
        "memory_key": memory_key,
        "timestamp": now.isoformat(),
        "content_preserved": True,
        "daily_file_updated": True
    }