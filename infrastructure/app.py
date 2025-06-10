#!/usr/bin/env python3
import aws_cdk as cdk
from mcp_stack import McpStack

app = cdk.App()
McpStack(app, "McpStack")
app.synth()
