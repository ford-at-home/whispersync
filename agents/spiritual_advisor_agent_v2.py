"""SpiritualAdvisorAgent V2 - Enhanced with diary features and rich metadata extraction.

Core enhancements:
- Diary feature with verbatim storage and intelligent extraction
- Rich metadata including emotional arcs, spiritual themes, and growth markers
- Knowledge architecture that identifies recurring life patterns
- Persona voice hooks for authentic spiritual guidance
- Multi-dimensional memory organization with relationship mapping
"""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import hashlib
import asyncio
from collections import defaultdict
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

import boto3

from .base import BaseAgent, requires_aws, AgentError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

# Configuration
MEMORY_ARCHIVE_BUCKET = os.environ.get('MEMORY_ARCHIVE_BUCKET', 'whispersync-memories')
DIARY_TABLE = os.environ.get('DIARY_TABLE', 'SpiritualAdvisor-Diary')
LIFE_PATTERNS_TABLE = os.environ.get('LIFE_PATTERNS_TABLE', 'SpiritualAdvisor-LifePatterns')
PERSONAL_CONTEXT_SECRET = os.environ.get('PERSONAL_CONTEXT_SECRET', 'spiritual/personal_context')

# Initialize NLTK components
try:
    nltk.download('vader_lexicon', quiet=True)
    sia = SentimentIntensityAnalyzer()
except:
    sia = None
    logger.warning("NLTK sentiment analyzer not available")


@dataclass
class DiaryEntry:
    """Rich diary entry with verbatim text and extracted wisdom."""
    
    id: str
    timestamp: datetime
    verbatim_text: str  # Exact transcript
    
    # Extracted elements
    extracted_quotes: List[str] = field(default_factory=list)  # Meaningful phrases
    emotional_arc: List[Dict[str, float]] = field(default_factory=list)  # Emotion progression
    spiritual_insights: List[str] = field(default_factory=list)
    life_questions: List[str] = field(default_factory=list)  # Questions posed
    gratitude_expressions: List[str] = field(default_factory=list)
    
    # Rich metadata
    primary_emotion: str = "contemplative"
    emotional_intensity: float = 0.5
    spiritual_themes: List[str] = field(default_factory=list)
    life_areas: List[str] = field(default_factory=list)
    mentioned_people: List[Dict[str, str]] = field(default_factory=list)  # name -> relationship
    mentioned_places: List[str] = field(default_factory=list)
    
    # Patterns and connections
    recurring_themes: List[str] = field(default_factory=list)
    life_phase_markers: List[str] = field(default_factory=list)
    growth_indicators: List[str] = field(default_factory=list)
    shadow_work: List[str] = field(default_factory=list)  # Challenges/difficulties
    
    # Significance scoring
    personal_significance: int = 5  # 1-10
    spiritual_significance: int = 5  # 1-10
    transformational_potential: int = 5  # 1-10
    
    # Connections
    related_entries: List[str] = field(default_factory=list)  # IDs of related diary entries
    triggered_memories: List[str] = field(default_factory=list)  # Connected memory IDs
    
    # Voice memo specific
    voice_qualities: Dict[str, Any] = field(default_factory=dict)  # tone, pace, pauses
    background_context: str = ""  # Time of day, location hints from audio


@dataclass
class LifePattern:
    """Recurring patterns discovered across diary entries."""
    
    pattern_id: str
    pattern_type: str  # emotional, behavioral, relational, spiritual
    description: str
    
    # Pattern details
    frequency: int = 0  # How often observed
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    
    # Pattern components
    trigger_conditions: List[str] = field(default_factory=list)
    typical_responses: List[str] = field(default_factory=list)
    associated_emotions: List[str] = field(default_factory=list)
    
    # Growth tracking
    evolution_notes: List[str] = field(default_factory=list)
    healing_progress: float = 0.0  # 0-1 scale
    integration_level: str = "emerging"  # emerging, active, integrating, integrated
    
    # Connections
    related_patterns: List[str] = field(default_factory=list)
    diary_entry_ids: List[str] = field(default_factory=list)


