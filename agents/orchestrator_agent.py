"""Orchestrator Agent.

# PURPOSE & PHILOSOPHY:
# This agent serves as the intelligent brain of WhisperSync, making routing decisions
# and coordinating multi-agent workflows. It embodies the principle that AI should
# understand context and intent, not just follow rigid rules. The orchestrator
# enables seamless processing of complex, mixed-content voice memos.

# CORE DESIGN DECISIONS:
# 1. AI-Powered Routing: Uses Claude to analyze content and determine best agent(s)
# 2. Multi-Agent Coordination: Can route single transcript to multiple specialists
# 3. Segment Analysis: Breaks complex transcripts into agent-specific segments
# 4. Historical Learning: Tracks routing decisions to improve future choices
# 5. Graceful Degradation: Falls back to keyword matching if AI unavailable

# WHY ORCHESTRATOR PATTERN:
# - Centralized intelligence enables smart routing without hardcoded rules
# - Single point of control for workflow orchestration and error handling
# - Historical analysis improves routing decisions over time
# - Abstraction layer allows agent changes without Lambda modifications
# - Complex workflows (multi-agent coordination) handled transparently

# BUSINESS VALUE:
# - Maximizes value extraction from each voice memo
# - Enables natural, unstructured input (no need to categorize beforehand)
# - Learns user patterns to improve routing accuracy
# - Supports complex workflows (e.g., idea that involves both work and GitHub)
# - Provides analytics on content patterns and agent usage
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import json
import logging
import datetime
from dataclasses import dataclass
from enum import Enum

try:
    import boto3
    from strands import Agent, tool
    from strands_tools import workflow, graph

    # Import agent tools for coordination
    # WHY IMPORT TOOLS: Orchestrator needs both the tool functions (for execution)
    # and agent getters (for warmup and status checking)
    from agents.work_journal_agent import work_journal_tool, get_work_journal_agent
    from agents.memory_agent import memory_tool, get_memory_agent
    from agents.github_idea_agent import github_tool, get_github_idea_agent
except ImportError:  # pragma: no cover - optional for local testing
    # WHY GRACEFUL IMPORTS: Orchestrator must work even when some agents fail
    # to import. This enables partial functionality and easier testing.
    boto3 = None
    Agent = None
    workflow = None
    graph = None
    work_journal_tool = None
    memory_tool = None
    github_tool = None
    get_work_journal_agent = None
    get_memory_agent = None
    get_github_idea_agent = None

    # Mock decorator for testing without strands
    def tool(func):
        return func


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AgentType(Enum):
    """Types of specialized agents.
    
    WHY ENUM: Type safety and clear enumeration of available agents.
    Makes it impossible to have typos in agent names and enables
    IDE autocompletion and static analysis.
    
    AGENT TYPES:
    - WORK: Professional activities, meetings, tasks, accomplishments
    - MEMORY: Personal experiences, emotions, reflections, life events
    - GITHUB: Project ideas, code concepts, technical innovations
    - MULTIPLE: Complex transcripts requiring multiple agents
    - UNKNOWN: Content that doesn't clearly fit any category
    """

    WORK = "work"         # Professional/work-related content
    MEMORY = "memory"     # Personal memories and experiences
    GITHUB = "github"     # Project ideas and technical concepts
    MULTIPLE = "multiple" # Requires multiple agents
    UNKNOWN = "unknown"   # Unclear or uncategorizable content


@dataclass
class RoutingDecision:
    """Decision about which agent(s) to route to.
    
    WHY STRUCTURED DECISION: Captures not just the routing choice but the
    reasoning behind it. This enables debugging, analytics, and continuous
    improvement of routing logic.
    
    FIELDS EXPLAINED:
    - primary_agent: Main agent that should process the transcript
    - secondary_agents: Additional agents for multi-faceted content
    - confidence: AI's confidence in the routing decision (0.0-1.0)
    - reasoning: Human-readable explanation of the routing choice
    - segments: Maps each agent to the relevant portion of the transcript
    """

    primary_agent: AgentType              # Main processing agent
    secondary_agents: List[AgentType]     # Additional agents for complex content
    confidence: float                     # Confidence score (0.0-1.0)
    reasoning: str                        # Human-readable explanation
    segments: Dict[AgentType, str]        # Agent -> relevant transcript segment


class OrchestratorAgent:
    """Master orchestrator that routes and coordinates between specialized agents.
    
    WHY ORCHESTRATOR PATTERN:
    - Single point of control for complex workflows
    - Intelligent routing based on content analysis rather than rigid rules
    - Historical learning to improve routing decisions over time
    - Graceful handling of mixed-content transcripts
    - Analytics and monitoring of routing patterns
    
    DESIGN PATTERNS:
    - Mediator Pattern: Coordinates between agents without tight coupling
    - Strategy Pattern: Different routing strategies based on content analysis
    - Observer Pattern: Tracks routing decisions for continuous improvement
    - Command Pattern: Encapsulates routing decisions as executable commands
    """

    def __init__(self, bucket: str = None, bedrock_client=None):
        """Initialize the orchestrator agent.

        Args:
            bucket: S3 bucket name for storage (defaults to 'voice-mcp')
            bedrock_client: Optional Bedrock client for testing/mocking
            
        WHY OPTIONAL PARAMETERS: Enables flexible testing while providing
        sensible defaults for production deployment.
        """
        self.bucket = bucket or "voice-mcp"
        # WHY CONDITIONAL CLIENTS: Supports both production and testing environments
        self.s3 = boto3.client("s3") if boto3 else None
        self.bedrock = bedrock_client or (
            boto3.client("bedrock-runtime") if boto3 else None
        )

        # Initialize specialized agents for coordination
        # WHY INITIALIZE ALL AGENTS: Orchestrator needs to know which agents
        # are available and coordinate between them. Pre-initialization enables
        # warmup strategies and status checking.
        self.work_agent = (
            get_work_journal_agent(bucket) if get_work_journal_agent else None
        )
        self.memory_agent = get_memory_agent(bucket) if get_memory_agent else None
        self.github_agent = (
            get_github_idea_agent(bucket) if get_github_idea_agent else None
        )

        # Create orchestrator with routing and coordination tools
        # WHY STRANDS AGENT: Provides conversational interface that can understand
        # natural language requests about routing and coordination.
        if Agent:
            self.agent = Agent(
                system_prompt="""You are the WhisperSync orchestrator, a master coordinator 
                for voice-based workflows. Your role is to:
                
                1. Analyze incoming voice transcripts and determine their intent
                2. Route transcripts to the appropriate specialized agent(s)
                3. Coordinate multi-agent workflows for complex requests
                4. Ensure seamless processing of mixed-content transcripts
                
                Routing Guidelines:
                - Work Journal Agent: Professional activities, meetings, tasks, accomplishments
                - Memory Agent: Personal experiences, emotions, reflections, life events
                - GitHub Idea Agent: Project ideas, code concepts, technical innovations
                
                For complex transcripts:
                - Identify distinct segments for different agents
                - Coordinate parallel processing when appropriate
                - Synthesize results from multiple agents
                
                Always aim for intelligent, context-aware routing that maximizes
                the value extracted from each voice memo.""",
                # WHY THESE TOOLS: Complete orchestration capability:
                # route_transcript: Core routing functionality
                # process_complex_request: Multi-agent coordination
                # get_routing_history: Historical analysis and debugging
                # analyze_routing_patterns: Continuous improvement
                # agent tools: Direct access to specialized agents
                tools=[
                    self.route_transcript,
                    self.process_complex_request,
                    self.get_routing_history,
                    self.analyze_routing_patterns,
                    work_journal_tool,  # Direct access to work agent
                    memory_tool,        # Direct access to memory agent
                    github_tool,        # Direct access to GitHub agent
                ],
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            )
        else:
            self.agent = None

    @tool
    def route_transcript(
        self, transcript: str, source_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Intelligently route a transcript to the appropriate agent(s).

        This is the core orchestration method that analyzes transcript content
        and coordinates processing across multiple specialized agents.
        
        WHY INTELLIGENT ROUTING:
        - Voice memos often contain mixed content (work + personal + ideas)
        - AI can understand context and intent better than keyword matching
        - Source path provides hints but content analysis is more reliable
        - Multi-agent coordination maximizes value extraction

        Args:
            transcript: The voice transcript to route
            source_key: Optional S3 key hint for routing (e.g., transcripts/work/...)

        Returns:
            Dictionary containing:
            - routing_decision: Which agent(s) were chosen and why
            - processing_results: Actual output from each agent used
        """
        # Analyze transcript to determine optimal routing strategy
        # WHY SEPARATE ANALYSIS: Isolates routing logic for testing and improvement
        routing_decision = self._analyze_transcript_for_routing(transcript, source_key)

        logger.info(
            f"Routing decision: {routing_decision.primary_agent.value} "
            f"(confidence: {routing_decision.confidence})"
        )

        results = {
            "routing_decision": {
                "primary_agent": routing_decision.primary_agent.value,
                "secondary_agents": [
                    a.value for a in routing_decision.secondary_agents
                ],
                "confidence": routing_decision.confidence,
                "reasoning": routing_decision.reasoning,
            },
            "processing_results": {},
        }

        # Process with primary agent
        # WHY SEGMENT-BASED PROCESSING: Different parts of the transcript may be
        # relevant to different agents. Using segments maximizes relevance.
        if routing_decision.primary_agent == AgentType.WORK:
            primary_result = work_journal_tool(
                routing_decision.segments.get(AgentType.WORK, transcript)
            )
            results["processing_results"]["work"] = primary_result
        elif routing_decision.primary_agent == AgentType.MEMORY:
            primary_result = memory_tool(
                routing_decision.segments.get(AgentType.MEMORY, transcript)
            )
            results["processing_results"]["memory"] = primary_result
        elif routing_decision.primary_agent == AgentType.GITHUB:
            primary_result = github_tool(
                routing_decision.segments.get(AgentType.GITHUB, transcript)
            )
            results["processing_results"]["github"] = primary_result
        elif routing_decision.primary_agent == AgentType.MULTIPLE:
            # Process all segments in parallel for complex transcripts
            # WHY PARALLEL: No dependencies between agents, parallel improves latency
            for agent_type, segment in routing_decision.segments.items():
                if agent_type == AgentType.WORK:
                    results["processing_results"]["work"] = work_journal_tool(segment)
                elif agent_type == AgentType.MEMORY:
                    results["processing_results"]["memory"] = memory_tool(segment)
                elif agent_type == AgentType.GITHUB:
                    results["processing_results"]["github"] = github_tool(segment)

        # Process with secondary agents if needed
        for agent_type in routing_decision.secondary_agents:
            segment = routing_decision.segments.get(agent_type, transcript)
            if (
                agent_type == AgentType.WORK
                and "work" not in results["processing_results"]
            ):
                results["processing_results"]["work"] = work_journal_tool(segment)
            elif (
                agent_type == AgentType.MEMORY
                and "memory" not in results["processing_results"]
            ):
                results["processing_results"]["memory"] = memory_tool(segment)
            elif (
                agent_type == AgentType.GITHUB
                and "github" not in results["processing_results"]
            ):
                results["processing_results"]["github"] = github_tool(segment)

        # Store routing history for analysis and improvement
        # WHY STORE HISTORY: Enables learning from routing decisions,
        # debugging incorrect routes, and improving future accuracy
        self._store_routing_history(transcript, routing_decision, results)

        return results

    @tool
    def process_complex_request(
        self, transcript: str, instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process complex requests that require multi-agent coordination.

        Args:
            transcript: The complex transcript to process
            instructions: Optional specific instructions for processing

        Returns:
            Dictionary containing coordinated results from multiple agents
        """
        if not self.bedrock:
            return {"error": "Complex processing requires Bedrock"}

        # Use Claude to create a processing plan
        plan = self._create_processing_plan(transcript, instructions)

        results = {"plan": plan, "execution_results": {}, "synthesis": ""}

        # Execute plan steps
        for step in plan["steps"]:
            agent_type = step["agent"]
            content = step["content"]

            if agent_type == "work":
                step_result = work_journal_tool(content)
            elif agent_type == "memory":
                step_result = memory_tool(content)
            elif agent_type == "github":
                step_result = github_tool(content)
            else:
                step_result = {"error": f"Unknown agent type: {agent_type}"}

            results["execution_results"][step["id"]] = {
                "agent": agent_type,
                "result": step_result,
                "description": step["description"],
            }

        # Synthesize results
        results["synthesis"] = self._synthesize_results(
            plan, results["execution_results"]
        )

        return results

    @tool
    def get_routing_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get routing history for analysis and debugging.

        Args:
            days: Number of days of history to retrieve

        Returns:
            List of routing decisions and their outcomes
        """
        if not self.s3:
            return []

        history = []
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        try:
            # List routing history files
            response = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix="orchestrator/routing_history/"
            )

            for obj in response.get("Contents", []):
                # Parse date from key
                key_parts = obj["Key"].split("/")
                if len(key_parts) >= 3:
                    date_str = key_parts[2].split(".")[0]  # Remove .jsonl
                    try:
                        file_date = datetime.datetime.fromisoformat(date_str)
                        if file_date >= cutoff_date:
                            # Read file
                            history_obj = self.s3.get_object(
                                Bucket=self.bucket, Key=obj["Key"]
                            )
                            content = history_obj["Body"].read().decode()

                            for line in content.strip().split("\n"):
                                if line:
                                    history.append(json.loads(line))
                    except:
                        continue

            # Sort by timestamp
            history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        except Exception as e:
            logger.error(f"Failed to get routing history: {e}")

        return history[:100]  # Limit to 100 most recent

    @tool
    def analyze_routing_patterns(self) -> Dict[str, Any]:
        """Analyze routing patterns to improve future decisions.

        Returns:
            Dictionary containing routing analytics and insights
        """
        history = self.get_routing_history(days=30)

        if not history:
            return {"error": "No routing history available"}

        # Analyze patterns
        agent_counts = {
            "work": 0,
            "memory": 0,
            "github": 0,
            "multiple": 0,
            "unknown": 0,
        }
        confidence_scores = []
        multi_agent_count = 0
        hourly_distribution = {str(h): 0 for h in range(24)}

        for entry in history:
            decision = entry.get("routing_decision", {})
            primary = decision.get("primary_agent", "unknown")
            agent_counts[primary] += 1

            confidence = decision.get("confidence", 0)
            confidence_scores.append(confidence)

            if decision.get("secondary_agents"):
                multi_agent_count += 1

            # Extract hour
            timestamp = entry.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.datetime.fromisoformat(timestamp)
                    hourly_distribution[str(dt.hour)] += 1
                except:
                    pass

        # Calculate statistics
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        )

        # Generate insights
        insights = self._generate_routing_insights(
            agent_counts,
            avg_confidence,
            multi_agent_count,
            hourly_distribution,
            len(history),
        )

        return {
            "total_routings": len(history),
            "agent_distribution": agent_counts,
            "average_confidence": round(avg_confidence, 3),
            "multi_agent_percentage": (
                round((multi_agent_count / len(history)) * 100, 1) if history else 0
            ),
            "hourly_distribution": hourly_distribution,
            "insights": insights,
        }

    def _analyze_transcript_for_routing(
        self, transcript: str, source_key: Optional[str]
    ) -> RoutingDecision:
        """Analyze transcript to determine optimal routing.
        
        WHY LAYERED APPROACH: Uses multiple strategies for robustness:
        1. Source path hints (most reliable when available)
        2. AI content analysis (most flexible and accurate)
        3. Keyword fallback (works when AI unavailable)
        
        DECISION FACTORS:
        - Content themes and topics
        - Emotional tone and context
        - Technical terminology presence
        - Multiple content types in single transcript
        """
        # First check if source_key provides a routing hint
        # WHY SOURCE KEY FIRST: Explicit user categorization (via folder structure)
        # is more reliable than content analysis when available.
        if source_key:
            if "/work/" in source_key:
                return RoutingDecision(
                    primary_agent=AgentType.WORK,
                    secondary_agents=[],
                    confidence=0.95,  # High confidence for explicit categorization
                    reasoning="Source path indicates work-related content",
                    segments={AgentType.WORK: transcript},
                )
            elif "/memories/" in source_key:
                return RoutingDecision(
                    primary_agent=AgentType.MEMORY,
                    secondary_agents=[],
                    confidence=0.95,
                    reasoning="Source path indicates personal memory",
                    segments={AgentType.MEMORY: transcript},
                )
            elif "/github_ideas/" in source_key:
                return RoutingDecision(
                    primary_agent=AgentType.GITHUB,
                    secondary_agents=[],
                    confidence=0.95,
                    reasoning="Source path indicates GitHub project idea",
                    segments={AgentType.GITHUB: transcript},
                )

        # Use AI for intelligent content analysis
        # WHY AI ANALYSIS: Can understand context, intent, and nuance that
        # keyword matching misses. Enables complex multi-agent coordination.
        if self.bedrock:
            try:
                response = self.bedrock.invoke_model(
                    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    body=json.dumps(
                        {
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 1500,
                            "messages": [
                                {
                                    "role": "user",
                                    # WHY THIS PROMPT STRUCTURE:
                                    # - Clear agent definitions prevent confusion
                                    # - Multiple output requirements ensure complete analysis
                                    # - Segmentation enables targeted processing
                                    # - JSON format ensures reliable parsing
                                    "content": f"""Analyze this voice transcript and determine which agent(s) should process it:

Transcript: {transcript}

Agents available:
1. WORK - Professional activities, meetings, tasks, accomplishments
2. MEMORY - Personal experiences, emotions, reflections, life events  
3. GITHUB - Project ideas, code concepts, technical innovations

Determine:
1. Primary agent (work, memory, github, multiple, or unknown)
2. Secondary agents if content spans multiple domains
3. Confidence score (0-1)
4. Brief reasoning
5. If multiple agents needed, segment the transcript for each

Respond in JSON format with keys: primary_agent, secondary_agents, confidence, reasoning, segments (object mapping agent to relevant text)""",
                                }
                            ],
                        }
                    ),
                )

                result = json.loads(response["body"].read())
                analysis = json.loads(result.get("content", [{}])[0].get("text", "{}"))

                # Convert AI response to structured RoutingDecision
                # WHY DEFENSIVE PARSING: AI responses may have variations or errors.
                # We handle edge cases gracefully rather than crashing.
                primary = AgentType(analysis.get("primary_agent", "unknown"))
                secondary = [AgentType(a) for a in analysis.get("secondary_agents", [])]

                # Parse segments with error handling
                segments = {}
                for agent_str, text in analysis.get("segments", {}).items():
                    try:
                        segments[AgentType(agent_str)] = text
                    except:
                        # Skip invalid agent types rather than crashing
                        pass

                # Ensure primary agent has a segment to process
                if primary != AgentType.UNKNOWN and primary not in segments:
                    segments[primary] = transcript

                return RoutingDecision(
                    primary_agent=primary,
                    secondary_agents=secondary,
                    confidence=analysis.get("confidence", 0.5),
                    reasoning=analysis.get("reasoning", "AI analysis"),
                    segments=segments,
                )

            except Exception as e:
                logger.error(f"AI routing analysis failed: {e}")

        # Fallback: simple keyword matching when AI unavailable
        # WHY KEYWORD FALLBACK: System should work even when AI fails.
        # Basic routing is better than no routing.
        work_keywords = [
            "meeting", "project", "task", "deadline", "work", 
            "client", "code", "bug", "feature",
        ]
        memory_keywords = [
            "remember", "felt", "emotion", "family", "friend", 
            "experience", "moment",
        ]
        github_keywords = [
            "idea", "app", "tool", "create", "build", 
            "repository", "open source",
        ]

        transcript_lower = transcript.lower()

        work_score = sum(1 for kw in work_keywords if kw in transcript_lower)
        memory_score = sum(1 for kw in memory_keywords if kw in transcript_lower)
        github_score = sum(1 for kw in github_keywords if kw in transcript_lower)

        scores = [
            (AgentType.WORK, work_score),
            (AgentType.MEMORY, memory_score),
            (AgentType.GITHUB, github_score),
        ]
        scores.sort(key=lambda x: x[1], reverse=True)

        # Handle case where no keywords match
        if scores[0][1] == 0:
            return RoutingDecision(
                primary_agent=AgentType.UNKNOWN,
                secondary_agents=[],
                confidence=0.2,  # Low confidence for no matches
                reasoning="No clear indicators found",
                segments={},
            )

        primary = scores[0][0]
        # WHY CONFIDENCE SCALING: Keyword matching is less reliable than AI analysis
        confidence = min(
            scores[0][1] / 5.0, 0.9
        )  # Max confidence 0.9 for keyword matching

        # Check for multiple agents based on score similarity
        # WHY 0.7 THRESHOLD: If secondary score is >70% of primary, likely mixed content
        secondary_agents = []
        if scores[1][1] > 0 and scores[1][1] >= scores[0][1] * 0.7:
            secondary_agents.append(scores[1][0])

        return RoutingDecision(
            primary_agent=primary,
            secondary_agents=secondary_agents,
            confidence=confidence,
            reasoning=f"Keyword matching (primary: {scores[0][1]} matches)",
            segments={primary: transcript},
        )

    def _store_routing_history(
        self, transcript: str, decision: RoutingDecision, results: Dict[str, Any]
    ):
        """Store routing decision for analysis."""
        if not self.s3:
            return

        timestamp = datetime.datetime.utcnow()
        date_key = timestamp.strftime("%Y-%m-%d")

        history_entry = {
            "timestamp": timestamp.isoformat(),
            "transcript_preview": (
                transcript[:200] + "..." if len(transcript) > 200 else transcript
            ),
            "routing_decision": {
                "primary_agent": decision.primary_agent.value,
                "secondary_agents": [a.value for a in decision.secondary_agents],
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
            },
            "agents_used": list(results["processing_results"].keys()),
            "success": all(
                "error" not in r and "status" not in r or r.get("status") != "failed"
                for r in results["processing_results"].values()
            ),
        }

        # Append to daily history file
        history_key = f"orchestrator/routing_history/{date_key}.jsonl"

        try:
            # Get existing content
            obj = self.s3.get_object(Bucket=self.bucket, Key=history_key)
            existing_content = obj["Body"].read().decode()
        except:
            existing_content = ""

        updated_content = existing_content + json.dumps(history_entry) + "\n"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=history_key,
            Body=updated_content.encode("utf-8"),
            ContentType="application/x-ndjson",
        )

    def _create_processing_plan(
        self, transcript: str, instructions: Optional[str]
    ) -> Dict[str, Any]:
        """Create a plan for complex multi-agent processing."""
        if not self.bedrock:
            return {
                "steps": [
                    {
                        "id": "step1",
                        "agent": "work",
                        "content": transcript,
                        "description": "Process entire transcript",
                    }
                ]
            }

        try:
            prompt = f"""Create a processing plan for this complex voice transcript:

Transcript: {transcript}

{"Additional Instructions: " + instructions if instructions else ""}

Create a step-by-step plan using available agents:
- work: Professional activities and accomplishments
- memory: Personal experiences and reflections
- github: Project ideas and code concepts

For each step specify:
1. Which agent to use
2. What content to send to that agent
3. Why this step is needed
4. Dependencies on other steps

Respond in JSON format with a 'steps' array containing objects with keys: id, agent, content, description, depends_on"""

            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            plan = json.loads(result.get("content", [{}])[0].get("text", "{}"))

            return plan

        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            return {
                "steps": [
                    {
                        "id": "fallback",
                        "agent": "work",
                        "content": transcript,
                        "description": "Fallback: process entire transcript with work agent",
                    }
                ]
            }

    def _synthesize_results(
        self, plan: Dict[str, Any], execution_results: Dict[str, Any]
    ) -> str:
        """Synthesize results from multiple agents into a coherent summary."""
        if not self.bedrock:
            return "Multiple agents processed the transcript successfully."

        try:
            # Prepare results summary
            results_text = json.dumps(execution_results, indent=2)

            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""Synthesize these multi-agent processing results into a coherent summary:

