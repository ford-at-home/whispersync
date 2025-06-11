"""AWS CDK stack for WhisperSync infrastructure."""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3n,
    aws_iam as iam,
)
from constructs import Construct
from pathlib import Path


class McpStack(Stack):
    """CDK stack that provisions S3, Lambda, and permissions."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Initialize the stack and set up resources."""
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(self, "VoiceMcpBucket",
                           bucket_name="voice-mcp",
                           removal_policy=s3.RemovalPolicy.DESTROY,
                           auto_delete_objects=True)

        lambda_fn = _lambda.Function(
            self,
            "McpAgentRouterLambda",
            function_name="mcpAgentRouterLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="router_handler.lambda_handler",
            code=_lambda.Code.from_asset(str(Path(__file__).resolve().parent.parent / "lambda")),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
            },
        )

        # Permissions
        bucket.grant_read_write(lambda_fn)

        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"]
            )
        )
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"]
            )
        )

        # S3 notifications
        notification = s3n.LambdaDestination(lambda_fn)
        bucket.add_event_notification(s3.EventType.OBJECT_CREATED,
                                      notification,
                                      s3.NotificationKeyFilter(prefix="transcripts/"))