@dataclass
class SpiritualKnowledgeBase:
    """Knowledge architecture for spiritual growth and self-understanding."""
    
    # Core themes across all entries
    life_themes: Dict[str, int] = field(default_factory=dict)  # theme -> frequency
    
    # Emotional landscape
    emotional_vocabulary: Set[str] = field(default_factory=set)
    emotional_patterns: Dict[str, List[str]] = field(default_factory=dict)
    
    # Relationship map
    key_relationships: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationship_dynamics: Dict[str, List[str]] = field(default_factory=dict)
    
    # Spiritual journey
    spiritual_milestones: List[Dict[str, Any]] = field(default_factory=list)
    wisdom_collection: List[str] = field(default_factory=list)
    practices_mentioned: Dict[str, int] = field(default_factory=dict)
    
    # Shadow integration
    shadow_themes: Dict[str, List[str]] = field(default_factory=dict)
    healing_journey: List[Dict[str, Any]] = field(default_factory=list)
    
    # Growth metrics
    self_awareness_indicators: List[str] = field(default_factory=list)
    compassion_expressions: List[str] = field(default_factory=list)
    
    def evolve(self, entry: DiaryEntry) -> Dict[str, Any]:
        """Evolve knowledge base with new diary entry."""
        evolution_report = {
            "new_themes": [],
            "pattern_reinforcements": [],
            "relationship_updates": [],
            "spiritual_insights": []
        }
        
        # Update life themes
        for theme in entry.spiritual_themes:
            if theme not in self.life_themes:
                evolution_report["new_themes"].append(theme)
            self.life_themes[theme] = self.life_themes.get(theme, 0) + 1
        
        # Expand emotional vocabulary
        before_size = len(self.emotional_vocabulary)
        self.emotional_vocabulary.add(entry.primary_emotion)
        if len(self.emotional_vocabulary) > before_size:
            evolution_report["new_emotions"] = entry.primary_emotion
        
        # Update relationships
        for person in entry.mentioned_people:
            name = person.get("name", "Unknown")
            if name not in self.key_relationships:
                self.key_relationships[name] = {
                    "first_mention": entry.timestamp,
                    "relationship_type": person.get("relationship", "unspecified"),
                    "mention_count": 0,
                    "associated_emotions": [],
                    "shared_experiences": []
                }
                evolution_report["relationship_updates"].append(f"New person: {name}")
            
            self.key_relationships[name]["mention_count"] += 1
            self.key_relationships[name]["associated_emotions"].append(entry.primary_emotion)
        
        # Collect wisdom
        self.wisdom_collection.extend(entry.spiritual_insights)
        
        # Track healing journey
        if entry.shadow_work:
            self.healing_journey.append({
                "date": entry.timestamp,
                "shadows_faced": entry.shadow_work,
                "growth_noted": entry.growth_indicators
            })
        
        return evolution_report


