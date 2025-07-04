"""Lambda entry point for WhisperSync voice memo processing.

# ARCHITECTURAL OVERVIEW:
# This Lambda function serves as the primary entry point for the WhisperSync pipeline.
# It's triggered by S3 events when new voice transcripts are uploaded to the bucket.

# WORKFLOW:
# 1. S3 Event → Lambda → Download Transcript → Route via Orchestrator → Process → Store Results
# 2. The orchestrator determines which agent(s) should handle the transcript
# 3. Results are written back to S3 with metadata for downstream processing

# WHY THIS DESIGN:
# - Serverless architecture for cost efficiency and automatic scaling
# - Event-driven processing ensures immediate response to new transcripts
# - Centralized routing through orchestrator enables intelligent multi-agent coordination
# - S3 as the data store provides durability and easy integration with other AWS services

# ERROR HANDLING PHILOSOPHY:
# - Comprehensive error logging to S3 for debugging without losing context
# - Graceful degradation when agents fail - partial results are better than none
# - Request IDs throughout for distributed tracing
"""

import json
import logging
import os
import datetime
import time
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

# Import the orchestrator agent for intelligent routing
# WHY TRY/EXCEPT: Lambda layers may place Python packages in /opt/python,
# which isn't in the default sys.path. This ensures we can find our agents
# regardless of the deployment method (direct upload vs. layers).
try:
    from agents.orchestrator_agent import route_to_agent, get_orchestrator_agent
except ImportError:
    # Fallback imports for AWS Lambda environment where dependencies are in layers
    import sys

    sys.path.insert(0, "/opt/python")
    from agents.orchestrator_agent import route_to_agent, get_orchestrator_agent

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client at module level for connection reuse across invocations
# WHY: Lambda containers can be reused, so initializing clients outside the handler
# function allows AWS SDK to reuse connections, reducing latency
s3 = boto3.client("s3")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for processing voice transcripts.

    This is the primary entry point invoked by AWS Lambda when S3 events occur.
    It orchestrates the entire processing pipeline from S3 event to agent execution.

    Args:
        event: S3 event containing bucket and key information. Expected structure:
               {"Records": [{"s3": {"bucket": {"name": "..."}, "object": {"key": "..."}}}]}
        context: Lambda context object containing request_id, function_name, etc.

    Returns:
        Dictionary with processing status and results:
        - statusCode: HTTP status code (200 for success, 500 for errors)
        - body: JSON string with detailed results or error information

    WHY THIS STRUCTURE:
    - Follows AWS Lambda's expected response format for API Gateway integration
    - Includes comprehensive error details for debugging distributed systems
    - Returns partial results even on failure for resilience
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract S3 information from event
        # NOTE: We only process the first record. S3 typically sends one record per event,
        # but the Records array structure allows for future batching if needed
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]  # Format: transcripts/{agent_type}/{timestamp}.txt

        logger.info(f"Processing transcript from s3://{bucket}/{key}")

        # Download transcript from S3
        # WHY SEPARATE TRY/CATCH: S3 download failures are different from processing failures.
        # We want to distinguish between "couldn't get the data" vs "couldn't process the data"
        # for monitoring and alerting purposes.
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            transcript = obj["Body"].read().decode("utf-8")
            logger.info(f"Downloaded transcript, {len(transcript)} characters")
        except Exception as e:
            logger.error(f"Failed to download transcript: {e}")
            # Return early with specific S3 error - no point continuing without data
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {"error": "Failed to download transcript", "details": str(e)}
                ),
            }

        # Route transcript through orchestrator
        # WHY ORCHESTRATOR: Instead of hardcoding routing logic here, we delegate to
        # the orchestrator agent which uses AI to intelligently determine which
        # specialized agent(s) should process this transcript. This allows for:
        # - Dynamic routing based on content analysis
        # - Multi-agent coordination for complex transcripts
        # - Easy addition of new agents without modifying Lambda code
        try:
            logger.info("Routing transcript through orchestrator")
            result = route_to_agent(
                transcript=transcript, 
                source_key=key,  # Provides routing hints based on S3 path structure
                bucket=bucket
            )

            logger.info(
                f"Routing complete. Primary agent: "
                f"{result.get('routing_decision', {}).get('primary_agent')}"
            )

            # Extract processing results
            processing_results = result.get("processing_results", {})
            routing_decision = result.get("routing_decision", {})

            # Prepare output for S3
            # WHY THIS STRUCTURE: We capture comprehensive metadata for:
            # - Debugging: Can trace from source transcript to final results
            # - Analytics: Understand routing patterns and agent performance
            # - Monitoring: Track success rates and failure modes
            output_data = {
                "source_key": key,
                "processed_at": context.request_id,  # Use request_id as unique identifier
                "routing_decision": routing_decision,  # Which agent(s) were chosen and why
                "agent_results": processing_results,   # Actual output from each agent
                "success": all(  # Overall success only if ALL agents succeeded
                    "error" not in r
                    and ("status" not in r or r.get("status") != "failed")
                    for r in processing_results.values()
                ),
            }

            # Write results back to S3
            # WHY THIS PATH STRUCTURE: Mirror the input structure but in 'outputs/' prefix
            # This maintains the agent type in the path for easy filtering/querying
            # Example: transcripts/work/2024-01-01.txt → outputs/work/2024-01-01_response.json
            output_key = key.replace("transcripts/", "outputs/").replace(
                ".txt", "_response.json"
            )

            s3.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=json.dumps(output_data, indent=2).encode("utf-8"),
                ContentType="application/json",
                # WHY METADATA: S3 object metadata enables efficient querying without
                # downloading objects. Can filter by agent type, trace requests, etc.
                Metadata={
                    "source_transcript": key,
                    "primary_agent": routing_decision.get("primary_agent", "unknown"),
                    "request_id": context.request_id,
                },
            )

            logger.info(f"Wrote results to s3://{bucket}/{output_key}")

            # Return success response
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Transcript processed successfully",
                        "source_key": key,
                        "output_key": output_key,
                        "routing": routing_decision,
                        "agents_used": list(processing_results.keys()),
                        "success": output_data["success"],
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)

            # Write error to S3 for debugging
            # WHY PERSIST ERRORS: In serverless architectures, logs can be ephemeral.
            # Storing errors in S3 ensures we never lose debugging information and
            # can analyze failure patterns over time.
            error_key = key.replace("transcripts/", "errors/").replace(
                ".txt", "_error.json"
            )

            error_data = {
                "source_key": key,
                "error": str(e),
                "error_type": type(e).__name__,
                "request_id": context.request_id,
            }

            try:
                s3.put_object(
                    Bucket=bucket,
                    Key=error_key,
                    Body=json.dumps(error_data, indent=2).encode("utf-8"),
                    ContentType="application/json",
                )
            except:
                # WHY SWALLOW EXCEPTION: If we can't log the error, we still want to
                # return the error response to the caller. Double-failure shouldn't
                # hide the original error.
                pass  # Don't fail if error logging fails

            return {
                "statusCode": 500,
                "body": json.dumps(
                    {"error": "Processing failed", "details": str(e), "source_key": key}
                ),
            }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Unexpected error", "details": str(e)}),
        }


