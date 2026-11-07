"""Advanced Emotional Intelligence System for WhisperSync.

This module implements sophisticated sentiment analysis and emotional intelligence
capabilities that go beyond basic positive/negative classification to understand
nuanced emotional states, emotional trajectories, and appropriate responses.

EMOTIONAL INTELLIGENCE COMPONENTS:
1. Multi-dimensional Emotion Recognition (Plutchik's Wheel + Extended)
2. Emotional Trajectory Analysis (tracking changes over time)
3. Contextual Emotion Understanding (why someone feels this way)
4. Empathetic Response Generation
5. Emotional Regulation Suggestions
6. Mood Prediction and Intervention

WHY ADVANCED EMOTIONAL INTELLIGENCE:
- Voice conveys rich emotional information beyond words
- Emotional awareness enables supportive, appropriate responses
- Early detection of concerning emotional patterns
- Personalized emotional support and interventions
- Better understanding of user needs and states
"""

from __future__ import annotations

import json
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import deque
import re

logger = logging.getLogger(__name__)


@dataclass
class EmotionalState:
    """Comprehensive emotional state representation."""
    
    # Primary emotions (Plutchik's wheel)
    joy: float = 0.0          # 0-1 scale
    trust: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    sadness: float = 0.0
    disgust: float = 0.0
    anger: float = 0.0
    anticipation: float = 0.0
    
    # Secondary emotions (combinations)
    love: float = 0.0         # joy + trust
    submission: float = 0.0   # trust + fear
    awe: float = 0.0         # fear + surprise
    disapproval: float = 0.0  # surprise + sadness
    remorse: float = 0.0     # sadness + disgust
    contempt: float = 0.0    # disgust + anger
    aggressiveness: float = 0.0  # anger + anticipation
    optimism: float = 0.0    # anticipation + joy
    
    # Meta-emotional states
    emotional_clarity: float = 0.7    # How clear/mixed the emotions are
    emotional_intensity: float = 0.5  # Overall intensity
    emotional_stability: float = 0.7  # How stable vs volatile
    
    # Contextual factors
    stress_indicators: List[str] = field(default_factory=list)
    coping_mechanisms: List[str] = field(default_factory=list)
    emotional_triggers: List[str] = field(default_factory=list)
    
    def get_dominant_emotion(self) -> Tuple[str, float]:
        """Get the strongest emotion and its intensity."""
        emotions = {
            "joy": self.joy,
            "trust": self.trust,
            "fear": self.fear,
            "surprise": self.surprise,
            "sadness": self.sadness,
            "disgust": self.disgust,
            "anger": self.anger,
            "anticipation": self.anticipation,
            "love": self.love,
            "awe": self.awe,
            "remorse": self.remorse,
            "optimism": self.optimism
        }
        
        dominant = max(emotions.items(), key=lambda x: x[1])
        return dominant[0], dominant[1]
    
    def get_emotional_valence(self) -> float:
        """Get overall positive/negative valence (-1 to 1)."""
        positive = self.joy + self.trust + self.anticipation + self.love + self.optimism
        negative = self.fear + self.sadness + self.disgust + self.anger + self.remorse
        
        total = positive + negative
        if total == 0:
            return 0.0
        
        return (positive - negative) / total


@dataclass
class EmotionalTrajectory:
    """Tracks emotional changes over time."""
    
    trajectory_type: str  # improving, declining, stable, volatile
    trend_strength: float  # 0-1 scale
    key_transitions: List[Dict[str, Any]] = field(default_factory=list)
    predicted_next_state: Optional[EmotionalState] = None
    intervention_recommended: bool = False
    intervention_type: Optional[str] = None


