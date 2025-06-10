# Infrastructure

AWS CDK app that provisions the resources for the Voice MCP system:

- S3 bucket `voice-mcp` with notifications on the `transcripts/` prefix
- Lambda function `mcpAgentRouterLambda` which routes transcripts to Strands agents
- IAM permissions for S3, Bedrock model invocation, and Secrets Manager access

Run `cdk deploy` inside this directory to deploy the stack.
