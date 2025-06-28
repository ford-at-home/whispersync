"""Memory Agent.

# PURPOSE & PHILOSOPHY:
# This agent serves as a digital memory keeper that preserves personal experiences,
# emotions, and reflections with deep contextual understanding. It's designed around
# the principle that our memories shape who we are, and AI can help us understand
# patterns in our experiences and emotional growth over time.

# CORE DESIGN DECISIONS:
# 1. Emotional Intelligence: Uses Claude to analyze sentiment, emotions, and themes
# 2. JSONL Storage: Append-only structure preserves chronological integrity
# 3. Rich Metadata: Extracts people, places, themes for powerful searching
# 4. Significance Scoring: AI rates memory importance for prioritization
# 5. Relationship Mapping: Connects related memories across time

# WHY JSONL + S3:
# - Append-only structure preserves memory integrity (no accidental overwrites)
# - Each line is a complete memory record, enabling streaming processing
# - S3 provides durability for irreplaceable personal data
# - JSONL enables efficient searching and aggregation

# BUSINESS VALUE:
# - Personal growth insights through pattern recognition
# - Emotional intelligence development through sentiment tracking
# - Rich life documentation for autobiography/memoir writing
# - Relationship history and pattern analysis
# - Therapeutic support through reflection and context
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import logging
import datetime
from dataclasses import dataclass, asdict

try:
    import boto3
    from strands import Agent, tool
    from strands_tools import bedrock_knowledge_base_retrieve
except ImportError:  # pragma: no cover - optional for local testing
    # WHY GRACEFUL IMPORTS: Allows local development and testing without
    # full AWS/Strands stack. Memory processing can continue in degraded mode.
    boto3 = None
    Agent = None
    bedrock_knowledge_base_retrieve = None

    # Mock decorator for testing without strands
    def tool(func):
        return func


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class Memory:
    """Structured memory with rich metadata.
    
    WHY RICH METADATA: Personal memories are multi-dimensional. The metadata
    enables powerful search, pattern recognition, and relationship mapping
    that would be impossible with just raw text.
    
    FIELDS EXPLAINED:
    - timestamp: When the memory occurred (not when recorded)
    - content: Original voice transcript of the memory
    - sentiment: Overall emotional tone (positive, neutral, negative, mixed)
    - emotions: Specific emotions identified (joy, nostalgia, sadness, etc.)
    - themes: Life areas/topics (family, achievement, loss, growth, etc.)
    - people: Names or relationships mentioned in the memory
    - locations: Places, cities, venues mentioned
    - significance: AI-rated importance (1-10) for prioritization
    """

    timestamp: datetime.datetime
    content: str           # Original transcript
    sentiment: str         # Overall emotional tone
    emotions: List[str]    # Specific emotions identified
    themes: List[str]      # Life areas/topics
    people: List[str]      # People mentioned
    locations: List[str]   # Places mentioned
    significance: int      # 1-10 importance rating


class MemoryAgent:
    """Agent specialized in memory storage and emotional analysis.
    
    WHY EMOTIONAL INTELLIGENCE FOCUS:
    - Memories are fundamentally emotional experiences
    - AI can identify patterns humans miss in their own emotional journey
    - Emotional metadata enables therapeutic and growth insights
    - Sentiment tracking reveals mental health patterns over time
    
    DESIGN PATTERNS:
    - Repository Pattern: Abstracts memory storage and retrieval
    - Strategy Pattern: Different analysis strategies for different memory types
    - Observer Pattern: Future extension for mood tracking notifications
    """

    def __init__(self, bucket: str = None, bedrock_client=None):
        """Initialize the memory agent.

        Args:
            bucket: S3 bucket name for storage (defaults to 'voice-mcp')
            bedrock_client: Optional Bedrock client for testing/mocking
            
        WHY OPTIONAL PARAMETERS: Enables testing with mocks while providing
        sensible defaults for production deployment.
        """
        self.bucket = bucket or "voice-mcp"
        # WHY CONDITIONAL CLIENTS: Supports both production and testing environments
        self.s3 = boto3.client("s3") if boto3 else None
        self.bedrock = bedrock_client or (
            boto3.client("bedrock-runtime") if boto3 else None
        )

        # Create agent with specialized tools
        # WHY STRANDS AGENT: Provides conversational interface that can intelligently
        # choose which memory tools to use based on natural language requests.
        if Agent:
            self.agent = Agent(
                system_prompt="""You are a memory specialist with expertise in:
                - Emotional intelligence and sentiment analysis
                - Identifying themes and patterns in personal narratives
                - Extracting meaningful connections between memories
                - Understanding the significance of life events
                - Creating a searchable knowledge base of experiences
                
                When processing memories:
                1. Analyze the emotional content and overall sentiment
                2. Identify key themes (family, achievement, challenge, joy, etc.)
                3. Extract mentions of people and locations
                4. Assess the significance of the memory (1-10 scale)
                5. Connect to related past memories when relevant
                
                Be empathetic and insightful in your analysis.""",
                # WHY THESE TOOLS: Cover complete memory lifecycle:
                # store_memory: Core functionality for new memories
                # search_memories: Retrieval with rich filtering
                # analyze_memory_themes: Pattern recognition across time
                # get_memory_timeline: Chronological exploration
                # find_related_memories: Relationship discovery
                tools=[
                    self.store_memory,
                    self.search_memories,
                    self.analyze_memory_themes,
                    self.get_memory_timeline,
                    self.find_related_memories,
                ],
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            )
        else:
            self.agent = None

    @tool
    def store_memory(self, transcript: str) -> Dict[str, Any]:
        """Store and analyze a personal memory.

        This is the core method that transforms raw voice transcripts into
        structured memories with rich emotional and contextual analysis.
        
        WHY DAILY JSONL FILES:
        - Natural grouping by day for memory browsing
        - Append-only structure preserves integrity
        - Each line is complete record (no cross-references to break)
        - Efficient for date-range queries and timeline views

        Args:
            transcript: The memory transcript to analyze and store

        Returns:
            Dictionary containing:
            - memory_key: S3 key where memory was stored
            - memory_id: Unique identifier for this memory
            - analysis: AI-extracted emotional and contextual metadata
            - related_memories: Connections to existing memories
        """
        if not self.s3:
            # WHY GRACEFUL DEGRADATION: Testing environments may not have S3.
            # We still want to return structured response for testing validation.
            logger.warning("S3 unavailable; returning dry-run response")
            return {
                "memory_key": "dry-run",
                "analysis": {
                    "sentiment": "neutral",
                    "themes": ["memory"],
                    "significance": 5,
                },
            }

        # Analyze memory with Claude for emotional intelligence insights
        analysis = self._analyze_memory(transcript)

        now = datetime.datetime.utcnow()

        # Create structured memory object with AI-extracted metadata
        # WHY STRUCTURED OBJECT: Type safety and consistent field access
        memory = Memory(
            timestamp=now,
            content=transcript,
            sentiment=analysis["sentiment"],
            emotions=analysis["emotions"],
            themes=analysis["themes"],
            people=analysis["people"],
            locations=analysis["locations"],
            significance=analysis["significance"],
        )

        # Store as JSONL for efficient append operations
        # WHY DATE-BASED KEYS: Natural grouping for timeline browsing
        date_key = now.strftime("%Y-%m-%d")  # e.g., "2024-01-15"
        memory_key = f"memories/{date_key}.jsonl"  # e.g., "memories/2024-01-15.jsonl"

        # Create record for JSONL storage with serializable timestamp
        # WHY UNIQUE ID: Combines timestamp + content hash for collision resistance
        memory_record = {
            **asdict(memory),
            "timestamp": memory.timestamp.isoformat(),  # JSON-serializable timestamp
            "id": f"{now.isoformat()}-{hash(transcript) % 10000}",  # Unique identifier
        }

        try:
            # Get existing daily file for appending
            obj = self.s3.get_object(Bucket=self.bucket, Key=memory_key)
            existing_content = obj["Body"].read().decode()
        except Exception:
            # First memory of the day - start new file
            existing_content = ""

        # Append new memory to daily file
        # WHY APPEND: Preserves chronological order and enables streaming
        updated_content = existing_content + json.dumps(memory_record) + "\n"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=memory_key,
            Body=updated_content.encode("utf-8"),
            ContentType="application/x-ndjson",  # JSONL MIME type
            # WHY METADATA: Enables efficient queries without downloading files
            Metadata={
                "date": date_key,
                "count": str(len(updated_content.strip().split("\n"))),  # Memory count
            },
        )

        # Update themes index for efficient searching
        # WHY SEPARATE INDEX: Enables fast theme-based queries without scanning all files
        self._update_themes_index(memory.themes, memory_record["id"])

        # Find related memories based on content similarity
        # WHY IMMEDIATE RELATION FINDING: Provides context while memory is fresh
        related = self._find_related_memories(memory)

        logger.info(f"Stored memory to {memory_key}")

        return {
            "memory_key": memory_key,
            "memory_id": memory_record["id"],
            "analysis": {
                "sentiment": memory.sentiment,
                "emotions": memory.emotions,
                "themes": memory.themes,
                "people": memory.people,
                "locations": memory.locations,
                "significance": memory.significance,
            },
            "related_memories": related,
        }

    @tool
    def search_memories(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories by content, themes, people, or emotions.
        
        WHY MULTI-FACETED SEARCH:
        - Memories can be recalled by content, people, emotions, or themes
        - Filtering enables targeted exploration (e.g., "positive memories with family")
        - Relevance scoring prioritizes best matches
        - Date filtering supports temporal exploration

        Args:
            query: Search query (matches against content, themes, people)
            filters: Optional filters:
                - themes: List of themes to match
                - people: List of people to match
                - sentiment: Specific sentiment (positive/neutral/negative)
                - min_significance: Minimum significance rating (1-10)
                - date_range: Tuple of (start_date, end_date)

        Returns:
            List of matching memories with:
            - memory_id: Unique identifier
            - timestamp: When memory occurred
            - preview: Truncated content for display
            - themes: Associated themes
            - sentiment: Emotional tone
            - significance: Importance rating
            - relevance: Search relevance score
        """
        if not self.s3:
            return []

        matches = []

        # Parse optional filters with defaults
        # WHY EXPLICIT PARSING: Provides clear API and prevents KeyError exceptions
        theme_filter = filters.get("themes", []) if filters else []
        people_filter = filters.get("people", []) if filters else []
        sentiment_filter = filters.get("sentiment") if filters else None
        min_significance = filters.get("min_significance", 1) if filters else 1

        # List all memory files for comprehensive search
        # WHY SCAN ALL FILES: Memories can span long time periods, so we need
        # to search across all daily files rather than just recent ones
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix="memories/")

        for obj in response.get("Contents", []):
            if not obj["Key"].endswith(".jsonl"):
                continue

            # Read memory file
            memory_obj = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
            content = memory_obj["Body"].read().decode()

            # Process each memory line
            for line in content.strip().split("\n"):
                if not line:
                    continue

                memory = json.loads(line)

                # Apply filters
                if (
                    min_significance
                    and memory.get("significance", 0) < min_significance
                ):
                    continue

                if sentiment_filter and memory.get("sentiment") != sentiment_filter:
                    continue

                if theme_filter and not any(
                    t in memory.get("themes", []) for t in theme_filter
                ):
                    continue

                if people_filter and not any(
                    p in memory.get("people", []) for p in people_filter
                ):
                    continue

                # Check query match against content
                # WHY CASE-INSENSITIVE: Natural language search should be flexible
                if query.lower() in memory.get("content", "").lower():
                    # Calculate relevance score for ranking
                    relevance = self._calculate_relevance(query, memory)

                    matches.append(
                        {
                            "memory_id": memory.get("id"),
                            "timestamp": memory.get("timestamp"),
                            "preview": memory.get("content", "")[:200] + "...",
                            "themes": memory.get("themes", []),
                            "sentiment": memory.get("sentiment"),
                            "significance": memory.get("significance", 5),
                            "relevance": relevance,
                        }
                    )

        # Sort by relevance and recency
        # WHY THIS SORT ORDER: Most relevant matches first, with recency as tiebreaker
        matches.sort(key=lambda x: (x["relevance"], x["timestamp"]), reverse=True)

        return matches[:20]  # Limit to 20 results

    @tool
    def analyze_memory_themes(self, time_period: str = "all") -> Dict[str, Any]:
        """Analyze recurring themes and patterns in memories.

        Args:
            time_period: Period to analyze ("week", "month", "year", "all")

        Returns:
            Dictionary containing theme analysis and insights
        """
        if not self.s3:
            return {"themes": {}, "insights": []}

        # Load theme index
        try:
            obj = self.s3.get_object(
                Bucket=self.bucket, Key="memories/indexes/themes.json"
            )
            theme_data = json.loads(obj["Body"].read().decode())
        except Exception:
            theme_data = {}

        # Calculate time cutoff
        now = datetime.datetime.utcnow()
        if time_period == "week":
            cutoff = now - datetime.timedelta(days=7)
        elif time_period == "month":
            cutoff = now - datetime.timedelta(days=30)
        elif time_period == "year":
            cutoff = now - datetime.timedelta(days=365)
        else:
            cutoff = None

        # Filter and count themes
        theme_counts = {}
        emotion_counts = {}
        sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}

        # Process all memories for comprehensive analysis
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix="memories/")

        total_memories = 0
        significant_memories = []

        for obj in response.get("Contents", []):
            if not obj["Key"].endswith(".jsonl"):
                continue

            memory_obj = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
            content = memory_obj["Body"].read().decode()

            for line in content.strip().split("\n"):
                if not line:
                    continue

                memory = json.loads(line)
                timestamp = datetime.datetime.fromisoformat(memory["timestamp"])

                if cutoff and timestamp < cutoff:
                    continue

                total_memories += 1

                # Count themes
                for theme in memory.get("themes", []):
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1

                # Count emotions
                for emotion in memory.get("emotions", []):
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

                # Track sentiment
                sentiment = memory.get("sentiment", "neutral")
                sentiment_distribution[sentiment] += 1

                # Collect significant memories
                if memory.get("significance", 0) >= 8:
                    significant_memories.append(
                        {
                            "id": memory["id"],
                            "preview": memory["content"][:100],
                            "significance": memory["significance"],
                        }
                    )

        # Generate insights with Claude
        insights = self._generate_theme_insights(
            theme_counts,
            emotion_counts,
            sentiment_distribution,
            significant_memories,
            total_memories,
            time_period,
        )

        return {
            "time_period": time_period,
            "total_memories": total_memories,
            "theme_counts": dict(
                sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
            ),
            "emotion_counts": dict(
                sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
            ),
            "sentiment_distribution": sentiment_distribution,
            "significant_memories": significant_memories[:5],
            "insights": insights,
        }

    @tool
    def get_memory_timeline(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get a timeline view of memories.

        Args:
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            List of memories organized by date
        """
        if not self.s3:
            return []

        timeline = []

        # Parse dates
        if start_date:
            start = datetime.datetime.fromisoformat(start_date)
        else:
            start = datetime.datetime.utcnow() - datetime.timedelta(days=30)

        if end_date:
            end = datetime.datetime.fromisoformat(end_date)
        else:
            end = datetime.datetime.utcnow()

        # List memory files in date range
        current = start
        while current <= end:
            date_key = current.strftime("%Y-%m-%d")
            memory_key = f"memories/{date_key}.jsonl"

            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=memory_key)
                content = obj["Body"].read().decode()

                daily_memories = []
                for line in content.strip().split("\n"):
                    if line:
                        memory = json.loads(line)
                        daily_memories.append(
                            {
                                "id": memory["id"],
                                "time": memory["timestamp"],
                                "preview": memory["content"][:150],
                                "sentiment": memory["sentiment"],
                                "themes": memory["themes"],
                                "significance": memory["significance"],
                            }
                        )

                if daily_memories:
                    timeline.append(
                        {
                            "date": date_key,
                            "memory_count": len(daily_memories),
                            "memories": daily_memories,
                            "day_summary": self._summarize_day(daily_memories),
                        }
                    )

            except Exception:
                pass

            current += datetime.timedelta(days=1)

        return timeline

    @tool
    def find_related_memories(
        self, memory_id: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find memories related to a specific memory.

        Args:
            memory_id: ID of the memory to find relations for
            max_results: Maximum number of related memories to return

        Returns:
            List of related memories with relationship explanations
        """
        if not self.s3:
            return []

        # First, find the target memory
        target_memory = None
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix="memories/")

        for obj in response.get("Contents", []):
            if not obj["Key"].endswith(".jsonl"):
                continue

            memory_obj = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
            content = memory_obj["Body"].read().decode()

            for line in content.strip().split("\n"):
                if line:
                    memory = json.loads(line)
                    if memory.get("id") == memory_id:
                        target_memory = memory
                        break

            if target_memory:
                break

        if not target_memory:
            return []

        # Find related memories based on themes, people, and content similarity
        related = []

        for obj in response.get("Contents", []):
            if not obj["Key"].endswith(".jsonl"):
                continue

            memory_obj = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
            content = memory_obj["Body"].read().decode()

            for line in content.strip().split("\n"):
                if line:
                    memory = json.loads(line)
                    if memory.get("id") == memory_id:
                        continue

                    # Calculate relationship score
                    score, relationship = self._calculate_relationship(
                        target_memory, memory
                    )

                    if score > 0.3:  # Threshold for relevance
                        related.append(
                            {
                                "memory_id": memory["id"],
                                "timestamp": memory["timestamp"],
                                "preview": memory["content"][:150],
                                "themes": memory["themes"],
                                "relationship": relationship,
                                "similarity_score": score,
                            }
                        )

        # Sort by similarity score and return top results
        related.sort(key=lambda x: x["similarity_score"], reverse=True)
        return related[:max_results]

    def _analyze_memory(self, transcript: str) -> Dict[str, Any]:
        """Analyze a memory transcript using Claude for emotional intelligence.
        
        WHY SEPARATE METHOD: Isolates AI interaction for easier testing and
        potential model switching. The emotional analysis prompt is centralized here.
        
        ANALYSIS EXTRACTS:
        - Sentiment: Overall emotional tone of the memory
        - Emotions: Specific emotions present (joy, nostalgia, sadness, etc.)
        - Themes: Life areas touched (family, achievement, loss, growth, etc.)
        - People: Names or relationships mentioned
        - Locations: Places, cities, venues referenced
        - Significance: AI assessment of importance (1-10 scale)
        """
        if not self.bedrock:
            # Fallback analysis for testing/degraded operation
            # WHY FALLBACK: System should capture memories even without AI analysis
            return {
                "sentiment": "neutral",
                "emotions": ["nostalgic"],
                "themes": ["personal"],
                "people": [],
                "locations": [],
                "significance": 5,
            }

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
                        # - Specific output format ensures consistent parsing
                        # - Examples guide AI toward meaningful categorization
                        # - Significance rating enables importance prioritization
                        # - Multiple dimensions capture memory's full context
                        "content": f"""Analyze this personal memory and extract:

1. Overall sentiment (positive, neutral, negative, mixed)
2. Specific emotions present (e.g., joy, nostalgia, sadness, gratitude, pride)
3. Key themes (e.g., family, achievement, loss, growth, friendship, adventure)
4. People mentioned (extract names or relationships)
5. Locations mentioned (places, cities, venues)
6. Significance rating (1-10, where 10 is life-changing)

Memory: {transcript}

Respond in JSON format with keys: sentiment, emotions, themes, people, locations, significance""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            return json.loads(result.get("content", [{}])[0].get("text", "{}"))

        except Exception as e:
            logger.error(f"Memory analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "emotions": ["unanalyzed"],
                "themes": ["personal"],
                "people": [],
                "locations": [],
                "significance": 5,
            }

    def _update_themes_index(self, themes: List[str], memory_id: str):
        """Update the themes index for efficient searching."""
        if not self.s3:
            return

        index_key = "memories/indexes/themes.json"

        try:
            # Get existing index
            obj = self.s3.get_object(Bucket=self.bucket, Key=index_key)
            index_data = json.loads(obj["Body"].read().decode())
        except Exception:
            index_data = {}

        # Update index with new themes
        for theme in themes:
            if theme not in index_data:
                index_data[theme] = []
            if memory_id not in index_data[theme]:
                index_data[theme].append(memory_id)

        # Save updated index
        self.s3.put_object(
            Bucket=self.bucket,
            Key=index_key,
            Body=json.dumps(index_data, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

    def _find_related_memories(self, memory: Memory) -> List[Dict[str, str]]:
        """Find memories related to the given memory."""
        # Simple implementation - in production, use vector similarity
        related = []

        # Search by shared themes
        for theme in memory.themes[:2]:  # Top 2 themes
            results = self.search_memories("", filters={"themes": [theme]})
            for result in results[:2]:
                if (
                    result["memory_id"]
                    != f"{memory.timestamp.isoformat()}-{hash(memory.content) % 10000}"
                ):
                    related.append(
                        {
                            "memory_id": result["memory_id"],
                            "relation_type": f"shared theme: {theme}",
                            "preview": result["preview"],
                        }
                    )

        return related[:3]

    def _calculate_relevance(self, query: str, memory: Dict[str, Any]) -> float:
        """Calculate relevance score for search results."""
        score = 0.0
        query_lower = query.lower()

        # Content match
        content = memory.get("content", "").lower()
        if query_lower in content:
            score += 0.5
            # Bonus for exact phrase match
            if f" {query_lower} " in f" {content} ":
                score += 0.2

        # Theme match
        for theme in memory.get("themes", []):
            if query_lower in theme.lower():
                score += 0.3

        # People match
        for person in memory.get("people", []):
            if query_lower in person.lower():
                score += 0.3

        # Significance bonus
        score += memory.get("significance", 5) / 50.0

        return min(score, 1.0)

    def _calculate_relationship(
        self, memory1: Dict[str, Any], memory2: Dict[str, Any]
    ) -> tuple[float, str]:
        """Calculate relationship between two memories."""
        score = 0.0
        relationships = []

        # Shared themes
        themes1 = set(memory1.get("themes", []))
        themes2 = set(memory2.get("themes", []))
        shared_themes = themes1.intersection(themes2)
        if shared_themes:
            score += len(shared_themes) * 0.2
            relationships.append(f"themes: {', '.join(shared_themes)}")

        # Shared people
        people1 = set(memory1.get("people", []))
        people2 = set(memory2.get("people", []))
        shared_people = people1.intersection(people2)
        if shared_people:
            score += len(shared_people) * 0.3
            relationships.append(f"people: {', '.join(shared_people)}")

        # Similar emotions
        emotions1 = set(memory1.get("emotions", []))
        emotions2 = set(memory2.get("emotions", []))
        shared_emotions = emotions1.intersection(emotions2)
        if shared_emotions:
            score += len(shared_emotions) * 0.1
            relationships.append(f"emotions: {', '.join(shared_emotions)}")

        # Time proximity (memories close in time)
        time1 = datetime.datetime.fromisoformat(memory1["timestamp"])
        time2 = datetime.datetime.fromisoformat(memory2["timestamp"])
        days_apart = abs((time1 - time2).days)
        if days_apart < 7:
            score += 0.2
            relationships.append("occurred within same week")
        elif days_apart < 30:
            score += 0.1
            relationships.append("occurred within same month")

        relationship_str = (
            "; ".join(relationships) if relationships else "indirect connection"
        )
        return score, relationship_str

    def _summarize_day(self, memories: List[Dict[str, Any]]) -> str:
        """Generate a brief summary of the day's memories."""
        if not memories:
            return ""

        themes = []
        sentiments = []

        for memory in memories:
            themes.extend(memory.get("themes", []))
            sentiments.append(memory.get("sentiment", "neutral"))

        # Most common theme
        if themes:
            theme_counts = {}
            for theme in themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
            dominant_theme = max(theme_counts.items(), key=lambda x: x[1])[0]
        else:
            dominant_theme = "various"

        # Overall sentiment
        positive = sentiments.count("positive")
        negative = sentiments.count("negative")
        if positive > negative:
            overall_sentiment = "positive"
        elif negative > positive:
            overall_sentiment = "challenging"
        else:
            overall_sentiment = "mixed"

        return f"A {overall_sentiment} day with {len(memories)} memories, mostly about {dominant_theme}"

    def _generate_theme_insights(
        self,
        theme_counts,
        emotion_counts,
        sentiment_dist,
        significant_memories,
        total_memories,
        time_period,
    ) -> List[str]:
        """Generate insights about memory themes and patterns."""
        if not self.bedrock:
            return ["Theme analysis requires Claude integration"]

        try:
            # Prepare data for Claude
            analysis_data = {
                "time_period": time_period,
                "total_memories": total_memories,
                "top_themes": dict(list(theme_counts.items())[:10]),
                "top_emotions": dict(list(emotion_counts.items())[:10]),
                "sentiment_distribution": sentiment_dist,
                "significant_memory_count": len(significant_memories),
            }

            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""Analyze these memory patterns and provide 3-5 meaningful insights:

{json.dumps(analysis_data, indent=2)}

Provide insights about:
1. Dominant themes and what they suggest about this person's life
2. Emotional patterns and overall well-being
3. Any notable trends or patterns
4. Suggestions for reflection or action

Return as a JSON array of insight strings.""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            insights = json.loads(result.get("content", [{}])[0].get("text", "[]"))
            return insights

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return [
                f"Most common theme: {list(theme_counts.keys())[0] if theme_counts else 'none'}",
                f"Overall sentiment: {max(sentiment_dist.items(), key=lambda x: x[1])[0]}",
                f"Total memories in period: {total_memories}",
            ]

    def __call__(self, prompt: str) -> Any:
        """Make the agent callable for Strands compatibility."""
        if self.agent:
            return self.agent(prompt)
        else:
            return {"message": "Agent not available", "prompt": prompt}


# Create singleton instance for Lambda efficiency
# WHY SINGLETON: Memory agent maintains internal state (themes index, etc.)
# and AWS clients that should be reused across Lambda invocations.
memory_agent = None


def get_memory_agent(bucket: str = None) -> MemoryAgent:
    """Get or create the memory agent instance.
    
    Implements singleton pattern for Lambda container reuse. The agent
    and its AWS clients persist across invocations when container is warm.
    """
    global memory_agent
    if memory_agent is None:
        memory_agent = MemoryAgent(bucket=bucket)
    return memory_agent


# Legacy compatibility
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy handler function for backward compatibility."""
    agent = get_memory_agent(bucket=payload.get("bucket"))
    return agent.store_memory(transcript=payload.get("transcript", ""))


# Tool wrapper for orchestrator use
@tool
def memory_tool(transcript: str) -> Dict[str, Any]:
    """Process personal memory transcripts.

    This tool handles personal memories, experiences, reflections,
    and any non-work related content. It analyzes emotional content,
    extracts themes, and builds a searchable knowledge base.
    
    WHY SEPARATE TOOL FUNCTION:
    - Clean interface for orchestrator integration
    - Wraps conversational agent with simple function signature
    - Enables testing and mocking without full agent complexity
    - Follows Strands tool pattern for agent coordination
    """
    agent = get_memory_agent()
    # WHY THIS PROMPT: Provides context for the agent to understand the task.
    # Agent can then choose appropriate tool (store_memory, search_memories, etc.)
    prompt = f"Store and analyze this personal memory: {transcript}"
    return agent(prompt)
