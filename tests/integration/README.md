# WhisperSync End-to-End Integration Tests

This directory contains comprehensive end-to-end integration tests for the WhisperSync voice memo processing pipeline. These tests validate the complete workflow from S3 upload through Lambda processing to final agent outputs.

## Overview

The integration tests are designed to:

1. **Validate Complete Pipeline**: Test the entire workflow from voice transcript upload to agent processing
2. **Use Real AWS Services**: Integration with actual S3 buckets and Lambda functions
3. **Mock External Dependencies**: GitHub API and other external services are mocked for controlled testing
4. **Measure Performance**: Ensure processing completes within 5-second threshold
5. **Test Error Handling**: Validate graceful failure scenarios and edge cases
6. **Clean Up Resources**: Automatically remove test data after execution

## Test Architecture

```
S3 Upload → Lambda Trigger → Orchestrator → Agent Processing → S3 Output
    ↓              ↓              ↓              ↓              ↓
Test Validates Each Step of the Pipeline
```

### Key Components Tested

- **Work Journal Agent**: Transcript → Executive agent → Weekly log
- **Memory Agent**: Transcript → Spiritual agent → JSONL file  
- **GitHub Agent**: Transcript → GitHub agent → Repository creation
- **Multi-Agent Coordination**: Complex transcripts → Multiple agents
- **Error Handling**: Invalid inputs → Graceful error responses
- **Performance**: All processing → < 5 seconds completion

## Prerequisites

### AWS Environment

1. **AWS Credentials**: Configure via AWS CLI, IAM role, or environment variables
2. **S3 Bucket**: Accessible bucket for test data (default: `macbook-transcriptions-test`)
3. **Lambda Function**: Deployed WhisperSync router function (default: `whispersync-router`)
4. **Permissions**: S3 read/write and Lambda invoke permissions

### Python Environment

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or install specific test packages
pip install pytest moto responses faker boto3
```

### Environment Variables

```bash
export TEST_BUCKET_NAME="macbook-transcriptions-test"
export TEST_LAMBDA_FUNCTION_NAME="whispersync-router" 
export AWS_DEFAULT_REGION="us-east-1"
export TRANSCRIPT_BUCKET_NAME="macbook-transcriptions-test"
```

## Running Tests

### Quick Start

```bash
# Run all integration tests
python scripts/run_e2e_tests.py

# Run with verbose output
python scripts/run_e2e_tests.py --verbose

# Validate environment only
python scripts/run_e2e_tests.py --dry-run
```

### Test Categories

```bash
# Run only performance tests
python scripts/run_e2e_tests.py --performance-only

# Run quick tests (skip performance benchmarks)
python scripts/run_e2e_tests.py --quick

# Clean up test resources only
python scripts/run_e2e_tests.py --cleanup-only
```

### Advanced Options

```bash
# Use custom bucket and Lambda function
python scripts/run_e2e_tests.py --bucket my-test-bucket --lambda my-function

# Use different AWS region
python scripts/run_e2e_tests.py --region us-west-2

# Run specific test methods
pytest tests/integration/test_end_to_end.py::TestEndToEndIntegration::test_work_journal_integration -v
```

### Direct pytest Execution

```bash
# Run with pytest directly
pytest -c pytest-e2e.ini tests/integration/test_end_to_end.py -v

# Run with coverage
pytest -c pytest-e2e.ini tests/integration/test_end_to_end.py --cov=agents --cov-report=html

