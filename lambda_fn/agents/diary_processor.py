"""Diary Processor - Emotionally Intelligent Personal Memory System.

This module handles personal memories with the care and nuance they deserve,
extracting emotional context, relationships, and meaningful moments while
preserving the original voice and sentiment.

DESIGN PHILOSOPHY:
- Memories are sacred - preserve the original voice and emotion
- Context matters - extract people, places, feelings, and themes
- Privacy first - personal data stays personal
- Beauty in simplicity - human-readable, queryable, meaningful
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib
import re

import boto3
from anthropic import Anthropic

logger = logging.getLogger(__name__)


@dataclass
class DiaryEntry:
    """Structured representation of a personal memory.
    
    This is designed to capture not just what was said, but the
    emotional context, relationships, and significance of the moment.
    """
    date: str  # ISO format date
    time: str  # HH:MM format
    verbatim: str  # Original transcript
    summary: str  # AI-generated summary
    tags: List[str]  # Extracted themes/tags
    people: List[str]  # People mentioned
    locations: List[str]  # Places mentioned
    emotions: List[str]  # Detected emotions
    sentiment: str  # Overall sentiment (positive/negative/mixed/neutral)
    significance_score: float  # 0-1 score of emotional significance
    audio_url: Optional[str] = None  # Original audio if available
    metadata: Dict[str, Any] = None  # Additional context
    
    def to_json(self) -> str:
        """Convert to beautifully formatted JSON."""
        data = asdict(self)
        # Ensure metadata is initialized
        if data['metadata'] is None:
            data['metadata'] = {}
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DiaryEntry':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class DiaryProcessor:
    """Emotionally intelligent processor for personal memories."""
    
    def __init__(self, anthropic_api_key: str, s3_bucket: str = "voice-memos-diary"):
        """Initialize the diary processor.
        
        Args:
            anthropic_api_key: API key for Claude
            s3_bucket: S3 bucket for storing diary entries
        """
        self.anthropic = Anthropic(api_key=anthropic_api_key)
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
        
        # Emotion lexicon for nuanced detection
        self.emotion_patterns = {
            'joy': ['happy', 'excited', 'delighted', 'joyful', 'elated', 'cheerful', 'laughed', 'funny'],
            'love': ['love', 'adore', 'cherish', 'care', 'affection', 'tender', 'sweet'],
            'gratitude': ['grateful', 'thankful', 'appreciated', 'blessed', 'fortunate'],
            'peace': ['calm', 'peaceful', 'serene', 'tranquil', 'relaxed', 'present'],
            'nostalgia': ['remember', 'reminded', 'memories', 'used to', 'back when'],
            'sadness': ['sad', 'cried', 'tears', 'miss', 'lonely', 'melancholy'],
            'worry': ['worried', 'anxious', 'concerned', 'nervous', 'stressed'],
            'grief': ['loss', 'grief', 'mourning', 'goodbye', 'passed away'],
            'wonder': ['amazing', 'incredible', 'awe', 'beautiful', 'magical'],
            'pride': ['proud', 'accomplished', 'achieved', 'succeeded'],
        }
        
        # Common relationship identifiers
        self.relationship_patterns = {
            'family': ['mom', 'dad', 'mother', 'father', 'sister', 'brother', 'daughter', 'son', 
                      'grandma', 'grandpa', 'aunt', 'uncle', 'cousin', 'family'],
            'partner': ['wife', 'husband', 'partner', 'boyfriend', 'girlfriend', 'spouse'],
            'children': ['kid', 'child', 'baby', 'toddler'],
            'friends': ['friend', 'buddy', 'pal', 'mate'],
        }
    
    async def process_transcript(
        self, 
        transcript: str, 
        audio_url: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> DiaryEntry:
        """Process a transcript into a structured diary entry.
        
        Args:
            transcript: The voice memo transcript
            audio_url: Optional URL to original audio
            source_metadata: Optional metadata about the source
            
        Returns:
            Structured DiaryEntry with extracted metadata
        """
        # Extract metadata using Claude for nuanced understanding
        analysis = await self._analyze_with_ai(transcript)
        
        # Extract people and relationships
        people = self._extract_people(transcript, analysis)
        
        # Extract locations
        locations = self._extract_locations(transcript, analysis)
        
        # Detect emotions with nuance
        emotions = self._detect_emotions(transcript, analysis)
        
        # Calculate significance score
        significance = self._calculate_significance(emotions, analysis)
        
        # Generate human-friendly tags
        tags = self._generate_tags(people, locations, emotions, analysis)
        
        # Create the diary entry
        now = datetime.now()
        entry = DiaryEntry(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M"),
            verbatim=transcript,
            summary=analysis.get('summary', ''),
            tags=tags,
            people=people,
            locations=locations,
            emotions=emotions,
            sentiment=analysis.get('sentiment', 'neutral'),
            significance_score=significance,
            audio_url=audio_url,
            metadata={
                'word_count': len(transcript.split()),
                'processing_timestamp': now.isoformat(),
                'source': source_metadata or {},
                'themes': analysis.get('themes', [])
            }
        )
        
        # Store the entry
        await self._store_entry(entry)
        
        return entry
    
    async def _analyze_with_ai(self, transcript: str) -> Dict[str, Any]:
        """Use Claude to deeply analyze the emotional content."""
        prompt = f"""Analyze this personal diary entry for emotional content and significance.
        
