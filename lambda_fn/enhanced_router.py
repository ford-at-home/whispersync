"""
Enhanced Router Lambda Handler for WhisperSync

This handler processes S3 events and routes transcripts to the orchestrator queue
for intelligent agent assignment. Key improvements:

1. SQS Integration: Decouples S3 event processing from agent execution
2. Message Attributes: Rich metadata for downstream processing
3. Batch Processing: Handles multiple S3 events efficiently
4. Error Handling: Comprehensive error tracking and recovery
5. Observability: Structured logging and CloudWatch metrics

ARCHITECTURAL FLOW:
S3 Event → Router Lambda → SQS Message → Orchestrator Queue → Agent Processing

WHY THIS DESIGN:
- Reliability: SQS ensures no transcript is lost even if agents are down
- Scalability: Queue depth auto-scales Lambda concurrency
- Flexibility: Easy to add new routing logic without affecting agents
- Monitoring: Queue metrics provide operational visibility
"""

import json
import logging
import os
import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import hashlib

import boto3
from botocore.exceptions import ClientError

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
s3 = boto3.client("s3")
sqs = boto3.client("sqs")
cloudwatch = boto3.client("cloudwatch")

# Environment variables
ORCHESTRATOR_QUEUE_URL = os.environ["ORCHESTRATOR_QUEUE_URL"]
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
METRICS_NAMESPACE = "WhisperSync"


@dataclass
class TranscriptMessage:
    """Structured message format for transcript processing."""
    message_id: str
    transcript_key: str
    bucket_name: str
    transcript_content: str
    source_metadata: Dict[str, Any]
    routing_hints: Dict[str, Any]
    timestamp: str
    environment: str
    
    def to_sqs_message(self) -> Dict[str, Any]:
        """Convert to SQS message format with attributes."""
        # Create content hash for deduplication
        content_hash = hashlib.sha256(
            f"{self.transcript_key}:{self.transcript_content[:100]}".encode()
        ).hexdigest()[:16]
        
        return {
            "Id": self.message_id,
            "MessageBody": json.dumps(asdict(self)),
            "MessageAttributes": {
                "transcript_key": {
                    "StringValue": self.transcript_key,
                    "DataType": "String"
                },
                "bucket_name": {
                    "StringValue": self.bucket_name,
                    "DataType": "String"
                },
                "content_length": {
                    "StringValue": str(len(self.transcript_content)),
                    "DataType": "Number"
                },
                "environment": {
                    "StringValue": self.environment,
                    "DataType": "String"
                },
                "timestamp": {
                    "StringValue": self.timestamp,
                    "DataType": "String"
                }
            },
            # For FIFO queues
            "MessageGroupId": "transcripts",
            "MessageDeduplicationId": f"{self.message_id}-{content_hash}"
        }


def extract_routing_hints(s3_key: str) -> Dict[str, Any]:
    """Extract routing hints from S3 key structure.
    
    Examples:
    - transcripts/work/2024-01-01.txt → {"suggested_agent": "work", "category": "work"}
    - transcripts/memories/personal/2024-01-01.txt → {"suggested_agent": "memory", "subcategory": "personal"}
    """
    hints = {}
    parts = s3_key.split("/")
    
    if len(parts) >= 2 and parts[0] == "transcripts":
        # Extract agent type from path
        agent_type = parts[1]
        hints["suggested_agent"] = agent_type
        hints["category"] = agent_type
        
        # Extract subcategory if present
        if len(parts) >= 4:
            hints["subcategory"] = parts[2]
            
        # Extract date from filename if present
        if len(parts) >= 3:
            filename = parts[-1]
            if filename.endswith(".txt"):
                name_parts = filename[:-4].split("_")
                for part in name_parts:
                    if part.count("-") == 2:  # Likely a date
                        hints["transcript_date"] = part
                        break
    
    return hints


def get_s3_metadata(bucket: str, key: str) -> Dict[str, Any]:
    """Retrieve S3 object metadata for additional context."""
    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        return {
            "content_length": response.get("ContentLength", 0),
            "last_modified": response.get("LastModified", "").isoformat() if response.get("LastModified") else None,
            "etag": response.get("ETag", "").strip('"'),
            "metadata": response.get("Metadata", {}),
            "storage_class": response.get("StorageClass", "STANDARD")
        }
    except Exception as e:
        logger.warning(f"Failed to get S3 metadata for {bucket}/{key}: {e}")
        return {}


def publish_metrics(metric_name: str, value: float, unit: str = "Count", dimensions: Optional[List[Dict]] = None):
    """Publish custom CloudWatch metrics."""
    try:
        cloudwatch.put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Timestamp": datetime.utcnow(),
                "Dimensions": dimensions or [
                    {"Name": "Environment", "Value": ENVIRONMENT}
                ]
            }]
        )
    except Exception as e:
        logger.error(f"Failed to publish metric {metric_name}: {e}")


