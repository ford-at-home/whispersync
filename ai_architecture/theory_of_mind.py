"""Theory of Mind Implementation for WhisperSync.

This module implements a sophisticated Theory of Mind (ToM) system that learns
and predicts user behavior patterns, emotional states, and cognitive patterns
over time. It builds a dynamic user model that improves system responses.

THEORY OF MIND COMPONENTS:
1. Behavioral Modeling: Learn user's typical patterns and routines
2. Emotional Modeling: Track emotional patterns and triggers
3. Cognitive Modeling: Understand thinking patterns and preferences
4. Social Modeling: Map relationships and social contexts
5. Temporal Modeling: Understand time-based patterns
6. Anomaly Detection: Identify unusual patterns requiring attention

WHY THEORY OF MIND:
- Enables personalized, context-aware responses
- Predicts user needs before they're expressed
- Identifies concerning patterns (stress, isolation)
- Improves routing accuracy through behavioral understanding
- Provides empathetic, appropriate responses
"""

from __future__ import annotations

import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class UserState:
    """Current state representation of the user."""
    
    # Immediate state
    current_mood: str = "neutral"
    energy_level: float = 0.5  # 0-1 scale
    stress_level: float = 0.3  # 0-1 scale
    focus_area: str = "general"
    
    # Recent patterns (last 7 days)
    dominant_themes: List[str] = field(default_factory=list)
    interaction_frequency: float = 0.0  # interactions per day
    emotional_volatility: float = 0.0  # 0-1 scale
    
    # Long-term traits
    personality_indicators: Dict[str, float] = field(default_factory=dict)
    communication_style: str = "balanced"
    typical_routines: Dict[str, List[str]] = field(default_factory=dict)  # time -> activities
    
    # Social context
    key_relationships: List[Dict[str, str]] = field(default_factory=list)
    social_interaction_level: float = 0.5  # 0-1 scale
    
    # Predictions
    likely_next_action: Optional[str] = None
    predicted_mood_trajectory: str = "stable"  # improving, stable, declining
    attention_needed_score: float = 0.0  # 0-1 scale


@dataclass
class BehavioralPattern:
    """Represents a learned behavioral pattern."""
    
    pattern_id: str
    pattern_type: str  # temporal, emotional, topical, social
    description: str
    
    # Pattern details
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    typical_sequence: List[str] = field(default_factory=list)
    frequency: float = 0.0  # occurrences per week
    confidence: float = 0.0  # 0-1 scale
    
    # Temporal aspects
    time_patterns: Dict[str, float] = field(default_factory=dict)  # hour -> probability
    day_patterns: Dict[str, float] = field(default_factory=dict)   # day -> probability
    
    # Associated states
    associated_moods: List[str] = field(default_factory=list)
    associated_topics: List[str] = field(default_factory=list)
    
    # Metadata
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    observation_count: int = 0


