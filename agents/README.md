# Agents

This package contains the Python modules that implement the individual
agents invoked by the WhisperSync Lambda router.  Each agent receives the
transcribed text of a voice memo and performs a specialized action.

- `work_journal_agent.py` – Appends entries to a weekly work log stored in
  S3 and returns a short summary confirming the write.
- `memory_agent.py` – Stores personal memories as JSON Lines files in S3
  for later analysis.
- `github_idea_agent.py` – Creates a new GitHub repository from an idea
  described in the transcript.  Metadata about the repo is also logged to
  S3.

Each module exposes a ``handle`` function decorated with ``@tool``. The
function parameters are individually typed (e.g. ``transcript: str`` and
``bucket: str``) so the Strands framework can derive a tool specification
automatically. These functions can be invoked directly with keyword
arguments or via the ``Agent`` class.