Transcript: "{transcript}"

Please provide:
1. A brief, warm summary (1-2 sentences) that captures the essence
2. The overall sentiment (positive/negative/mixed/neutral)
3. Key themes present in the memory
4. Any notable emotional moments or turning points
5. Suggested tags that capture the spirit of this memory

Respond in JSON format:
{{
    "summary": "Brief warm summary",
    "sentiment": "positive/negative/mixed/neutral",
    "themes": ["theme1", "theme2"],
    "emotional_moments": ["moment1", "moment2"],
    "suggested_tags": ["tag1", "tag2"],
    "significance_notes": "Why this memory might be meaningful"
}}"""
        
        try:
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                temperature=0.7,  # Slightly creative for emotional understanding
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse the JSON response
            content = response.content[0].text
            # Extract JSON from the response (handling potential markdown)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.error("No JSON found in AI response")
                return {}
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                'summary': transcript[:100] + "..." if len(transcript) > 100 else transcript,
                'sentiment': 'neutral',
                'themes': [],
                'emotional_moments': [],
                'suggested_tags': []
            }
    
    def _extract_people(self, transcript: str, ai_analysis: Dict[str, Any]) -> List[str]:
        """Extract people mentioned in the transcript."""
        people = set()
        transcript_lower = transcript.lower()
        
        # Look for capitalized names (simple heuristic)
        words = transcript.split()
        for i, word in enumerate(words):
            # Check if it's capitalized and not at sentence start
            if word[0].isupper() and i > 0 and words[i-1][-1] not in '.!?':
                # Basic name validation
                clean_word = word.strip('.,!?"\'')
                if len(clean_word) > 2 and clean_word.isalpha():
                    people.add(clean_word)
        
        # Add specific names mentioned in common patterns
        name_patterns = [
            r'\b([A-Z][a-z]+)\s+said\b',
            r'\bwith\s+([A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+)\s+and\s+I\b',
            r'\bmy\s+\w+\s+([A-Z][a-z]+)\b',  # "my friend Sarah"
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, transcript)
            people.update(matches)
        
        # Add relationship identifiers if no specific names
        if not people:
            for rel_type, rel_words in self.relationship_patterns.items():
                if any(word in transcript_lower for word in rel_words):
                    people.add(f"[{rel_type}]")
        
        return sorted(list(people))
    
    def _extract_locations(self, transcript: str, ai_analysis: Dict[str, Any]) -> List[str]:
        """Extract locations mentioned in the transcript."""
        locations = set()
        
        # Common location indicators
        location_patterns = [
            r'\bat\s+the\s+([A-Z]\w+(?:\s+[A-Z]\w+)*)\b',
            r'\bin\s+([A-Z]\w+(?:\s+[A-Z]\w+)*)\b',
            r'\bto\s+([A-Z]\w+(?:\s+[A-Z]\w+)*)\b',
            r'\b(?:beach|park|restaurant|cafe|home|house|office|school|church|store|mall|mountain|lake|river)\b',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            locations.update(match.title() if isinstance(match, str) else match for match in matches)
        
        # Add location types even if no specific names
        location_words = ['beach', 'park', 'restaurant', 'cafe', 'home', 'house', 
                         'office', 'school', 'church', 'store', 'mall', 'mountain', 
                         'lake', 'river', 'ocean', 'forest', 'garden']
        
        transcript_lower = transcript.lower()
        for word in location_words:
            if word in transcript_lower:
                locations.add(word.title())
        
        return sorted(list(locations))
    
    def _detect_emotions(self, transcript: str, ai_analysis: Dict[str, Any]) -> List[str]:
        """Detect emotions with nuance and context."""
        detected_emotions = set()
        transcript_lower = transcript.lower()
        
        # Check emotion patterns
        for emotion, keywords in self.emotion_patterns.items():
            if any(keyword in transcript_lower for keyword in keywords):
                detected_emotions.add(emotion)
        
        # Add emotions from AI analysis
        if 'emotional_moments' in ai_analysis:
            # Extract emotion words from AI's emotional moments
            for moment in ai_analysis['emotional_moments']:
                for emotion in self.emotion_patterns:
                    if emotion in moment.lower():
                        detected_emotions.add(emotion)
        
        # If no emotions detected, check sentiment
        if not detected_emotions and ai_analysis.get('sentiment') == 'positive':
            detected_emotions.add('contentment')
        elif not detected_emotions and ai_analysis.get('sentiment') == 'negative':
            detected_emotions.add('melancholy')
        
        return sorted(list(detected_emotions))
    
    def _calculate_significance(self, emotions: List[str], ai_analysis: Dict[str, Any]) -> float:
        """Calculate emotional significance score (0-1)."""
        score = 0.0
        
        # Base score from emotion count and intensity
        emotion_weights = {
            'love': 0.9, 'grief': 0.9, 'joy': 0.8, 'gratitude': 0.8,
            'wonder': 0.7, 'pride': 0.7, 'nostalgia': 0.6,
            'worry': 0.5, 'sadness': 0.6, 'peace': 0.5,
            'contentment': 0.3, 'melancholy': 0.4
        }
        
        if emotions:
            emotion_score = sum(emotion_weights.get(e, 0.3) for e in emotions) / len(emotions)
            score += emotion_score * 0.5
        
        # Boost for multiple people mentioned (shared experiences)
        if ai_analysis.get('themes'):
            score += min(len(ai_analysis['themes']) * 0.1, 0.3)
        
        # Boost for emotional moments identified by AI
        if ai_analysis.get('emotional_moments'):
            score += min(len(ai_analysis['emotional_moments']) * 0.1, 0.2)
        
        return min(score, 1.0)
    
    def _generate_tags(
        self, 
        people: List[str], 
        locations: List[str], 
        emotions: List[str],
        ai_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate human-friendly tags for the memory."""
        tags = set()
        
        # Add emotion tags
        tags.update(f"#{emotion}" for emotion in emotions[:3])  # Top 3 emotions
        
        # Add relationship tags
        if people:
            if any(rel in str(people) for rel in ['family', 'mom', 'dad', 'sister', 'brother']):
                tags.add('#family')
            if any(rel in str(people) for rel in ['friend']):
                tags.add('#friendship')
            if any(rel in str(people) for rel in ['wife', 'husband', 'partner']):
                tags.add('#love')
        
        # Add location-based tags
        if locations:
            if any(loc in str(locations).lower() for loc in ['beach', 'ocean', 'mountain', 'forest']):
                tags.add('#nature')
            if any(loc in str(locations).lower() for loc in ['home', 'house']):
                tags.add('#home')
        
        # Add theme tags from AI
        if ai_analysis.get('suggested_tags'):
            tags.update(f"#{tag}" if not tag.startswith('#') else tag 
                       for tag in ai_analysis['suggested_tags'][:3])
        
        # Add time-based tags
        now = datetime.now()
        if now.weekday() in [5, 6]:  # Weekend
            tags.add('#weekend')
        
        # Season tags
        month = now.month
        if month in [12, 1, 2]:
            tags.add('#winter')
        elif month in [3, 4, 5]:
            tags.add('#spring')
        elif month in [6, 7, 8]:
            tags.add('#summer')
        else:
            tags.add('#autumn')
        
        return sorted(list(tags))
    
    async def _store_entry(self, entry: DiaryEntry) -> str:
        """Store diary entry in S3 with beautiful organization."""
        # Create a human-readable file path
        date_path = f"diary/{entry.date[:4]}/{entry.date[5:7]}/{entry.date}-{entry.time.replace(':', '')}"
        
        # Add a content preview to the filename for easier browsing
        preview = re.sub(r'[^\w\s-]', '', entry.summary[:30]).strip()
        preview = re.sub(r'[-\s]+', '-', preview)
        
        key = f"{date_path}-{preview}.json"
        
        try:
            # Store the entry
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=entry.to_json().encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'significance': str(entry.significance_score),
                    'sentiment': entry.sentiment,
                    'people_count': str(len(entry.people)),
                    'emotion_primary': entry.emotions[0] if entry.emotions else 'none'
                }
            )
            
            # Also store in a daily index for easy retrieval
            daily_index_key = f"diary/{entry.date[:4]}/{entry.date[5:7]}/daily/{entry.date}-index.jsonl"
            index_entry = {
                'time': entry.time,
                'summary': entry.summary,
                'significance': entry.significance_score,
                'emotions': entry.emotions[:2],  # Top 2 emotions
                'tags': entry.tags[:3],  # Top 3 tags
                'key': key
            }
            
            # Append to daily index (creates if doesn't exist)
            try:
                existing = self.s3_client.get_object(Bucket=self.s3_bucket, Key=daily_index_key)
                content = existing['Body'].read().decode('utf-8')
            except:
                content = ""
            
            content += json.dumps(index_entry) + '\n'
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=daily_index_key,
                Body=content.encode('utf-8'),
                ContentType='application/x-ndjson'
            )
            
            logger.info(f"Stored diary entry: {key}")
            return key
            
        except Exception as e:
            logger.error(f"Failed to store diary entry: {e}")
            raise


