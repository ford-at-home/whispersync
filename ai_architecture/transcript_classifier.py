"""Advanced Transcript Classification System using Claude 3.5 Sonnet.

This module implements a sophisticated multi-dimensional classification system
that goes beyond simple agent routing to understand deep context, intent,
and emotional nuance in voice transcripts.

CLASSIFICATION DIMENSIONS:
1. Primary Intent: What the user is trying to accomplish
2. Content Type: Work, personal, technical, creative, etc.
3. Emotional State: User's emotional context and urgency
4. Complexity Level: Simple note vs. complex multi-faceted thought
5. Temporal Context: Past reflection, present action, future planning
6. Relational Context: Who/what is involved in the content
7. Action Requirements: What needs to be done with this information

WHY THIS APPROACH:
- Traditional folder routing misses nuanced, mixed-content thoughts
- Understanding intent enables proactive assistance
- Emotional awareness improves response appropriateness
- Complexity assessment guides processing strategy
- Temporal awareness enables better memory connections
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import datetime

logger = logging.getLogger(__name__)


class Intent(Enum):
    """Primary user intent categories."""
    
    DOCUMENTATION = "documentation"      # Recording for future reference
    REFLECTION = "reflection"            # Processing thoughts/emotions
    IDEATION = "ideation"               # Generating new ideas
    PLANNING = "planning"               # Organizing future actions
    PROBLEM_SOLVING = "problem_solving" # Working through challenges
    SOCIAL = "social"                   # Communication/relationship content
    LEARNING = "learning"               # Educational/skill development
    CREATIVE = "creative"               # Artistic/creative expression


class EmotionalTone(Enum):
    """Emotional context of the transcript."""
    
    EXCITED = "excited"         # High positive energy
    CONTENT = "content"         # Calm positive
    NEUTRAL = "neutral"         # Balanced/factual
    FRUSTRATED = "frustrated"   # Negative but energetic
    ANXIOUS = "anxious"        # Worried/uncertain
    REFLECTIVE = "reflective"  # Thoughtful/contemplative
    CELEBRATORY = "celebratory" # Achievement/success
    MELANCHOLIC = "melancholic" # Sad/nostalgic


class ComplexityLevel(Enum):
    """Complexity assessment of the content."""
    
    SIMPLE = "simple"           # Single clear thought
    MODERATE = "moderate"       # Multiple related points
    COMPLEX = "complex"         # Multiple domains/deep analysis
    HIGHLY_COMPLEX = "highly_complex" # Requires extensive processing


class TemporalFocus(Enum):
    """Time orientation of the content."""
    
    PAST = "past"              # Memories, reflections
    PRESENT = "present"        # Current state, immediate actions
    FUTURE = "future"          # Plans, goals, aspirations
    TIMELESS = "timeless"      # Abstract concepts, principles


@dataclass
class ClassificationResult:
    """Comprehensive classification of a voice transcript."""
    
    # Core classifications
    primary_intent: Intent
    content_types: List[str]  # Can span multiple types
    emotional_tone: EmotionalTone
    complexity: ComplexityLevel
    temporal_focus: TemporalFocus
    
    # Detailed analysis
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    key_entities: List[Dict[str, str]] = field(default_factory=list)  # People, places, projects
    themes: List[str] = field(default_factory=list)
    suggested_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Routing recommendations
    primary_agent: str = ""
    secondary_agents: List[str] = field(default_factory=list)
    processing_strategy: str = "standard"  # standard, parallel, sequential, conditional
    
    # Context for Theory of Mind
    user_state_indicators: Dict[str, Any] = field(default_factory=dict)
    historical_pattern_match: Optional[str] = None
    anomaly_flags: List[str] = field(default_factory=list)


class TranscriptClassifier:
    """Advanced transcript classifier using Claude 3.5 Sonnet."""
    
    def __init__(self, bedrock_client=None):
        """Initialize the classifier with AI capabilities."""
        self.bedrock = bedrock_client
        self.classification_history = []  # For pattern learning
        
    def classify(self, transcript: str, user_context: Optional[Dict] = None) -> ClassificationResult:
        """Perform comprehensive classification of a transcript.
        
        Args:
            transcript: The voice transcript to classify
            user_context: Optional user history and preferences
            
        Returns:
            Detailed classification result with routing recommendations
        """
        if not self.bedrock:
            return self._fallback_classification(transcript)
            
        # Build context-aware prompt
        analysis_prompt = self._build_classification_prompt(transcript, user_context)
        
        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2500,
                    "temperature": 0.3,  # Lower temperature for consistent classification
                    "messages": [{
                        "role": "user",
                        "content": analysis_prompt
                    }]
                })
            )
            
            result = json.loads(response["body"].read())
            classification_data = json.loads(result.get("content", [{}])[0].get("text", "{}"))
            
            # Parse and validate classification
            classification = self._parse_classification(classification_data, transcript)
            
            # Store for pattern learning
            self.classification_history.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "classification": classification,
                "transcript_preview": transcript[:100]
            })
            
            return classification
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self._fallback_classification(transcript)
    
    def _build_classification_prompt(self, transcript: str, user_context: Optional[Dict]) -> str:
        """Build sophisticated classification prompt."""
        
        context_section = ""
        if user_context:
            context_section = f"""
