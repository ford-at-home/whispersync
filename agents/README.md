# Agents

This package contains the Strands agents that process voice memo transcripts.

- `work_journal_agent.py` – appends weekly work journal logs and returns a summary.
- `memory_agent.py` – archives personal memories as JSON Lines.
- `github_idea_agent.py` – creates a GitHub repository from a transcript using PyGithub.

Each module exposes a `handle(payload: dict)` function used by the Lambda router or Strands platform.
