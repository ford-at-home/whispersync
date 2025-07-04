"""SpiritualAdvisorAgent - Personal memory preservation with deep emotional intelligence.

Core responsibilities:
- Process memories with emotional analysis and significance scoring
- Extract people, places, themes, and emotional patterns
- Organize memories in multi-dimensional S3 structure
- Discover connections between memories across time
- Generate periodic life reviews with growth insights
- Provide spiritual and philosophical reflections
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import asyncio
import re

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Configuration
MEMORY_ARCHIVE_BUCKET = os.environ.get('MEMORY_ARCHIVE_BUCKET', 'whispersync-memories')
PERSONAL_CONTEXT_SECRET = os.environ.get('PERSONAL_CONTEXT_SECRET', 'spiritual/personal_context')


@dataclass
class Memory:
    """Structured memory with rich emotional and contextual metadata.
    
    Combines the best of memory_agent and diary_processor to create
    deeply meaningful memory records with spiritual insights.
    """
    
    timestamp: datetime
    content: str
    
    # Emotional intelligence (from memory_agent.py)
    sentiment: str              # positive, neutral, negative, mixed
    emotions: List[Dict[str, float]]  # [{"name": "joy", "intensity": 0.8}]
    emotional_intensity: float  # 0.0 to 1.0
    
    # Contextual extraction (from both v1 agents)
    themes: List[str]          # family, achievement, loss, growth, etc.
    people: List[str]          # Names or relationships mentioned
    locations: List[str]       # Places, cities, venues
    
    # Significance and insights (enhanced from diary_processor.py)
    significance: int          # 1-10 importance rating
    life_area: str            # personal, family, spiritual, health, etc.
    growth_insights: List[str] # Personal development observations
    gratitude_notes: List[str] # Things to be grateful for
    
    # Memory connections
    related_memories: List[str]  # IDs of related memories
    memory_type: str            # reflection, experience, dream, insight
    
    # Spiritual insights (new enhancement)
    spiritual_insights: str = ""
    key_quotes: List[str] = None
    
    def __post_init__(self):
        if self.key_quotes is None:
            self.key_quotes = []


@dataclass
class PersonalContext:
    """Deep personal context that informs memory interpretation."""
    
    life_challenges: Dict[str, str] = None
    growth_themes: List[str] = None
    key_relationships: Dict[str, str] = None
    wisdom_gained: List[str] = None
    current_phase: str = "Unknown"
    emotional_baseline: Dict[str, float] = None  # Track emotional patterns
    recurring_people: Dict[str, int] = None      # People mention frequency
    sacred_places: List[str] = None              # Meaningful locations
    
    def __post_init__(self):
        if self.life_challenges is None:
            self.life_challenges = {}
        if self.growth_themes is None:
            self.growth_themes = []
        if self.key_relationships is None:
            self.key_relationships = {}
        if self.wisdom_gained is None:
            self.wisdom_gained = []
        if self.emotional_baseline is None:
            self.emotional_baseline = {}
        if self.recurring_people is None:
            self.recurring_people = {}
        if self.sacred_places is None:
            self.sacred_places = []


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager."""
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve Anthropic API key: {e}")
        raise


def load_personal_context() -> PersonalContext:
    """Load personal context from Secrets Manager.
    
    This contains sensitive personal information that helps the agent
    understand the deeper context of memories.
    """
    try:
        response = secrets_client.get_secret_value(SecretId=PERSONAL_CONTEXT_SECRET)
        context_data = json.loads(response['SecretString'])
        
        return PersonalContext(
            life_challenges=context_data.get('life_challenges', {}),
            growth_themes=context_data.get('growth_themes', []),
            key_relationships=context_data.get('key_relationships', {}),
            wisdom_gained=context_data.get('wisdom_gained', []),
            current_phase=context_data.get('current_phase', 'Unknown')
        )
    except Exception as e:
        logger.warning(f"Failed to load personal context: {e}")
        # Return default context
        return PersonalContext(
            life_challenges={
                "health": "Managing narcolepsy",
                "relationships": "Navigating post-divorce life"
            },
            growth_themes=["resilience", "self-discovery", "authenticity"],
            current_phase="Rebuilding and growth"
        )