User Context:
- Recent activity: {user_context.get('recent_activity', 'Unknown')}
- Common themes: {', '.join(user_context.get('common_themes', []))}
- Typical patterns: {user_context.get('patterns', 'No patterns identified')}
"""
        
        return f"""Perform a comprehensive multi-dimensional analysis of this voice transcript:

{context_section}

Transcript: "{transcript}"

Analyze across these dimensions:

1. PRIMARY INTENT - What is the user fundamentally trying to achieve?
   Options: documentation, reflection, ideation, planning, problem_solving, social, learning, creative

2. CONTENT TYPES - What types of content are present? (can be multiple)
   Examples: work_task, personal_memory, technical_idea, emotional_processing, 
   relationship_matter, creative_expression, learning_note, goal_setting

3. EMOTIONAL TONE - What is the emotional context?
   Options: excited, content, neutral, frustrated, anxious, reflective, celebratory, melancholic

4. COMPLEXITY LEVEL - How complex is the processing required?
   Options: simple (single thought), moderate (related points), complex (multiple domains), 
   highly_complex (deep interconnections)

5. TEMPORAL FOCUS - What time period is the focus?
   Options: past (memories/reflection), present (current state), future (plans/goals), 
   timeless (abstract concepts)

6. KEY ENTITIES - Extract important people, places, projects, or concepts
   Format: [{{type: "person/place/project/concept", name: "...", significance: "..."}}, ...]

7. THEMES - Identify 3-5 core themes or topics

8. SUGGESTED ACTIONS - What should the system do with this information?
   Format: [{{action: "...", reason: "...", priority: "high/medium/low"}}, ...]

9. ROUTING RECOMMENDATION
   - primary_agent: work/memory/github/multiple
   - secondary_agents: [] (if applicable)
   - processing_strategy: standard/parallel/sequential/conditional

10. USER STATE INDICATORS - What does this reveal about the user's current state?
    Include: stress_level, energy_level, focus_area, emotional_needs

11. ANOMALY FLAGS - Any unusual patterns compared to typical behavior?

Provide confidence scores (0.0-1.0) for each major classification.

