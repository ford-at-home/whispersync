"""
Master Persona Configuration for ElevenLabs Voice Integration

This module provides the central configuration and selection logic for all voice personas.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random

from .british_guardian import (
    BRITISH_GUARDIAN_SYSTEM_PROMPT,
    BRITISH_GUARDIAN_CONTEXT_INJECTION,
    BRITISH_GUARDIAN_VOICE_EXAMPLES,
    BRITISH_GUARDIAN_FALLBACK_RESPONSES
)
from .indian_mystic import (
    INDIAN_MYSTIC_SYSTEM_PROMPT,
    INDIAN_MYSTIC_CONTEXT_INJECTION,
    INDIAN_MYSTIC_VOICE_EXAMPLES,
    INDIAN_MYSTIC_FALLBACK_RESPONSES
)
from .southern_sage import (
    SOUTHERN_SAGE_SYSTEM_PROMPT,
    SOUTHERN_SAGE_CONTEXT_INJECTION,
    SOUTHERN_SAGE_VOICE_EXAMPLES,
    SOUTHERN_SAGE_FALLBACK_RESPONSES
)
from .challenger import (
    THE_CHALLENGER_SYSTEM_PROMPT,
    THE_CHALLENGER_CONTEXT_INJECTION,
    THE_CHALLENGER_VOICE_EXAMPLES,
    THE_CHALLENGER_FALLBACK_RESPONSES
)


class PersonaType(Enum):
    """Available voice personas."""
    BRITISH_GUARDIAN = "british_guardian"
    INDIAN_MYSTIC = "indian_mystic"
    SOUTHERN_SAGE = "southern_sage"
    CHALLENGER = "challenger"


@dataclass
class PersonaConfig:
    """Complete configuration for a voice persona."""
    persona_type: PersonaType
    system_prompt: str
    context_templates: Dict[str, Dict]
    voice_examples: Dict[str, List[str]]
    fallback_responses: Dict[str, str]
    elevenlabs_voice_id: Optional[str] = None
    voice_settings: Optional[Dict] = None


# Master persona registry
PERSONA_REGISTRY = {
    PersonaType.BRITISH_GUARDIAN: PersonaConfig(
        persona_type=PersonaType.BRITISH_GUARDIAN,
        system_prompt=BRITISH_GUARDIAN_SYSTEM_PROMPT,
        context_templates=BRITISH_GUARDIAN_CONTEXT_INJECTION,
        voice_examples=BRITISH_GUARDIAN_VOICE_EXAMPLES,
        fallback_responses=BRITISH_GUARDIAN_FALLBACK_RESPONSES,
        elevenlabs_voice_id="british_professional_voice_id",  # Replace with actual ElevenLabs ID
        voice_settings={
            "stability": 0.75,
            "similarity_boost": 0.80,
            "style": 0.6,
            "use_speaker_boost": True,
            "model_id": "eleven_turbo_v2"
        }
    ),
    PersonaType.INDIAN_MYSTIC: PersonaConfig(
        persona_type=PersonaType.INDIAN_MYSTIC,
        system_prompt=INDIAN_MYSTIC_SYSTEM_PROMPT,
        context_templates=INDIAN_MYSTIC_CONTEXT_INJECTION,
        voice_examples=INDIAN_MYSTIC_VOICE_EXAMPLES,
        fallback_responses=INDIAN_MYSTIC_FALLBACK_RESPONSES,
        elevenlabs_voice_id="gentle_indian_voice_id",  # Replace with actual ElevenLabs ID
        voice_settings={
            "stability": 0.90,
            "similarity_boost": 0.70,
            "style": 0.3,
            "use_speaker_boost": False,
            "model_id": "eleven_monolingual_v1"
        }
    ),
    PersonaType.SOUTHERN_SAGE: PersonaConfig(
        persona_type=PersonaType.SOUTHERN_SAGE,
        system_prompt=SOUTHERN_SAGE_SYSTEM_PROMPT,
        context_templates=SOUTHERN_SAGE_CONTEXT_INJECTION,
        voice_examples=SOUTHERN_SAGE_VOICE_EXAMPLES,
        fallback_responses=SOUTHERN_SAGE_FALLBACK_RESPONSES,
        elevenlabs_voice_id="gravelly_southern_voice_id",  # Replace with actual ElevenLabs ID
        voice_settings={
            "stability": 0.85,
            "similarity_boost": 0.75,
            "style": 0.5,
            "use_speaker_boost": True,
            "model_id": "eleven_monolingual_v1"
        }
    ),
    PersonaType.CHALLENGER: PersonaConfig(
        persona_type=PersonaType.CHALLENGER,
        system_prompt=THE_CHALLENGER_SYSTEM_PROMPT,
        context_templates=THE_CHALLENGER_CONTEXT_INJECTION,
        voice_examples=THE_CHALLENGER_VOICE_EXAMPLES,
        fallback_responses=THE_CHALLENGER_FALLBACK_RESPONSES,
        elevenlabs_voice_id="sharp_contemporary_voice_id",  # Replace with actual ElevenLabs ID
        voice_settings={
            "stability": 0.65,
            "similarity_boost": 0.85,
            "style": 0.8,
            "use_speaker_boost": True,
            "model_id": "eleven_turbo_v2"
        }
    )
}


class PersonaSelector:
    """Intelligent persona selection based on context and need."""
    
    def __init__(self):
        self.persona_registry = PERSONA_REGISTRY
        self.last_persona = None
        self.interaction_count = 0
    
    def select_persona(
        self,
        context_type: str,
        user_state: Optional[Dict] = None,
        agent_type: Optional[str] = None,
        time_of_day: Optional[str] = None,
        emotional_tone: Optional[str] = None
    ) -> PersonaConfig:
        """
        Select the most appropriate persona based on context.
        
        Args:
            context_type: Type of interaction (summary, reflection, guidance, challenge)
            user_state: Current user state information
            agent_type: Which agent is requesting the persona
            time_of_day: Morning, afternoon, evening, night
            emotional_tone: Detected emotional context
            
        Returns:
            PersonaConfig for the selected persona
        """
        # Default mappings
        context_persona_map = {
            "morning_summary": PersonaType.BRITISH_GUARDIAN,
            "evening_summary": PersonaType.BRITISH_GUARDIAN,
            "diary_reflection": PersonaType.INDIAN_MYSTIC,
            "emotional_processing": PersonaType.INDIAN_MYSTIC,
            "value_guidance": PersonaType.SOUTHERN_SAGE,
            "practical_advice": PersonaType.SOUTHERN_SAGE,
            "contradiction_check": PersonaType.CHALLENGER,
            "excuse_challenge": PersonaType.CHALLENGER
        }
        
        # Start with context-based selection
        selected_type = context_persona_map.get(context_type)
        
        # Override based on emotional tone if high intensity
        if emotional_tone:
            if emotional_tone in ["grief", "deep_sadness", "trauma"]:
                selected_type = PersonaType.INDIAN_MYSTIC
            elif emotional_tone in ["procrastination", "avoidance", "excuse_making"]:
                selected_type = PersonaType.CHALLENGER
            elif emotional_tone in ["confusion", "value_conflict", "moral_dilemma"]:
                selected_type = PersonaType.SOUTHERN_SAGE
        
        # Agent-specific preferences
        agent_persona_preferences = {
            "SpiritualAgent": [PersonaType.INDIAN_MYSTIC, PersonaType.SOUTHERN_SAGE],
            "ExecutiveAgent": [PersonaType.BRITISH_GUARDIAN, PersonaType.CHALLENGER],
            "GitHubAgent": [PersonaType.BRITISH_GUARDIAN, PersonaType.CHALLENGER]
        }
        
        if agent_type and agent_type in agent_persona_preferences:
            if selected_type not in agent_persona_preferences[agent_type]:
                selected_type = agent_persona_preferences[agent_type][0]
        
        # Time-based adjustments
        if time_of_day:
            if time_of_day in ["morning", "early_morning"] and not selected_type:
                selected_type = PersonaType.BRITISH_GUARDIAN
            elif time_of_day in ["late_night", "night"] and selected_type == PersonaType.CHALLENGER:
                # Soften late at night
                selected_type = PersonaType.SOUTHERN_SAGE
        
        # Default fallback
        if not selected_type:
            selected_type = PersonaType.BRITISH_GUARDIAN
        
        # Track persona usage
        self.last_persona = selected_type
        self.interaction_count += 1
        
        return self.persona_registry[selected_type]
    
    def get_context_template(
        self,
        persona: PersonaConfig,
        template_name: str
    ) -> Optional[Dict]:
        """Get a specific context template for a persona."""
        return persona.context_templates.get(template_name)
    
    def get_voice_example(
        self,
        persona: PersonaConfig,
        example_type: str
    ) -> Optional[str]:
        """Get a random voice example of a specific type."""
        examples = persona.voice_examples.get(example_type, [])
        return random.choice(examples) if examples else None
    
    def get_fallback_response(
        self,
        persona: PersonaConfig,
        situation: str
    ) -> str:
        """Get an appropriate fallback response."""
        return persona.fallback_responses.get(
            situation,
            "I'm having a bit of trouble understanding that. Could you help me out?"
        )


class PersonaConsistencyManager:
    """Maintains consistency in persona voice across interactions."""
    
    def __init__(self):
        self.persona_memory = {}
        self.style_preferences = {}
    
    def apply_consistency_rules(
        self,
        text: str,
        persona: PersonaConfig,
        previous_interactions: Optional[List[str]] = None
    ) -> str:
        """
        Apply consistency rules to maintain persona voice.
        
        Args:
            text: The text to be spoken
            persona: The persona configuration
            previous_interactions: Recent interactions for context
            
        Returns:
            Text adjusted for consistency
        """
        # Persona-specific adjustments
        if persona.persona_type == PersonaType.BRITISH_GUARDIAN:
            text = self._apply_british_consistency(text)
        elif persona.persona_type == PersonaType.INDIAN_MYSTIC:
            text = self._apply_mystic_consistency(text)
        elif persona.persona_type == PersonaType.SOUTHERN_SAGE:
            text = self._apply_southern_consistency(text)
        elif persona.persona_type == PersonaType.CHALLENGER:
            text = self._apply_challenger_consistency(text)
        
        return text
    
    def _apply_british_consistency(self, text: str) -> str:
        """Ensure British English consistency."""
        # American to British replacements
        replacements = {
            "realize": "realise",
            "organize": "organise",
            "color": "colour",
            "favor": "favour",
            "center": "centre",
            "defense": "defence",
            "analyze": "analyse"
        }
        
        for american, british in replacements.items():
            text = text.replace(american, british)
            text = text.replace(american.capitalize(), british.capitalize())
        
        return text
    
    def _apply_mystic_consistency(self, text: str) -> str:
        """Ensure contemplative pacing."""
        # Add pauses at meaningful points
        text = text.replace(". ", ". ... ")
        text = text.replace("? ", "? ... ")
        
        # Soften directive language
        text = text.replace("You should", "Perhaps you might")
        text = text.replace("You must", "You may find it helpful to")
        
        return text
    
    def _apply_southern_consistency(self, text: str) -> str:
        """Ensure authentic Southern voice."""
        # Add natural contractions
        text = text.replace("going to", "gonna")
        text = text.replace("want to", "wanna")
        text = text.replace("isn't", "ain't")  # Used sparingly
        
        return text
    
    def _apply_challenger_consistency(self, text: str) -> str:
        """Ensure sharp, contemporary voice."""
        # Add emphasis markers
        text = text.replace("really", "*really*")
        text = text.replace("seriously", "*seriously*")
        
        return text


# Example usage function
def get_persona_for_context(
    context: str,
    **kwargs
) -> Tuple[PersonaConfig, str]:
    """
    Get the appropriate persona and system prompt for a given context.
    
    Args:
        context: The context type for the interaction
        **kwargs: Additional context parameters
        
    Returns:
        Tuple of (PersonaConfig, formatted_system_prompt)
    """
    selector = PersonaSelector()
    persona = selector.select_persona(context, **kwargs)
    
    # Format system prompt with any dynamic elements
    system_prompt = persona.system_prompt
    
    # Add any context-specific instructions
    if context in persona.context_templates:
        template_info = persona.context_templates[context]
        system_prompt += f"\n\nFor this interaction, focus on: {template_info.get('focus', 'general guidance')}"
        system_prompt += f"\nEnergy level: {template_info.get('energy_level', 'moderate')}"
    
    return persona, system_prompt