class EmotionalIntelligenceEngine:
    """Advanced emotional intelligence system."""
    
    def __init__(self, bedrock_client=None):
        """Initialize the emotional intelligence engine."""
        self.bedrock = bedrock_client
        self.emotion_history: deque = deque(maxlen=100)
        self.linguistic_analyzer = LinguisticEmotionAnalyzer()
        self.voice_pattern_analyzer = VoicePatternAnalyzer()
        self.contextual_analyzer = ContextualEmotionAnalyzer()
        
    def analyze_emotional_content(self, transcript: str, 
                                voice_features: Optional[Dict] = None,
                                context: Optional[Dict] = None) -> Dict[str, Any]:
        """Perform comprehensive emotional analysis.
        
        Args:
            transcript: The voice transcript text
            voice_features: Optional voice analysis features (tone, pace, etc.)
            context: Optional contextual information
            
        Returns:
            Detailed emotional analysis results
        """
        
        # Linguistic emotion analysis
        linguistic_emotions = self.linguistic_analyzer.analyze(transcript)
        
        # Voice pattern analysis (if available)
        voice_emotions = {}
        if voice_features:
            voice_emotions = self.voice_pattern_analyzer.analyze(voice_features)
        
        # AI-powered deep analysis
        if self.bedrock:
            ai_analysis = self._perform_ai_analysis(transcript, linguistic_emotions, context)
        else:
            ai_analysis = self._fallback_analysis(transcript, linguistic_emotions)
        
        # Combine all analyses
        emotional_state = self._synthesize_emotional_state(
            linguistic_emotions, voice_emotions, ai_analysis
        )
        
        # Analyze trajectory
        trajectory = self._analyze_trajectory(emotional_state)
        
        # Generate recommendations
        recommendations = self._generate_emotional_recommendations(
            emotional_state, trajectory, context
        )
        
        # Store in history
        self.emotion_history.append({
            "timestamp": datetime.utcnow(),
            "emotional_state": emotional_state,
            "transcript_preview": transcript[:100]
        })
        
        return {
            "emotional_state": emotional_state,
            "trajectory": trajectory,
            "linguistic_analysis": linguistic_emotions,
            "voice_analysis": voice_emotions,
            "ai_insights": ai_analysis,
            "recommendations": recommendations,
            "empathetic_response": self._generate_empathetic_response(emotional_state, context)
        }
    
    def _perform_ai_analysis(self, transcript: str, linguistic_emotions: Dict,
                           context: Optional[Dict]) -> Dict[str, Any]:
        """Use Claude for deep emotional analysis."""
        
        context_info = ""
        if context:
            context_info = f"""
Context Information:
- Time of day: {context.get('time_of_day', 'unknown')}
- Recent mood: {context.get('recent_mood', 'unknown')}
- Current situation: {context.get('situation', 'unknown')}
"""
        
        prompt = f"""Perform a deep emotional analysis of this voice transcript:

Transcript: "{transcript}"

Linguistic Analysis Results:
{json.dumps(linguistic_emotions, indent=2)}

{context_info}

Analyze:
1. PRIMARY EMOTIONS (rate 0.0-1.0 for each):
   - Joy, Trust, Fear, Surprise, Sadness, Disgust, Anger, Anticipation
   
2. SECONDARY EMOTIONS (rate 0.0-1.0):
   - Love (joy+trust), Awe (fear+surprise), Remorse (sadness+disgust), 
   - Optimism (anticipation+joy), Submission (trust+fear)
   
3. EMOTIONAL COMPLEXITY:
   - Emotional clarity (0-1): How clear vs mixed/conflicted
   - Emotional intensity (0-1): Overall strength of emotions
   - Emotional stability (0-1): How stable vs volatile
   
4. DEEPER INSIGHTS:
   - Underlying emotional needs
   - Potential emotional triggers mentioned
   - Coping mechanisms being used
   - Stress indicators present
   - Subtext and unexpressed emotions
   
5. CONTEXTUAL UNDERSTANDING:
   - Why might they be feeling this way?
   - What support might be helpful?
   - Any concerning patterns?

Respond in JSON format with all requested information."""
        
        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response["body"].read())
            return json.loads(result.get("content", [{}])[0].get("text", "{}"))
            
        except Exception as e:
            logger.error(f"AI emotional analysis failed: {e}")
            return {}
    
    def _synthesize_emotional_state(self, linguistic: Dict, voice: Dict, 
                                  ai: Dict) -> EmotionalState:
        """Combine multiple analyses into unified emotional state."""
        
        state = EmotionalState()
        
        # Weight different sources
        weights = {
            "linguistic": 0.3,
            "voice": 0.2,
            "ai": 0.5
        }
        
        # If voice analysis unavailable, redistribute weight
        if not voice:
            weights["linguistic"] = 0.4
            weights["ai"] = 0.6
            weights["voice"] = 0.0
        
        # Combine primary emotions
        emotions = ["joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation"]
        for emotion in emotions:
            value = 0.0
            if emotion in linguistic:
                value += linguistic[emotion] * weights["linguistic"]
            if emotion in voice:
                value += voice[emotion] * weights["voice"]
            if emotion in ai.get("primary_emotions", {}):
                value += ai["primary_emotions"][emotion] * weights["ai"]
            
            setattr(state, emotion, min(value, 1.0))
        
        # Calculate secondary emotions
        state.love = (state.joy + state.trust) / 2
        state.submission = (state.trust + state.fear) / 2
        state.awe = (state.fear + state.surprise) / 2
        state.disapproval = (state.surprise + state.sadness) / 2
        state.remorse = (state.sadness + state.disgust) / 2
        state.contempt = (state.disgust + state.anger) / 2
        state.aggressiveness = (state.anger + state.anticipation) / 2
        state.optimism = (state.anticipation + state.joy) / 2
        
        # Set meta-emotional states from AI analysis
        if ai:
            state.emotional_clarity = ai.get("emotional_complexity", {}).get("clarity", 0.7)
            state.emotional_intensity = ai.get("emotional_complexity", {}).get("intensity", 0.5)
            state.emotional_stability = ai.get("emotional_complexity", {}).get("stability", 0.7)
            state.stress_indicators = ai.get("deeper_insights", {}).get("stress_indicators", [])
            state.coping_mechanisms = ai.get("deeper_insights", {}).get("coping_mechanisms", [])
            state.emotional_triggers = ai.get("deeper_insights", {}).get("triggers", [])
        
        return state
    
    def _analyze_trajectory(self, current_state: EmotionalState) -> EmotionalTrajectory:
        """Analyze emotional trajectory based on history."""
        
        if len(self.emotion_history) < 3:
            return EmotionalTrajectory(
                trajectory_type="insufficient_data",
                trend_strength=0.0
            )
        
        # Get recent emotional states
        recent_states = [h["emotional_state"] for h in list(self.emotion_history)[-10:]]
        
        # Calculate valence trajectory
        valences = [state.get_emotional_valence() for state in recent_states]
        
        # Simple linear regression for trend
        x = np.arange(len(valences))
        slope = np.polyfit(x, valences, 1)[0]
        
        # Determine trajectory type
        if abs(slope) < 0.05:
            trajectory_type = "stable"
        elif slope > 0.1:
            trajectory_type = "improving"
        elif slope < -0.1:
            trajectory_type = "declining"
        else:
            # Check volatility
            volatility = np.std(valences)
            trajectory_type = "volatile" if volatility > 0.3 else "stable"
        
        # Identify key transitions
        transitions = []
        for i in range(1, len(recent_states)):
            prev_dominant = recent_states[i-1].get_dominant_emotion()
            curr_dominant = recent_states[i].get_dominant_emotion()
            
            if prev_dominant[0] != curr_dominant[0]:
                transitions.append({
                    "from": prev_dominant[0],
                    "to": curr_dominant[0],
                    "index": i
                })
        
        # Determine if intervention needed
        intervention_needed = (
            trajectory_type == "declining" and abs(slope) > 0.2 or
            current_state.stress_indicators and len(current_state.stress_indicators) > 2 or
            current_state.emotional_intensity > 0.8 and current_state.get_emotional_valence() < -0.5
        )
        
        return EmotionalTrajectory(
            trajectory_type=trajectory_type,
            trend_strength=abs(slope),
            key_transitions=transitions,
            intervention_recommended=intervention_needed,
            intervention_type="emotional_support" if intervention_needed else None
        )
    
    def _generate_emotional_recommendations(self, state: EmotionalState,
                                          trajectory: EmotionalTrajectory,
                                          context: Optional[Dict]) -> List[Dict[str, str]]:
        """Generate personalized emotional support recommendations."""
        
        recommendations = []
        
        # High stress recommendations
        if state.stress_indicators:
            recommendations.append({
                "type": "stress_relief",
                "suggestion": "Consider a 5-minute breathing exercise or mindfulness break",
                "reason": f"Stress indicators detected: {', '.join(state.stress_indicators[:2])}",
                "urgency": "high" if len(state.stress_indicators) > 2 else "medium"
            })
        
        # Sadness/grief support
        if state.sadness > 0.7:
            recommendations.append({
                "type": "emotional_support",
                "suggestion": "It's okay to feel sad. Consider journaling or talking to someone you trust",
                "reason": "High sadness levels detected",
                "urgency": "medium"
            })
        
        # Anger management
        if state.anger > 0.7:
            recommendations.append({
                "type": "anger_management",
                "suggestion": "Take a walk or engage in physical activity to release tension",
                "reason": "Elevated anger levels detected",
                "urgency": "high"
            })
        
        # Positive reinforcement
        if state.joy > 0.7 or state.optimism > 0.7:
            recommendations.append({
                "type": "positive_reinforcement",
                "suggestion": "Celebrate this positive moment! Consider sharing with someone or noting what contributed to this feeling",
                "reason": "Positive emotional state detected",
                "urgency": "low"
            })
        
        # Trajectory-based recommendations
        if trajectory.trajectory_type == "declining":
            recommendations.append({
                "type": "preventive_care",
                "suggestion": "Your mood seems to be declining. Consider scheduling self-care time or reaching out for support",
                "reason": "Declining emotional trajectory detected",
                "urgency": "medium"
            })
        
        return recommendations
    
    def _generate_empathetic_response(self, state: EmotionalState,
                                    context: Optional[Dict]) -> str:
        """Generate an empathetic response based on emotional state."""
        
        dominant_emotion, intensity = state.get_dominant_emotion()
        valence = state.get_emotional_valence()
        
        # Base responses for different emotional states
        responses = {
            "joy": "It's wonderful to hear the joy in your voice! 🌟",
            "sadness": "I hear that you're going through a difficult time. Your feelings are valid.",
            "anger": "I understand you're feeling frustrated. It's okay to feel this way.",
            "fear": "It sounds like you're dealing with some uncertainty. You're not alone in this.",
            "trust": "Thank you for sharing this with me. I'm here to support you.",
            "surprise": "That does sound unexpected! How are you processing this?",
            "anticipation": "I can sense your excitement about what's ahead!",
            "love": "The care and connection in your words really comes through."
        }
        
        base_response = responses.get(dominant_emotion, "Thank you for sharing your thoughts with me.")
        
        # Add intensity modifiers
        if intensity > 0.8:
            base_response = "I can really feel the intensity of your emotions. " + base_response
        elif intensity < 0.3:
            base_response = "I sense some subtle feelings here. " + base_response
        
        # Add support for negative valence
        if valence < -0.5:
            base_response += " Remember, it's okay to not be okay sometimes. I'm here to listen whenever you need."
        
        return base_response
    
    def get_emotional_insights(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get insights about emotional patterns over time."""
        
        if not self.emotion_history:
            return {"message": "No emotional history available"}
        
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_entries = [e for e in self.emotion_history 
                         if e["timestamp"] > cutoff]
        
        if not recent_entries:
            return {"message": f"No entries in the last {time_window_hours} hours"}
        
        # Calculate statistics
        states = [e["emotional_state"] for e in recent_entries]
        
        # Dominant emotions
        emotion_counts = {}
        for state in states:
            dominant, _ = state.get_dominant_emotion()
            emotion_counts[dominant] = emotion_counts.get(dominant, 0) + 1
        
        # Average valence
        avg_valence = np.mean([s.get_emotional_valence() for s in states])
        
        # Emotional volatility
        valences = [s.get_emotional_valence() for s in states]
        volatility = np.std(valences) if len(valences) > 1 else 0.0
        
        # Stress analysis
        stress_count = sum(1 for s in states if s.stress_indicators)
        
        return {
            "time_window_hours": time_window_hours,
            "total_analyses": len(recent_entries),
            "dominant_emotions": emotion_counts,
            "average_valence": float(avg_valence),
            "emotional_volatility": float(volatility),
            "stress_percentage": (stress_count / len(states)) * 100 if states else 0,
            "insights": self._generate_period_insights(states, emotion_counts, avg_valence, volatility)
        }
    
    def _generate_period_insights(self, states: List[EmotionalState], 
                                emotion_counts: Dict, avg_valence: float, 
                                volatility: float) -> List[str]:
        """Generate human-readable insights about emotional patterns."""
        
        insights = []
        
        # Overall mood insight
        if avg_valence > 0.3:
            insights.append("Overall positive emotional state during this period")
        elif avg_valence < -0.3:
            insights.append("Challenging emotional period detected - consider self-care")
        else:
            insights.append("Emotionally balanced period with mixed feelings")
        
        # Volatility insight
        if volatility > 0.5:
            insights.append("High emotional volatility - emotions changing rapidly")
        elif volatility < 0.2:
            insights.append("Emotionally stable period")
        
        # Dominant emotion insight
        if emotion_counts:
            dominant = max(emotion_counts.items(), key=lambda x: x[1])
            percentage = (dominant[1] / len(states)) * 100
            insights.append(f"Most frequent emotion: {dominant[0]} ({percentage:.0f}% of time)")
        
        # Stress insight
        stress_indicators = []
        for state in states:
            stress_indicators.extend(state.stress_indicators)
        
        if stress_indicators:
            unique_stressors = list(set(stress_indicators))[:3]
            insights.append(f"Common stress indicators: {', '.join(unique_stressors)}")
        
        return insights


class LinguisticEmotionAnalyzer:
    """Analyzes emotions from linguistic patterns."""
    
    def __init__(self):
        # Emotion lexicons (simplified - use comprehensive lexicons in production)
        self.emotion_words = {
            "joy": ["happy", "excited", "thrilled", "delighted", "joyful", "elated", "wonderful"],
            "sadness": ["sad", "depressed", "down", "blue", "miserable", "heartbroken", "grief"],
            "anger": ["angry", "furious", "mad", "irritated", "annoyed", "rage", "frustrated"],
            "fear": ["scared", "afraid", "anxious", "worried", "terrified", "nervous", "panic"],
            "trust": ["trust", "believe", "faith", "confident", "secure", "reliable"],
            "disgust": ["disgusted", "revolted", "sick", "repulsed", "awful", "terrible"],
            "surprise": ["surprised", "shocked", "amazed", "astonished", "unexpected", "sudden"],
            "anticipation": ["excited", "looking forward", "can't wait", "eager", "hopeful"]
        }
        
        # Intensity modifiers
        self.intensifiers = ["very", "extremely", "really", "so", "incredibly", "absolutely"]
        self.diminishers = ["somewhat", "slightly", "a bit", "kind of", "sort of"]
    
    def analyze(self, text: str) -> Dict[str, float]:
        """Analyze emotional content from text."""
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Initialize emotion scores
        scores = {emotion: 0.0 for emotion in self.emotion_words}
        
        # Count emotion words with intensity modifiers
        for i, word in enumerate(words):
            for emotion, keywords in self.emotion_words.items():
                if word in keywords:
                    score = 1.0
                    
                    # Check for intensifiers/diminishers
                    if i > 0:
                        if words[i-1] in self.intensifiers:
                            score *= 1.5
                        elif words[i-1] in self.diminishers:
                            score *= 0.5
                    
                    scores[emotion] += score
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            for emotion in scores:
                scores[emotion] = min(scores[emotion] / total, 1.0)
        
        return scores


class VoicePatternAnalyzer:
    """Analyzes emotions from voice patterns (placeholder for actual implementation)."""
    
    def analyze(self, voice_features: Dict) -> Dict[str, float]:
        """Analyze emotions from voice features like tone, pace, volume."""
        
        # Placeholder implementation
        # In production, use actual voice analysis features
        return {
            "joy": voice_features.get("pitch_variability", 0.5),
            "sadness": 1.0 - voice_features.get("energy", 0.5),
            "anger": voice_features.get("volume_intensity", 0.3),
            "fear": voice_features.get("speech_rate", 0.5) * voice_features.get("tremor", 0.0),
            "trust": voice_features.get("steadiness", 0.5),
            "disgust": 0.0,
            "surprise": voice_features.get("pitch_peaks", 0.0),
            "anticipation": voice_features.get("speech_rate", 0.5)
        }


class ContextualEmotionAnalyzer:
    """Analyzes emotions based on context."""
    
    def analyze(self, context: Dict) -> Dict[str, Any]:
        """Analyze how context affects emotional interpretation."""
        
        modifiers = {}
        
        # Time of day effects
        hour = datetime.utcnow().hour
        if 22 <= hour or hour <= 4:
            modifiers["late_night_factor"] = 1.2  # Emotions often intensified late at night
        
        # Day of week effects
        weekday = datetime.utcnow().weekday()
        if weekday == 0:  # Monday
            modifiers["monday_blues"] = 1.1
        elif weekday >= 5:  # Weekend
            modifiers["weekend_relaxation"] = 0.9
        
        return modifiers