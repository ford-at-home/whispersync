"""Work Journal Agent.

A sophisticated agent that manages work logs with AI-powered summaries and insights.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import datetime
import json
import logging
from dataclasses import dataclass

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


@dataclass
class WorkEntry:
    """Structured work entry with metadata."""

    timestamp: datetime.datetime
    content: str
    categories: List[str]
    key_points: List[str]
    sentiment: str


class WorkJournalAgent(BaseAgent):
    """Agent specialized in work journal management and analysis.
    
    WHY WORK JOURNAL AGENT:
    - Captures professional activities and accomplishments automatically
    - Provides structured logging for reflection and review cycles
    - Enables productivity pattern analysis and insights
    - Supports weekly summaries and goal tracking
    - Maintains professional development history
    """

    def __init__(self, bucket: str = None, correlation_id: str = None):
        """Initialize the work journal agent.

        Args:
            bucket: S3 bucket name for storage
            correlation_id: Request correlation ID for tracing
        """
        super().__init__(bucket=bucket, correlation_id=correlation_id)
        self.config = get_config()

        # Create agent with specialized tools
        if Agent:
            self.agent = Agent(
                system_prompt="""You are a work journal specialist with expertise in:
                - Analyzing work transcripts and extracting key accomplishments
                - Categorizing work activities (coding, meetings, planning, etc.)
                - Identifying patterns and trends in work habits
                - Generating insightful weekly summaries
                - Providing productivity insights
                
                When processing transcripts:
                1. Extract actionable items and accomplishments
                2. Identify the type of work activity
                3. Note any blockers or challenges mentioned
                4. Highlight achievements and progress made
                
                Be concise but thorough in your analysis.""",
                tools=[
                    self.append_work_log,
                    self.generate_weekly_summary,
                    self.analyze_productivity_patterns,
                    self.search_past_entries,
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
            Dictionary containing log_key, summary, and extracted metadata
            
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

            # Analyze transcript with Claude
            analysis = self._analyze_transcript(transcript)

            now = datetime.datetime.utcnow()
            year, week, _ = now.isocalendar()
            log_key = f"work/{weekly_logs}/{year}-W{week}.md"

            # Get existing content with proper error handling
            try:
                existing = self.s3.get_object(Bucket=self.bucket, Key=log_key)
                content = existing["Body"].read().decode()
                logger.info(f"Retrieved existing log: {log_key}")
            except self.s3.exceptions.NoSuchKey:
                content = f"# Work Journal - {year} Week {week}\n\n"
                logger.info(f"Created new log: {log_key}")
            except Exception as e:
                return self.handle_error(e, "s3_read_existing_log")

            # Format entry with analysis
            entry = f"""
## {now.strftime('%Y-%m-%d %H:%M')} UTC

**Categories:** {', '.join(analysis['categories'])}  
**Sentiment:** {analysis['sentiment']}

### Original Transcript
{transcript}

### Key Points
{chr(10).join(f'- {point}' for point in analysis['key_points'])}

