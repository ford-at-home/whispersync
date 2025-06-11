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

Every module exposes a ``handle(payload: dict)`` function which the Lambda
router or Strands platform can call.  The payload always includes the
transcript text, the target S3 bucket and the source object key.