# Run specific test patterns
pytest -c pytest-e2e.ini tests/integration/test_end_to_end.py -k "work_journal" -v
```

## Test Scenarios

### 1. Work Journal Integration Test

**Scenario**: User records work-related voice memo

**Pipeline**: S3 upload → Lambda trigger → Work agent → Weekly log

**Validation**:
- Correct agent routing (work agent selected)
- Work entry logged with proper categorization
- Performance under 5 seconds
- Output contains work-specific fields

**Test Data**: Complex development work transcript with technical details

### 2. Memory Preservation Integration Test

**Scenario**: User records personal memory or reflection

**Pipeline**: S3 upload → Lambda trigger → Memory agent → JSONL storage

**Validation**:
- Memory agent selection and processing
- Sentiment analysis performed
- Themes and significance scoring
- Performance under 5 seconds
- JSONL output format validation

**Test Data**: Personal graduation memory with emotional content

### 3. GitHub Repository Creation Test

**Scenario**: User records idea for new project

**Pipeline**: S3 upload → Lambda trigger → GitHub agent → Repository created

**Validation**:
- GitHub agent selection
- Repository creation (mocked)
- Tech stack inference
- Project description generation
- Performance under 5 seconds

**Test Data**: AI-powered development tool idea with technical specifications

### 4. Multi-Agent Coordination Test

**Scenario**: Complex transcript spanning multiple domains

**Pipeline**: S3 upload → Lambda trigger → Orchestrator → Multiple agents

**Validation**:
- Multiple agent detection
- All relevant agents process content
- Results properly aggregated
- Lower confidence for ambiguous content
- Performance under 10 seconds (extended for multi-agent)

**Test Data**: Mixed work/memory/project content

### 5. Error Handling Tests

**Scenarios**: 
- Empty transcript
- Invalid S3 keys
- Malformed content
- Network failures

**Validation**:
- Graceful error handling
- Proper error logging to S3
- No crashes or exceptions
- Detailed error information

### 6. Performance Benchmark Tests

**Scenarios**:
- Short transcripts (< 100 words)
- Medium transcripts (100-500 words)  
- Long transcripts (> 500 words)

**Validation**:
- All processing under 5 seconds (short/medium)
- Long transcripts under 10 seconds
- Performance metrics reporting
- Memory usage tracking

### 7. Lambda Trigger Validation

**Scenario**: Validate S3 event configuration

**Validation**:
- Lambda triggered within 15 seconds
- Proper S3 event structure
- Correct key parsing
- Request ID tracking

### 8. S3 Output Validation

**Scenario**: Validate output file structure

**Validation**:
- Required fields present
- Proper JSON formatting
- Correct S3 metadata
- Appropriate content type

## Test Data

### Provided Test Files

Located in `test_data/transcripts/`:

- `work/complex_work_transcript.txt`: Detailed development work
- `work/performance_test_long.txt`: Long transcript for performance testing
- `work/error_scenario_transcript.txt`: Empty file for error testing
- `memories/personal_memory_transcript.txt`: Personal graduation memory
- `github_ideas/innovative_project_idea.txt`: AI development tool idea
- `general/multi_domain_transcript.txt`: Mixed content for multi-agent testing

### Dynamic Test Data

Tests also generate dynamic test data using:
- Unique test IDs to prevent conflicts
- Timestamps for file naming
- Faker library for realistic content generation

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**
   ```bash
   aws configure
   # or
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   ```

2. **S3 Bucket Not Accessible**
   ```bash
   aws s3 mb s3://macbook-transcriptions-test
   # or check bucket permissions
   ```

3. **Lambda Function Not Found**
   - Deploy the WhisperSync infrastructure using CDK
   - Verify function name matches TEST_LAMBDA_FUNCTION_NAME

4. **Tests Timeout**
   - Check AWS service status
   - Verify Lambda function is not cold starting
   - Increase timeout in pytest-e2e.ini

5. **Permission Denied**
   - Verify IAM permissions for S3 and Lambda
   - Check bucket policies and CORS settings

### Debug Mode

```bash
# Enable debug logging
python scripts/run_e2e_tests.py --verbose

# Run single test with debug output
pytest tests/integration/test_end_to_end.py::TestEndToEndIntegration::test_work_journal_integration -v -s --log-cli-level=DEBUG
```

### Manual Testing

```bash
# Test environment validation
python scripts/run_e2e_tests.py --dry-run