async def analyze_memory_with_spiritual_lens(
    transcript: str,
    personal_context: PersonalContext
) -> Dict[str, Any]:
    """Analyze memory with deep emotional and spiritual intelligence.
    
    This combines the emotional analysis from memory_agent with the
    life pattern recognition from diary_processor, adding spiritual
    insights and personal growth observations.
    
    Args:
        transcript: Memory transcript
        personal_context: Personal life context
        
    Returns:
        Deep analysis with emotional intelligence and spiritual insights
    """
    try:
        from anthropic import Anthropic
        
        api_key = get_anthropic_api_key()
        anthropic = Anthropic(api_key=api_key)
        
        # Prepare context prompt
        context_info = f"""You are a wise spiritual advisor who deeply understands this person's life journey.

Life Context:
- Current Phase: {personal_context.current_phase}
- Key Challenges: {json.dumps(personal_context.life_challenges)}
- Growth Themes: {', '.join(personal_context.growth_themes)}
- Important Relationships: {json.dumps(personal_context.key_relationships)}

Your role is to understand not just what happened, but what it means in the context of their life journey."""

        prompt = f"""{context_info}

Memory Transcript: "{transcript}"

Analyze this memory with deep emotional and spiritual intelligence:

1. Overall sentiment (positive, neutral, negative, mixed)
2. Specific emotions with intensity (0.0-1.0)
3. Life themes (family, growth, challenge, joy, loss, achievement, spiritual, health, etc.)
4. People mentioned (names or relationships like "my daughter", "my mentor")
5. Locations (specific places, cities, or meaningful spaces)
6. Significance rating (1-10, where 10 is life-changing)
7. Life area (personal, family, career, spiritual, health, relationships)
8. Memory type (reflection, experience, dream, realization, gratitude)
9. Growth insights (what this reveals about personal development)
10. Gratitude elements (things to be grateful for in this memory)
11. Spiritual or philosophical insights
12. Key quotes (exact meaningful phrases from the memory)

Provide deep, meaningful analysis that helps understand patterns in their life journey.

Respond in JSON format:
{{
    "sentiment": "positive|neutral|negative|mixed",
    "emotions": [{{"name": "joy", "intensity": 0.8}}, {{"name": "nostalgia", "intensity": 0.6}}],
    "emotional_intensity": 0.7,
    "themes": ["family", "growth", "gratitude"],
    "people": ["my mother", "Sarah"],
    "locations": ["childhood home", "Seattle"],
    "significance": 8,
    "life_area": "family",
    "memory_type": "reflection",
    "growth_insights": ["Learning to appreciate...", "Recognizing pattern of..."],
    "gratitude_notes": ["Grateful for mother's wisdom", "Blessed to have experienced..."],
    "spiritual_insights": "This memory reveals the cyclical nature of life...",
    "key_quotes": ["exact meaningful phrases from the memory"],
    "surface_content": "What literally happened",
    "deeper_context": "What this means in their life journey",
    "life_phase_indicator": "What this says about where they are now"
}}"""

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.7,  # More creative for spiritual interpretation
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            raise ValueError("No valid JSON in response")
        
    except Exception as e:
        logger.error(f"Failed to analyze memory: {e}")
        # Return meaningful defaults that match the new structure
        return {
            "sentiment": "neutral",
            "emotions": [{"name": "contemplative", "intensity": 0.5}],
            "emotional_intensity": 0.5,
            "themes": ["personal", "reflection"],
            "people": [],
            "locations": [],
            "significance": 5,
            "life_area": "personal",
            "memory_type": "experience",
            "growth_insights": ["Unable to analyze - see original memory"],
            "gratitude_notes": [],
            "spiritual_insights": "",
            "key_quotes": [],
            "surface_content": transcript[:200] + "..." if len(transcript) > 200 else transcript,
            "deeper_context": "Analysis unavailable",
            "life_phase_indicator": "Unknown"
        }


