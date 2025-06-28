#!/usr/bin/env python3
"""
WhisperSync CDK Application Entry Point

This is the main entry point for deploying the WhisperSync infrastructure.
The CDK app orchestrates the deployment of all AWS resources needed for
the voice memo processing pipeline.

DEPLOYMENT STRATEGY:

1. Single Stack Architecture:
   - WHY: Simple deployment model for a focused application
   - TRADEOFFS: Less flexibility than multi-stack, but easier to manage
   - FUTURE: Could split into networking, compute, and storage stacks

2. Stack Naming Convention:
   - WHY: Predictable resource names for cross-references and automation
   - PATTERN: "McpStack" creates resources with consistent prefixes

3. Environment Handling:
   - WHY: Enable dev/staging/prod deployments with environment-specific config
   - HOW: CDK context and environment variables (future enhancement)

OPERATIONAL CONSIDERATIONS:

1. Deployment Process:
   - `cdk bootstrap` (one-time): Sets up CDK deployment infrastructure
   - `cdk deploy`: Deploys/updates the stack
   - `cdk destroy`: Tears down all resources (careful in production)

2. Change Management:
   - CDK diff: Preview changes before deployment  
   - CloudFormation: Manages resource lifecycle and rollbacks
   - Resource dependencies: CDK handles proper ordering

3. Monitoring Integration:
   - Stack events visible in CloudFormation console
   - CDK metadata tags for cost allocation and governance
   - Resource drift detection via CloudFormation

SECURITY POSTURE:

1. IAM: Least privilege principles applied to all resources
2. Encryption: Data at rest and in transit protection
3. Network: No public endpoints, AWS PrivateLink where applicable
4. Secrets: AWS Secrets Manager for sensitive credentials

COST MANAGEMENT:

1. Resource Tagging: Automatic cost allocation and tracking
2. Lifecycle Policies: Prevent resource accumulation
3. Right-sizing: Optimized resource configurations
4. Usage Monitoring: CloudWatch metrics for cost optimization
"""

import aws_cdk as cdk
from mcp_stack import McpStack

# Create CDK application instance
# This orchestrates the deployment of all infrastructure resources
app = cdk.App()

# Deploy the main WhisperSync stack
# Contains S3, Lambda, IAM, and event routing infrastructure
stack = McpStack(app, "McpStack")

# Apply common tags for governance and cost allocation
# WHY: Enable cost tracking, compliance reporting, and resource management
cdk.Tags.of(stack).add("Project", "WhisperSync")
cdk.Tags.of(stack).add("Component", "VoiceMemoProcessing") 
cdk.Tags.of(stack).add("Environment", "dev")  # TODO: Make environment-aware
cdk.Tags.of(stack).add("Owner", "AI-Agents-Team")
cdk.Tags.of(stack).add("CostCenter", "R&D")

# Synthesize CloudFormation templates
# This generates the JSON/YAML that CloudFormation will deploy
app.synth()
