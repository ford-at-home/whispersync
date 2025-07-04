# WhisperSync Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Production Deployment](#production-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Security Setup](#security-setup)
7. [Monitoring & Observability](#monitoring--observability)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

## Overview

WhisperSync is a voice-to-action AI platform that processes iPhone voice memos through specialized agents. This guide covers deployment from development to production.

### Architecture Summary

```
iPhone Voice Memo → Local Whisper → S3 → Lambda → AI Agents → Actions
```

**Key Components:**
- **S3 Bucket**: Stores transcripts and outputs
- **Lambda Function**: Routes transcripts to appropriate agents
- **AI Agents**: Specialized processors (Work, Memory, GitHub)
- **Monitoring**: CloudWatch, X-Ray, custom metrics

## Prerequisites

### Required Tools
- **AWS CLI**: Version 2.0+ configured with appropriate permissions
- **AWS CDK**: Version 2.0+ for infrastructure as code
- **Python**: Version 3.11+ for Lambda runtime compatibility
- **Node.js**: Version 18+ for CDK operations
- **Git**: For version control and deployment

### AWS Permissions Required
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*",
                "lambda:*",
                "iam:*",
                "cloudformation:*",
                "bedrock:InvokeModel",
                "secretsmanager:GetSecretValue",
                "cloudwatch:*",
                "xray:*"
            ],
            "Resource": "*"
        }
    ]
}
```

### GitHub Token Setup
1. Create GitHub Personal Access Token with `repo` scope
2. Store in AWS Secrets Manager:
```bash
aws secretsmanager create-secret \
    --name "github/personal_token" \
    --description "GitHub token for WhisperSync" \
    --secret-string "your_token_here"
```

## Quick Start

### 1. Environment Setup
```bash
# Clone repository
git clone https://github.com/your-org/whispersync.git
cd whispersync

# Create Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-lock.txt

# Install CDK dependencies
cd infrastructure
npm install
```

### 2. Configuration
```bash
# Set environment variables
export WHISPERSYNC_ENV=development
export AWS_REGION=us-east-1
export BUCKET_NAME=voice-mcp-dev
export LOG_LEVEL=INFO

# Initialize CDK (first time only)
cdk bootstrap
```

### 3. Deploy Development Environment
```bash
# Deploy infrastructure
cd infrastructure
cdk deploy --parameters Environment=development

# Verify deployment
aws lambda list-functions --query 'Functions[?contains(FunctionName, `whispersync`)]'
```

### 4. Test Deployment
```bash
# Run local tests
cd ..
python -m pytest tests/unit/ -v

# Test with sample transcript
python scripts/local_test_runner.py test_data/transcripts/work/test.txt
```

## Production Deployment

### 1. Pre-Production Checklist

#### Security Review
- [ ] IAM policies follow least privilege principle
- [ ] S3 bucket has proper encryption enabled
- [ ] Secrets are stored in AWS Secrets Manager
- [ ] VPC configuration is properly set up
- [ ] CloudTrail logging is enabled

#### Performance Validation
- [ ] Load testing completed with expected voice memo volume
- [ ] Lambda memory and timeout settings optimized
- [ ] CloudWatch alarms configured for key metrics
- [ ] Cost analysis performed and approved

#### Code Quality
- [ ] All tests passing (unit, integration, end-to-end)
- [ ] Code coverage > 80%
- [ ] Security scan completed with no high/critical issues
- [ ] Documentation updated and reviewed

### 2. Production Infrastructure

```bash
# Deploy production environment
cd infrastructure
cdk deploy \
    --parameters Environment=production \
    --parameters EnableXRay=true \
    --parameters ReservedConcurrency=10 \
    --require-approval never
```

### 3. Post-Deployment Verification

```bash
# Health check
aws lambda invoke \
    --function-name whispersync-health-check-production \
    --payload '{}' \
    response.json

