# Scripts

Utility scripts for local development and integration with the
Strands platform. They allow you to exercise the agents without
deploying any AWS infrastructure.

- `local_test_runner.py` – simulates the Lambda by invoking agents on a transcript file
- `register_agents.py` – helper to register agents with the Strands platform

Place sample transcripts under `test_data/transcripts/<agent_name>/` and run the test runner:

```bash
python scripts/local_test_runner.py test_data/transcripts/work/test.txt
```

``register_agents.py`` only needs to be run when a new agent module is
added or its metadata changes.