### AI Summary
{analysis['summary']}

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

            # Prepare result with metadata
            result = {
                "status": "success",
                "log_key": log_key,
                "summary": analysis["summary"],
                "categories": analysis["categories"],
                "key_points": analysis["key_points"],
                "sentiment": analysis["sentiment"],
                "processing_time": self.get_processing_time(),
                "week": f"{year}-W{week}"
            }

            # Store detailed result for tracking
            output_key = generate_output_key("work", f"work_journal/{year}-W{week}.txt")
            self.store_result(result, output_key)

            # Emit success metrics
            self.emit_metric("WorkLogProcessingCompleted", 1.0)
            self.emit_metric("WorkLogProcessingTime", self.get_processing_time(), "Seconds")

            return result
            
        except Exception as e:
            return self.handle_error(e, "work_log_processing")

    @tool
    def generate_weekly_summary(
        self, week: Optional[int] = None, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate an AI-powered summary of the week's work.
        
        WHY WEEKLY SUMMARIES:
        - Provides high-level view for status reports and performance reviews
        - Identifies patterns and themes across multiple work sessions
        - Highlights major accomplishments that might be buried in daily details
        - Creates historical context for future decision-making

        Args:
            week: Week number (defaults to current week)
            year: Year (defaults to current year)

        Returns:
            Dictionary containing:
            - summary: Executive summary of the week
            - highlights: Major accomplishments
            - insights: Pattern analysis and observations
            - recommendations: Suggestions for improvement
        """
        if not self.s3:
            return {"summary": "S3 unavailable", "insights": []}

        # Default to current week if not specified
        if not week or not year:
            now = datetime.datetime.utcnow()
            year, week, _ = now.isocalendar()

        log_key = f"work_journal/{year}-W{week}.md"

        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key=log_key)
            content = obj["Body"].read().decode()

            # Use Claude to generate comprehensive summary with strategic insights
            # WHY AI SUMMARY: Humans often miss patterns in their own work.
            # Claude can identify productivity trends, skill development, and
            # strategic themes that emerge from daily activities.
            summary = self._generate_summary(content, week, year)

            # Save summary
            summary_key = f"work_journal/summaries/{year}-W{week}-summary.json"
            self.s3.put_object(
                Bucket=self.bucket,
                Key=summary_key,
                Body=json.dumps(summary, indent=2).encode("utf-8"),
                ContentType="application/json",
            )

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "error": str(e),
                "summary": "Unable to generate summary",
                "insights": [],
            }

    @tool
    def analyze_productivity_patterns(self, weeks: int = 4) -> Dict[str, Any]:
        """Analyze productivity patterns over recent weeks.
        
        WHY PATTERN ANALYSIS:
        - Identifies optimal working conditions and times
        - Reveals recurring blockers and challenges
        - Suggests areas for skill development or process improvement
        - Provides data-driven insights for career development
        
        ANALYSIS INCLUDES:
        - Activity distribution (coding vs meetings vs planning)
        - Sentiment trends over time
        - Productivity cycles and peak performance periods
        - Common themes and recurring challenges

        Args:
            weeks: Number of weeks to analyze (default: 4, covers ~1 month)

        Returns:
            Dictionary containing:
            - patterns: Identified productivity patterns
            - trends: Temporal trends in activity and sentiment
            - recommendations: Actionable suggestions for improvement
        """
        if not self.s3:
            return {"patterns": [], "recommendations": []}

        now = datetime.datetime.utcnow()
        current_year, current_week, _ = now.isocalendar()

        all_entries = []

        # Collect entries from recent weeks
        # WHY BACKWARDS ITERATION: Start from current week and go back in time
        for i in range(weeks):
            week = current_week - i
            year = current_year

            # Handle year boundary crossing (week numbers reset at year start)
            if week <= 0:
                week = 52 + week  # Wrap to previous year's week numbering
                year -= 1

            log_key = f"work_journal/{year}-W{week}.md"

            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=log_key)
                content = obj["Body"].read().decode()
                all_entries.append({"week": week, "year": year, "content": content})
            except Exception:
                continue

        if not all_entries:
            return {"patterns": ["No data available"], "recommendations": []}

        # Analyze patterns with Claude
        analysis = self._analyze_patterns(all_entries)

        return analysis

    @tool
    def search_past_entries(
        self, query: str, weeks_back: int = 12
    ) -> List[Dict[str, Any]]:
        """Search past work entries for specific content.

        Args:
            query: Search query
            weeks_back: How many weeks to search (default: 12)

        Returns:
            List of matching entries with context
        """
        if not self.s3:
            return []

        matches = []
        now = datetime.datetime.utcnow()
        current_year, current_week, _ = now.isocalendar()

        for i in range(weeks_back):
            week = current_week - i
            year = current_year

            if week <= 0:
                week = 52 + week
                year -= 1

            log_key = f"work_journal/{year}-W{week}.md"

            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=log_key)
                content = obj["Body"].read().decode()

                # Search for query in content
                if query.lower() in content.lower():
                    # Extract relevant entries
                    entries = content.split("\n## ")
                    for entry in entries:
                        if query.lower() in entry.lower():
                            matches.append(
                                {
                                    "week": f"{year}-W{week}",
                                    "preview": entry[:200] + "...",
                                    "log_key": log_key,
                                }
                            )
            except Exception:
                continue

        return matches[:10]  # Limit to 10 most recent matches

    def _analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """Analyze a transcript using Claude for intelligent categorization.
        
        WHY SEPARATE METHOD: Isolates AI interaction for easier testing and
        potential model switching. The prompt engineering is centralized here.
        
        ANALYSIS EXTRACTS:
        - Categories: Type of work activity (coding, meeting, planning, etc.)
        - Key Points: Accomplishments, decisions, and important outcomes
        - Sentiment: Overall tone (positive, neutral, challenging)
        - Summary: Concise overview of the work session
        """
        if not self.bedrock:
            # Fallback analysis without Claude for testing/degraded operation
            # WHY FALLBACK: System should function even when AI services are unavailable
            return {
                "summary": transcript[:100] + "...",
                "categories": ["general"],
                "key_points": [transcript[:50]],
                "sentiment": "neutral",
            }

        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "messages": [
                            {
                                "role": "user",
                                # WHY THIS PROMPT STRUCTURE:
                        # - Specific output format ensures consistent parsing
                        # - Enumerated instructions reduce ambiguity
                        # - Example categories guide consistent classification
                        # - Sentiment tracking enables mood/productivity correlation
                        "content": f"""Analyze this work transcript and extract:
1. A concise summary (2-3 sentences)
2. Categories (e.g., coding, meetings, planning, debugging, documentation)
3. 3-5 key points or accomplishments
4. Overall sentiment (positive, neutral, challenging)

Transcript: {transcript}

Respond in JSON format with keys: summary, categories, key_points, sentiment""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            return json.loads(result.get("content", [{}])[0].get("text", "{}"))

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return {
                "summary": transcript[:100] + "...",
                "categories": ["general"],
                "key_points": ["Analysis unavailable"],
                "sentiment": "neutral",
            }

    def _generate_summary(self, content: str, week: int, year: int) -> Dict[str, Any]:
        """Generate weekly summary using Claude."""
        if not self.bedrock:
            return {
                "week": f"{year}-W{week}",
                "summary": "Weekly summary unavailable",
                "highlights": [],
                "insights": [],
                "recommendations": [],
            }

        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2000,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""Generate a comprehensive weekly summary from these work journal entries.

Include:
1. Executive summary (3-4 sentences)
2. Major highlights and accomplishments
3. Key insights about work patterns
4. Recommendations for next week

Week: {year}-W{week}

Journal Content:
{content}

Respond in JSON format with keys: week, summary, highlights, insights, recommendations""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            return json.loads(result.get("content", [{}])[0].get("text", "{}"))

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "week": f"{year}-W{week}",
                "summary": "Unable to generate summary",
                "highlights": [],
                "insights": [],
                "recommendations": [],
            }

    def _analyze_patterns(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze productivity patterns across multiple weeks."""
        if not self.bedrock:
            return {
                "patterns": ["Pattern analysis unavailable"],
                "trends": [],
                "recommendations": [],
            }

        # Combine all content for analysis
        combined_content = "\n\n".join(
            [f"Week {e['year']}-W{e['week']}:\n{e['content']}" for e in entries]
        )

        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2000,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""Analyze these work journal entries from the past {len(entries)} weeks to identify:

1. Productivity patterns (when most productive, common blockers)
2. Work trends (increasing/decreasing focus areas)
3. Actionable recommendations for improvement

Content:
{combined_content[:8000]}  # Limit context size

Respond in JSON format with keys: patterns, trends, recommendations""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            return json.loads(result.get("content", [{}])[0].get("text", "{}"))

        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return {
                "patterns": ["Analysis failed"],
                "trends": [],
                "recommendations": [],
            }

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
    """Process work-related transcripts.

    This tool handles work journal entries, meeting notes, task updates,
    and any professional activities. It extracts key points, categorizes
    the work, and maintains organized weekly logs.
    
    WHY SEPARATE TOOL FUNCTION:
    - Provides a clean interface for the orchestrator to use
    - Wraps the agent's conversational interface with a simple function call
    - Enables easy testing and integration with other systems
    - Follows the Strands tool pattern for agent coordination
    """
    agent = get_work_journal_agent()
    # WHY THIS PROMPT: Gives the agent context about what action to take.
    # The agent can then decide which of its tools to use (append_work_log, etc.)
    prompt = f"Process this work transcript and append it to the journal: {transcript}"
    return agent(prompt)