def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Health check endpoint for monitoring and load balancer probes.
    
    This handler performs comprehensive system health checks including:
    - S3 connectivity and bucket access
    - Agent initialization status
    - External service availability
    - System resource utilization
    
    Returns:
        HTTP response with health status and detailed service information
        
    WHY HEALTH CHECKS:
    - Enable load balancer health probes for high availability
    - Provide operational visibility into system components
    - Support automated alerting and recovery procedures
    - Validate infrastructure changes before production traffic
    """
    start_time = time.time()
    
    try:
        logger.info("Performing health check")
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "request_id": context.request_id,
            "services": {},
            "metrics": {}
        }
        
        # Test S3 connectivity
        try:
            bucket_name = os.environ.get('BUCKET_NAME', 'voice-mcp')
            s3.head_bucket(Bucket=bucket_name)
            health_status["services"]["s3"] = {
                "status": "available",
                "bucket": bucket_name
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            health_status["services"]["s3"] = {
                "status": "error",
                "error": error_code
            }
            if error_code in ['403', 'NoSuchBucket']:
                health_status["status"] = "degraded"
            else:
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["services"]["s3"] = {
                "status": "error", 
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
        # Test agent initialization
        try:
            orchestrator = get_orchestrator_agent()
            agent_status = {
                "orchestrator": orchestrator is not None,
                "work_agent": orchestrator.work_agent is not None if orchestrator else False,
                "memory_agent": orchestrator.memory_agent is not None if orchestrator else False,
                "github_agent": orchestrator.github_agent is not None if orchestrator else False
            }
            
            health_status["services"]["agents"] = {
                "status": "initialized" if all(agent_status.values()) else "partial",
                "details": agent_status
            }
            
            if not orchestrator:
                health_status["status"] = "degraded"
                
        except Exception as e:
            health_status["services"]["agents"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Test Bedrock availability (optional)
        try:
            bedrock = boto3.client('bedrock-runtime')
            # Simple model list call to test connectivity
            bedrock.list_foundation_models()
            health_status["services"]["bedrock"] = {"status": "available"}
        except Exception as e:
            health_status["services"]["bedrock"] = {
                "status": "error",
                "error": str(e)
            }
            # Bedrock unavailable is degraded, not unhealthy
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
        
        # Performance metrics
        health_check_time = time.time() - start_time
        health_status["metrics"] = {
            "health_check_duration_ms": round(health_check_time * 1000, 2),
            "memory_usage_mb": context.memory_limit_in_mb,
            "remaining_time_ms": context.get_remaining_time_in_millis()
        }
        
        # Determine HTTP status code based on health
        if health_status["status"] == "healthy":
            status_code = 200
        elif health_status["status"] == "degraded":
            status_code = 200  # Still healthy enough to serve traffic
        else:
            status_code = 503  # Service unavailable
        
        logger.info(f"Health check completed: {health_status['status']} in {health_check_time:.2f}s")
        
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
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "request_id": getattr(context, 'request_id', 'unknown')
            }, indent=2),
            "headers": {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            }
        }


def warmup_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Warmup handler to pre-initialize agents.

    This can be called periodically to keep the Lambda warm and agents initialized.
    
    WHY WARMUP:
    - Lambda cold starts can be slow, especially when loading AI models
    - Pre-initializing agents reduces latency for actual requests
    - Can be triggered by CloudWatch Events on a schedule
    
    USAGE:
    - Set up CloudWatch Events rule to call this every 5-10 minutes
    - Ensures consistent low-latency responses for voice memos
    """
    try:
        logger.info("Warming up agents")

        # Initialize orchestrator (which initializes all agents)
        orchestrator = get_orchestrator_agent()

        # Verify agents are available
        # WHY CHECK EACH AGENT: Different agents may have different initialization
        # requirements (e.g., GitHub agent needs API token). This helps identify
        # which specific components might be failing.
        agents_status = {
            "orchestrator": orchestrator is not None,
            "work_agent": (
                orchestrator.work_agent is not None if orchestrator else False
            ),
            "memory_agent": (
                orchestrator.memory_agent is not None if orchestrator else False
            ),
            "github_agent": (
                orchestrator.github_agent is not None if orchestrator else False
            ),
        }

        logger.info(f"Agent status: {agents_status}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Warmup complete", "agents_ready": agents_status}
            ),
        }

    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Warmup failed", "details": str(e)}),
        }


# Legacy handler mapping for backward compatibility
# WHY LEGACY HANDLERS: These support the original design where each agent had
# its own Lambda function. By maintaining these, we can migrate gradually
# without breaking existing S3 event configurations.
def handle_work_transcript(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Legacy handler for work transcripts.
    
    Transforms the S3 key to ensure routing to work agent, then delegates
    to the main handler. This maintains compatibility with original S3 event
    configurations that might still be pointing to agent-specific functions.
    """
    # Modify event to ensure it routes to work agent
    if "Records" in event and event["Records"]:
        event["Records"][0]["s3"]["object"]["key"] = event["Records"][0]["s3"][
            "object"
        ]["key"].replace("transcripts/", "transcripts/work/")
    return lambda_handler(event, context)


def handle_memory_transcript(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Legacy handler for memory transcripts."""
    # Modify event to ensure it routes to memory agent
    if "Records" in event and event["Records"]:
        event["Records"][0]["s3"]["object"]["key"] = event["Records"][0]["s3"][
            "object"
        ]["key"].replace("transcripts/", "transcripts/memories/")
    return lambda_handler(event, context)


def handle_github_transcript(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Legacy handler for GitHub idea transcripts."""
    # Modify event to ensure it routes to GitHub agent
    if "Records" in event and event["Records"]:
        event["Records"][0]["s3"]["object"]["key"] = event["Records"][0]["s3"][
            "object"
        ]["key"].replace("transcripts/", "transcripts/github_ideas/")
    return lambda_handler(event, context)