def organize_memory_in_s3(
    memory: Memory,
    s3_bucket: str,
    analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Organize memory in beautiful S3 structure with multiple access patterns.
    
    Structure:
    - memories/daily/{date}.jsonl - Chronological by day
    - memories/significant/{year}/{significance}-{id}.json - High significance memories
    - memories/themes/{theme}/{year}-{month}.jsonl - Theme-based organization
    - memories/people/{person}/{year}.jsonl - People-centric view
    - memories/timeline/{year}-{month}-summary.json - Monthly summaries
    """
    now = memory.timestamp
    memory_id = f"{now.isoformat()}-{hash(memory.content) % 10000}"
    
    # Prepare memory record
    memory_record = {
        "id": memory_id,
        "timestamp": memory.timestamp.isoformat(),
        "content": memory.content,
        "sentiment": memory.sentiment,
        "emotions": memory.emotions,
        "emotional_intensity": memory.emotional_intensity,
        "themes": memory.themes,
        "people": memory.people,
        "locations": memory.locations,
        "significance": memory.significance,
        "life_area": memory.life_area,
        "memory_type": memory.memory_type,
        "growth_insights": memory.growth_insights,
        "gratitude_notes": memory.gratitude_notes,
        "spiritual_insights": memory.spiritual_insights,
        "key_quotes": memory.key_quotes
    }
    
    stored_paths = []
    
    # 1. Daily chronicle (JSONL for append-only integrity)
    daily_key = f"memories/daily/{now.strftime('%Y-%m-%d')}.jsonl"
    try:
        # Get existing daily file
        obj = s3_client.get_object(Bucket=s3_bucket, Key=daily_key)
        existing_content = obj['Body'].read().decode('utf-8')
    except s3_client.exceptions.NoSuchKey:
        existing_content = ""
    
    updated_content = existing_content + json.dumps(memory_record) + "\n"
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=daily_key,
        Body=updated_content.encode('utf-8'),
        ContentType='application/x-ndjson',
        Metadata={
            'date': now.strftime('%Y-%m-%d'),
            'count': str(len(updated_content.strip().split('\n'))),
            'significance_range': f"1-{memory.significance}"
        }
    )
    stored_paths.append(daily_key)
    
    # 2. Significant memories (8+ rating) get special treatment
    if memory.significance >= 8:
        sig_key = f"memories/significant/{now.year}/sig{memory.significance}-{memory_id}.json"
        sig_doc = {
            **memory_record,
            "created_paths": stored_paths
        }
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=sig_key,
            Body=json.dumps(sig_doc, indent=2).encode('utf-8'),
            ContentType='application/json',
            ServerSideEncryption='AES256',
            Metadata={
                'significance': str(memory.significance),
                'primary_theme': memory.themes[0] if memory.themes else 'life'
            }
        )
        stored_paths.append(sig_key)
    
    # 3. Theme-based organization (top 2 themes)
    for theme in memory.themes[:2]:
        theme_key = f"memories/themes/{theme.lower().replace(' ', '_')}/{now.strftime('%Y-%m')}.jsonl"
        try:
            obj = s3_client.get_object(Bucket=s3_bucket, Key=theme_key)
            existing = obj['Body'].read().decode('utf-8')
        except s3_client.exceptions.NoSuchKey:
            existing = ""
        
        updated = existing + json.dumps(memory_record) + "\n"
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=theme_key,
            Body=updated.encode('utf-8'),
            ContentType='application/x-ndjson'
        )
        stored_paths.append(theme_key)
    
    # 4. People-centric organization
    for person in memory.people[:3]:  # Top 3 people
        person_key = f"memories/people/{person.lower().replace(' ', '_')}/{now.year}.jsonl"
        try:
            obj = s3_client.get_object(Bucket=s3_bucket, Key=person_key)
            existing = obj['Body'].read().decode('utf-8')
        except s3_client.exceptions.NoSuchKey:
            existing = ""
        
        updated = existing + json.dumps(memory_record) + "\n"
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=person_key,
            Body=updated.encode('utf-8'),
            ContentType='application/x-ndjson'
        )
        stored_paths.append(person_key)
    
    return {
        "memory_id": memory_id,
        "primary_path": daily_key,
        "stored_paths": stored_paths,
        "organization": {
            "daily": daily_key,
            "by_significance": memory.significance >= 8,
            "themes_indexed": memory.themes[:2],
            "people_indexed": memory.people[:3]
        }
    }


def update_life_context(
    current_context: PersonalContext,
    memory: Memory,
    analysis: Dict[str, Any]
) -> PersonalContext:
    """Update understanding of the person's life journey based on new memory."""
    
    # Update themes (keep most recent/relevant)
    current_context.growth_themes = list(dict.fromkeys(memory.themes + current_context.growth_themes))[:10]
    
    # Track people mentions
    for person in memory.people:
        current_context.recurring_people[person] = current_context.recurring_people.get(person, 0) + 1
    
    # Update sacred places
    for location in memory.locations:
        if location not in current_context.sacred_places and memory.significance >= 7:
            current_context.sacred_places.append(location)
    
    # Track growth insights as wisdom
    for insight in memory.growth_insights:
        if insight not in current_context.wisdom_gained:
            current_context.wisdom_gained.append(insight)
    
    # Update emotional baseline
    for emotion in memory.emotions:
        emotion_name = emotion.get('name', 'unknown')
        intensity = emotion.get('intensity', 0.5)
        
        current = current_context.emotional_baseline.get(emotion_name, 0)
        current_context.emotional_baseline[emotion_name] = (current + intensity) / 2
    
    # Determine life phase based on patterns
    if memory.significance >= 8 and "transformation" in memory.themes:
        current_context.current_phase = "transforming"
    elif "gratitude" in memory.themes and memory.sentiment == "positive":
        current_context.current_phase = "appreciating"
    elif memory.emotional_intensity > 0.7:
        current_context.current_phase = "processing"
    
    return current_context


def find_memory_connections(
    memory: Memory,
    s3_bucket: str
) -> List[Dict[str, str]]:
    """Find connections to previous memories based on themes, people, and time."""
    connections = []
    
    try:
        # Search by shared themes
        for theme in memory.themes[:2]:  # Top 2 themes
            theme_key = f"memories/themes/{theme.lower().replace(' ', '_')}/"
            
            # List objects with this theme prefix
            response = s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=theme_key,
                MaxKeys=5
            )
            
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.jsonl'):
                    connections.append({
                        "type": "theme",
                        "theme": theme,
                        "path": obj['Key'],
                        "date": obj['LastModified'].strftime('%Y-%m-%d')
                    })
        
        # Search by people
        for person in memory.people[:1]:  # Most important person
            person_key = f"memories/people/{person.lower().replace(' ', '_')}/"
            
            response = s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=person_key,
                MaxKeys=3
            )
            
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.jsonl'):
                    connections.append({
                        "type": "person",
                        "person": person,
                        "path": obj['Key'],
                        "date": obj['LastModified'].strftime('%Y-%m-%d')
                    })
    
    except Exception as e:
        logger.error(f"Failed to find connections: {e}")
    
    return connections[:5]  # Return top 5 connections