# Test specific components
python -c "
import boto3
s3 = boto3.client('s3')
print(s3.list_buckets())
"
```

## Performance Expectations

### Response Time Targets

- **Single Agent Processing**: < 5 seconds
- **Multi-Agent Coordination**: < 10 seconds  
- **Lambda Cold Start**: < 15 seconds
- **S3 Upload/Download**: < 2 seconds

### Resource Usage

- **S3 Operations**: Minimal cost (< $0.01 per test run)
- **Lambda Invocations**: Free tier friendly (< 100 invocations per test)
- **Data Transfer**: Negligible (< 1MB per test)

### Scalability Testing

The test suite can be extended for load testing:

```bash
# Install load testing dependencies
pip install locust

# Run load tests (future enhancement)
locust -f tests/load/test_load.py --host=https://api.whispersync.com
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run integration tests
        run: python scripts/run_e2e_tests.py --quick
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          TEST_BUCKET_NAME: ${{ vars.TEST_BUCKET_NAME }}
```

### Test Reports

Tests generate multiple report formats:

- **HTML Report**: `htmlcov/index.html` (coverage)
- **JSON Report**: `test_report.json` (results)
- **JUnit XML**: `test-results.xml` (CI integration)

## Contributing

### Adding New Tests

1. **Create Test Method**: Add to `TestEndToEndIntegration` class
2. **Use Test Fixture**: Leverage `e2e_test` fixture for setup/cleanup
3. **Follow Naming**: Use descriptive test method names
4. **Add Documentation**: Include docstring with scenario description
5. **Validate Cleanup**: Ensure test resources are cleaned up

### Test Development Guidelines

1. **Independent Tests**: Each test should be completely independent
2. **Clear Assertions**: Use descriptive assertion messages
3. **Resource Cleanup**: Always clean up test resources
4. **Performance Aware**: Monitor test execution time
5. **Error Handling**: Test both success and failure paths

### Example Test Structure

```python
def test_new_scenario_integration(self, e2e_test):
    """Test description and scenario.
    
    SCENARIO: What user action triggers this test
    PIPELINE: Step-by-step flow being tested
    VALIDATION: What specific outcomes are verified
    """
    print("\n=== Testing New Scenario ===")
    
    # Arrange: Set up test data
    transcript = "Test transcript content..."
    
    # Act: Execute the pipeline
    start_time = time.time()
    key = e2e_test.upload_test_transcript("agent_type", transcript)
    processing_result = e2e_test.wait_for_processing(key)
    processing_time = time.time() - start_time
    
    # Assert: Validate results
    assert processing_result["success"], "Processing should succeed"
    assert processing_time < 5.0, "Should complete within 5 seconds"
    
    # Validate specific agent outputs
    result = processing_result["result"]
    # Add specific validations...
    
    print(f"✓ New scenario test passed in {processing_time:.2f}s")
```

## Security Considerations

### Test Data

- **No Sensitive Data**: Test transcripts contain only fictional content
- **Temporary Resources**: All test objects are automatically deleted
- **Isolated Environment**: Tests use dedicated test bucket and resources

### API Keys and Secrets

- **GitHub API**: Mocked in tests, no real API calls
- **AWS Credentials**: Use dedicated test account with limited permissions
- **Environment Variables**: Never commit credentials to repository

### Resource Access

Tests require minimal AWS permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject", 
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::macbook-transcriptions-test",
        "arn:aws:s3:::macbook-transcriptions-test/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:GetFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:whispersync-router"
    }
  ]
}
```

---

## Support

For issues with integration tests:

1. **Check Prerequisites**: Verify AWS access and bucket permissions
2. **Review Logs**: Enable verbose output for detailed error information  
3. **Validate Environment**: Use `--dry-run` to check configuration
4. **Clean Resources**: Use `--cleanup-only` to reset test state
5. **Consult Documentation**: Review troubleshooting section above

The integration tests are designed to provide comprehensive validation of the WhisperSync pipeline while being easy to run and maintain. They serve as both quality assurance and documentation of expected system behavior.