class TheoryOfMind:
    """Theory of Mind system for understanding and predicting user behavior."""
    
    def __init__(self, user_id: str, bedrock_client=None):
        """Initialize Theory of Mind for a specific user."""
        self.user_id = user_id
        self.bedrock = bedrock_client
        
        # Core models
        self.user_state = UserState()
        self.behavioral_patterns: Dict[str, BehavioralPattern] = {}
        self.interaction_history: deque = deque(maxlen=1000)  # Last 1000 interactions
        
        # Learning components
        self.pattern_detector = PatternDetector()
        self.emotion_tracker = EmotionTracker()
        self.relationship_mapper = RelationshipMapper()
        self.anomaly_detector = AnomalyDetector()
        
        # Memory systems
        self.short_term_memory: deque = deque(maxlen=50)  # Last 50 interactions
        self.working_memory: Dict[str, Any] = {}  # Current context
        self.episodic_memory: List[Dict] = []  # Significant events
        
    def process_interaction(self, transcript: str, classification: Any, 
                          timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Process a new interaction and update user model.
        
        Args:
            transcript: The voice transcript
            classification: Classification result from transcript classifier
            timestamp: When the interaction occurred
            
        Returns:
            Analysis results and predictions
        """
        timestamp = timestamp or datetime.utcnow()
        
        # Create interaction record
        interaction = {
            "timestamp": timestamp,
            "transcript": transcript,
            "classification": classification,
            "context": self._extract_context(transcript, classification)
        }
        
        # Update histories
        self.interaction_history.append(interaction)
        self.short_term_memory.append(interaction)
        
        # Update various models
        self._update_emotional_model(interaction)
        self._update_behavioral_model(interaction)
        self._update_social_model(interaction)
        self._detect_patterns(interaction)
        
        # Check for anomalies
        anomalies = self.anomaly_detector.check(interaction, self.user_state)
        
        # Generate predictions
        predictions = self._generate_predictions()
        
        # Update user state
        self._update_user_state(interaction, anomalies, predictions)
        
        # Determine if this is a significant event
        if self._is_significant_event(interaction, anomalies):
            self.episodic_memory.append({
                "interaction": interaction,
                "user_state": asdict(self.user_state),
                "anomalies": anomalies,
                "significance_reason": self._determine_significance_reason(interaction, anomalies)
            })
        
        return {
            "user_state": asdict(self.user_state),
            "anomalies": anomalies,
            "predictions": predictions,
            "recommendations": self._generate_recommendations(anomalies, predictions),
            "pattern_insights": self._get_pattern_insights()
        }
    
    def _extract_context(self, transcript: str, classification: Any) -> Dict[str, Any]:
        """Extract contextual information from the interaction."""
        
        context = {
            "length": len(transcript),
            "complexity": classification.complexity.value,
            "intent": classification.primary_intent.value,
            "emotions": classification.emotional_tone.value,
            "entities": classification.key_entities,
            "themes": classification.themes
        }
        
        # Add temporal context
        now = datetime.utcnow()
        context["hour"] = now.hour
        context["day_of_week"] = now.strftime("%A")
        context["time_of_day"] = self._categorize_time_of_day(now.hour)
        
        # Add behavioral context
        if self.short_term_memory:
            recent_interactions = list(self.short_term_memory)[-5:]
            context["recent_themes"] = self._extract_recent_themes(recent_interactions)
            context["mood_trajectory"] = self._calculate_mood_trajectory(recent_interactions)
        
        return context
    
    def _update_emotional_model(self, interaction: Dict) -> None:
        """Update the emotional model based on the interaction."""
        
        emotion = interaction["classification"].emotional_tone.value
        timestamp = interaction["timestamp"]
        
        # Update emotion tracker
        self.emotion_tracker.add_observation(emotion, timestamp)
        
        # Calculate emotional metrics
        recent_emotions = self.emotion_tracker.get_recent_emotions(hours=24)
        if recent_emotions:
            # Calculate emotional volatility
            emotion_changes = self._calculate_emotion_changes(recent_emotions)
            self.user_state.emotional_volatility = min(emotion_changes / 10.0, 1.0)
            
            # Update current mood
            self.user_state.current_mood = self.emotion_tracker.get_dominant_emotion()
            
            # Calculate stress level
            stress_indicators = ["frustrated", "anxious", "overwhelmed"]
            stress_count = sum(1 for e in recent_emotions if e in stress_indicators)
            self.user_state.stress_level = min(stress_count / len(recent_emotions), 1.0)
    
    def _update_behavioral_model(self, interaction: Dict) -> None:
        """Update behavioral patterns based on the interaction."""
        
        # Extract behavioral features
        features = {
            "time": interaction["timestamp"],
            "intent": interaction["classification"].primary_intent.value,
            "themes": interaction["classification"].themes,
            "complexity": interaction["classification"].complexity.value,
            "agent": interaction["classification"].primary_agent
        }
        
        # Update pattern detector
        self.pattern_detector.add_observation(features)
        
        # Check for new patterns
        new_patterns = self.pattern_detector.detect_patterns()
        for pattern in new_patterns:
            pattern_id = self._generate_pattern_id(pattern)
            if pattern_id not in self.behavioral_patterns:
                self.behavioral_patterns[pattern_id] = pattern
    
    def _update_social_model(self, interaction: Dict) -> None:
        """Update social relationship model."""
        
        entities = interaction["classification"].key_entities
        people = [e for e in entities if e.get("type") == "person"]
        
        if people:
            self.relationship_mapper.update(people, interaction["timestamp"])
            self.user_state.key_relationships = self.relationship_mapper.get_key_relationships()
            self.user_state.social_interaction_level = self.relationship_mapper.get_interaction_level()
    
    def _detect_patterns(self, interaction: Dict) -> None:
        """Detect and update behavioral patterns."""
        
        # Temporal patterns
        hour = interaction["timestamp"].hour
        day = interaction["timestamp"].strftime("%A")
        
        for pattern in self.behavioral_patterns.values():
            if pattern.pattern_type == "temporal":
                # Update time-based probabilities
                pattern.time_patterns[str(hour)] = pattern.time_patterns.get(str(hour), 0) + 0.1
                pattern.day_patterns[day] = pattern.day_patterns.get(day, 0) + 0.1
                
                # Normalize probabilities
                self._normalize_probabilities(pattern.time_patterns)
                self._normalize_probabilities(pattern.day_patterns)
    
    def _generate_predictions(self) -> Dict[str, Any]:
        """Generate predictions based on current state and patterns."""
        
        predictions = {
            "next_interaction_time": self._predict_next_interaction(),
            "likely_topics": self._predict_topics(),
            "emotional_forecast": self._predict_emotional_trajectory(),
            "needs_assessment": self._assess_user_needs()
        }
        
        # Use AI for complex predictions if available
        if self.bedrock and len(self.interaction_history) > 10:
            ai_predictions = self._generate_ai_predictions()
            predictions.update(ai_predictions)
        
        return predictions
    
    def _generate_ai_predictions(self) -> Dict[str, Any]:
        """Use Claude for sophisticated pattern analysis and predictions."""
        
        # Prepare interaction summary
        recent_interactions = list(self.interaction_history)[-20:]
        interaction_summary = self._summarize_interactions(recent_interactions)
        
        prompt = f"""Based on this user's recent interaction history, provide insights and predictions:

User State:
- Current mood: {self.user_state.current_mood}
- Stress level: {self.user_state.stress_level}
- Energy level: {self.user_state.energy_level}
- Dominant themes: {', '.join(self.user_state.dominant_themes[:5])}

Recent Interactions Summary:
{interaction_summary}

Behavioral Patterns Detected:
{self._summarize_patterns()}

Provide:
1. Likely next actions or topics (next 24 hours)
2. Emotional trajectory prediction (next 3 days)
3. Potential stress points or concerns
4. Recommended support strategies
5. Unusual patterns that need attention

Format as JSON with keys: next_actions, emotional_trajectory, concerns, support_strategies, attention_flags"""
        
        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1500,
                    "temperature": 0.4,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response["body"].read())
            return json.loads(result.get("content", [{}])[0].get("text", "{}"))
            
        except Exception as e:
            logger.error(f"AI prediction generation failed: {e}")
            return {}
    
    def _update_user_state(self, interaction: Dict, anomalies: List[str], 
                          predictions: Dict[str, Any]) -> None:
        """Update the user state based on all analyses."""
        
        # Update interaction frequency
        recent_count = sum(1 for i in self.interaction_history 
                          if i["timestamp"] > datetime.utcnow() - timedelta(days=7))
        self.user_state.interaction_frequency = recent_count / 7.0
        
        # Update dominant themes
        theme_counts = defaultdict(int)
        for i in list(self.interaction_history)[-50:]:
            for theme in i["classification"].themes:
                theme_counts[theme] += 1
        
        self.user_state.dominant_themes = [
            theme for theme, _ in sorted(theme_counts.items(), 
                                        key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Update focus area
        if self.user_state.dominant_themes:
            self.user_state.focus_area = self.user_state.dominant_themes[0]
        
        # Update attention needed score
        attention_factors = [
            self.user_state.stress_level > 0.7,
            self.user_state.emotional_volatility > 0.6,
            len(anomalies) > 0,
            predictions.get("emotional_forecast") == "declining"
        ]
        self.user_state.attention_needed_score = sum(attention_factors) / 4.0
    
    def _generate_recommendations(self, anomalies: List[str], 
                                predictions: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate actionable recommendations."""
        
        recommendations = []
        
        # Stress-based recommendations
        if self.user_state.stress_level > 0.7:
            recommendations.append({
                "type": "stress_management",
                "action": "Consider guided relaxation or break",
                "reason": "Elevated stress levels detected",
                "priority": "high"
            })
        
        # Social recommendations
        if self.user_state.social_interaction_level < 0.3:
            recommendations.append({
                "type": "social_connection",
                "action": "Reach out to friends or family",
                "reason": "Low social interaction detected",
                "priority": "medium"
            })
        
        # Pattern-based recommendations
        for pattern in self.behavioral_patterns.values():
            if pattern.confidence > 0.8 and "negative" in pattern.associated_moods:
                recommendations.append({
                    "type": "pattern_intervention",
                    "action": f"Address recurring pattern: {pattern.description}",
                    "reason": "Negative pattern detected with high confidence",
                    "priority": "high"
                })
        
        return recommendations
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get comprehensive user profile based on learned patterns."""
        
        return {
            "user_id": self.user_id,
            "current_state": asdict(self.user_state),
            "behavioral_patterns": [asdict(p) for p in self.behavioral_patterns.values()],
            "interaction_statistics": self._calculate_interaction_stats(),
            "personality_profile": self._generate_personality_profile(),
            "relationship_network": self.relationship_mapper.get_network_summary(),
            "temporal_patterns": self._analyze_temporal_patterns()
        }
    
    # Helper methods
    def _categorize_time_of_day(self, hour: int) -> str:
        if 5 <= hour < 9:
            return "early_morning"
        elif 9 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "midday"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 20:
            return "evening"
        elif 20 <= hour < 23:
            return "night"
        else:
            return "late_night"
    
    def _calculate_emotion_changes(self, emotions: List[str]) -> int:
        """Count the number of emotion changes in the list."""
        if len(emotions) < 2:
            return 0
        return sum(1 for i in range(1, len(emotions)) if emotions[i] != emotions[i-1])
    
    def _generate_pattern_id(self, pattern: Dict) -> str:
        """Generate unique ID for a pattern."""
        pattern_str = json.dumps(pattern, sort_keys=True)
        return hashlib.md5(pattern_str.encode()).hexdigest()[:12]
    
    def _normalize_probabilities(self, prob_dict: Dict[str, float]) -> None:
        """Normalize probabilities to sum to 1."""
        total = sum(prob_dict.values())
        if total > 0:
            for key in prob_dict:
                prob_dict[key] /= total


class PatternDetector:
    """Detects behavioral patterns from interaction sequences."""
    
    def __init__(self):
        self.observations = []
        self.pattern_cache = {}
    
    def add_observation(self, features: Dict) -> None:
        self.observations.append(features)
    
    def detect_patterns(self) -> List[BehavioralPattern]:
        # Simplified pattern detection
        # In production, use more sophisticated algorithms
        patterns = []
        
        # Detect temporal patterns
        if len(self.observations) > 20:
            temporal_pattern = self._detect_temporal_patterns()
            if temporal_pattern:
                patterns.append(temporal_pattern)
        
        return patterns
    
    def _detect_temporal_patterns(self) -> Optional[BehavioralPattern]:
        # Simplified implementation
        return None


class EmotionTracker:
    """Tracks and analyzes emotional patterns."""
    
    def __init__(self):
        self.emotion_history = []
    
    def add_observation(self, emotion: str, timestamp: datetime) -> None:
        self.emotion_history.append({"emotion": emotion, "timestamp": timestamp})
    
    def get_recent_emotions(self, hours: int = 24) -> List[str]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [e["emotion"] for e in self.emotion_history if e["timestamp"] > cutoff]
    
    def get_dominant_emotion(self) -> str:
        recent = self.get_recent_emotions(hours=6)
        if not recent:
            return "neutral"
        return max(set(recent), key=recent.count)


class RelationshipMapper:
    """Maps and analyzes social relationships."""
    
    def __init__(self):
        self.relationships = defaultdict(lambda: {"mentions": 0, "last_seen": None})
    
    def update(self, people: List[Dict], timestamp: datetime) -> None:
        for person in people:
            name = person.get("name", "")
            if name:
                self.relationships[name]["mentions"] += 1
                self.relationships[name]["last_seen"] = timestamp
    
    def get_key_relationships(self) -> List[Dict[str, str]]:
        sorted_relationships = sorted(
            self.relationships.items(), 
            key=lambda x: x[1]["mentions"], 
            reverse=True
        )
        return [
            {"name": name, "mentions": data["mentions"], "last_seen": data["last_seen"].isoformat() if data["last_seen"] else None}
            for name, data in sorted_relationships[:10]
        ]
    
    def get_interaction_level(self) -> float:
        if not self.relationships:
            return 0.0
        recent_mentions = sum(1 for r in self.relationships.values() 
                            if r["last_seen"] and r["last_seen"] > datetime.utcnow() - timedelta(days=7))
        return min(recent_mentions / 10.0, 1.0)
    
    def get_network_summary(self) -> Dict[str, Any]:
        return {
            "total_relationships": len(self.relationships),
            "active_relationships": sum(1 for r in self.relationships.values() 
                                      if r["last_seen"] and r["last_seen"] > datetime.utcnow() - timedelta(days=30)),
            "key_relationships": self.get_key_relationships()
        }


class AnomalyDetector:
    """Detects anomalous patterns in user behavior."""
    
    def __init__(self):
        self.baseline_patterns = {}
    
    def check(self, interaction: Dict, user_state: UserState) -> List[str]:
        anomalies = []
        
        # Check for unusual timing
        hour = interaction["timestamp"].hour
        if 2 <= hour <= 5:  # Very late night/early morning
            anomalies.append("unusual_timing_late_night")
        
        # Check for emotional anomalies
        if user_state.emotional_volatility > 0.8:
            anomalies.append("high_emotional_volatility")
        
        # Check for stress indicators
        if user_state.stress_level > 0.8:
            anomalies.append("high_stress_level")
        
        # Check for isolation
        if user_state.social_interaction_level < 0.2:
            anomalies.append("social_isolation_risk")
        
        return anomalies