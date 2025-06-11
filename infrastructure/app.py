#!/usr/bin/env python3
"""CDK application entry point.

This script synthesizes the :class:`~McpStack` which provisions all AWS
resources for the WhisperSync system.
"""

import aws_cdk as cdk
from mcp_stack import McpStack

app = cdk.App()
McpStack(app, "McpStack")
app.synth()
