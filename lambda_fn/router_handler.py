"""Lambda entry point to route transcripts to Strands agents."""
import json
import logging
import os

try:
    from strands import Agent
    from agents.work_journal_agent import append_work_log
    from agents.memory_agent import store_memory
    from agents.github_idea_agent import create_github_repo
except ImportError:  # pragma: no cover - optional for local testing
    Agent = None
    append_work_log = None
    store_memory = None
    create_github_repo = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Entry point for AWS Lambda to route transcripts."""
    if Agent is None:
        raise RuntimeError("strands-agents is required for lambda_handler")
        
    logger.info("Received event: %s", json.dumps(event))

    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    agent_name = key.split("/")[1]
    logger.info("Parsed agent: %s", agent_name)

    # Get transcript from S3
    import boto3
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    transcript = obj["Body"].read().decode()
    logger.info("Transcript downloaded, %d bytes", len(transcript))

    # Create agent with appropriate tools based on agent type
    agent_tools_map = {
        "work": [append_work_log],
        "memories": [store_memory],
        "github_ideas": [create_github_repo],
    }
    
    if agent_name not in agent_tools_map:
        raise ValueError(f"Unknown agent: {agent_name}")
    
    tools = agent_tools_map[agent_name]
    agent = Agent(tools=tools)
    
    # Create a natural language prompt for the agent
    prompt_map = {
        "work": f"Please log this work transcript: {transcript}",
        "memories": f"Please store this memory: {transcript}",
        "github_ideas": f"Please create a GitHub repository for this idea: {transcript}",
    }
    
    prompt = prompt_map[agent_name]
    
    try:
        result = agent(prompt)
        # Extract the result from the agent response
        if hasattr(result, 'message') and hasattr(result.message, 'content'):
            # The agent returned a structured result
            content = result.message.content
            if isinstance(content, list) and len(content) > 0:
                # Extract text from the first content item
                result_data = content[0].get('text', str(content[0]))
            else:
                result_data = str(content)
        else:
            result_data = str(result)
            
        # Try to parse as JSON if it looks like JSON
        try:
            if isinstance(result_data, str) and result_data.strip().startswith('{'):
                result_data = json.loads(result_data)
        except json.JSONDecodeError:
            pass
            
    except Exception as exc:
        logger.exception("Agent invocation failed: %s", exc)
        raise

    # Write response back to S3
    output_key = key.replace("transcripts/", "outputs/").replace(".txt", "_response.json")
    body = json.dumps(result_data).encode("utf-8") if not isinstance(result_data, (bytes, bytearray)) else result_data
    s3.put_object(Bucket=bucket, Key=output_key, Body=body)
    logger.info("Wrote response to %s", output_key)

    return {"status": "ok", "output_key": output_key}
