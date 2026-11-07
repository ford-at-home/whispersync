#!/usr/bin/env python3
"""
Enhanced WhisperSync CDK Application

This application deploys the enhanced WhisperSync infrastructure with:
- SQS queues for decoupling
- DynamoDB for Theory of Mind
- Enhanced security and monitoring
- Cost optimization features
- Scalability patterns

Usage:
    # Deploy development environment
    cdk deploy WhisperSyncDev --context environment=development

    # Deploy production environment
    cdk deploy WhisperSyncProd --context environment=production --context enable_vpc=true

    # Deploy with specific features
    cdk deploy --context enable_eleven_labs=true --context enable_vpc=false
"""

import os
from aws_cdk import App, Environment, Tags
from enhanced_mcp_stack import EnhancedMcpStack

# Get AWS account and region from environment
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")

app = App()

# Get context variables
environment = app.node.try_get_context("environment") or "development"
enable_vpc = app.node.try_get_context("enable_vpc") == "true"
enable_eleven_labs = app.node.try_get_context("enable_eleven_labs") != "false"  # Default true

# Development Stack
if environment == "development" or environment == "all":
    dev_stack = EnhancedMcpStack(
        app, 
        "WhisperSyncDev",
        env=Environment(account=account, region=region),
        environment="development",
        enable_vpc=False,  # No VPC in dev to save costs
        enable_eleven_labs=enable_eleven_labs,
        description="WhisperSync Development Environment - Enhanced Architecture"
    )
    
    # Tag all resources in dev stack
    Tags.of(dev_stack).add("CostCenter", "Development")
    Tags.of(dev_stack).add("Owner", "DevTeam")
    Tags.of(dev_stack).add("AutoShutdown", "true")  # For cost saving automation

# Production Stack
if environment == "production" or environment == "all":
    prod_stack = EnhancedMcpStack(
        app, 
        "WhisperSyncProd",
        env=Environment(account=account, region=region),
        environment="production",
        enable_vpc=enable_vpc,  # VPC optional based on security requirements
        enable_eleven_labs=enable_eleven_labs,
        description="WhisperSync Production Environment - Enhanced Architecture"
    )
    
    # Production tags
    Tags.of(prod_stack).add("CostCenter", "Production")
    Tags.of(prod_stack).add("Owner", "PlatformTeam")
    Tags.of(prod_stack).add("Compliance", "HIPAA")  # If handling health data
    Tags.of(prod_stack).add("DataClassification", "Confidential")
    Tags.of(prod_stack).add("BackupRequired", "true")

# Staging Stack (optional)
if environment == "staging":
    staging_stack = EnhancedMcpStack(
        app, 
        "WhisperSyncStaging",
        env=Environment(account=account, region=region),
        environment="staging",
        enable_vpc=enable_vpc,
        enable_eleven_labs=enable_eleven_labs,
        description="WhisperSync Staging Environment - Pre-production Testing"
    )
    
    Tags.of(staging_stack).add("CostCenter", "QA")
    Tags.of(staging_stack).add("Owner", "QATeam")

# Multi-region deployment example (commented out)
# To deploy in multiple regions, uncomment and modify:
"""
# US West deployment
west_stack = EnhancedMcpStack(
    app, 
    "WhisperSyncWest",
    env=Environment(account=account, region="us-west-2"),
    environment=environment,
    enable_vpc=enable_vpc,
    enable_eleven_labs=enable_eleven_labs,
    description="WhisperSync West Region - Disaster Recovery"
)

# EU deployment for GDPR compliance
eu_stack = EnhancedMcpStack(
    app, 
    "WhisperSyncEU",
    env=Environment(account=account, region="eu-west-1"),
    environment=environment,
    enable_vpc=True,  # Always use VPC in EU for compliance
    enable_eleven_labs=enable_eleven_labs,
    description="WhisperSync EU Region - GDPR Compliance"
)
"""

# Print deployment information
print(f"""
WhisperSync Enhanced Infrastructure Deployment
=============================================
Environment: {environment}
Region: {region}
Account: {account}
VPC Enabled: {enable_vpc}
ElevenLabs Enabled: {enable_eleven_labs}

To deploy:
  cdk deploy WhisperSync{environment.title()}

To destroy:
  cdk destroy WhisperSync{environment.title()}

For more options:
  cdk deploy --help
""")

app.synth()