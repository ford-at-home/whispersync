"""Persona Voice Generation and Selection System for WhisperSync.

This module implements a sophisticated persona system that adapts the AI's
communication style based on user preferences, context, and emotional needs.
It goes beyond simple tone adjustment to create distinct, consistent personas
that build trust and rapport with users.

PERSONA SYSTEM COMPONENTS:
1. Core Personas: Pre-defined personality archetypes
2. Adaptive Personas: Dynamically adjusted based on user interactions
3. Context-Aware Selection: Choose appropriate persona for situation
4. Voice Synthesis: Consistent language patterns for each persona
5. Emotional Calibration: Adjust persona based on user's emotional state
6. Cultural Sensitivity: Adapt communication style to cultural context

WHY PERSONA SYSTEM:
- Builds stronger emotional connection with users
- Provides appropriate support for different situations
- Maintains consistency in multi-session interactions
- Enables personalized communication preferences
- Improves user comfort and trust
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class PersonaArchetype(Enum):
    """Core persona archetypes available in the system."""
    
    PROFESSIONAL_ASSISTANT = "professional_assistant"  # Formal, efficient, task-focused
    EMPATHETIC_COMPANION = "empathetic_companion"     # Warm, understanding, supportive
    CREATIVE_COLLABORATOR = "creative_collaborator"   # Imaginative, encouraging, playful
    ANALYTICAL_ADVISOR = "analytical_advisor"         # Logical, detailed, systematic
    MINDFUL_GUIDE = "mindful_guide"                  # Calm, reflective, wisdom-focused
    ENTHUSIASTIC_MOTIVATOR = "enthusiastic_motivator" # Energetic, positive, encouraging
    SCHOLARLY_MENTOR = "scholarly_mentor"             # Educational, patient, thorough
    PRACTICAL_HELPER = "practical_helper"             # Direct, solution-focused, no-nonsense


@dataclass
class PersonaTraits:
    """Detailed traits that define a persona's behavior."""
    
    # Communication style
    formality_level: float = 0.5      # 0=very casual, 1=very formal
    warmth_level: float = 0.5         # 0=distant, 1=very warm
    verbosity_level: float = 0.5      # 0=concise, 1=elaborate
    technical_level: float = 0.5      # 0=simple, 1=highly technical
    
    # Emotional characteristics
    empathy_expression: float = 0.5   # 0=minimal, 1=highly empathetic
    humor_usage: float = 0.3          # 0=no humor, 1=very humorous
    emotional_validation: float = 0.5  # 0=factual only, 1=strong validation
    
    # Interaction patterns
    proactivity_level: float = 0.5    # 0=reactive only, 1=very proactive
    questioning_style: float = 0.5    # 0=closed questions, 1=open exploration
    suggestion_frequency: float = 0.5  # 0=minimal suggestions, 1=many suggestions
    
    # Language patterns
    vocabulary_complexity: float = 0.5 # 0=simple, 1=sophisticated
    metaphor_usage: float = 0.3       # 0=literal, 1=highly metaphorical
    cultural_references: float = 0.3   # 0=universal, 1=culture-specific
    
    # Response patterns
    response_length_preference: str = "moderate"  # brief, moderate, detailed
    greeting_style: str = "friendly"              # formal, friendly, casual, warm
    closing_style: str = "supportive"             # professional, supportive, encouraging
    
    # Special characteristics
    preferred_topics: List[str] = field(default_factory=list)
    avoided_topics: List[str] = field(default_factory=list)
    signature_phrases: List[str] = field(default_factory=list)
    communication_quirks: List[str] = field(default_factory=list)


