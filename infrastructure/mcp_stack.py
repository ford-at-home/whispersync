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

import os
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    aws_kms as kms,
    aws_ec2 as ec2,
    Duration,  # For timeout configuration
    RemovalPolicy,  # For lifecycle management
)
from constructs import Construct
from pathlib import Path


class McpStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, environment: str = "development", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment
        self.is_production = environment == "production"

        # KMS Key for enhanced encryption (production only)
        kms_key = None
        if self.is_production:
            kms_key = kms.Key(
                self, "WhisperSyncKMSKey",
                description="WhisperSync encryption key for sensitive voice data",
                enable_key_rotation=True,
                removal_policy=RemovalPolicy.RETAIN
            )
        
        # S3 Bucket for transcript storage and agent output
        # WHY S3: Durable storage for voice transcripts, cost-effective for infrequent access,
        # native event notifications, supports hierarchical organization via prefixes
        bucket_name = os.environ.get('TRANSCRIPT_BUCKET_NAME', 'macbook-transcriptions')
        if self.env_name != "production":
            bucket_name = f"{bucket_name}-{self.env_name}"
        
        bucket = s3.Bucket(
            self, 
            "VoiceMcpBucket",
            bucket_name=bucket_name,
            
            # ENHANCED SECURITY: KMS encryption for production, AES-256 for dev
            encryption=(
                s3.BucketEncryption.KMS if self.is_production 
                else s3.BucketEncryption.S3_MANAGED
            ),
            encryption_key=kms_key if self.is_production else None,
            
            # LIFECYCLE: Auto-delete for development/testing environments
            removal_policy=(
                RemovalPolicy.RETAIN if self.is_production 
                else RemovalPolicy.DESTROY
            ),
            auto_delete_objects=not self.is_production,
            
            # VERSIONING: Enabled for production data protection
            versioned=self.is_production,
            
            # PUBLIC ACCESS: Blocked by default (secure by default)
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            
            # NOTIFICATION CONFIGURATION: Enable event notifications
            event_bridge_enabled=True
        )
        
        # Bucket policy for enhanced security
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[
                    bucket.bucket_arn,
                    bucket.arn_for_objects("*")
                ],
                conditions={
                    "Bool": {"aws:SecureTransport": "false"}
                }
            )
        )

        # SNS Topic for alerts and notifications
        alert_topic = sns.Topic(
            self, "WhisperSyncAlerts",
            topic_name=f"whispersync-alerts-{self.env_name}",
            display_name="WhisperSync System Alerts"
        )
        
        # Lambda Function for agent routing and execution
        lambda_fn = _lambda.Function(
            self,
            "McpAgentRouterLambda",
            function_name=f"mcpAgentRouterLambda-{self.env_name}",
            
            # RUNTIME: Python 3.11 for latest features and performance
            runtime=_lambda.Runtime.PYTHON_3_11,
            
            # HANDLER: Entry point in router_handler.py (full orchestrator version)
            handler="router_handler.lambda_handler",
            
            # CODE: References lambda_fn directory relative to this file
            code=_lambda.Code.from_asset(
                str(Path(__file__).resolve().parent.parent / "lambda_fn")
            ),
            
            # PERFORMANCE: Environment-specific configuration
            timeout=Duration.minutes(5 if self.is_production else 3),
            memory_size=512 if self.is_production else 256,
            
            # ENVIRONMENT: Comprehensive runtime configuration
            environment={
                "TRANSCRIPT_BUCKET_NAME": bucket.bucket_name,
                "BUCKET_NAME": bucket.bucket_name,  # Keep for backward compatibility
                "WHISPERSYNC_ENV": self.env_name,
                "LOG_LEVEL": "WARNING" if self.is_production else "INFO",
                "ENABLE_METRICS": "true",
                "ENABLE_XRAY": "true" if self.is_production else "false",
                "METRICS_NAMESPACE": "WhisperSync"
            },
            
            # MONITORING: X-Ray tracing for production
            tracing=(
                _lambda.Tracing.ACTIVE if self.is_production 
                else _lambda.Tracing.DISABLED
            ),
            
            # CONCURRENCY: Set reserved concurrency for production
            reserved_concurrent_executions=(
                10 if self.is_production else None
            ),
            
            # SECURITY: Enhanced configuration
            description=f"WhisperSync voice memo processing ({self.env_name})",
        )
        
        # Health Check Lambda Function
        health_check_fn = _lambda.Function(
            self,
            "HealthCheckLambda",
            function_name=f"whispersync-health-check-{self.env_name}",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="simple_router.health_check_handler",
            code=_lambda.Code.from_asset(
                str(Path(__file__).resolve().parent.parent / "lambda_fn")
            ),
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "TRANSCRIPT_BUCKET_NAME": bucket.bucket_name,
                "BUCKET_NAME": bucket.bucket_name,  # Keep for backward compatibility
                "WHISPERSYNC_ENV": self.env_name
            },
            description=f"WhisperSync health check endpoint ({self.env_name})"
        )

        # IAM PERMISSIONS - Enhanced Security with Least Privilege
        
        # S3 Access: Read transcripts, write agent outputs
        bucket.grant_read_write(lambda_fn)
        bucket.grant_read(health_check_fn)  # Health check only needs read access
        
        # Bedrock Access: Restricted to specific models and actions
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.*"
            ]
        )
        lambda_fn.add_to_role_policy(bedrock_policy)
        health_check_fn.add_to_role_policy(bedrock_policy)
        
        # Secrets Manager Access: Restricted to WhisperSync secrets
        secrets_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["secretsmanager:GetSecretValue"],
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:github/personal_token*",
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:whispersync/*"
            ]
        )
        lambda_fn.add_to_role_policy(secrets_policy)
        
        # CloudWatch Metrics: Custom metrics publishing
        metrics_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudwatch:PutMetricData"
            ],
            resources=["*"],
            conditions={
                "StringEquals": {
                    "cloudwatch:namespace": "WhisperSync"
                }
            }
        )
        lambda_fn.add_to_role_policy(metrics_policy)
        health_check_fn.add_to_role_policy(metrics_policy)
        
        # CloudWatch Logs: Automatic via Lambda service
        # WHY: Essential for debugging, monitoring, and alerting
        
        # X-Ray Tracing: Not explicitly enabled (can be added)
        # WHY: Useful for performance analysis and debugging complex agent workflows
        # tracing=_lambda.Tracing.ACTIVE,  # Uncomment to enable

        # MONITORING AND ALERTING
        
        # CloudWatch Alarms for Lambda errors
        error_alarm = cloudwatch.Alarm(
            self, "LambdaErrorAlarm",
            alarm_name=f"whispersync-lambda-errors-{self.env_name}",
            metric=lambda_fn.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum"
            ),
            threshold=3,
            evaluation_periods=2,
            alarm_description="WhisperSync Lambda function error rate too high"
        )
        error_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(alert_topic)
        )
        
        # CloudWatch Alarm for Lambda duration
        duration_alarm = cloudwatch.Alarm(
            self, "LambdaDurationAlarm",
            alarm_name=f"whispersync-lambda-duration-{self.env_name}",
            metric=lambda_fn.metric_duration(
                period=Duration.minutes(5),
                statistic="Average"
            ),
            threshold=240000,  # 4 minutes (close to 5-minute timeout)
            evaluation_periods=2,
            alarm_description="WhisperSync Lambda function duration too high"
        )
        duration_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(alert_topic)
        )
        
        # S3 EVENT NOTIFICATIONS - Event-Driven Processing
        notification = s3n.LambdaDestination(lambda_fn)
        
        # Event Filter: Only process transcript uploads
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            notification,
            s3.NotificationKeyFilter(
                prefix="transcripts/",
                suffix=".txt"
            )
        )
        
        # OUTPUTS: CDK stack outputs for external integration
        
        CfnOutput(
            self, "BucketName",
            value=bucket.bucket_name,
            description="S3 bucket for voice memo transcripts",
            export_name=f"WhisperSync-BucketName-{self.env_name}"
        )
        
        CfnOutput(
            self, "LambdaFunctionName", 
            value=lambda_fn.function_name,
            description="Lambda function handling agent routing",
            export_name=f"WhisperSync-LambdaFunction-{self.env_name}"
        )
        
        CfnOutput(
            self, "HealthCheckFunctionName",
            value=health_check_fn.function_name,
            description="Health check Lambda function",
            export_name=f"WhisperSync-HealthCheck-{self.env_name}"
        )
        
        CfnOutput(
            self, "AlertTopicArn",
            value=alert_topic.topic_arn,
            description="SNS topic for system alerts",
            export_name=f"WhisperSync-AlertTopic-{self.env_name}"
        )
        
        if kms_key:
            CfnOutput(
                self, "KMSKeyId",
                value=kms_key.key_id,
                description="KMS key for encryption",
                export_name=f"WhisperSync-KMSKey-{self.env_name}"
            )
        
        # Store references for other methods
        self.bucket = bucket
        self.lambda_fn = lambda_fn
        self.health_check_fn = health_check_fn
        self.alert_topic = alert_topic
        self.kms_key = kms_key

