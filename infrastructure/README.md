# Infrastructure

AWS CDK app that provisions the resources for the WhisperSync system.
It builds an S3 bucket and a Lambda function capable of routing
transcripts to the correct agent.

- S3 bucket `voice-mcp` with notifications on the `transcripts/` prefix
- Lambda function `mcpAgentRouterLambda` which routes transcripts to Strands agents
- IAM permissions for S3, Bedrock model invocation, and Secrets Manager access

Run ``cdk deploy`` from this directory to deploy the stack to your AWS
account.  The stack is intentionally minimal so it can be extended for
additional agents or storage locations.
