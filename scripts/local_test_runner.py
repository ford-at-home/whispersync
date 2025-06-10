"""Local test runner to mimic Lambda invocation."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from importlib import import_module

logging.basicConfig(level=logging.INFO)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
invoke_agent = import_module("lambda.router_handler").invoke_agent


def main(path: str, bucket: str = "local-bucket") -> None:
    key = str(Path(path))
    parts = Path(key).parts
    agent_name = parts[parts.index("transcripts") + 1] if "transcripts" in parts else parts[-2]

    with open(path, "r") as f:
        transcript = f.read()

    payload = {
        "transcript": transcript,
        "bucket": bucket,
        "source_s3_key": key,
    }

    result = invoke_agent(agent_name, payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python local_test_runner.py <transcript_path>")
        sys.exit(1)
    main(sys.argv[1])
