# 🎙️ WhisperSync Live Demo Walkthrough

## Quick Demo: See Your Voice-to-Action Pipeline in Action!

This demo will show you exactly what your rockstar team built by walking through the complete pipeline from voice transcript to agent action.

## 🚀 Option 1: Quick Local Demo (No AWS Required)

### Step 1: Run the Interactive Demo UI
```bash
cd /Users/williamprior/Development/GitHub/whispersync

# Activate your environment
source .venv/bin/activate

# Start the Streamlit demo
cd demo
streamlit run app.py
```

**What you'll see:**
- Web interface at `http://localhost:8501`
- Upload test transcripts and see agent routing decisions
- Real-time processing simulation
- Agent output previews

### Step 2: Test Individual Agents Locally
```bash
# Test the GitHub Agent
python -c "
from agents.github_idea_agent import handle
result = handle({
    'transcript': 'I want to build a habit tracking app with gamification features',
    'bucket': 'test-bucket'
})
print('GitHub Agent Result:', result)
"

# Test the Executive Agent  
python -c "
from agents.work_journal_agent import handle
result = handle({
    'transcript': 'Today I completed the authentication system and fixed three critical bugs',
    'bucket': 'test-bucket'
})
print('Executive Agent Result:', result)
"

# Test the Spiritual Agent
python -c "
from agents.spiritual_advisor_agent import handle
result = handle({
    'transcript': 'I remember my first camping trip with dad when I was seven years old',
    'bucket': 'test-bucket'
})
print('Spiritual Agent Result:', result)
"
```

## 🎯 Option 2: Full AWS Integration Demo

### Step 1: Verify Your Deployment
```bash
# Check if your Lambda is deployed
aws lambda list-functions --profile personal --query 'Functions[?contains(FunctionName, `whispersync`)]'

# Check your S3 bucket
aws s3 ls s3://macbook-transcriptions-development --profile personal
```

### Step 2: Upload Test Transcripts
```bash
# Create test transcript files
mkdir -p test_transcripts

# Work transcript
echo "Today I worked on implementing the user authentication system. I completed the login flow, added password reset functionality, and wrote comprehensive unit tests. The feature is now ready for code review." > test_transcripts/work_demo.txt

# Memory transcript  
echo "I remember the day my daughter took her first steps. She was holding onto the coffee table, looked at me with those bright eyes, let go and walked straight into my arms. Pure joy." > test_transcripts/memory_demo.txt

# GitHub idea transcript
echo "I have an idea for a personal finance app that uses AI to categorize expenses automatically. It would connect to your bank account, analyze spending patterns, and provide insights on budgeting. Maybe call it SmartBudget." > test_transcripts/github_demo.txt

# Upload to S3 (triggers the pipeline!)
aws s3 cp test_transcripts/work_demo.txt s3://macbook-transcriptions-development/transcripts/work/2025/07/04/demo_work.txt --profile personal

aws s3 cp test_transcripts/memory_demo.txt s3://macbook-transcriptions-development/transcripts/memories/2025/07/04/demo_memory.txt --profile personal

aws s3 cp test_transcripts/github_demo.txt s3://macbook-transcriptions-development/transcripts/github_ideas/2025/07/04/demo_github.txt --profile personal
```

### Step 3: Watch the Magic Happen
```bash
# Check Lambda logs (processing should happen within seconds)
aws logs tail /aws/lambda/mcpAgentRouterLambda-development --follow --profile personal

# Check for outputs (wait 10-30 seconds after upload)
aws s3 ls s3://macbook-transcriptions-development/outputs/ --recursive --profile personal

# Download and view results
aws s3 cp s3://macbook-transcriptions-development/outputs/work/2025/07/04/demo_work_response.json . --profile personal
aws s3 cp s3://macbook-transcriptions-development/outputs/memories/2025/07/04/demo_memory_response.json . --profile personal  
aws s3 cp s3://macbook-transcriptions-development/outputs/github/2025/07/04/demo_github_response.json . --profile personal

# View the results
cat demo_work_response.json | jq '.'
cat demo_memory_response.json | jq '.'
cat demo_github_response.json | jq '.'
```

