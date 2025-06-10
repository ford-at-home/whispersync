# Lambda

This folder contains the `router_handler.py` entry point used by AWS Lambda. The function listens for S3 `ObjectCreated` events on the `transcripts/` prefix and routes each transcript to the appropriate Strands agent. Results are written back to `outputs/` in the same bucket.

Use the provided infrastructure stack to deploy this Lambda with the required permissions.