def generate_life_review(
    s3_bucket: str,
    time_period: str = "month"
) -> Dict[str, Any]:
    """Generate a comprehensive life review with insights and patterns.
    
    Args:
        s3_bucket: S3 bucket containing memories
        time_period: Period to review (week, month, quarter, year)
        
    Returns:
        Life review with insights and patterns
    """
    now = datetime.utcnow()
    
    # Determine time range
    if time_period == "week":
        start_date = now - timedelta(days=7)
        period_name = f"Week of {start_date.strftime('%B %d, %Y')}"
    elif time_period == "month":
        start_date = now - timedelta(days=30)
        period_name = f"{now.strftime('%B %Y')}"
    elif time_period == "quarter":
        start_date = now - timedelta(days=90)
        period_name = f"Q{(now.month-1)//3 + 1} {now.year}"
    else:
        start_date = now - timedelta(days=365)
        period_name = f"Year {now.year}"
    
    # Collect memories from time period
    memories = []
    current = start_date
    
    while current <= now:
        daily_key = f"memories/daily/{current.strftime('%Y-%m-%d')}.jsonl"
        try:
            obj = s3_client.get_object(Bucket=s3_bucket, Key=daily_key)
            content = obj['Body'].read().decode('utf-8')
            for line in content.strip().split('\n'):
                if line:
                    memories.append(json.loads(line))
        except:
            pass
        current += timedelta(days=1)
    
    if not memories:
        return {
            "period": period_name,
            "message": "No memories found for this period",
            "insights": []
        }
    
    # Analyze patterns
    theme_counts = {}
    emotion_summary = {}
    significant_memories = []
    gratitude_collection = []
    people_mentioned = {}
    
    total_significance = 0
    sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    
    for memory in memories:
        # Themes
        for theme in memory.get('themes', []):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        # Emotions
        for emotion in memory.get('emotions', []):
            if isinstance(emotion, dict):
                emotion_name = emotion.get('name', 'unknown')
            else:
                emotion_name = emotion
            emotion_summary[emotion_name] = emotion_summary.get(emotion_name, 0) + 1
        
        # Significance
        sig = memory.get('significance', 5)
        total_significance += sig
        if sig >= 8:
            significant_memories.append({
                'date': memory['timestamp'][:10],
                'preview': memory['content'][:100],
                'significance': sig,
                'themes': memory.get('themes', [])
            })
        
        # Gratitude
        gratitude_collection.extend(memory.get('gratitude_notes', []))
        
        # People
        for person in memory.get('people', []):
            people_mentioned[person] = people_mentioned.get(person, 0) + 1
        
        # Sentiment
        sentiment = memory.get('sentiment', 'neutral')
        sentiment_distribution[sentiment] += 1
    
    # Generate insights using AI
    insights = generate_period_insights(
        period_name, theme_counts, emotion_summary,
        sentiment_distribution, significant_memories,
        gratitude_collection, people_mentioned,
        len(memories), total_significance / max(len(memories), 1)
    )
    
    review = {
        "period": period_name,
        "memory_count": len(memories),
        "average_significance": round(total_significance / max(len(memories), 1), 1),
        "dominant_themes": sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        "emotional_landscape": sorted(emotion_summary.items(), key=lambda x: x[1], reverse=True)[:5],
        "sentiment_distribution": sentiment_distribution,
        "significant_memories": significant_memories[:5],
        "gratitude_highlights": gratitude_collection[:10],
        "important_people": sorted(people_mentioned.items(), key=lambda x: x[1], reverse=True)[:5],
        "insights": insights,
        "generated_at": now.isoformat()
    }
    
    # Store the review
    review_key = f"memories/reviews/{now.strftime('%Y-%m')}-{time_period}-review.json"
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=review_key,
        Body=json.dumps(review, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    return review


def generate_period_insights(
    period_name: str,
    theme_counts: Dict[str, int],
    emotion_summary: Dict[str, int],
    sentiment_dist: Dict[str, int],
    significant_memories: List[Dict],
    gratitude_notes: List[str],
    people_mentioned: Dict[str, int],
    total_memories: int,
    avg_significance: float
) -> List[str]:
    """Generate AI-powered insights about the time period."""
    
    try:
        from anthropic import Anthropic
        
        api_key = get_anthropic_api_key()
        anthropic = Anthropic(api_key=api_key)
        
        # Prepare data summary
        data_summary = f"""
Period: {period_name}
Total Memories: {total_memories}
Average Significance: {avg_significance:.1f}/10

Top Themes: {', '.join([f"{k} ({v})" for k, v in list(theme_counts.items())[:5]])}
Emotional Summary: {', '.join([f"{k} ({v})" for k, v in list(emotion_summary.items())[:5]])}
Sentiment: Positive {sentiment_dist['positive']}, Neutral {sentiment_dist['neutral']}, Negative {sentiment_dist['negative']}, Mixed {sentiment_dist['mixed']}
Key People: {', '.join([f"{k} ({v} mentions)" for k, v in list(people_mentioned.items())[:3]])}
Significant Events: {len(significant_memories)} memories rated 8+/10
Sample Gratitudes: {'; '.join(gratitude_notes[:3])}
"""
        
        prompt = f"""Analyze this life period data and provide 5-7 meaningful insights about the person's journey, patterns, and growth.

{data_summary}

Focus on:
1. Overall life themes and what they suggest about this period
2. Emotional patterns and well-being
3. Relationships and connections
4. Personal growth and development
5. Gratitude and appreciation patterns
6. Any notable shifts or transformations
7. Gentle suggestions for reflection or future focus

Be warm, insightful, and supportive. Write as a wise friend who sees patterns the person might miss.

Respond as a JSON array of insight strings."""

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        # Extract JSON array
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            insights = json.loads(json_match.group())
            return insights
        else:
            raise ValueError("No valid JSON array in response")
            
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        # Provide basic insights as fallback
        return [
            f"This {period_name} included {total_memories} memories with an average significance of {avg_significance:.1f}/10.",
            f"Your most common themes were: {', '.join(list(theme_counts.keys())[:3])}.",
            f"Emotionally, you experienced: {', '.join(list(emotion_summary.keys())[:3])} most frequently.",
            f"You have {len(significant_memories)} highly significant memories from this period worth revisiting.",
            f"Your gratitude practice shows appreciation for: {', '.join(gratitude_notes[:2])}" if gratitude_notes else "Consider noting what you're grateful for in your memories."
        ]


def search_memories(
    query: str,
    filters: Optional[Dict[str, Any]],
    s3_bucket: str,
    max_results: int = 20
) -> List[Dict[str, Any]]:
    """Search memories by content, themes, people, or emotions.
    
    Args:
        query: Search query
        filters: Optional filters (themes, people, sentiment, date_range)
        s3_bucket: S3 bucket to search
        max_results: Maximum results to return
        
    Returns:
        List of matching memories
    """
    matches = []
    
    # Parse filters
    theme_filter = filters.get('themes', []) if filters else []
    people_filter = filters.get('people', []) if filters else []
    sentiment_filter = filters.get('sentiment') if filters else None
    min_significance = filters.get('min_significance', 1) if filters else 1
    
    # For demonstration, search recent daily files
    # In production, this would use a search index
    now = datetime.utcnow()
    for days_back in range(30):  # Search last 30 days
        date = now - timedelta(days=days_back)
        daily_key = f"memories/daily/{date.strftime('%Y-%m-%d')}.jsonl"
        
        try:
            obj = s3_client.get_object(Bucket=s3_bucket, Key=daily_key)
            content = obj['Body'].read().decode('utf-8')
            
            for line in content.strip().split('\n'):
                if not line:
                    continue
                    
                memory = json.loads(line)
                
                # Apply filters
                if min_significance and memory.get('significance', 0) < min_significance:
                    continue
                    
                if sentiment_filter and memory.get('sentiment') != sentiment_filter:
                    continue
                    
                if theme_filter and not any(t in memory.get('themes', []) for t in theme_filter):
                    continue
                    
                if people_filter and not any(p in memory.get('people', []) for p in people_filter):
                    continue
                
                # Check query match
                if query.lower() in memory.get('content', '').lower():
                    matches.append({
                        "memory_id": memory.get('id'),
                        "timestamp": memory.get('timestamp'),
                        "preview": memory.get('content', '')[:200] + '...',
                        "themes": memory.get('themes', []),
                        "people": memory.get('people', []),
                        "sentiment": memory.get('sentiment'),
                        "significance": memory.get('significance', 5)
                    })
                    
                    if len(matches) >= max_results:
                        return matches
                        
        except Exception as e:
            continue
    
    return matches


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SQS events from SpiritualAdvisor queue.
    
    Processes personal memories with deep emotional and spiritual intelligence,
    organizing them beautifully in S3 and providing insights for personal growth.
    """
    try:
        # Load personal context once
        personal_context = load_personal_context()
        logger.info(f"Loaded personal context for phase: {personal_context.current_phase}")
        
        # Process each record
        for record in event['Records']:
            # Parse message
            message = json.loads(record['body'])
            transcript = message['transcript']
            s3_bucket = message['bucket']
            s3_key = message['key']
            
            logger.info(f"Processing personal memory from {s3_key}")
            
            # Run async analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Analyze memory with spiritual lens
                analysis = loop.run_until_complete(
                    analyze_memory_with_spiritual_lens(transcript, personal_context)
                )
                
                # Create structured memory
                emotions_list = []
                emotional_intensity = analysis.get('emotional_intensity', 0.5)
                
                for emotion in analysis.get('emotions', []):
                    if isinstance(emotion, dict):
                        emotions_list.append(emotion)
                    else:
                        emotions_list.append({"name": emotion, "intensity": 0.5})
                
                memory = Memory(
                    timestamp=datetime.utcnow(),
                    content=transcript,
                    sentiment=analysis['sentiment'],
                    emotions=emotions_list,
                    emotional_intensity=emotional_intensity,
                    themes=analysis['themes'],
                    people=analysis['people'],
                    locations=analysis['locations'],
                    significance=analysis['significance'],
                    life_area=analysis['life_area'],
                    memory_type=analysis['memory_type'],
                    growth_insights=analysis['growth_insights'],
                    gratitude_notes=analysis['gratitude_notes'],
                    spiritual_insights=analysis.get('spiritual_insights', ''),
                    key_quotes=analysis.get('key_quotes', []),
                    related_memories=[]  # Will be populated by find_memory_connections
                )
                
                # Find connections to past memories
                connections = find_memory_connections(memory, s3_bucket)
                memory.related_memories = [c['path'] for c in connections[:3]]
                
                # Organize in S3 with beautiful structure
                storage_result = organize_memory_in_s3(memory, s3_bucket, analysis)
                
                # Update life context
                updated_context = update_life_context(personal_context, memory, analysis)
                
                # Create output document
                output = {
                    "status": "success",
                    "memory_id": storage_result['memory_id'],
                    "timestamp": memory.timestamp.isoformat(),
                    "storage_paths": storage_result['stored_paths'],
                    "analysis": {
                        "sentiment": memory.sentiment,
                        "emotions": memory.emotions,
                        "emotional_intensity": memory.emotional_intensity,
                        "themes": memory.themes,
                        "significance": memory.significance,
                        "life_area": memory.life_area,
                        "memory_type": memory.memory_type
                    },
                    "insights": {
                        "growth": memory.growth_insights,
                        "gratitude": memory.gratitude_notes,
                        "spiritual": memory.spiritual_insights
                    },
                    "connections": {
                        "people": memory.people,
                        "places": memory.locations,
                        "themes": memory.themes,
                        "related_memories": connections[:3]
                    },
                    "life_context": {
                        "current_phase": updated_context.current_phase,
                        "emotional_baseline": dict(list(updated_context.emotional_baseline.items())[:5]),
                        "recurring_people": dict(sorted(updated_context.recurring_people.items(), 
                                                      key=lambda x: x[1], reverse=True)[:5])
                    }
                }
                
                # Store detailed output
                output_key = s3_key.replace('transcripts/', 'outputs/spiritual_advisor/').replace('.txt', '_memory.json')
                s3_client.put_object(
                    Bucket=s3_bucket,
                    Key=output_key,
                    Body=json.dumps(output, indent=2),
                    ContentType='application/json',
                    ServerSideEncryption='AES256',  # Encrypt personal data
                    Metadata={
                        'memory_id': storage_result['memory_id'],
                        'significance': str(memory.significance),
                        'primary_theme': memory.themes[0] if memory.themes else 'personal',
                        'sentiment': memory.sentiment
                    }
                )
                
                logger.info(f"Successfully processed memory: {storage_result['memory_id']} (significance: {memory.significance})")
                
                # Log high-significance memories
                if memory.significance >= 8:
                    logger.info(f"HIGH SIGNIFICANCE MEMORY: {memory.spiritual_insights or memory.growth_insights[0] if memory.growth_insights else 'Significant moment'}")
                
                # Generate weekly review on Sundays
                if datetime.utcnow().weekday() == 6:  # Sunday
                    weekly_review = generate_life_review(s3_bucket, "week")
                    logger.info(f"Generated weekly life review")
                
                # Monthly review on the 1st
                if datetime.utcnow().day == 1:
                    monthly_review = generate_life_review(s3_bucket, "month")
                    logger.info(f"Generated monthly life review")
                
            finally:
                loop.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Memories processed with love and wisdom'})
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }