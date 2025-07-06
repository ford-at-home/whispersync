"""Work Journal Agent.

Minimal working implementation for MVP that logs work transcripts to weekly markdown files.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import datetime
import logging

# Import base functionality with configuration
from .base import (
    BaseAgent, 
    Agent, 
    tool,
    requires_aws,
    validate_transcript,
    generate_output_key,
    ProcessingError,
    bedrock_knowledge_base_retrieve
)
from .config import get_config


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WorkJournalAgent(BaseAgent):
    """Minimal work journal agent for MVP implementation.
    
    WHY MINIMAL WORK JOURNAL AGENT:
    - Captures work transcripts with timestamps
    - Maintains weekly logs in markdown format
    - Provides simple append-only operations
    - Handles year boundaries gracefully
    - Returns success confirmation with log location
    """

    def __init__(self, bucket: str = None, correlation_id: str = None):
        """Initialize the work journal agent.

        Args:
            bucket: S3 bucket name for storage
            correlation_id: Request correlation ID for tracing
        """
        super().__init__(bucket=bucket, correlation_id=correlation_id)
        self.config = get_config()

        # Create agent with minimal tools for MVP
        if Agent:
            self.agent = Agent(
                system_prompt="""You are a minimal work journal agent focused on:
                - Logging work transcripts with timestamps
                - Maintaining weekly work logs in markdown format
                - Providing simple append-only operations
                
                When processing transcripts:
                1. Simply append the transcript to the appropriate weekly log
                2. Use ISO-8601 timestamp format
                3. Return success confirmation with log location
                
                Keep it simple and reliable.""",
                tools=[
                    self.append_work_log,
                ],
                model=self.config.aws.bedrock_model,
            )
        else:
            self.agent = None

    @tool
    @requires_aws
    def append_work_log(self, transcript: str) -> Dict[str, Any]:
        """Process and append a work transcript to the weekly log.

        Args:
            transcript: The work transcript to process and store

        Returns:
            Dictionary containing log_key and success status
            
        WHY WEEKLY LOGS:
        - Balances detail retention with manageable file sizes
        - Aligns with natural work reflection cycles
        - Enables weekly summary generation and review
        - Provides logical partitioning for search and analysis
        """
        # Validate input
        if not validate_transcript(transcript):
            return self.handle_error(
                ProcessingError("Invalid transcript content"),
                "transcript_validation",
                retryable=False
            )
        
        try:
            # Track processing time
            self.emit_metric("WorkLogProcessingStarted", 1.0)

            # Get current time with ISO-8601 format
            now = datetime.datetime.utcnow()
            year, week, _ = now.isocalendar()
            log_key = f"work/weekly_logs/{year}-W{week:02d}.md"

            # Get existing content with proper error handling
            try:
                existing = self.s3.get_object(Bucket=self.bucket, Key=log_key)
                content = existing["Body"].read().decode()
                logger.info(f"Retrieved existing log: {log_key}")
            except self.s3.exceptions.NoSuchKey:
                content = f"# Work Journal - {year} Week {week:02d}\n\n"
                logger.info(f"Created new log: {log_key}")
            except Exception as e:
                return self.handle_error(e, "s3_read_existing_log")

            # Format entry with simple timestamp and transcript
            entry = f"""## {now.isoformat()}Z

{transcript}

---

"""

            content += entry

            # Save updated log with proper error handling
            try:
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=log_key,
                    Body=content.encode("utf-8"),
                    ContentType="text/markdown",
                    Metadata={
                        "week": str(week),
                        "year": str(year),
                        "entry_count": str(content.count("## 20")),
                        "correlation_id": self.correlation_id or "unknown",
                    },
                )
                logger.info(f"Appended work entry to {log_key}")
            except Exception as e:
                return self.handle_error(e, "s3_save_work_log")

            # Prepare minimal result
            result = {
                "status": "success",
                "log_key": log_key,
                "processing_time": self.get_processing_time(),
                "week": f"{year}-W{week:02d}",
                "message": f"Successfully logged work entry to {log_key}"
            }

            # Store detailed result for tracking
            output_key = generate_output_key("work", f"work_journal/{year}-W{week:02d}.txt")
            self.store_result(result, output_key)

            # Emit success metrics
            self.emit_metric("WorkLogProcessingCompleted", 1.0)
            self.emit_metric("WorkLogProcessingTime", self.get_processing_time(), "Seconds")

            return result
            
        except Exception as e:
            return self.handle_error(e, "work_log_processing")




    def __call__(self, prompt: str) -> Any:
        """Make the agent callable for Strands compatibility."""
        if self.agent:
            return self.agent(prompt)
        else:
            # Fallback for testing without Strands
            return {"message": "Agent not available", "prompt": prompt}


# Create a singleton instance for Lambda use
# WHY SINGLETON: Lambda containers can be reused across invocations.
# Reusing the agent instance (and its AWS clients) improves performance
# by avoiding repeated initialization costs.
work_journal_agent = None


def get_work_journal_agent(bucket: str = None) -> WorkJournalAgent:
    """Get or create the work journal agent instance.
    
    Implements singleton pattern for Lambda efficiency. The agent instance
    and its AWS clients are reused across Lambda invocations when the
    container is warm.
    """
    global work_journal_agent
    if work_journal_agent is None:
        work_journal_agent = WorkJournalAgent(bucket=bucket)
    return work_journal_agent


# Legacy compatibility
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy handler function for backward compatibility."""
    agent = get_work_journal_agent(bucket=payload.get("bucket"))
    return agent.append_work_log(transcript=payload.get("transcript", ""))


# Tool wrapper for orchestrator use
@tool
def work_journal_tool(transcript: str) -> Dict[str, Any]:
    """Process work-related transcripts with minimal logging.

    This tool handles work journal entries by appending them to weekly logs
    with timestamps. No AI analysis - just simple logging for MVP.
    
    WHY SEPARATE TOOL FUNCTION:
    - Provides a clean interface for the orchestrator to use
    - Wraps the agent's conversational interface with a simple function call
    - Enables easy testing and integration with other systems
    - Follows the Strands tool pattern for agent coordination
    """
    agent = get_work_journal_agent()
    # WHY THIS PROMPT: Gives the agent context about what action to take.
    # The agent will use the append_work_log tool directly
    prompt = f"Log this work transcript to the weekly journal: {transcript}"
    return agent(prompt)
