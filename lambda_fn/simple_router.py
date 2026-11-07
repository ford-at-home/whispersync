"""Simple Lambda handler for WhisperSync without Strands dependencies.

This is a simplified version for initial deployment that doesn't rely on Strands agents.
It will log the transcript and return a basic response.
"""

import json
import logging
import os
import datetime
from typing import Any, Dict
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3 = boto3.client("s3")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for processing voice transcripts."""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Validate event structure
        if not event or "Records" not in event:
            logger.error("Invalid event: missing Records field")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Invalid event format", "details": "Missing 'Records' field"}
                ),
            }

        if not event["Records"]:
            logger.warning("Empty Records array in S3 event")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"message": "No records to process", "processed": 0}
                ),
            }

        # Process all records in the event
        processed_count = 0
        results = []

        for idx, record in enumerate(event["Records"]):
            try:
                # Validate record structure
                if "s3" not in record:
                    logger.error(f"Record {idx} missing 's3' field")
                    continue

                if "bucket" not in record["s3"] or "object" not in record["s3"]:
                    logger.error(f"Record {idx} missing bucket or object information")
                    continue

                # Extract S3 information
                bucket = record["s3"]["bucket"]["name"]
                key = record["s3"]["object"]["key"]
                
                # Handle URL-encoded keys
                key = unquote_plus(key)
                
                logger.info(f"Processing record {idx}: s3://{bucket}/{key}")

                # Process individual transcript
                result = process_simple_transcript(bucket, key, context)
                results.append(result)
                
                if result.get("statusCode") == 200:
                    processed_count += 1

            except Exception as e:
                logger.error(f"Failed to process record {idx}: {e}", exc_info=True)

        # Return success response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Processed {processed_count} transcripts successfully",
                "processed": processed_count,
                "total": len(event["Records"]),
                "results": results
            }),
        }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Unexpected error",
                "details": str(e),
                "error_type": type(e).__name__
            }),
        }


def process_simple_transcript(bucket: str, key: str, context: Any) -> Dict[str, Any]:
    """Process a single transcript from S3 with simple routing."""
    try:
        logger.info(f"Processing transcript from s3://{bucket}/{key}")

        # Download transcript from S3
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            transcript = obj["Body"].read().decode("utf-8")
            logger.info(f"Downloaded transcript, {len(transcript)} characters")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 error downloading transcript: {error_code}")
            return {
                "statusCode": 404 if error_code == 'NoSuchKey' else 500,
                "error": "Failed to download transcript",
                "details": str(e),
                "error_code": error_code
            }

        # Simple routing based on S3 key path
        agent_type = "unknown"
        if "work" in key:
            agent_type = "work"
        elif "memories" in key:
            agent_type = "memory"
        elif "github" in key:
            agent_type = "github"
        
        # Simple processing (just logging for now)
        logger.info(f"Routing transcript to {agent_type} agent")
        logger.info(f"Transcript content: {transcript[:200]}...")  # Log first 200 chars
        
        # Create simple response
        response_data = {
            "agent_type": agent_type,
            "transcript_length": len(transcript),
            "processed_at": datetime.datetime.utcnow().isoformat(),
            "request_id": context.aws_request_id,
            "source_key": key,
            "message": f"Transcript processed by {agent_type} agent (simplified version)"
        }
        
        # Write simple response to S3
        output_key = key.replace("transcripts/", "outputs/").replace(".txt", "_response.json")
        
        try:
            s3.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=json.dumps(response_data, indent=2).encode("utf-8"),
                ContentType="application/json",
                Metadata={
                    "source_transcript": key,
                    "agent_type": agent_type,
                    "request_id": context.aws_request_id,
                },
            )
            logger.info(f"Wrote response to s3://{bucket}/{output_key}")
        except Exception as e:
            logger.warning(f"Failed to write response to S3: {e}")
            # Don't fail the entire process if we can't write the response
        
        return {
            "statusCode": 200,
            "message": "Transcript processed successfully",
            "source_key": key,
            "output_key": output_key,
            "agent_type": agent_type,
            "success": True,
        }

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "error": "Processing failed",
            "details": str(e),
            "source_key": key
        }


def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Simple health check endpoint."""
    try:
        logger.info("Performing health check")
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "request_id": context.aws_request_id,
            "message": "WhisperSync Lambda is running (simplified version)"
        }
        
        # Test S3 connectivity
        try:
            bucket_name = os.environ.get('TRANSCRIPT_BUCKET_NAME', 'macbook-transcriptions')
            s3.head_bucket(Bucket=bucket_name)
            health_status["s3_status"] = "available"
            health_status["bucket"] = bucket_name
        except Exception as e:
            health_status["s3_status"] = "error"
            health_status["s3_error"] = str(e)
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return {
            "statusCode": status_code,
            "body": json.dumps(health_status, indent=2),
            "headers": {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "statusCode": 503,
            "body": json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }),
            "headers": {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            }
        }