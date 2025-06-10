# Scripts

Utility scripts for local development and Strands integration.

- `local_test_runner.py` – simulates the Lambda by invoking agents on a transcript file
- `register_agents.py` – helper to register agents with the Strands platform

Place sample transcripts under `test_data/transcripts/<agent_name>/` and run the test runner:

```bash
python scripts/local_test_runner.py test_data/transcripts/work/test.txt
```