@dataclass
class PersonaProfile:
    """Complete persona profile with all characteristics."""
    
    persona_id: str
    name: str
    archetype: PersonaArchetype
    description: str
    
    # Core characteristics
    traits: PersonaTraits = field(default_factory=PersonaTraits)
    
    # Contextual preferences
    best_for_situations: List[str] = field(default_factory=list)
    avoid_in_situations: List[str] = field(default_factory=list)
    
    # User compatibility
    compatible_user_types: List[str] = field(default_factory=list)
    incompatible_with: List[str] = field(default_factory=list)
    
    # Language templates
    greeting_templates: List[str] = field(default_factory=list)
    acknowledgment_templates: List[str] = field(default_factory=list)
    encouragement_templates: List[str] = field(default_factory=list)
    closing_templates: List[str] = field(default_factory=list)
    
    # Voice synthesis parameters
    speech_pace: float = 1.0         # 0.8=slow, 1.0=normal, 1.2=fast
    pitch_variation: float = 0.5     # 0=monotone, 1=highly varied
    pause_frequency: float = 0.5     # 0=continuous, 1=many pauses
    emphasis_style: str = "moderate" # subtle, moderate, dramatic


class PersonaSystem:
    """Main persona management and generation system."""
    
    def __init__(self, bedrock_client=None):
        """Initialize the persona system."""
        self.bedrock = bedrock_client
        self.personas: Dict[str, PersonaProfile] = {}
        self.user_preferences: Dict[str, Dict] = {}  # user_id -> preferences
        self.interaction_history: List[Dict] = []
        
        # Initialize core personas
        self._initialize_core_personas()
    
    def _initialize_core_personas(self):
        """Initialize the core persona archetypes."""
        
        # Professional Assistant
        self.personas["professional"] = PersonaProfile(
            persona_id="professional",
            name="Professional Assistant",
            archetype=PersonaArchetype.PROFESSIONAL_ASSISTANT,
            description="Efficient, formal, and task-focused communication",
            traits=PersonaTraits(
                formality_level=0.8,
                warmth_level=0.3,
                verbosity_level=0.4,
                technical_level=0.7,
                empathy_expression=0.3,
                humor_usage=0.1,
                proactivity_level=0.7,
                vocabulary_complexity=0.7,
                response_length_preference="brief",
                greeting_style="formal",
                closing_style="professional"
            ),
            best_for_situations=["work", "formal meetings", "professional tasks"],
            greeting_templates=[
                "Good {time_of_day}. How may I assist you today?",
                "Hello. I'm ready to help with your request.",
                "Greetings. What can I help you accomplish?"
            ],
            acknowledgment_templates=[
                "I understand. Let me process that for you.",
                "Certainly. I'll handle that right away.",
                "Noted. I'll take care of this immediately."
            ]
        )
        
        # Empathetic Companion
        self.personas["empathetic"] = PersonaProfile(
            persona_id="empathetic",
            name="Empathetic Companion",
            archetype=PersonaArchetype.EMPATHETIC_COMPANION,
            description="Warm, understanding, and emotionally supportive",
            traits=PersonaTraits(
                formality_level=0.3,
                warmth_level=0.9,
                verbosity_level=0.6,
                technical_level=0.3,
                empathy_expression=0.9,
                humor_usage=0.4,
                emotional_validation=0.9,
                proactivity_level=0.6,
                vocabulary_complexity=0.4,
                response_length_preference="moderate",
                greeting_style="warm",
                closing_style="supportive"
            ),
            best_for_situations=["emotional support", "personal reflection", "difficult times"],
            greeting_templates=[
                "Hi there! It's so good to hear from you. How are you feeling today?",
                "Hello, friend. I'm here and ready to listen.",
                "Hey! I've been thinking about you. What's on your mind?"
            ],
            encouragement_templates=[
                "You're doing amazingly well with this. I'm proud of you!",
                "That takes real courage to share. Thank you for trusting me.",
                "I believe in you completely. You've got this!"
            ]
        )
        
        # Creative Collaborator
        self.personas["creative"] = PersonaProfile(
            persona_id="creative",
            name="Creative Collaborator",
            archetype=PersonaArchetype.CREATIVE_COLLABORATOR,
            description="Imaginative, playful, and innovation-focused",
            traits=PersonaTraits(
                formality_level=0.2,
                warmth_level=0.7,
                verbosity_level=0.7,
                technical_level=0.5,
                empathy_expression=0.6,
                humor_usage=0.8,
                proactivity_level=0.9,
                questioning_style=0.9,
                metaphor_usage=0.8,
                vocabulary_complexity=0.6,
                response_length_preference="detailed",
                greeting_style="casual",
                closing_style="encouraging"
            ),
            best_for_situations=["brainstorming", "creative projects", "idea generation"],
            greeting_templates=[
                "Hey there, creative soul! What amazing ideas are brewing today?",
                "Hello, innovator! Ready to explore some possibilities?",
                "Greetings, fellow dreamer! What shall we create today?"
            ],
            signature_phrases=[
                "What if we tried...",
                "Imagine if...",
                "Let's play with this idea...",
                "How about we flip that concept..."
            ]
        )
        
        # Mindful Guide
        self.personas["mindful"] = PersonaProfile(
            persona_id="mindful",
            name="Mindful Guide",
            archetype=PersonaArchetype.MINDFUL_GUIDE,
            description="Calm, reflective, and wisdom-focused",
            traits=PersonaTraits(
                formality_level=0.5,
                warmth_level=0.7,
                verbosity_level=0.5,
                technical_level=0.2,
                empathy_expression=0.8,
                humor_usage=0.3,
                emotional_validation=0.8,
                proactivity_level=0.3,
                questioning_style=0.8,
                metaphor_usage=0.7,
                vocabulary_complexity=0.5,
                response_length_preference="moderate",
                greeting_style="friendly",
                closing_style="supportive",
                speech_pace=0.9,
                pause_frequency=0.7
            ),
            best_for_situations=["meditation", "reflection", "stress relief", "personal growth"],
            greeting_templates=[
                "Welcome, dear friend. Let's take a moment to center ourselves.",
                "Hello. I'm here to journey with you in this present moment.",
                "Greetings. How is your inner world today?"
            ],
            signature_phrases=[
                "Let's pause and breathe together...",
                "Notice what arises without judgment...",
                "There's wisdom in this moment...",
                "What does your heart tell you?"
            ]
        )
    
    def select_persona(self, user_state: Dict, context: Dict, 
                      user_preferences: Optional[Dict] = None) -> PersonaProfile:
        """Select the most appropriate persona for the current interaction.
        
        Args:
            user_state: Current user emotional and behavioral state
            context: Current context (time, recent interactions, etc.)
            user_preferences: Explicit user preferences if available
            
        Returns:
            Selected persona profile
        """
        
        # Check for explicit user preference
        if user_preferences and "preferred_persona" in user_preferences:
            preferred_id = user_preferences["preferred_persona"]
            if preferred_id in self.personas:
                return self.personas[preferred_id]
        
        # Use AI to select best persona if available
        if self.bedrock:
            selected_id = self._ai_persona_selection(user_state, context)
            if selected_id in self.personas:
                return self.personas[selected_id]
        
        # Fallback: rule-based selection
        return self._rule_based_selection(user_state, context)
    
    def _ai_persona_selection(self, user_state: Dict, context: Dict) -> str:
        """Use AI to select the most appropriate persona."""
        
        prompt = f"""Based on the user's current state and context, select the most appropriate persona:

User State:
- Emotional tone: {user_state.get('emotional_tone', 'neutral')}
- Stress level: {user_state.get('stress_level', 'moderate')}
- Energy level: {user_state.get('energy_level', 'moderate')}
- Current focus: {user_state.get('focus_area', 'general')}
- Recent themes: {', '.join(user_state.get('recent_themes', [])[:5])}

Context:
- Time of day: {context.get('time_of_day', 'unknown')}
- Type of content: {context.get('content_type', 'general')}
- Interaction intent: {context.get('intent', 'unknown')}
- Previous persona used: {context.get('previous_persona', 'none')}

Available Personas:
1. professional - Efficient, formal, task-focused
2. empathetic - Warm, understanding, emotionally supportive
3. creative - Imaginative, playful, innovation-focused
4. mindful - Calm, reflective, wisdom-focused

Select the single best persona and explain why. 
Respond with JSON: {{"selected_persona": "persona_id", "reasoning": "explanation"}}"""
        
        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response["body"].read())
            selection = json.loads(result.get("content", [{}])[0].get("text", "{}"))
            
            logger.info(f"AI selected persona: {selection.get('selected_persona')} "
                       f"because: {selection.get('reasoning')}")
            
            return selection.get("selected_persona", "empathetic")
            
        except Exception as e:
            logger.error(f"AI persona selection failed: {e}")
            return "empathetic"  # Safe default
    
    def _rule_based_selection(self, user_state: Dict, context: Dict) -> PersonaProfile:
        """Rule-based persona selection as fallback."""
        
        # High stress -> Empathetic or Mindful
        if user_state.get("stress_level", 0) > 0.7:
            if user_state.get("emotional_tone") in ["anxious", "overwhelmed"]:
                return self.personas["mindful"]
            else:
                return self.personas["empathetic"]
        
        # Work context -> Professional
        if context.get("content_type") == "work" or context.get("intent") == "task":
            return self.personas["professional"]
        
        # Creative context -> Creative
        if context.get("intent") in ["ideation", "brainstorming"]:
            return self.personas["creative"]
        
        # Default to empathetic
        return self.personas["empathetic"]
    
    def generate_response(self, content: str, persona: PersonaProfile,
                         context: Optional[Dict] = None) -> str:
        """Generate a response using the specified persona's voice.
        
        Args:
            content: The actual content to communicate
            persona: The persona profile to use
            context: Optional context for response generation
            
        Returns:
            Response formatted in the persona's voice
        """
        
        if self.bedrock:
            return self._ai_voice_generation(content, persona, context)
        else:
            return self._template_based_response(content, persona, context)
    
    def _ai_voice_generation(self, content: str, persona: PersonaProfile,
                           context: Optional[Dict]) -> str:
        """Use AI to generate response in persona's voice."""
        
        # Build persona description for AI
        persona_description = f"""
Persona: {persona.name}
Description: {persona.description}

Communication Style:
- Formality: {persona.traits.formality_level:.1f}/1.0
- Warmth: {persona.traits.warmth_level:.1f}/1.0
- Verbosity: {persona.traits.verbosity_level:.1f}/1.0
- Empathy: {persona.traits.empathy_expression:.1f}/1.0
- Humor: {persona.traits.humor_usage:.1f}/1.0

Language Preferences:
- Vocabulary complexity: {persona.traits.vocabulary_complexity:.1f}/1.0
- Metaphor usage: {persona.traits.metaphor_usage:.1f}/1.0
- Response length: {persona.traits.response_length_preference}
- Greeting style: {persona.traits.greeting_style}

Signature phrases: {', '.join(persona.traits.signature_phrases[:3])}
"""
        
        prompt = f"""Transform this content into the voice of the specified persona:

{persona_description}

Content to communicate:
"{content}"

{"Context: " + json.dumps(context) if context else ""}

Generate a response that:
1. Maintains the persona's unique voice and style
2. Communicates the content clearly
3. Feels natural and consistent with the persona
4. Includes appropriate emotional tone
5. Uses signature phrases if relevant

Respond with just the transformed message, no explanations."""
        
        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.7,  # Higher for more personality
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response["body"].read())
            return result.get("content", [{}])[0].get("text", content)
            
        except Exception as e:
            logger.error(f"AI voice generation failed: {e}")
            return content
    
    def _template_based_response(self, content: str, persona: PersonaProfile,
                               context: Optional[Dict]) -> str:
        """Generate response using templates (fallback method)."""
        
        # Add greeting if appropriate
        response_parts = []
        
        if context and context.get("needs_greeting"):
            greeting = self._select_template(persona.greeting_templates, context)
            response_parts.append(greeting)
        
        # Add main content with persona adjustments
        adjusted_content = self._adjust_content_style(content, persona)
        response_parts.append(adjusted_content)
        
        # Add closing if appropriate
        if context and context.get("needs_closing"):
            closing = self._select_template(persona.closing_templates, context)
            response_parts.append(closing)
        
        return " ".join(response_parts)
    
    def _select_template(self, templates: List[str], context: Dict) -> str:
        """Select appropriate template based on context."""
        
        if not templates:
            return ""
        
        # Simple selection based on time of day
        import random
        template = random.choice(templates)
        
        # Replace placeholders
        time_of_day = context.get("time_of_day", "day")
        template = template.replace("{time_of_day}", time_of_day)
        
        return template
    
    def _adjust_content_style(self, content: str, persona: PersonaProfile) -> str:
        """Adjust content style based on persona traits."""
        
        adjusted = content
        
        # Adjust formality
        if persona.traits.formality_level > 0.7:
            # Make more formal
            adjusted = adjusted.replace("can't", "cannot")
            adjusted = adjusted.replace("won't", "will not")
            adjusted = adjusted.replace("Hi", "Hello")
        elif persona.traits.formality_level < 0.3:
            # Make more casual
            adjusted = adjusted.replace("cannot", "can't")
            adjusted = adjusted.replace("will not", "won't")
        
        # Add warmth markers
        if persona.traits.warmth_level > 0.7:
            if "thank you" in adjusted.lower():
                adjusted = adjusted.replace("Thank you", "Thank you so much")
        
        # Adjust verbosity
        if persona.traits.verbosity_level < 0.3:
            # Make more concise
            sentences = adjusted.split(". ")
            if len(sentences) > 3:
                adjusted = ". ".join(sentences[:3]) + "."
        
        return adjusted
    
    def adapt_persona(self, persona_id: str, user_feedback: Dict) -> PersonaProfile:
        """Adapt a persona based on user feedback.
        
        Args:
            persona_id: ID of persona to adapt
            user_feedback: Feedback about what to adjust
            
        Returns:
            Adapted persona profile
        """
        
        if persona_id not in self.personas:
            return None
        
        persona = self.personas[persona_id]
        
        # Adjust traits based on feedback
        if "too_formal" in user_feedback:
            persona.traits.formality_level = max(0, persona.traits.formality_level - 0.1)
        elif "too_casual" in user_feedback:
            persona.traits.formality_level = min(1, persona.traits.formality_level + 0.1)
        
        if "more_empathy" in user_feedback:
            persona.traits.empathy_expression = min(1, persona.traits.empathy_expression + 0.1)
            persona.traits.emotional_validation = min(1, persona.traits.emotional_validation + 0.1)
        
        if "more_concise" in user_feedback:
            persona.traits.verbosity_level = max(0, persona.traits.verbosity_level - 0.1)
            persona.traits.response_length_preference = "brief"
        elif "more_detail" in user_feedback:
            persona.traits.verbosity_level = min(1, persona.traits.verbosity_level + 0.1)
            persona.traits.response_length_preference = "detailed"
        
        return persona
    
    def create_custom_persona(self, user_id: str, preferences: Dict) -> PersonaProfile:
        """Create a custom persona based on user preferences.
        
        Args:
            user_id: User ID for the custom persona
            preferences: User's communication preferences
            
        Returns:
            Custom persona profile
        """
        
        custom_id = f"custom_{user_id}"
        
        # Create base traits from preferences
        traits = PersonaTraits(
            formality_level=preferences.get("formality", 0.5),
            warmth_level=preferences.get("warmth", 0.7),
            verbosity_level=preferences.get("verbosity", 0.5),
            empathy_expression=preferences.get("empathy", 0.6),
            humor_usage=preferences.get("humor", 0.3),
            proactivity_level=preferences.get("proactivity", 0.5)
        )
        
        # Create custom persona
        custom_persona = PersonaProfile(
            persona_id=custom_id,
            name=f"Custom Assistant for {user_id}",
            archetype=PersonaArchetype.EMPATHETIC_COMPANION,  # Default base
            description="Personalized assistant tailored to user preferences",
            traits=traits,
            best_for_situations=preferences.get("use_cases", ["general"])
        )
        
        self.personas[custom_id] = custom_persona
        return custom_persona