def process_s3_record(record: Dict[str, Any]) -> Optional[TranscriptMessage]:
    """Process a single S3 event record and create a message."""
    try:
        # Extract S3 information
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        event_name = record.get("eventName", "")
        
        logger.info(f"Processing S3 event: {event_name} for s3://{bucket}/{key}")
        
        # Skip if not a creation event
        if not event_name.startswith("ObjectCreated:"):
            logger.info(f"Skipping non-creation event: {event_name}")
            return None
        
        # Download transcript
        start_time = time.time()
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            transcript_content = obj["Body"].read().decode("utf-8")
            download_time = time.time() - start_time
            
            logger.info(f"Downloaded {len(transcript_content)} characters in {download_time:.2f}s")
            publish_metrics("TranscriptDownloadTime", download_time * 1000, "Milliseconds")
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"Failed to download transcript: {error_code}")
            publish_metrics("TranscriptDownloadErrors", 1)
            
            if error_code == "NoSuchKey":
                # Object might have been deleted already
                return None
            raise
        
        # Create structured message
        message = TranscriptMessage(
            message_id=str(uuid.uuid4()),
            transcript_key=key,
            bucket_name=bucket,
            transcript_content=transcript_content,
            source_metadata=get_s3_metadata(bucket, key),
            routing_hints=extract_routing_hints(key),
            timestamp=datetime.utcnow().isoformat(),
            environment=ENVIRONMENT
        )
        
        # Validate message size for SQS (256KB limit)
        message_json = json.dumps(asdict(message))
        if len(message_json.encode("utf-8")) > 262144:  # 256KB
            logger.warning(f"Message too large for SQS, truncating transcript content")
            # Truncate transcript content to fit
            max_content_length = 250000 - len(message_json) + len(message.transcript_content)
            message.transcript_content = message.transcript_content[:max_content_length] + "... [TRUNCATED]"
        
        return message
        
    except Exception as e:
        logger.error(f"Failed to process S3 record: {e}", exc_info=True)
        publish_metrics("ProcessingErrors", 1)
        raise


def send_messages_to_sqs(messages: List[TranscriptMessage]) -> Dict[str, Any]:
    """Send messages to SQS in batches."""
    results = {"successful": 0, "failed": 0, "failed_messages": []}
    
    # SQS batch size limit is 10
    batch_size = 10
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        sqs_messages = [msg.to_sqs_message() for msg in batch]
        
        try:
            response = sqs.send_message_batch(
                QueueUrl=ORCHESTRATOR_QUEUE_URL,
                Entries=sqs_messages
            )
            
            # Process successful sends
            results["successful"] += len(response.get("Successful", []))
            
            # Process failures
            failed = response.get("Failed", [])
            if failed:
                results["failed"] += len(failed)
                for failure in failed:
                    logger.error(
                        f"Failed to send message {failure['Id']}: "
                        f"{failure['Code']} - {failure['Message']}"
                    )
                    results["failed_messages"].append(failure["Id"])
                    
        except Exception as e:
            logger.error(f"Failed to send batch to SQS: {e}")
            results["failed"] += len(batch)
            results["failed_messages"].extend([msg.message_id for msg in batch])
    
    # Publish metrics
    publish_metrics("MessagesRoutedToSQS", results["successful"])
    if results["failed"] > 0:
        publish_metrics("MessageRoutingFailures", results["failed"])
    
    return results


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for routing S3 events to SQS.
    
    This handler:
    1. Processes S3 event notifications
    2. Downloads transcripts from S3
    3. Enriches messages with metadata and routing hints
    4. Sends messages to the orchestrator SQS queue
    5. Tracks metrics and handles errors gracefully
    """
    start_time = time.time()
    request_id = getattr(context, "request_id", str(uuid.uuid4()))
    
    logger.info(f"Router invoked with request_id: {request_id}")
    logger.debug(f"Event: {json.dumps(event)}")
    
    try:
        # Extract S3 records from event
        records = event.get("Records", [])
        if not records:
            logger.warning("No records found in event")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No records to process"})
            }
        
        logger.info(f"Processing {len(records)} S3 records")
        
        # Process each record
        messages = []
        processing_errors = []
        
        for record in records:
            try:
                message = process_s3_record(record)
                if message:
                    messages.append(message)
            except Exception as e:
                error_info = {
                    "record": record,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                processing_errors.append(error_info)
                logger.error(f"Failed to process record: {error_info}")
        
        # Send messages to SQS
        send_results = {"successful": 0, "failed": 0} if not messages else send_messages_to_sqs(messages)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        publish_metrics("RouterExecutionTime", execution_time * 1000, "Milliseconds")
        
        # Prepare response
        response_body = {
            "message": "Router processing complete",
            "request_id": request_id,
            "records_processed": len(records),
            "messages_created": len(messages),
            "messages_sent": send_results["successful"],
            "messages_failed": send_results["failed"],
            "processing_errors": len(processing_errors),
            "execution_time_ms": round(execution_time * 1000, 2)
        }
        
        # Determine status code
        if send_results["failed"] > 0 or processing_errors:
            # Partial failure
            status_code = 202  # Accepted with issues
            response_body["errors"] = processing_errors[:5]  # Include first 5 errors
        else:
            status_code = 200
        
        logger.info(f"Router completed: {response_body}")
        
        return {
            "statusCode": status_code,
            "body": json.dumps(response_body),
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": request_id
            }
        }
        
    except Exception as e:
        logger.error(f"Router failed with unexpected error: {e}", exc_info=True)
        publish_metrics("RouterErrors", 1)
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "error_type": type(e).__name__,
                "message": str(e),
                "request_id": request_id
            }),
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": request_id
            }
        }


def warmup_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Warmup handler to prevent cold starts."""
    logger.info("Router warmup invoked")
    
    # Pre-warm SQS connection
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=ORCHESTRATOR_QUEUE_URL,
            AttributeNames=["ApproximateNumberOfMessages"]
        )
        queue_depth = response["Attributes"].get("ApproximateNumberOfMessages", "0")
        logger.info(f"Orchestrator queue depth: {queue_depth}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Router warmed up",
                "queue_depth": queue_depth
            })
        }
    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }