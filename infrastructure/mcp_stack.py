"""
WhisperSync MCP Stack - Voice Memo Processing Pipeline Infrastructure

This CDK stack defines the AWS resources for a serverless voice memo processing pipeline
that automatically routes transcripts to AI agents for intelligent actions.

ARCHITECTURAL DECISIONS:

1. Event-Driven Architecture: 
   - WHY: Enables real-time processing with minimal latency between voice memo upload
     and agent action. Decouples transcription from agent processing.
   - HOW: S3 triggers Lambda on object creation

2. Serverless Pattern:
   - WHY: Cost-effective for sporadic voice memo uploads, zero idle costs,
     automatic scaling, minimal operational overhead
   - HOW: Lambda functions process on-demand

3. Agent Routing via Path Convention:
   - WHY: Simple, predictable routing without complex classification logic
   - HOW: S3 key paths like "transcripts/work/" determine agent selection

SECURITY CONSIDERATIONS:

1. Principle of Least Privilege: Each service has minimal required permissions
2. Resource-Based Security: IAM policies restrict access to specific resources
3. Encryption: S3 bucket uses default encryption, Lambda has encrypted environment
4. Secrets Management: GitHub tokens stored in AWS Secrets Manager, not environment

SCALING DECISIONS:

1. Lambda Concurrency: Default limits handle expected voice memo volume
2. S3 Event Filtering: Reduces unnecessary Lambda invocations 
3. Batch Processing: Future enhancement for bulk transcript processing

COST OPTIMIZATION:

1. Pay-per-use: No fixed infrastructure costs
2. S3 Standard Storage: Optimal for frequently accessed transcripts
3. Lambda Memory: Right-sized for transcript processing workload
4. Auto-delete Objects: Prevents accumulation of old transcripts
"""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    Duration,  # For timeout configuration
    RemovalPolicy,  # For lifecycle management
)
from constructs import Construct
from pathlib import Path


class McpStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for transcript storage and agent output
        # WHY S3: Durable storage for voice transcripts, cost-effective for infrequent access,
        # native event notifications, supports hierarchical organization via prefixes
        bucket = s3.Bucket(
            self, 
            "VoiceMcpBucket",
            bucket_name="voice-mcp",  # Fixed name for predictable cross-service access
            
            # SECURITY: Server-side encryption enabled by default (AES-256)
            # encryption=s3.BucketEncryption.S3_MANAGED,  # Default behavior
            
            # LIFECYCLE: Auto-delete for development/testing environments
            # WHY: Prevents accumulation of test data, reduces storage costs
            # PRODUCTION: Should use lifecycle policies instead of auto-delete
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            
            # VERSIONING: Disabled for cost optimization
            # WHY: Voice transcripts are immutable once processed
            versioned=False,
            
            # PUBLIC ACCESS: Blocked by default (secure by default)
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        # Lambda Function for agent routing and execution
        # WHY Lambda: Serverless execution model matches sporadic voice memo pattern,
        # automatic scaling, pay-per-execution, managed runtime updates
        lambda_fn = _lambda.Function(
            self,
            "McpAgentRouterLambda",
            function_name="mcpAgentRouterLambda",  # Fixed name for monitoring/logging
            
            # RUNTIME: Python 3.11 for latest features and performance
            # WHY: Strands SDK compatibility, async/await support, type hints
            runtime=_lambda.Runtime.PYTHON_3_11,
            
            # HANDLER: Entry point in router_handler.py
            handler="router_handler.lambda_handler",
            
            # CODE: References lambda_fn directory relative to this file
            # WHY: Keeps code separate from infrastructure, enables independent testing
            code=_lambda.Code.from_asset(
                str(Path(__file__).resolve().parent.parent / "lambda_fn")
            ),
            
            # TIMEOUT: Default 3 seconds may be too short for AI agent processing
            # WHY: Strands agent execution can take 10-30 seconds for complex operations
            timeout=Duration.minutes(5),  # Sufficient for most agent operations
            
            # MEMORY: 128MB default may be insufficient for AI processing
            # WHY: Strands SDK, boto3, and AI model inference need adequate memory
            memory_size=512,  # Balanced performance and cost
            
            # ENVIRONMENT: Runtime configuration
            environment={
                "BUCKET_NAME": bucket.bucket_name,  # S3 bucket reference
                # Future: Add STRANDS_API_ENDPOINT, OPENTELEMETRY_ENDPOINT
            },
            
            # RESERVED CONCURRENCY: Not set (uses account default)
            # WHY: Voice memos are sporadic, unlikely to hit concurrency limits
            # FUTURE: Set to prevent runaway costs if needed
        )

        # IAM PERMISSIONS - Principle of Least Privilege
        
        # S3 Access: Read transcripts, write agent outputs
        # WHY: Lambda needs to read incoming transcripts and store agent responses
        bucket.grant_read_write(lambda_fn)
        
        # Bedrock Access: AI model invocation for agent processing
        # WHY: Strands agents use AWS Bedrock for LLM inference
        # SECURITY: Wildcard resource acceptable as Bedrock controls access via IAM
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"  # For streaming responses
                ],
                resources=["*"]  # Bedrock models are region-specific, * is appropriate
            )
        )
        
        # Secrets Manager Access: GitHub tokens and API keys
        # WHY: Secure storage of sensitive credentials, automatic rotation capability
        # SCOPE: Could be narrowed to specific secret ARNs in production
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"]  # FUTURE: Restrict to specific secret ARNs
            )
        )
        
        # CloudWatch Logs: Automatic via Lambda service
        # WHY: Essential for debugging, monitoring, and alerting
        
        # X-Ray Tracing: Not explicitly enabled (can be added)
        # WHY: Useful for performance analysis and debugging complex agent workflows
        # tracing=_lambda.Tracing.ACTIVE,  # Uncomment to enable

        # S3 EVENT NOTIFICATIONS - Event-Driven Processing
        
        # Lambda Destination: Route S3 events to Lambda function
        notification = s3n.LambdaDestination(lambda_fn)
        
        # Event Filter: Only process transcript uploads
        # WHY: Prevents unnecessary Lambda invocations from other S3 operations,
        # reduces costs and improves performance
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,  # Trigger on new objects only
            notification,
            s3.NotificationKeyFilter(
                prefix="transcripts/"  # Only files in transcripts/ directory
                # suffix=".txt"  # Could add file type filtering
            )
        )
        
        # OUTPUTS: CDK stack outputs for reference by other stacks or services
        # WHY: Enable cross-stack references and external service integration
        
        # Output bucket name for external reference
        # Used by: Local transcription uploader, monitoring systems
        # CfnOutput(
        #     self, "BucketName",
        #     value=bucket.bucket_name,
        #     description="S3 bucket for voice memo transcripts"
        # )
        
        # Output Lambda function name for monitoring setup
        # CfnOutput(
        #     self, "LambdaFunctionName", 
        #     value=lambda_fn.function_name,
        #     description="Lambda function handling agent routing"
        # )

