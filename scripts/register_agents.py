"""Register agents with the Strands platform.

Running this script will create or update agent records so that the
platform knows how to invoke the local implementation modules.
"""
try:
    from strands import register_agent
except Exception:  # pragma: no cover - optional
    def register_agent(**kwargs):
        print(f"register_agent called with: {kwargs['name']}")

register_agent(
    name="work_journal_agent",
    description="Summarizes and logs weekly work activity.",
    entrypoint="agents/work_journal_agent.py",
)

register_agent(
    name="memory_agent",
    description="Cleans and archives personal memories.",
    entrypoint="agents/memory_agent.py",
)

register_agent(
    name="github_idea_agent",
    description="Turns voice ideas into GitHub repos.",
    entrypoint="agents/github_idea_agent.py",
)
