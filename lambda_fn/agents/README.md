# Agents

This package contains the Strands agents that process voice memo transcripts.

## WHY THREE SEPARATE AGENTS

**Domain Specialization**: Each agent handles a distinct type of content with specialized logic and outputs.

**Independent Evolution**: Work logging needs differ from memory preservation, which differs from code project creation.

**Failure Isolation**: If one agent has issues, the others continue working normally.

**Clear Mental Model**: Users can predict which agent will handle their memo based on content type.

- `work_journal_agent.py` – appends weekly work journal logs and returns a summary.
- `memory_agent.py` – archives personal memories as JSON Lines.
- `github_idea_agent.py` – creates a GitHub repository from a transcript using PyGithub.

### WHY THESE SPECIFIC AGENT PURPOSES

**Work Journal Agent**: Knowledge workers need to track progress and reflect on achievements. Voice memos capture context that written logs miss - the "why" behind decisions, the emotions during challenges, the insights that emerge.

**Memory Agent**: Personal memories fade unless preserved with context. AI can extract emotional themes, identify important people and places, and connect memories across time in ways humans miss in the moment.

**GitHub Idea Agent**: Great ideas die in note-taking apps. Immediate repo creation with AI-generated structure reduces the activation energy for turning thoughts into projects.

Each module exposes a `handle(payload: dict)` function used by the Lambda router or Strands platform.

## Strands SDK Usage

### WHY TWO DIFFERENT IMPORT PATTERNS

**Separation of Concerns**: The core `strands` package defines agent structure, while `strands_sdk` handles runtime operations.

**Deployment Flexibility**: Agent definitions can be validated without requiring full SDK infrastructure.

**Clear Dependencies**: Import patterns make it obvious which functionality requires which package.

The agents use two different import patterns from the Strands SDK:
- `from strands import Agent, tool` - For defining agent classes and tool decorators
- `from strands_sdk import invoke_agent` - For invoking registered agents from Lambda

### WHY CONSISTENT `handle()` FUNCTION SIGNATURE

**Standardized Interface**: Lambda router can call any agent with the same function signature.

**Testing Simplicity**: Unit tests use identical setup across all agents.

**Future Composability**: Agents could potentially call each other using the same interface.

**Error Handling**: Consistent error response format across all agents.