### Step 4: See Agent Outputs
```bash
# Check work journal entry
aws s3 cp s3://macbook-transcriptions-development/work/weekly_logs/2025-W27.md . --profile personal
cat 2025-W27.md

# Check memory preservation
aws s3 cp s3://macbook-transcriptions-development/memories/2025-07-04.jsonl . --profile personal
cat 2025-07-04.jsonl

# Check GitHub history (if GitHub agent ran)
aws s3 cp s3://macbook-transcriptions-development/github/history.jsonl . --profile personal 2>/dev/null || echo "GitHub history not yet created"
```

## 🧪 Option 3: Run Integration Tests

### Comprehensive End-to-End Testing
```bash
# Validate your setup first
python scripts/validate_e2e_setup.py

# Run the full integration test suite
python scripts/run_e2e_tests.py

# Just run performance tests
python scripts/run_e2e_tests.py --performance-only

# Dry run (check setup without actual AWS calls)
python scripts/run_e2e_tests.py --dry-run
```

## 📊 Option 4: Monitor Your System

### Real-time Monitoring
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=mcpAgentRouterLambda-development \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --profile personal

# Check for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/mcpAgentRouterLambda-development \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR" \
  --profile personal
```

### Health Check
```bash
# Test the health endpoint
aws lambda invoke \
  --function-name whispersync-health-check-development \
  --payload '{}' \
  --profile personal \
  health_response.json

cat health_response.json | jq '.'
```

## 🎯 What You Should See

### Expected Outputs:

#### 1. Work Journal Entry (`2025-W27.md`):
```markdown
# Work Journal - 2025 Week 27

## 2025-07-04T15:30:45.123456Z

Today I worked on implementing the user authentication system. I completed the login flow, added password reset functionality, and wrote comprehensive unit tests. The feature is now ready for code review.

---
```

#### 2. Memory Preservation (`2025-07-04.jsonl`):
```json
{"timestamp": "2025-07-04T15:30:45.123456", "content": "I remember the day my daughter took her first steps. She was holding onto the coffee table, looked at me with those bright eyes, let go and walked straight into my arms. Pure joy."}
```

#### 3. GitHub Repository:
- New repo created: `smartbudget` or similar
- README with your idea description
- Basic project structure

#### 4. Lambda Response:
```json
{
  "statusCode": 200,
  "message": "Transcript processed successfully",
  "routing": {
    "primary_agent": "work",
    "confidence": 0.95,
    "reasoning": "Source path indicates work-related content"
  },
  "agents_used": ["work"],
  "success": true
}
```

## 🚨 Troubleshooting

### If nothing happens:
```bash
# Check AWS credentials
aws sts get-caller-identity --profile personal

# Check S3 bucket exists
aws s3 ls s3://macbook-transcriptions-development --profile personal

# Check Lambda function exists
aws lambda get-function --function-name mcpAgentRouterLambda-development --profile personal
```

### If you get permission errors:
```bash
# Re-deploy with proper permissions
cd infrastructure
cdk deploy --profile personal
```

### Need to update GitHub token:
```bash
# Update with your real GitHub Personal Access Token
aws secretsmanager update-secret \
  --secret-id github/personal_token \
  --secret-string "ghp_your_actual_token_here" \
  --profile personal
```

## 🎉 What This Demonstrates

This demo shows your complete **voice-to-action cognitive exoskeleton**:

1. **📁 Intelligent Routing**: Folder structure determines which agent processes your transcript
2. **🤖 Agent Processing**: Three specialized agents handle different types of content
3. **💾 Persistent Storage**: All outputs stored in S3 with metadata
4. **📊 Monitoring**: CloudWatch tracks all processing with metrics and logs
5. **⚡ Speed**: Sub-5-second processing from upload to output

Your WhisperSync system is now processing voice memos and taking intelligent actions automatically!

**Try it out and watch your ideas transform into GitHub repos, your work thoughts become organized journals, and your memories get preserved with perfect fidelity.** 🎙️→🤖→✨