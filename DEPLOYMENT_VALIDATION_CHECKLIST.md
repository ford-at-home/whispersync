# WhisperSync Deployment Validation Checklist

This checklist ensures your WhisperSync deployment is working correctly.

## Prerequisites
- [ ] AWS CLI installed and configured
- [ ] AWS profile set: `export AWS_PROFILE=personal`
- [ ] Python 3.11+ installed
- [ ] CDK CLI installed: `npm install -g aws-cdk`

## Deployment Steps

### 1. Infrastructure Deployment
```bash
cd infrastructure
cdk deploy --require-approval never
```

Expected output:
- ✅ Stack creates successfully (~2 minutes)
- ✅ Outputs show bucket name, Lambda function name, etc.

### 2. Verify Resources Created

Check S3 bucket:
```bash
aws s3 ls | grep macbook-transcriptions
```

Check Lambda function:
```bash
aws lambda get-function --function-name mcpAgentRouterLambda-development
```

Check CloudWatch log group:
```bash
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/mcpAgentRouter
```

## Validation Tests

### 1. Health Check
```bash
aws lambda invoke \
  --function-name whispersync-health-check-development \
  --region us-east-1 \
  /tmp/health-output.json && cat /tmp/health-output.json | jq
```

Expected: `"status": "healthy"`

### 2. Test Each Agent Type

#### Work Agent Test
```bash
echo "Today I completed the API integration and fixed three critical bugs." > work_test.txt
aws s3 cp work_test.txt s3://macbook-transcriptions-development/transcripts/work/test_$(date +%s).txt
```

#### Memory Agent Test
```bash
echo "I'll always remember the day we launched our first product to real users." > memory_test.txt
aws s3 cp memory_test.txt s3://macbook-transcriptions-development/transcripts/memories/test_$(date +%s).txt
```

#### GitHub Agent Test
```bash
echo "New idea: AI Code Reviewer - automatically reviews PRs for best practices." > github_test.txt
aws s3 cp github_test.txt s3://macbook-transcriptions-development/transcripts/github_ideas/test_$(date +%s).txt
```

### 3. Verify Processing

Wait 5 seconds, then check outputs:
```bash
aws s3 ls s3://macbook-transcriptions-development/outputs/ --recursive | tail -5
```

Expected: See JSON response files for each test

### 4. Check Logs
```bash
aws logs tail /aws/lambda/mcpAgentRouterLambda-development --since 5m
```

Look for:
- ✅ "Routing decision: work/memory/github"
- ✅ "Processing complete"
- ❌ No ERROR messages

### 5. Performance Check
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=mcpAgentRouterLambda-development \
  --statistics Average \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600
```

Expected: Average duration < 1000ms

## Common Issues and Fixes

### Issue: Lambda timeout
**Fix**: Check CloudWatch logs for specific errors. Common causes:
- S3 permissions issue
- Missing environment variables

### Issue: Wrong agent routing
**Fix**: The orchestrator uses folder names for routing hints:
- `transcripts/work/` → Work agent
- `transcripts/memories/` → Memory agent  
- `transcripts/github_ideas/` → GitHub agent

### Issue: No output files created
**Fix**: Check Lambda has S3 write permissions to the bucket

### Issue: GitHub agent not creating repos
**Fix**: Ensure GitHub token is in Secrets Manager:
```bash
aws secretsmanager create-secret \
  --name github/personal_token \
  --secret-string "ghp_your_token_here"
```

## Monitoring Dashboard

Create a simple monitoring view:
```bash
# Recent invocations
aws logs filter-log-events \
  --log-group-name /aws/lambda/mcpAgentRouterLambda-development \
  --filter-pattern "Routing decision" \
  --max-items 10

# Error count
aws logs filter-log-events \
  --log-group-name /aws/lambda/mcpAgentRouterLambda-development \
  --filter-pattern "[ERROR]" \
  --start-time $(date -d '1 hour ago' +%s)000
```

## Success Criteria

Your deployment is successful when:
- [ ] All three agent types route correctly
- [ ] Processing completes in <3 seconds
- [ ] Output files are created in S3
- [ ] No errors in CloudWatch logs
- [ ] Health check returns healthy

## Next Steps

Once validated:
1. Set up iPhone Shortcuts for voice recording
2. Configure local Whisper transcription
3. Create automated upload script
4. Start using WhisperSync daily!

## Rollback Procedure

If issues arise:
```bash
# Destroy the stack
cd infrastructure
cdk destroy

# Clean up S3 bucket (if needed)
aws s3 rm s3://macbook-transcriptions-development --recursive
```