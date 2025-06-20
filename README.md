# 🧠 Voice Memo MCP Agent System (AWS + Strands Edition)

This project turns iPhone voice memos into intelligent workflows, automatically routed to different agents based on folder/prefix and powered by AWS Strands.

---

## 📦 Overview

### Use Case
You record voice memos into folders like `work`, `memories`, or `github_ideas` on your iPhone. These are transcribed (locally or remotely), synced to S3, and processed via AWS Strands agents triggered by S3 events.

---

## 📁 Architecture

### 📤 Input
- Transcriptions are synced into:
s3://<YOUR_BUCKET>/transcripts/{agent_name}/{timestamp}.txt

makefile
Copy
Edit
Example:
s3://voice-mcp/transcripts/work/2025-06-09_1030.txt

yaml
Copy
Edit

### ⚙️ Trigger
- S3 `ObjectCreated` event on prefix `transcripts/`
- Triggers a Lambda that:
1. Extracts the agent name from the key
2. Fetches the transcript
3. Passes content + context to a registered Strands agent

---

## 🤖 Supported Agents

### 1. `work` → 🧾 Work Journal Agent
- Appends entries to a weekly work log in S3
- Generates weekly summaries
- Suggests reflection or feedback actions using Claude

### 2. `memories` → 🧠 Memory Agent
- Stores memory narratives in `memories/` as `.jsonl`
- Optionally classifies sentiment, theme, and key figures
- Claude can clean up or stylize the memory

### 3. `github_ideas` → 🐙 GitHub Agent
- Creates new repos based on ideas
- Uses Claude to generate:
- Repo name
- README
- Initial issue list
- Calls GitHub API (via `PyGithub`)
- Stores metadata in `s3://voice-mcp/github/history.jsonl`

---

## 🧬 AWS Architecture

```mermaid
graph TD
subgraph iPhone
  A1[Voice Memo App] --> A2[Transcription Script]
  A2 --> A3[S3: /transcripts/...]
end

A3 -->|S3 Event| B1[Lambda: router_handler.py]
B1 -->|agent_name| B2[Strands Agent Router]
B2 -->|Claude / GitHub / Memory| C[Agent Action Result]
C --> D1[S3: /outputs/...]
🛠️ Setup
1. Deploy Infrastructure (CDK or Terraform)
Create an S3 bucket: voice-mcp

Enable ObjectCreated:* events on prefix transcripts/

Create a Lambda: mcpAgentRouterLambda

Grant Lambda permissions:

s3:GetObject

bedrock:InvokeModel

secretsmanager:GetSecretValue (for GitHub token)

2. Strands Agent Registration
Define agents locally using the Strands SDK:

```python
from strands import Agent, tool

@tool
def work_journal_agent(transcript: str, bucket: str) -> dict:
    ...

agent = Agent(tools=[work_journal_agent])
```
3. Store GitHub Token
In AWS Secrets Manager:

makefile
Copy
Edit
Name: github/personal_token
Value: <YOUR_TOKEN>
🐍 Lambda Logic (router_handler.py)
python
Copy
Edit
import boto3, os
from strands import Agent
from agents.work_journal_agent import handle as work_journal_agent

s3 = boto3.client('s3')

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key    = event['Records'][0]['s3']['object']['key']
    
    agent_name = key.split("/")[1]
    obj = s3.get_object(Bucket=bucket, Key=key)
    transcript = obj['Body'].read().decode()

    agent = Agent(tools=[work_journal_agent])
    result = agent(transcript)
    
    output_key = key.replace("transcripts", "outputs").replace(".txt", "_response.json")
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=str(result).encode("utf-8")
    )
🧪 Test Locally
Place transcript in test_data/transcripts/work/2025-06-09_1230.txt

Run:

```bash
python local_test_runner.py transcripts/work/2025-06-09_1230.txt
```
Use `--stream` to stream events and `--callback` to enable the demo callback
handler. This mimics the Lambda + S3 pipeline and prints the result.

📓 Logs & Output
Processed agent responses go to:

```
s3://<YOUR_BUCKET>/outputs/{agent}/{date}_response.json
```

Agent history (optional) written to:

```
s3://<YOUR_BUCKET>/{agent}/history.jsonl
```

## 🌀 Streaming Responses with Async Iterators

The Strands Agents SDK supports asynchronous iterators for real‑time
streaming. Use `stream_async()` on an agent to iterate over events as
they are produced. This is ideal for async frameworks like FastAPI.

```python
import asyncio
from strands import Agent
from strands_tools import calculator

agent = Agent(tools=[calculator], callback_handler=None)

async def process_streaming_response():
    async for event in agent.stream_async("Calculate 2+2"):
        print(event)

asyncio.run(process_streaming_response())
```

### Event Types

The async iterator yields the same event payloads as callback handlers:

- **Text Generation**: `data`, `complete`, `delta`
- **Tool Events**: `current_tool_use` with `toolUseId`, `name`, and
  accumulated `input`
- **Lifecycle**: `init_event_loop`, `start_event_loop`, `start`, `message`,
  raw `event`, `force_stop`, `force_stop_reason`
- **Reasoning**: `reasoning`, `reasoningText`, `reasoning_signature`

### FastAPI Example

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from strands import Agent
from strands_tools import calculator, http_request

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

@app.post("/stream")
async def stream_response(request: PromptRequest):
    async def generate():
        agent = Agent(tools=[calculator, http_request], callback_handler=None)
        try:
            async for event in agent.stream_async(request.prompt):
                if "data" in event:
                    yield event["data"]
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")
```

## 🛎️ Callback Handlers

Callback handlers intercept events as they occur. Pass a function via the
`callback_handler` parameter:

```python
from strands import Agent
from strands_tools import calculator

def custom_callback_handler(**kwargs):
    if "data" in kwargs:
        print(f"MODEL OUTPUT: {kwargs['data']}")

agent = Agent(tools=[calculator], callback_handler=custom_callback_handler)
agent("Calculate 2+2")
```

Handlers receive the same event types as async iterators. The default
`PrintingCallbackHandler` prints text and tool usage. Specify `None` to
disable output entirely.
📅 Future Extensions
Schedule weekly summary via EventBridge + Step Functions

Store vector embeddings in Pinecone or OpenSearch for memories

Add family, dreams, or spiritual agents

Use Claude for suggestion chaining or emotional tone analysis

🧼 Requirements
Dependency	Version
Python	3.11+
boto3	latest
strands-agents	latest
PyGithub	latest
AWS Lambda runtime	python3.11

🧠 Philosophy
This system is not a productivity hack.
It’s a cognitive exoskeleton — built to support memory, reflection, and effortless ideation through natural speech and structured automation.

📫 Contact
For help, ideas, or weird bugs, open an issue or whisper into the nearest tree.