Respond in JSON format with all fields populated."""
        
    def _parse_classification(self, data: Dict, transcript: str) -> ClassificationResult:
        """Parse AI response into structured classification."""
        
        # Parse enums with fallback
        try:
            primary_intent = Intent(data.get("primary_intent", "documentation"))
        except ValueError:
            primary_intent = Intent.DOCUMENTATION
            
        try:
            emotional_tone = EmotionalTone(data.get("emotional_tone", "neutral"))
        except ValueError:
            emotional_tone = EmotionalTone.NEUTRAL
            
        try:
            complexity = ComplexityLevel(data.get("complexity", "moderate"))
        except ValueError:
            complexity = ComplexityLevel.MODERATE
            
        try:
            temporal_focus = TemporalFocus(data.get("temporal_focus", "present"))
        except ValueError:
            temporal_focus = TemporalFocus.PRESENT
        
        return ClassificationResult(
            primary_intent=primary_intent,
            content_types=data.get("content_types", ["general"]),
            emotional_tone=emotional_tone,
            complexity=complexity,
            temporal_focus=temporal_focus,
            confidence_scores=data.get("confidence_scores", {}),
            key_entities=data.get("key_entities", []),
            themes=data.get("themes", []),
            suggested_actions=data.get("suggested_actions", []),
            primary_agent=data.get("routing_recommendation", {}).get("primary_agent", "work"),
            secondary_agents=data.get("routing_recommendation", {}).get("secondary_agents", []),
            processing_strategy=data.get("routing_recommendation", {}).get("processing_strategy", "standard"),
            user_state_indicators=data.get("user_state_indicators", {}),
            anomaly_flags=data.get("anomaly_flags", [])
        )
    
    def _fallback_classification(self, transcript: str) -> ClassificationResult:
        """Basic classification when AI is unavailable."""
        
        # Simple keyword-based classification
        transcript_lower = transcript.lower()
        
        # Determine primary intent
        if any(word in transcript_lower for word in ["remember", "memory", "reminds me"]):
            primary_intent = Intent.REFLECTION
        elif any(word in transcript_lower for word in ["idea", "what if", "create", "build"]):
            primary_intent = Intent.IDEATION
        elif any(word in transcript_lower for word in ["plan", "tomorrow", "next week", "will"]):
            primary_intent = Intent.PLANNING
        else:
            primary_intent = Intent.DOCUMENTATION
            
        # Determine emotional tone
        if any(word in transcript_lower for word in ["excited", "amazing", "love"]):
            emotional_tone = EmotionalTone.EXCITED
        elif any(word in transcript_lower for word in ["frustrated", "annoying", "problem"]):
            emotional_tone = EmotionalTone.FRUSTRATED
        else:
            emotional_tone = EmotionalTone.NEUTRAL
            
        # Determine agent routing
        if "work" in transcript_lower or "meeting" in transcript_lower:
            primary_agent = "work"
        elif "memory" in transcript_lower or "remember" in transcript_lower:
            primary_agent = "memory"
        elif "github" in transcript_lower or "repository" in transcript_lower:
            primary_agent = "github"
        else:
            primary_agent = "work"  # Default
            
        return ClassificationResult(
            primary_intent=primary_intent,
            content_types=["general"],
            emotional_tone=emotional_tone,
            complexity=ComplexityLevel.SIMPLE,
            temporal_focus=TemporalFocus.PRESENT,
            primary_agent=primary_agent,
            confidence_scores={"overall": 0.4}  # Low confidence for fallback
        )
    
    def analyze_patterns(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Analyze classification patterns over time."""
        
        if not self.classification_history:
            return {"message": "No classification history available"}
            
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=time_window_hours)
        recent_classifications = [
            c for c in self.classification_history 
            if datetime.datetime.fromisoformat(c["timestamp"]) > cutoff
        ]
        
        if not recent_classifications:
            return {"message": f"No classifications in the last {time_window_hours} hours"}
        
        # Analyze patterns
        intent_counts = {}
        emotional_patterns = {}
        complexity_trend = []
        
        for entry in recent_classifications:
            classification = entry["classification"]
            
            # Count intents
            intent = classification.primary_intent.value
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            # Track emotional patterns
            emotion = classification.emotional_tone.value
            emotional_patterns[emotion] = emotional_patterns.get(emotion, 0) + 1
            
            # Track complexity
            complexity_trend.append(classification.complexity.value)
        
        return {
            "time_window_hours": time_window_hours,
            "total_classifications": len(recent_classifications),
            "intent_distribution": intent_counts,
            "emotional_patterns": emotional_patterns,
            "complexity_trend": complexity_trend,
            "insights": self._generate_pattern_insights(
                intent_counts, emotional_patterns, complexity_trend
            )
        }
    
    def _generate_pattern_insights(self, intents: Dict, emotions: Dict, complexity: List) -> List[str]:
        """Generate insights from classification patterns."""
        
        insights = []
        
        # Intent insights
        if intents:
            dominant_intent = max(intents.items(), key=lambda x: x[1])
            insights.append(f"Primary focus: {dominant_intent[0]} ({dominant_intent[1]} occurrences)")
        
        # Emotional insights
        if emotions:
            dominant_emotion = max(emotions.items(), key=lambda x: x[1])
            if dominant_emotion[0] in ["frustrated", "anxious"]:
                insights.append(f"Elevated stress indicators: {dominant_emotion[0]} is predominant")
            elif dominant_emotion[0] in ["excited", "celebratory"]:
                insights.append(f"Positive momentum: {dominant_emotion[0]} emotional state")
        
        # Complexity insights
        if complexity:
            if complexity.count("complex") + complexity.count("highly_complex") > len(complexity) / 2:
                insights.append("Processing complex thoughts - may benefit from structured support")
        
        return insights