# Verify response
cat response.json | jq '.statusCode'  # Should be 200
```

## Environment Configuration

### Development Environment
```bash
export WHISPERSYNC_ENV=development
export LOG_LEVEL=DEBUG
export ENABLE_XRAY=false
export STRANDS_USE_MOCKS=true
export LAMBDA_MEMORY=256
export LAMBDA_TIMEOUT=180
```

### Staging Environment
```bash
export WHISPERSYNC_ENV=staging
export LOG_LEVEL=INFO
export ENABLE_XRAY=true
export STRANDS_USE_MOCKS=false
export LAMBDA_MEMORY=512
export LAMBDA_TIMEOUT=300
```

### Production Environment
```bash
export WHISPERSYNC_ENV=production
export LOG_LEVEL=WARNING
export ENABLE_XRAY=true
export STRANDS_USE_MOCKS=false
export LAMBDA_MEMORY=512
export LAMBDA_TIMEOUT=300
export RESERVED_CONCURRENCY=10
```

### Configuration Validation
```python
# Validate configuration
from agents.config import get_config

config = get_config()
errors = config.validate()

if errors:
    print("Configuration errors:", errors)
else:
    print("Configuration valid")
```

## Security Setup

### 1. S3 Bucket Security

#### Bucket Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyInsecureConnections",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::voice-mcp-production",
                "arn:aws:s3:::voice-mcp-production/*"
            ],
            "Condition": {
                "Bool": {
                    "aws:SecureTransport": "false"
                }
            }
        }
    ]
}
```

#### Encryption Configuration
```bash
# Enable default encryption
aws s3api put-bucket-encryption \
    --bucket voice-mcp-production \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }'
```

### 2. Lambda Security

#### IAM Role Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::voice-mcp-production/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "arn:aws:bedrock:*:*:foundation-model/anthropic.claude-3-5-sonnet-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:*:*:secret:github/personal_token*"
        }
    ]
}
```

### 3. Network Security

#### VPC Configuration (Optional but Recommended)
```python
# In infrastructure/mcp_stack.py
vpc = ec2.Vpc(
    self, "WhisperSyncVPC",
    max_azs=2,
    nat_gateways=1,
    subnet_configuration=[
        ec2.SubnetConfiguration(
            name="Private",
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            cidr_mask=24
        ),
        ec2.SubnetConfiguration(
            name="Public",
            subnet_type=ec2.SubnetType.PUBLIC,
            cidr_mask=24
        )
    ]
)

# Add Lambda to VPC
lambda_fn.add_environment("VPC_ID", vpc.vpc_id)
lambda_fn.connections.allow_to_any_ipv4(ec2.Port.tcp(443), "HTTPS outbound")
```

## Monitoring & Observability

### 1. CloudWatch Dashboards

#### Create Custom Dashboard
```bash
aws cloudwatch put-dashboard \
    --dashboard-name "WhisperSync-Production" \
    --dashboard-body file://monitoring/dashboard.json
```

#### Key Metrics to Monitor
- **Lambda Invocations**: Total processing volume
- **Lambda Errors**: Error rate and types
- **Lambda Duration**: Processing latency
- **S3 Objects**: Storage growth and access patterns
- **Custom Metrics**: Agent-specific success rates

### 2. Alarms Configuration

#### Error Rate Alarm
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "WhisperSync-High-Error-Rate" \
    --alarm-description "WhisperSync error rate too high" \
    --metric-name "Errors" \
    --namespace "AWS/Lambda" \
    --statistic "Sum" \
    --period 300 \
    --threshold 5 \
    --comparison-operator "GreaterThanThreshold" \
    --evaluation-periods 2 \
    --alarm-actions "arn:aws:sns:us-east-1:123456789012:whispersync-alerts"
```

#### Duration Alarm
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "WhisperSync-High-Duration" \
    --alarm-description "WhisperSync processing too slow" \
    --metric-name "Duration" \
    --namespace "AWS/Lambda" \
    --statistic "Average" \
    --period 300 \
    --threshold 240000 \
    --comparison-operator "GreaterThanThreshold" \
    --evaluation-periods 2
```

### 3. X-Ray Tracing

#### Enable X-Ray
```python
# In Lambda configuration
tracing=_lambda.Tracing.ACTIVE
```

#### View Traces
```bash
# Get trace summaries
aws xray get-trace-summaries \
    --time-range-type TimeRangeByStartTime \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-01T23:59:59Z
```

### 4. Log Analysis

#### Structured Logging Query
```bash
# CloudWatch Insights query
aws logs start-query \
    --log-group-name "/aws/lambda/mcpAgentRouterLambda-production" \
    --start-time $(date -d '1 hour ago' +%s) \
    --end-time $(date +%s) \
    --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc'
