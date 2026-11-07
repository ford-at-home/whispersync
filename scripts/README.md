# Scripts Directory

Utility scripts for local development and Strands integration.

## Purpose and Design Philosophy

This directory contains development automation scripts that bridge local development with production infrastructure. Each script serves a specific role in the development workflow:

### WHY THESE SCRIPTS EXIST:
- **Rapid Development Feedback**: Test agent logic without AWS costs or complexity
- **Deployment Automation**: Consistent agent registration across environments  
- **Development Workflow**: Bridge unit tests and integration tests
- **Production Parity**: Simulate production data flow locally

## Script Documentation

### `local_test_runner.py`
**Purpose**: Simulates the Lambda environment for testing agent pipeline locally

**WHY THIS DESIGN**:
- Enables instant feedback during agent development
- Supports both file-based and interactive testing modes
- Falls back gracefully when Strands SDK unavailable
- Maintains production S3 key structure for realistic testing
- Provides rich output for debugging agent behavior

**Usage Examples**:
```bash
# Test with specific transcript file
python scripts/local_test_runner.py test_data/transcripts/work/test.txt

# Interactive mode for exploring agent responses
python scripts/local_test_runner.py

# Test memory agent with sample data
python scripts/local_test_runner.py test_data/transcripts/memories/personal_note.txt
```

**Key Features**:
- Auto-detects agent type from file path structure
- Supports both legacy single-agent and new orchestrator modes
- Provides detailed output including routing decisions and agent results
- Mimics production Lambda handler interface

### `register_agents.py`
**Purpose**: Registers all agents with the Strands platform for deployment

**WHY THIS DESIGN**:
- Single source of truth for agent metadata
- Automates deployment consistency
- Version controls agent descriptions and entrypoints
- Enables CI/CD integration for agent registration

**Usage**:
```bash
# Register all agents after deployment
python scripts/register_agents.py

# Typically run as part of deployment pipeline
cd infrastructure && cdk deploy && python ../scripts/register_agents.py
```

**Agent Registry**:
- `work_journal_agent`: Summarizes and logs weekly work activity
- `memory_agent`: Cleans and archives personal memories with sentiment analysis
- `github_idea_agent`: Transforms voice ideas into GitHub repositories

## Development Workflow Integration

### Local Testing Flow:
1. Develop agent logic in `agents/` directory
2. Create test transcript in `test_data/transcripts/{agent}/`
3. Run `python scripts/local_test_runner.py test_data/transcripts/{agent}/test.txt`
4. Iterate on agent implementation based on local results
5. Run unit tests: `make test-unit`
6. Deploy and register: `cd infrastructure && cdk deploy && python ../scripts/register_agents.py`

### Directory Structure Requirements:
```
test_data/
├── transcripts/
│   ├── work/
│   │   └── test.txt
│   ├── memories/
│   │   └── personal_note.txt
│   └── github_ideas/
│       └── app_idea.txt
```

**WHY THIS STRUCTURE**: Matches production S3 key pattern (`transcripts/{agent}/{file}`) for realistic routing simulation.

## Environment Setup

### Dependencies:
- Core: Python 3.11+, basic project dependencies
- Optional: Strands SDK (scripts degrade gracefully without it)
- Development: pytest, black, flake8 (installed via `make install`)

### Configuration:
- No additional configuration required
- Scripts auto-detect project structure
- Graceful fallback when dependencies unavailable

## Troubleshooting

### Common Issues:
1. **ImportError for Strands**: Normal during development, scripts continue with fallback mode
2. **Path not found**: Ensure running from project root directory
3. **Agent not found**: Check file path matches `transcripts/{agent_name}/` pattern

### Development Tips:
- Use interactive mode for exploring agent responses
- Check agent routing with different transcript content
- Verify agent tools are working correctly before deployment
- Test error handling with malformed input