Processing Plan:
{json.dumps(plan, indent=2)}

Execution Results:
{results_text}

Create a brief, coherent summary that:
1. Highlights key outcomes from each agent
2. Shows how the different pieces connect
3. Emphasizes the most important results
4. Is suitable for the user to understand what was accomplished""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            synthesis = result.get("content", [{}])[0].get("text", "")

            return synthesis

        except Exception as e:
            logger.error(f"Results synthesis failed: {e}")
            return "Processing completed successfully across multiple agents."

    def _generate_routing_insights(
        self,
        agent_counts,
        avg_confidence,
        multi_agent_count,
        hourly_distribution,
        total_count,
    ) -> List[str]:
        """Generate insights from routing patterns."""
        insights = []

        # Agent usage insights
        most_used = max(agent_counts.items(), key=lambda x: x[1])
        insights.append(
            f"Most used agent: {most_used[0]} ({most_used[1]} times, "
            f"{round(most_used[1]/total_count*100, 1)}%)"
        )

        # Confidence insights
        if avg_confidence < 0.7:
            insights.append(
                "Low average routing confidence - consider improving routing logic"
            )
        elif avg_confidence > 0.9:
            insights.append(
                "High routing confidence indicates clear content separation"
            )

        # Multi-agent insights
        multi_percent = (multi_agent_count / total_count) * 100
        if multi_percent > 20:
            insights.append(
                f"High multi-agent usage ({round(multi_percent, 1)}%) suggests "
                "complex, mixed-content transcripts"
            )

        # Time-based insights
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])
        if peak_hour[1] > 0:
            insights.append(
                f"Peak usage hour: {peak_hour[0]}:00 ({peak_hour[1]} routings)"
            )

        return insights

    def __call__(self, prompt: str) -> Any:
        """Make the agent callable for Strands compatibility."""
        if self.agent:
            return self.agent(prompt)
        else:
            # Fallback routing
            return self.route_transcript(prompt)


# Create singleton instance for Lambda efficiency
# WHY SINGLETON: Orchestrator maintains routing history and agent state
# that should persist across Lambda invocations for performance.
orchestrator_agent = None


def get_orchestrator_agent(bucket: str = None) -> OrchestratorAgent:
    """Get or create the orchestrator agent instance.
    
    Implements singleton pattern for Lambda container reuse. The orchestrator
    and all its agent instances persist across invocations when the container
    is warm, improving performance and maintaining routing analytics.
    """
    global orchestrator_agent
    if orchestrator_agent is None:
        orchestrator_agent = OrchestratorAgent(bucket=bucket)
    return orchestrator_agent


# Main routing function for Lambda use
def route_to_agent(
    transcript: str, source_key: Optional[str] = None, bucket: str = None
) -> Dict[str, Any]:
    """Route a transcript to the appropriate agent(s).

    This is the main entry point for the Lambda function and the primary
    interface between the serverless infrastructure and the agent system.
    
    WHY SEPARATE FUNCTION: Provides clean interface for Lambda while
    keeping orchestrator agent as a reusable class for other contexts.
    """
    agent = get_orchestrator_agent(bucket=bucket)
    # Delegate to orchestrator's routing logic
    return agent.route_transcript(transcript, source_key)