class DiaryProcessor:
    """Process diary entries with rich extraction and pattern detection."""
    
    def __init__(self):
        self.knowledge_base = SpiritualKnowledgeBase()
        self.life_patterns: Dict[str, LifePattern] = {}
    
    async def process_diary_entry(
        self,
        transcript: str,
        personal_context: Dict[str, Any]
    ) -> DiaryEntry:
        """Process transcript into rich diary entry."""
        
        # Generate unique ID
        entry_id = hashlib.md5(
            f"{datetime.utcnow().isoformat()}_{transcript[:50]}".encode()
        ).hexdigest()[:12]
        
        # Create base entry
        entry = DiaryEntry(
            id=entry_id,
            timestamp=datetime.utcnow(),
            verbatim_text=transcript
        )
        
        # Extract meaningful quotes (look for complete thoughts)
        entry.extracted_quotes = self._extract_meaningful_quotes(transcript)
        
        # Analyze emotional arc
        entry.emotional_arc = self._analyze_emotional_arc(transcript)
        entry.primary_emotion = self._determine_primary_emotion(entry.emotional_arc)
        
        # Extract spiritual and life elements
        entry.spiritual_insights = await self._extract_spiritual_insights(transcript, personal_context)
        entry.life_questions = self._extract_questions(transcript)
        entry.gratitude_expressions = self._extract_gratitude(transcript)
        
        # Extract entities and themes
        entry.mentioned_people = self._extract_people(transcript)
        entry.mentioned_places = self._extract_places(transcript)
        entry.spiritual_themes = self._identify_spiritual_themes(transcript)
        entry.life_areas = self._identify_life_areas(transcript)
        
        # Identify patterns and growth
        entry.growth_indicators = self._identify_growth_indicators(transcript)
        entry.shadow_work = self._identify_shadow_work(transcript)
        entry.life_phase_markers = self._identify_life_phase_markers(transcript, personal_context)
        
        # Calculate significance scores
        entry.personal_significance = self._calculate_personal_significance(entry)
        entry.spiritual_significance = self._calculate_spiritual_significance(entry)
        entry.transformational_potential = self._calculate_transformational_potential(entry)
        
        # Find connections to past entries
        entry.related_entries = await self._find_related_entries(entry)
        
        # Detect life patterns
        self._update_life_patterns(entry)
        
        # Evolve knowledge base
        evolution_report = self.knowledge_base.evolve(entry)
        logger.info(f"Knowledge base evolved: {evolution_report}")
        
        return entry
    
    def _extract_meaningful_quotes(self, text: str) -> List[str]:
        """Extract complete, meaningful thoughts from text."""
        quotes = []
        
        # Split by sentence-like boundaries
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Look for meaningful indicators
            if any(indicator in sentence.lower() for indicator in [
                'realize', 'understand', 'feel', 'believe', 'think',
                'remember', 'learned', 'discovered', 'noticed',
                'grateful', 'appreciate', 'love', 'hope'
            ]):
                if len(sentence) > 20:  # Meaningful length
                    quotes.append(sentence)
        
        # Also look for quoted text
        quoted = re.findall(r'"([^"]+)"', text)
        quotes.extend([q for q in quoted if len(q) > 20])
        
        return quotes[:10]  # Top 10 quotes
    
    def _analyze_emotional_arc(self, text: str) -> List[Dict[str, float]]:
        """Analyze how emotions progress through the entry."""
        arc = []
        
        # Split text into chunks
        chunks = [text[i:i+200] for i in range(0, len(text), 150)]  # Overlapping chunks
        
        for chunk in chunks:
            if sia:
                scores = sia.polarity_scores(chunk)
                arc.append({
                    "positive": scores['pos'],
                    "negative": scores['neg'],
                    "neutral": scores['neu'],
                    "compound": scores['compound']
                })
            else:
                # Fallback to simple keyword analysis
                pos_words = len(re.findall(r'\b(happy|joy|grateful|love|peace)\b', chunk.lower()))
                neg_words = len(re.findall(r'\b(sad|angry|frustrated|worried|fear)\b', chunk.lower()))
                total = pos_words + neg_words + 1
                
                arc.append({
                    "positive": pos_words / total,
                    "negative": neg_words / total,
                    "neutral": 1 - (pos_words + neg_words) / total,
                    "compound": (pos_words - neg_words) / total
                })
        
        return arc
    
    def _determine_primary_emotion(self, emotional_arc: List[Dict[str, float]]) -> str:
        """Determine primary emotion from emotional arc."""
        if not emotional_arc:
            return "contemplative"
        
        # Average the emotional scores
        avg_positive = sum(e['positive'] for e in emotional_arc) / len(emotional_arc)
        avg_negative = sum(e['negative'] for e in emotional_arc) / len(emotional_arc)
        avg_compound = sum(e['compound'] for e in emotional_arc) / len(emotional_arc)
        
        # Determine primary emotion based on patterns
        if avg_compound > 0.5:
            return "joyful"
        elif avg_compound > 0.2:
            return "content"
        elif avg_compound < -0.5:
            return "struggling"
        elif avg_compound < -0.2:
            return "melancholic"
        elif avg_positive > avg_negative:
            return "hopeful"
        else:
            return "contemplative"
    
    async def _extract_spiritual_insights(
        self,
        text: str,
        personal_context: Dict[str, Any]
    ) -> List[str]:
        """Extract spiritual insights using AI."""
        try:
            from anthropic import Anthropic
            
            api_key = get_anthropic_api_key()
            anthropic = Anthropic(api_key=api_key)
            
            prompt = f"""Extract spiritual insights and wisdom from this diary entry.

Personal Context: {json.dumps(personal_context, indent=2)}

Diary Entry: "{text}"

Look for:
1. Moments of realization or awakening
2. Spiritual observations or connections
3. Life wisdom or universal truths recognized
4. Growth insights or transformation moments
5. Connection to something greater than self

Return as JSON array of insight strings."""

            response = anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            insights = json.loads(content)
            return insights[:5]  # Top 5 insights
            
        except Exception as e:
            logger.error(f"Failed to extract spiritual insights: {e}")
            return []
    
    def _extract_questions(self, text: str) -> List[str]:
        """Extract questions posed in the diary entry."""
        # Find question patterns
        questions = re.findall(r'([^.!?]*\?)', text)
        
        # Also find rhetorical questions without question marks
        rhetorical = re.findall(
            r'((?:I wonder|what if|how can|why do|where does|when will)[^.!?]+)',
            text, re.IGNORECASE
        )
        
        all_questions = questions + rhetorical
        return [q.strip() for q in all_questions if len(q.strip()) > 10][:5]
    
    def _extract_gratitude(self, text: str) -> List[str]:
        """Extract expressions of gratitude."""
        gratitude_patterns = [
            r'(?:grateful|thankful|appreciate|blessed)\s+(?:for|that|to have)([^.!?]+)',
            r'(?:thank you for)([^.!?]+)',
            r'(?:I love|I\'m loving)([^.!?]+)'
        ]
        
        expressions = []
        for pattern in gratitude_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            expressions.extend([m.strip() for m in matches])
        
        return expressions[:5]
    
    def _extract_people(self, text: str) -> List[Dict[str, str]]:
        """Extract mentioned people with relationships."""
        people = []
        
        # Common relationship patterns
        patterns = [
            (r'my (\w+)', 'family'),  # my mom, my brother
            (r'(?:friend|colleague|coworker) (\w+)', 'friend/colleague'),
            (r'(\w+), (?:my|a) (\w+)', 'specified'),  # Sarah, my friend
        ]
        
        for pattern, rel_type in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0]
                    relationship = match[1] if rel_type == 'specified' else rel_type
                else:
                    name = match
                    relationship = rel_type
                
                if name.lower() not in ['i', 'me', 'myself', 'we', 'us']:
                    people.append({"name": name.capitalize(), "relationship": relationship})
        
        # Also look for capitalized names
        proper_names = re.findall(r'\b([A-Z][a-z]+)\b', text)
        for name in proper_names:
            if name not in [p['name'] for p in people] and name not in ['I', 'The', 'This', 'That']:
                people.append({"name": name, "relationship": "unspecified"})
        
        return people[:10]
    
    def _extract_places(self, text: str) -> List[str]:
        """Extract mentioned places."""
        places = []
        
        # Location indicators
        place_patterns = [
            r'(?:at|in|to|from) (?:the )?([A-Z][a-z]+ ?[A-Z]?[a-z]*)',
            r'(?:went to|visited|arrived at) ([^.!?,]+)',
            r'([A-Z][a-z]+(?:\'s)? (?:house|home|place|office|apartment))'
        ]
        
        for pattern in place_patterns:
            matches = re.findall(pattern, text)
            places.extend([m.strip() for m in matches if len(m.strip()) > 3])
        
        return list(set(places))[:5]
    
    def _identify_spiritual_themes(self, text: str) -> List[str]:
        """Identify spiritual themes in the entry."""
        themes = []
        
        theme_keywords = {
            "awakening": ["realize", "awaken", "discover", "understand deeply"],
            "gratitude": ["grateful", "thankful", "appreciate", "blessed"],
            "presence": ["present moment", "here and now", "mindful", "aware"],
            "connection": ["connected", "oneness", "unity", "belonging"],
            "surrender": ["let go", "release", "accept", "flow with"],
            "growth": ["growing", "evolving", "transforming", "becoming"],
            "love": ["love", "compassion", "kindness", "heart"],
            "purpose": ["purpose", "meaning", "calling", "mission"],
            "healing": ["healing", "recovery", "integration", "wholeness"],
            "shadow": ["shadow", "darkness", "difficulty", "challenge"]
        }
        
        text_lower = text.lower()
        for theme, keywords in theme_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                themes.append(theme)
        
        return themes
    
    def _identify_life_areas(self, text: str) -> List[str]:
        """Identify life areas mentioned."""
        areas = []
        
        area_keywords = {
            "family": ["family", "mother", "father", "sister", "brother", "daughter", "son"],
            "relationship": ["partner", "relationship", "marriage", "dating", "love life"],
            "career": ["work", "job", "career", "professional", "business"],
            "health": ["health", "body", "physical", "energy", "sleep"],
            "spirituality": ["spiritual", "soul", "divine", "meditation", "prayer"],
            "creativity": ["creative", "art", "music", "writing", "expression"],
            "finances": ["money", "financial", "income", "expenses", "budget"],
            "home": ["home", "house", "living space", "apartment"],
            "friendships": ["friend", "friendship", "social", "community"]
        }
        
        text_lower = text.lower()
        for area, keywords in area_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                areas.append(area)
        
        return areas
    
    def _identify_growth_indicators(self, text: str) -> List[str]:
        """Identify indicators of personal growth."""
        indicators = []
        
        growth_patterns = [
            r'(?:I\'ve learned|I realize now|I understand that)([^.!?]+)',
            r'(?:I\'m becoming|I\'m growing|I\'m changing)([^.!?]+)',
            r'(?:I used to.*but now)([^.!?]+)',
            r'(?:I\'m more|I\'m less)([^.!?]+)(?:than before)'
        ]
        
        for pattern in growth_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            indicators.extend([m.strip() for m in matches])
        
        return indicators[:5]
    
    def _identify_shadow_work(self, text: str) -> List[str]:
        """Identify shadow work or challenges being faced."""
        shadows = []
        
        shadow_patterns = [
            r'(?:struggling with|dealing with|facing)([^.!?]+)',
            r'(?:my fear of|afraid of|scared of)([^.!?]+)',
            r'(?:hard to|difficult to|challenging to)([^.!?]+)',
            r'(?:my shadow|my darkness|the part of me that)([^.!?]+)'
        ]
        
        for pattern in shadow_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            shadows.extend([m.strip() for m in matches])
        
        return shadows[:5]
    
    def _identify_life_phase_markers(self, text: str, context: Dict[str, Any]) -> List[str]:
        """Identify markers of life phase or transitions."""
        markers = []
        
        # Transition words
        if any(word in text.lower() for word in [
            "transition", "change", "new chapter", "ending", "beginning",
            "crossroads", "turning point", "threshold"
        ]):
            markers.append("life_transition")
        
        # Phase indicators based on context
        current_phase = context.get("current_phase", "unknown")
        if "divorce" in text.lower() and "rebuilding" in current_phase.lower():
            markers.append("post_divorce_rebuilding")
        
        if "growth" in text.lower() and "discovery" in text.lower():
            markers.append("self_discovery_phase")
        
        return markers
    
    def _calculate_personal_significance(self, entry: DiaryEntry) -> int:
        """Calculate personal significance score."""
        score = 5  # Base score
        
        # Increase for emotional intensity
        score += min(3, int(entry.emotional_intensity * 3))
        
        # Increase for questions (self-reflection)
        if entry.life_questions:
            score += 1
        
        # Increase for growth indicators
        if entry.growth_indicators:
            score += 1
        
        # Increase for shadow work (facing difficulties)
        if entry.shadow_work:
            score += 1
        
        return min(10, score)
    
    def _calculate_spiritual_significance(self, entry: DiaryEntry) -> int:
        """Calculate spiritual significance score."""
        score = 5  # Base score
        
        # Increase for spiritual insights
        score += min(3, len(entry.spiritual_insights))
        
        # Increase for spiritual themes
        score += min(2, len(entry.spiritual_themes))
        
        # Increase for gratitude
        if entry.gratitude_expressions:
            score += 1
        
        return min(10, score)
    
    def _calculate_transformational_potential(self, entry: DiaryEntry) -> int:
        """Calculate transformational potential score."""
        score = 5  # Base score
        
        # High emotion + growth indicators = transformation
        if entry.emotional_intensity > 0.7 and entry.growth_indicators:
            score += 2
        
        # Shadow work is transformational
        if entry.shadow_work:
            score += 2
        
        # Life phase markers indicate transformation
        if entry.life_phase_markers:
            score += 1
        
        return min(10, score)
    
    async def _find_related_entries(self, entry: DiaryEntry) -> List[str]:
        """Find related diary entries based on themes and content."""
        # This would query the diary table for similar entries
        # For now, return empty list
        return []
    
    def _update_life_patterns(self, entry: DiaryEntry):
        """Update life patterns based on new entry."""
        # Check for recurring themes
        for theme in entry.spiritual_themes:
            pattern_id = f"theme_{theme}"
            
            if pattern_id not in self.life_patterns:
                self.life_patterns[pattern_id] = LifePattern(
                    pattern_id=pattern_id,
                    pattern_type="spiritual",
                    description=f"Recurring theme of {theme}",
                    first_observed=entry.timestamp
                )
            
            pattern = self.life_patterns[pattern_id]
            pattern.frequency += 1
            pattern.last_observed = entry.timestamp
            pattern.diary_entry_ids.append(entry.id)
            pattern.associated_emotions.append(entry.primary_emotion)


