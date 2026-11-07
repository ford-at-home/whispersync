"""Register agents with Strands platform.

WHY THIS SCRIPT EXISTS:
- Automates agent registration process for deployment consistency
- Ensures all agents are properly registered with correct metadata
- Provides single point of configuration for agent discovery
- Enables automated deployment pipelines to register agents
- Maintains agent descriptions and entrypoints in version control

DESIGN DECISIONS:
- Uses simple imperative calls rather than config files for clarity
- Matches agent filenames to maintain consistency
- Descriptive names explain agent purpose for platform discovery
- Entrypoints use relative paths for deployment portability

USAGE:
Run after CDK deployment to register agents with Strands platform:
  python scripts/register_agents.py

Or integrate into deployment pipeline for automated registration.
"""

from strands_sdk import register_agent

# WHY work_journal_agent: Core productivity feature for work logging
# Summarizes daily activities into structured weekly logs
register_agent(
    name="work_journal_agent",
    description="Summarizes and logs weekly work activity.",
    entrypoint="agents/work_journal_agent.py",
)

# WHY memory_agent: Personal life documentation and archival
# Processes personal memories with sentiment analysis and tagging
register_agent(
    name="memory_agent",
    description="Cleans and archives personal memories.",
    entrypoint="agents/memory_agent.py",
)

# WHY github_idea_agent: Innovation capture and project initialization
# Transforms voice ideas into actionable GitHub repositories
register_agent(
    name="github_idea_agent",
    description="Turns voice ideas into GitHub repos.",
    entrypoint="agents/github_idea_agent.py",
)
