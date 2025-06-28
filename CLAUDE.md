# WhisperSync - Voice Memo MCP Agent System

## Quick Start Summary

WhisperSync is a voice-to-action pipeline that automatically processes iPhone voice memos through AI agents. Record a memo → It gets transcribed → Routed to the right agent → Action taken.

### WHY THIS DEVELOPMENT WORKFLOW

**Local-First Development**: The entire pipeline can be tested without AWS infrastructure, enabling rapid iteration.

**Test-Driven Agents**: Each agent has comprehensive unit tests because voice transcripts are unpredictable.

**Infrastructure as Code**: CDK ensures reproducible deployments and environment parity.

**Observability First**: OpenTelemetry tracing is built-in because distributed agent systems are hard to debug.

**Core Workflow:**
1. Record voice memo on iPhone (into folders: `work`, `memories`, `github_ideas`)
2. Local Whisper transcribes to text
3. Upload to S3: `s3://voice-mcp/transcripts/{agent_name}/{timestamp}.txt`
4. Lambda routes to appropriate Strands agent
5. Agent processes and takes action (logs work, archives memory, creates GitHub repo)

## Key Architecture Points

```
iPhone → Whisper → S3 → Lambda → Strands Agent → Action
```

### WHY THIS SPECIFIC PIPELINE

**iPhone Voice Memos**: Native app users already know, syncs to iCloud automatically.

**Local Whisper**: Privacy-first transcription, no audio data sent to cloud services.

**S3 as Message Bus**: Durable, event-driven, handles network disconnections gracefully.

**Lambda Router**: Stateless routing keeps the system simple and scalable.

**Strands Agents**: Purpose-built for AI workflows, handles Claude integration complexity.

- **S3 Bucket**: `voice-mcp` (triggers on `transcripts/` prefix)
- **Lambda**: `mcpAgentRouterLambda` (extracts agent from S3 key path)
- **Agents**: Work Journal, Memory Archive, GitHub Repo Creator
- **Tech Stack**: Python 3.11+, AWS CDK, Strands SDK, boto3, PyGithub
- **Observability**: OpenTelemetry integration for tracing and monitoring
- **Demo UI**: Streamlit app for testing the pipeline

## Important Code Locations

### WHY THIS DIRECTORY STRUCTURE

**Agents Separation**: Each agent is a standalone module for independent development and testing.

**Lambda Function Isolation**: Single-purpose function in dedicated directory for clear deployment boundaries.

**Infrastructure Code Separation**: CDK stacks separate from application logic for DevOps clarity.

**Local Development Tools**: `mac-to-s3/` and `demo/` enable development without cloud dependencies.

**Test Organization**: Unit and integration tests separated for different execution contexts.

- **Agents**: `agents/` - Contains the three agent implementations
- **Lambda**: `lambda_fn/router_handler.py` - Routes S3 events to agents
- **Infrastructure**: `infrastructure/mcp_stack.py` - AWS CDK stack
- **Local Transcription**: `mac-to-s3/` - Whisper transcription pipeline
- **Tests**: `tests/` - Unit and integration tests
- **Demo**: `demo/app.py` - Streamlit UI for testing

## Common Development Tasks

### Environment Setup
```bash
make install       # Create venv and install dependencies
source .venv/bin/activate  # Activate virtual environment
```

### Running Tests
```bash
make test          # Run all tests with coverage
make test-unit     # Unit tests only
make test-integ    # Integration tests
make test-local    # Test with local sample data
```

### Code Quality
```bash
make format        # Format with black
make lint          # Lint with flake8
make clean         # Clean up cache and build artifacts
```

### Deploying Infrastructure
```bash
cd infrastructure
cdk deploy
```

## Key Implementation Details

1. **Agent Routing**: Agent name extracted from S3 key path (e.g., `transcripts/work/...` → `work_agent`)

2. **Agent Inputs**: All agents receive:
   - `transcript`: The transcribed text
   - `s3_key`: Original S3 key for context
   - `bucket`: S3 bucket name

3. **Agent Outputs**: Written to `s3://voice-mcp/outputs/{agent}/{date}_response.json`

4. **Secrets**: GitHub token stored in AWS Secrets Manager as `github/personal_token`

5. **Strands Import Pattern**:
   - `from strands import Agent, tool` - For agent class and decorators
   - `from strands_sdk import invoke_agent, register_agent` - For SDK operations
   - `from strands_tools import bedrock_knowledge_base_retrieve` - For tool integrations

## Resolved Issues & Updates

1. **✅ Lambda Path**: Infrastructure correctly references `lambda_fn/` directory
2. **✅ Strands SDK**: Separate packages (strands, strands-agents, strands-tools) clarify imports
3. **✅ Monitoring**: OpenTelemetry added for distributed tracing and observability
4. **✅ Demo UI**: Streamlit app provides visual testing interface
5. **✅ Virtual Environment**: Project uses `.venv` for dependency isolation
6. **✅ Code Quality**: Black and flake8 configured for consistent formatting

## Current Limitations & TODOs

1. **Partial Claude Integration**: Agents have Bedrock client support but may still use placeholders
2. **Error Handling**: Need comprehensive failure scenario documentation
3. **CloudWatch Alarms**: Still need specific alarm configurations

## Agent-Specific Notes

### Work Journal Agent
- Appends to weekly logs: `work/weekly_logs/{year}-W{week}.md`
- Each entry includes ISO-8601 timestamp
- TODO: Add Claude for weekly summaries

### Memory Agent
- Stores as JSONL in `memories/{date}.jsonl`
- Schema: `{timestamp, content, sentiment, themes, people}`
- TODO: Implement sentiment analysis

### GitHub Idea Agent
- Creates public repos by default
- Generates repo name from idea content
- Stores history in `github/history.jsonl`
- Requires GitHub PAT in Secrets Manager

## Testing Strategy

1. **Unit Tests**: Test each agent in isolation with mock S3/GitHub
2. **Integration Tests**: Test full pipeline with real AWS resources
3. **Local Runner**: Mimics Lambda execution for rapid development

## Philosophy & Vision

This isn't just a transcription tool - it's a "cognitive exoskeleton" for capturing and acting on thoughts. The friction-free capture (just speak) combined with intelligent routing makes it powerful for:
- Maintaining work journals without typing
- Preserving personal memories with context
- Turning shower thoughts into GitHub projects

Future extensions could include:
- Dream journal agent
- Task/TODO agent
- Family update agent
- Learning notes agent

## Quick Fixes & Common Issues

1. **S3 Permissions**: Lambda needs `s3:GetObject` and `s3:PutObject`
2. **Strands Registration**: Run `scripts/register_agents.py` after deployment
3. **Local Testing**: Use `test_data/` directory structure matching S3
4. **GitHub Token**: Must have `repo` scope for creating repositories

## Development Workflow

1. Make changes to agents in `agents/`
2. Run unit tests: `pytest tests/unit/test_{agent}.py`
3. Test locally: `python local_test_runner.py test_data/transcripts/{agent}/test.txt`
4. Run integration tests if touching infrastructure
5. Deploy with CDK if infrastructure changed
6. Monitor CloudWatch logs for Lambda execution

Remember: The goal is frictionless thought capture with intelligent automation. Keep the recording → action pipeline as simple as possible.