# Lambda

This folder contains the ``router_handler.py`` entry point used by the
deployed Lambda function.  Whenever a transcript text file is uploaded to
S3 under the ``transcripts/`` prefix, the Lambda downloads that file,
determines which agent should handle it and invokes the agent.  Responses
are stored back in the ``outputs/`` prefix.

The Lambda runs with permissions created by the infrastructure stack
allowing it to read and write from S3, call models via Bedrock and fetch
secrets for the GitHub agent.