class DiarySearch:
    """Search and query interface for diary entries."""
    
    def __init__(self, s3_bucket: str = "voice-memos-diary"):
        """Initialize the diary search interface."""
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
    
    async def search_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[DiaryEntry]:
        """Search diary entries within a date range."""
        entries = []
        
        # Convert dates to datetime for comparison
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # List all diary entries in the range
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for year in range(start.year, end.year + 1):
            prefix = f"diary/{year}/"
            
            for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    # Extract date from key
                    if obj['Key'].endswith('.json') and 'daily' not in obj['Key']:
                        try:
                            # Parse date from filename
                            parts = obj['Key'].split('/')
                            if len(parts) >= 4:
                                date_part = parts[3][:10]  # YYYY-MM-DD
                                entry_date = datetime.strptime(date_part, "%Y-%m-%d")
                                
                                if start <= entry_date <= end:
                                    # Fetch and parse entry
                                    response = self.s3_client.get_object(
                                        Bucket=self.s3_bucket,
                                        Key=obj['Key']
                                    )
                                    content = response['Body'].read().decode('utf-8')
                                    entry = DiaryEntry.from_json(content)
                                    entries.append(entry)
                        except Exception as e:
                            logger.error(f"Error parsing entry {obj['Key']}: {e}")
        
        return sorted(entries, key=lambda e: f"{e.date} {e.time}", reverse=True)
    
    async def search_by_tags(self, tags: List[str]) -> List[DiaryEntry]:
        """Search diary entries by tags."""
        entries = []
        tag_set = set(tags)
        
        # We need to scan all entries for tags
        # In a production system, we'd have a tag index
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.s3_bucket, Prefix="diary/"):
            for obj in page.get('Contents', []):
                if obj['Key'].endswith('.json') and 'daily' not in obj['Key']:
                    try:
                        response = self.s3_client.get_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        content = response['Body'].read().decode('utf-8')
                        entry = DiaryEntry.from_json(content)
                        
                        # Check if entry has any of the requested tags
                        if tag_set.intersection(set(entry.tags)):
                            entries.append(entry)
                    except Exception as e:
                        logger.error(f"Error checking entry {obj['Key']}: {e}")
        
        return sorted(entries, key=lambda e: f"{e.date} {e.time}", reverse=True)
    
    async def search_by_emotion(self, emotion: str) -> List[DiaryEntry]:
        """Search diary entries by emotion."""
        entries = []
        
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.s3_bucket, Prefix="diary/"):
            for obj in page.get('Contents', []):
                # Check metadata first for quick filtering
                if 'emotion_primary' in obj.get('Metadata', {}):
                    if obj['Metadata']['emotion_primary'] == emotion:
                        try:
                            response = self.s3_client.get_object(
                                Bucket=self.s3_bucket,
                                Key=obj['Key']
                            )
                            content = response['Body'].read().decode('utf-8')
                            entry = DiaryEntry.from_json(content)
                            entries.append(entry)
                        except Exception as e:
                            logger.error(f"Error loading entry {obj['Key']}: {e}")
        
        return sorted(entries, key=lambda e: e.significance_score, reverse=True)
    
    async def get_daily_summary(self, date: str) -> Dict[str, Any]:
        """Get a summary of a day's diary entries."""
        daily_index_key = f"diary/{date[:4]}/{date[5:7]}/daily/{date}-index.jsonl"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=daily_index_key
            )
            content = response['Body'].read().decode('utf-8')
            
            entries = []
            emotions_count = {}
            total_significance = 0.0
            
            for line in content.strip().split('\n'):
                if line:
                    entry_data = json.loads(line)
                    entries.append(entry_data)
                    
                    # Count emotions
                    for emotion in entry_data.get('emotions', []):
                        emotions_count[emotion] = emotions_count.get(emotion, 0) + 1
                    
                    total_significance += entry_data.get('significance', 0)
            
            return {
                'date': date,
                'entry_count': len(entries),
                'entries': entries,
                'dominant_emotions': sorted(emotions_count.items(), key=lambda x: x[1], reverse=True)[:3],
                'average_significance': total_significance / len(entries) if entries else 0,
                'tags': list(set(tag for e in entries for tag in e.get('tags', [])))
            }
            
        except Exception as e:
            logger.error(f"Error getting daily summary for {date}: {e}")
            return {
                'date': date,
                'entry_count': 0,
                'entries': [],
                'dominant_emotions': [],
                'average_significance': 0,
                'tags': []
            }


# Example usage
async def main():
    """Example of how to use the diary processor."""
    processor = DiaryProcessor(
        anthropic_api_key="your-api-key",
        s3_bucket="voice-memos-diary"
    )
    
    # Process a sample memory
    transcript = """
    Rio said the funniest thing today at breakfast. She looked at her cereal and said 
    "Daddy, the milk is swimming!" and then started making swimming motions with her spoon. 
    It was such a pure moment of joy. These little observations she makes remind me why 
    childhood is so magical. I want to remember this feeling forever.
    """
    
    entry = await processor.process_transcript(
        transcript,
        audio_url="s3://voice-memos/2025-07-03T0812.mp3"
    )
    
    print(f"Created diary entry:")
    print(entry.to_json())
    
    # Example search
    search = DiarySearch(s3_bucket="voice-memos-diary")
    
    # Find all joyful memories
    joyful_memories = await search.search_by_emotion("joy")
    print(f"\nFound {len(joyful_memories)} joyful memories")
    
    # Get today's summary
    today = datetime.now().strftime("%Y-%m-%d")
    summary = await search.get_daily_summary(today)
    print(f"\nToday's diary summary: {summary}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())