```

## Troubleshooting

### Common Issues

#### 1. Lambda Timeout Errors
**Symptoms**: Function timeouts, incomplete processing
**Solutions**:
- Increase Lambda timeout configuration
- Optimize agent processing logic
- Check Bedrock API latency

```bash
# Update Lambda timeout
aws lambda update-function-configuration \
    --function-name mcpAgentRouterLambda-production \
    --timeout 300
```

#### 2. S3 Permission Errors
**Symptoms**: Access denied errors in logs
**Solutions**:
- Verify IAM role permissions
- Check bucket policy configuration
- Validate resource ARNs

```bash
# Test S3 access
aws s3 ls s3://voice-mcp-production/transcripts/ --recursive
```

#### 3. Agent Processing Failures
**Symptoms**: Agent errors in CloudWatch logs
**Solutions**:
- Check Bedrock model availability
- Verify Secrets Manager access
- Review agent configuration

```bash
# Test Bedrock access
aws bedrock-runtime invoke-model \
    --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
    --body '{"anthropic_version": "bedrock-2023-05-31", "max_tokens": 100, "messages": [{"role": "user", "content": "Hello"}]}' \
    response.json
```

### Debug Mode

#### Enable Debug Logging
```bash
# Update Lambda environment
aws lambda update-function-configuration \
    --function-name mcpAgentRouterLambda-production \
    --environment Variables='{LOG_LEVEL=DEBUG}'
```

#### Local Debug Testing
```bash
# Run local debug session
export LOG_LEVEL=DEBUG
python scripts/local_test_runner.py test_data/transcripts/work/debug.txt
```

## Maintenance

### Regular Maintenance Tasks

#### Weekly
- [ ] Review CloudWatch metrics and alarms
- [ ] Check error logs for patterns
- [ ] Verify backup and retention policies
- [ ] Update security patches if available

#### Monthly
- [ ] Review and rotate secrets
- [ ] Analyze cost optimization opportunities
- [ ] Update dependencies and test
- [ ] Review and update documentation

#### Quarterly
- [ ] Security audit and penetration testing
- [ ] Disaster recovery testing
- [ ] Performance baseline review
- [ ] Architecture review for improvements

### Backup Strategy

#### S3 Cross-Region Replication
```bash
# Enable replication to backup region
aws s3api put-bucket-replication \
    --bucket voice-mcp-production \
    --replication-configuration file://backup/replication-config.json
```

#### Lambda Function Backup
```bash
# Export Lambda function
aws lambda get-function \
    --function-name mcpAgentRouterLambda-production \
    --query 'Code.Location' \
    --output text | xargs curl -o lambda-backup.zip
```

### Updates and Rollbacks

#### Blue-Green Deployment
```bash
# Deploy new version with alias
cdk deploy --parameters Environment=production-v2

# Test new version
aws lambda invoke \
    --function-name mcpAgentRouterLambda-production-v2 \
    --payload '{}' test-response.json

# Switch traffic to new version
aws lambda update-alias \
    --function-name mcpAgentRouterLambda \
    --name production \
    --function-version 2
```

#### Rollback Procedure
```bash
# Rollback to previous version
aws lambda update-alias \
    --function-name mcpAgentRouterLambda \
    --name production \
    --function-version 1

# Verify rollback
aws lambda get-alias \
    --function-name mcpAgentRouterLambda \
    --name production
```

### Cost Optimization

#### Monitor Costs
```bash
# Get cost and usage
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

#### Optimization Strategies
1. **Right-size Lambda memory**: Monitor memory usage and adjust
2. **S3 lifecycle policies**: Archive old transcripts to cheaper storage
3. **Reserved capacity**: Use reserved Lambda concurrency for predictable workloads
4. **Bedrock usage optimization**: Cache frequent queries when possible

---

## Support

For deployment issues or questions:
- **Documentation**: Check this guide and README.md
- **Issues**: Open GitHub issue with deployment logs
- **Emergency**: Follow incident response procedures in INCIDENT_RESPONSE.md

## Next Steps

After successful deployment:
1. Set up monitoring dashboards
2. Configure alerting and notifications
3. Train team on operational procedures
4. Plan capacity scaling based on usage patterns
5. Schedule regular maintenance windows