class SpiritualAdvisorAgentV2(BaseAgent):
    """Enhanced Spiritual Advisor with diary and learning capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diary_table = dynamodb.Table(DIARY_TABLE)
        self.patterns_table = dynamodb.Table(LIFE_PATTERNS_TABLE)
        self.diary_processor = DiaryProcessor()
    
    def load_personal_context(self) -> Dict[str, Any]:
        """Load personal context from Secrets Manager."""
        try:
            response = secrets_client.get_secret_value(SecretId=PERSONAL_CONTEXT_SECRET)
            context_data = json.loads(response['SecretString'])
            return context_data
        except Exception as e:
            logger.warning(f"Failed to load personal context: {e}")
            return {
                "life_challenges": {"health": "Managing narcolepsy"},
                "growth_themes": ["resilience", "self-discovery"],
                "current_phase": "Growth and integration"
            }
    
    async def process_as_diary(self, transcript: str) -> DiaryEntry:
        """Process transcript as diary entry with rich extraction."""
        personal_context = self.load_personal_context()
        
        # Process through diary processor
        entry = await self.diary_processor.process_diary_entry(transcript, personal_context)
        
        # Store in DynamoDB
        self.store_diary_entry(entry)
        
        # Update life patterns
        self.update_life_patterns(self.diary_processor.life_patterns)
        
        return entry
    
    def store_diary_entry(self, entry: DiaryEntry) -> None:
        """Store diary entry in DynamoDB."""
        try:
            # Convert entry to dict
            entry_dict = asdict(entry)
            entry_dict['timestamp'] = entry.timestamp.isoformat()
            
            # Store in diary table
            self.diary_table.put_item(Item=entry_dict)
            
            logger.info(f"Stored diary entry: {entry.id} (significance: P{entry.personal_significance}/S{entry.spiritual_significance})")
            
        except Exception as e:
            logger.error(f"Failed to store diary entry: {e}")
    
    def update_life_patterns(self, patterns: Dict[str, LifePattern]) -> None:
        """Update life patterns in DynamoDB."""
        try:
            for pattern_id, pattern in patterns.items():
                pattern_dict = asdict(pattern)
                if pattern.first_observed:
                    pattern_dict['first_observed'] = pattern.first_observed.isoformat()
                if pattern.last_observed:
                    pattern_dict['last_observed'] = pattern.last_observed.isoformat()
                
                self.patterns_table.put_item(Item=pattern_dict)
                
        except Exception as e:
            logger.error(f"Failed to update life patterns: {e}")
    
    def organize_diary_in_s3(self, entry: DiaryEntry, s3_bucket: str) -> Dict[str, Any]:
        """Organize diary entry in S3 with multiple access patterns."""
        stored_paths = []
        
        # 1. Daily diary entries
        daily_key = f"diary/daily/{entry.timestamp.strftime('%Y/%m/%d')}/{entry.id}.json"
        entry_dict = asdict(entry)
        entry_dict['timestamp'] = entry.timestamp.isoformat()
        
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=daily_key,
            Body=json.dumps(entry_dict, indent=2).encode('utf-8'),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        stored_paths.append(daily_key)
        
        # 2. By significance (high significance gets special treatment)
        if entry.personal_significance >= 8 or entry.spiritual_significance >= 8:
            sig_key = f"diary/significant/{entry.timestamp.year}/sig{max(entry.personal_significance, entry.spiritual_significance)}-{entry.id}.json"
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=sig_key,
                Body=json.dumps(entry_dict, indent=2).encode('utf-8'),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            stored_paths.append(sig_key)
        
        # 3. By primary theme
        if entry.spiritual_themes:
            theme = entry.spiritual_themes[0].replace(' ', '_')
            theme_key = f"diary/themes/{theme}/{entry.timestamp.strftime('%Y-%m')}.jsonl"
            
            # Append to theme file
            try:
                obj = s3_client.get_object(Bucket=s3_bucket, Key=theme_key)
                existing = obj['Body'].read().decode('utf-8')
            except s3_client.exceptions.NoSuchKey:
                existing = ""
            
            updated = existing + json.dumps(entry_dict) + "\n"
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=theme_key,
                Body=updated.encode('utf-8'),
                ContentType='application/x-ndjson'
            )
            stored_paths.append(theme_key)
        
        # 4. Extracted quotes collection
        if entry.extracted_quotes:
            quotes_key = f"diary/quotes/{entry.timestamp.strftime('%Y-%m')}.jsonl"
            
            try:
                obj = s3_client.get_object(Bucket=s3_bucket, Key=quotes_key)
                existing = obj['Body'].read().decode('utf-8')
            except s3_client.exceptions.NoSuchKey:
                existing = ""
            
            for quote in entry.extracted_quotes:
                quote_entry = {
                    "quote": quote,
                    "entry_id": entry.id,
                    "date": entry.timestamp.isoformat(),
                    "context": entry.primary_emotion
                }
                existing += json.dumps(quote_entry) + "\n"
            
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=quotes_key,
                Body=existing.encode('utf-8'),
                ContentType='application/x-ndjson'
            )
            stored_paths.append(quotes_key)
        
        return {
            "diary_id": entry.id,
            "stored_paths": stored_paths,
            "primary_storage": daily_key
        }
    
    def generate_diary_insights(self, time_period: str = "week") -> Dict[str, Any]:
        """Generate insights from diary entries over time period."""
        # Query diary entries for time period
        # This would involve scanning the diary table
        # For now, return placeholder
        
        return {
            "period": time_period,
            "insights": [
                "Your spiritual themes this week centered on gratitude and presence.",
                "Emotional arc shows increasing peace and acceptance.",
                "Shadow work focused on perfectionism and control.",
                "Key relationships mentioned: family (5x), close friends (3x).",
                "Growth edge: Learning to surrender to life's flow."
            ],
            "recommendations": [
                "Continue morning gratitude practice - it's shifting your perspective.",
                "The shadow work on perfectionism is yielding breakthroughs.",
                "Consider exploring the question you asked about purpose more deeply."
            ]
        }
    
    @requires_aws
    def process_transcript(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcript as both diary and memory."""
        transcript = event['transcript']
        s3_bucket = event['bucket']
        s3_key = event['key']
        
        logger.info(f"Processing spiritual memory/diary from {s3_key}")
        
        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Process as diary entry
            diary_entry = loop.run_until_complete(
                self.process_as_diary(transcript)
            )
            
            # Also process as memory (reuse v1 logic)
            from .spiritual_advisor_agent import analyze_memory_with_spiritual_lens
            personal_context = self.load_personal_context()
            memory_analysis = loop.run_until_complete(
                analyze_memory_with_spiritual_lens(transcript, personal_context)
            )
            
            # Organize in S3
            diary_result = self.organize_diary_in_s3(diary_entry, s3_bucket)
            
            # Create comprehensive output
            output = {
                "status": "success",
                "diary_entry": {
                    "id": diary_entry.id,
                    "timestamp": diary_entry.timestamp.isoformat(),
                    "primary_emotion": diary_entry.primary_emotion,
                    "significance_scores": {
                        "personal": diary_entry.personal_significance,
                        "spiritual": diary_entry.spiritual_significance,
                        "transformational": diary_entry.transformational_potential
                    },
                    "extracted_wisdom": {
                        "quotes": diary_entry.extracted_quotes[:3],
                        "insights": diary_entry.spiritual_insights[:3],
                        "questions": diary_entry.life_questions[:3],
                        "gratitude": diary_entry.gratitude_expressions[:3]
                    },
                    "themes": diary_entry.spiritual_themes,
                    "growth_edges": diary_entry.growth_indicators,
                    "shadow_work": diary_entry.shadow_work
                },
                "memory_analysis": memory_analysis,
                "storage": diary_result,
                "knowledge_evolution": self.diary_processor.knowledge_base.life_themes,
                "persona_voice": {
                    "applied": False,  # Hook for future enhancement
                    "style": "compassionate_wisdom"
                }
            }
            
            # Store comprehensive output
            output_key = s3_key.replace('transcripts/', 'outputs/spiritual_advisor_v2/').replace('.txt', '_diary.json')
            self.store_result(output, output_key)
            
            # Log high-significance entries
            if diary_entry.personal_significance >= 8 or diary_entry.spiritual_significance >= 8:
                logger.info(
                    f"HIGH SIGNIFICANCE DIARY ENTRY: "
                    f"P{diary_entry.personal_significance}/S{diary_entry.spiritual_significance} - "
                    f"{diary_entry.spiritual_insights[0] if diary_entry.spiritual_insights else 'Deep moment recorded'}"
                )
            
            return {
                "status": "success",
                "output_key": output_key,
                "diary_id": diary_entry.id,
                "significance": max(diary_entry.personal_significance, diary_entry.spiritual_significance)
            }
            
        finally:
            loop.close()


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager."""
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve Anthropic API key: {e}")
        raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SpiritualAdvisorV2."""
    agent = SpiritualAdvisorAgentV2()
    
    try:
        # Process each record
        results = []
        for record in event['Records']:
            message = json.loads(record['body'])
            result = agent.process_transcript(message)
            results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Spiritual memories processed with diary extraction',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }