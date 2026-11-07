- Voice memos are recorded on an iPhone and transcribed.
- Transcripts are uploaded to S3 under `transcripts/{agent_name}/{timestamp}.txt`.
- An S3 `ObjectCreated` event on the `transcripts/` prefix triggers a Lambda.
- The Lambda identifies the agent from the key, downloads the transcript, and
  invokes the matching Strands agent.
- Results from an agent are stored under `outputs/{agent_name}/..._response.json`
  in the same bucket. Each agent may also maintain a `history.jsonl` file.
- **Supported agents**:
  - `work` → **Work Journal Agent**
    - Appends entries to a weekly work log in S3.
    - Generates weekly summaries.
    - Suggests reflection or feedback actions using Claude.
  - `memories` → **Memory Agent**
    - Stores cleaned memory narratives as `.jsonl` under `memories/`.
    - Can classify sentiment, theme and key figures.
    - Uses Claude to clean up or stylize memories.
  - `github_ideas` → **GitHub Agent**
    - Creates new repos from voice ideas.
    - Uses Claude to generate repo name, README and an initial issue list.
    - Creates repositories using PyGithub.
    - Writes metadata to `s3://voice-mcp/github/history.jsonl`.
- AWS infrastructure must include an S3 bucket named `voice-mcp` and a Lambda
  function `mcpAgentRouterLambda` with permissions for S3 access, Bedrock model
  invocation and GitHub token retrieval from Secrets Manager.
- Local testing involves running `local_test_runner.py` with a transcript path to
  mimic Lambda invocation.
