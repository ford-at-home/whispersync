"""
Usage Guide and Examples for Voice Personas

This module provides practical examples of how to use the voice personas
in various contexts within the WhisperSync system.
"""

from typing import Dict, Any
from datetime import datetime
import json

from .persona_config import PersonaSelector, PersonaConsistencyManager, PersonaType


class PersonaUsageExamples:
    """Examples of persona usage in different scenarios."""
    
    @staticmethod
    def morning_summary_example():
        """Example: British Guardian delivering a morning summary."""
        
        # Context setup
        context = {
            "time": "7:00 AM",
            "day_of_week": "Tuesday",
            "weather_desc": "crisp autumn",
            "user_name": "William",
            "tasks_today": [
                "Team standup at 9 AM",
                "Code review for authentication module",
                "Lunch with Sarah at noon",
                "Quarterly planning meeting at 3 PM"
            ],
            "completed_yesterday": 5,
            "energy_level": "moderate"
        }
        
        # Get persona
        selector = PersonaSelector()
        persona = selector.select_persona(
            context_type="morning_summary",
            time_of_day="morning",
            user_state={"energy": context["energy_level"]}
        )
        
        # Format response using template
        template = persona.context_templates["morning_summary"]["template"]
        
        response = template.format(
            time=context["time"],
            weather_desc=context["weather_desc"],
            day_of_week=context["day_of_week"],
            greeting_personalization=f"I hope you're feeling refreshed after completing {context['completed_yesterday']} tasks yesterday!",
            priority_items="First up, you've got your team standup at 9 - perfect time to share yesterday's progress.\nThe code review this morning should be straightforward.",
            calendar_summary="Your afternoon's quite full with that quarterly planning meeting, but lunch with Sarah should be a nice break.",
            gentle_reminders="Oh, and remember to prepare those quarterly metrics - the team will want to see them.",
            motivational_closing="You've got a good rhythm going this week"
        )
        
        return {
            "persona": persona.persona_type.value,
            "response": response,
            "voice_settings": persona.voice_settings,
            "energy_level": "bright"
        }
    
    @staticmethod
    def emotional_diary_example():
        """Example: Indian Mystic processing emotional diary entry."""
        
        # Context setup
        context = {
            "diary_entry": "I feel so lost today. The project failed and I don't know if I'm cut out for this.",
            "detected_emotions": ["self-doubt", "disappointment", "confusion"],
            "emotional_intensity": 0.8,
            "time_of_day": "evening"
        }
        
        # Get persona
        selector = PersonaSelector()
        persona = selector.select_persona(
            context_type="emotional_processing",
            emotional_tone="self-doubt",
            time_of_day=context["time_of_day"]
        )
        
        # Format response
        template = persona.context_templates["emotional_processing"]["template"]
        
        response = template.format(
            acknowledgment_of_feeling="I hear the weight of disappointment in your words, the questioning that comes when our efforts don't bloom as expected.",
            normalizing_statement="You know, even the mightiest rivers sometimes lose their way, creating new paths through unexpected terrain.",
            gentle_exploration="What if this moment of feeling lost is actually the beginning of finding a truer path?",
            reframing_perspective="The project may have ended differently than hoped, but the learning, the growth, the courage to try - these remain with you, like seeds waiting for their season.",
            self_compassion_reminder="Remember, my friend, that being 'cut out' for something isn't fixed in stone. We are all rivers, constantly shaping and being shaped by our journey."
        )
        
        return {
            "persona": persona.persona_type.value,
            "response": response,
            "voice_settings": persona.voice_settings,
            "pacing": "slow with meaningful pauses"
        }
    
    @staticmethod
    def value_guidance_example():
        """Example: Southern Sage providing value-based guidance."""
        
        # Context setup
        context = {
            "situation": "User considering cutting corners on a project to meet deadline",
            "value_conflict": "integrity vs. expediency",
            "user_history": "usually values quality work"
        }
        
        # Get persona
        selector = PersonaSelector()
        persona = selector.select_persona(
            context_type="value_guidance",
            user_state={"conflict": context["value_conflict"]}
        )
        
        # Format response
        template = persona.context_templates["value_reminder"]["template"]
        
        response = template.format(
            acknowledgment_opener="I hear you're in a tight spot with that deadline",
            situation_observation="Seems like you're thinking about taking a shortcut or two to get it done on time.",
            value_connection="Now, I've known you long enough to know you take pride in your work. That's something your daddy would've respected.",
            practical_wisdom="Here's the thing - shortcuts have a way of turning into long roads. What you save today, you'll likely pay for tomorrow with interest.",
            story_or_saying="My granddaddy used to say, 'A job worth doing is worth doing right.' Course, he also said 'Done is better than perfect' when it mattered.",
            actionable_advice="How about this - identify what absolutely has to be perfect, and what can be 'good enough' for now. Then circle back when you can.",
            encouragement_close="Your reputation's built on solid work. Don't let one deadline change that."
        )
        
        return {
            "persona": persona.persona_type.value,
            "response": response,
            "voice_settings": persona.voice_settings,
            "tone": "firm but understanding"
        }
    
    @staticmethod
    def contradiction_challenge_example():
        """Example: The Challenger calling out contradictory behavior."""
        
        # Context setup
        context = {
            "stated_goal": "I want to get in shape",
            "actual_behavior": "Haven't exercised in 3 weeks, ordered takeout 5 times this week",
            "pattern_history": "This is the 4th time starting this goal this year",
            "excuse_given": "I've just been too busy with work"
        }
        
        # Get persona
        selector = PersonaSelector()
        persona = selector.select_persona(
            context_type="contradiction_check",
            emotional_tone="excuse_making"
        )
        
        # Format response
        template = persona.context_templates["calling_out_contradiction"]["template"]
        
        response = template.format(
            sarcastic_opener="Oh, this is FASCINATING.",
            contradiction_highlight=f"So you want to get in shape, but you've ordered takeout five times this week and haven't moved more than from couch to fridge in three weeks?",
            rhetorical_question="Tell me, how exactly does that math work in your universe?",
            pattern_observation="And let's not pretend this is new - this is literally the FOURTH time this year you've had this 'epiphany.'",
            reality_check=f"'Too busy with work' - really? The same work you had when you binged that entire series last weekend?",
            challenge_statement="Here's a wild thought: What if you spent even HALF the time you spend making excuses actually, I don't know, doing a pushup?",
            growth_nudge="Look, I'm not saying you need to become a fitness influencer. But maybe, just maybe, admit you don't actually want this as much as you claim. Or prove me wrong. Your choice."
        )
        
        return {
            "persona": persona.persona_type.value,
            "response": response,
            "voice_settings": persona.voice_settings,
            "delivery": "sharp with dramatic pauses"
        }


class PersonaIntegrationPatterns:
    """Patterns for integrating personas with WhisperSync agents."""
    
    @staticmethod
    def agent_persona_mapping() -> Dict[str, Dict[str, Any]]:
        """Map agents to their preferred personas and contexts."""
        
        return {
            "ExecutiveAgent": {
                "primary_personas": [PersonaType.BRITISH_GUARDIAN, PersonaType.CHALLENGER],
                "context_mappings": {
                    "daily_summary": PersonaType.BRITISH_GUARDIAN,
                    "goal_accountability": PersonaType.CHALLENGER,
                    "achievement_celebration": PersonaType.BRITISH_GUARDIAN,
                    "excuse_detection": PersonaType.CHALLENGER
                },
                "time_preferences": {
                    "morning": PersonaType.BRITISH_GUARDIAN,
                    "evening": PersonaType.BRITISH_GUARDIAN,
                    "midday": PersonaType.CHALLENGER
                }
            },
            "SpiritualAgent": {
                "primary_personas": [PersonaType.INDIAN_MYSTIC, PersonaType.SOUTHERN_SAGE],
                "context_mappings": {
                    "diary_reflection": PersonaType.INDIAN_MYSTIC,
                    "life_guidance": PersonaType.SOUTHERN_SAGE,
                    "emotional_support": PersonaType.INDIAN_MYSTIC,
                    "value_alignment": PersonaType.SOUTHERN_SAGE
                },
                "emotional_overrides": {
                    "high_distress": PersonaType.INDIAN_MYSTIC,
                    "moral_conflict": PersonaType.SOUTHERN_SAGE
                }
            },
            "GitHubAgent": {
                "primary_personas": [PersonaType.BRITISH_GUARDIAN, PersonaType.CHALLENGER],
                "context_mappings": {
                    "idea_excitement": PersonaType.BRITISH_GUARDIAN,
                    "procrastination_check": PersonaType.CHALLENGER,
                    "project_planning": PersonaType.BRITISH_GUARDIAN,
                    "commitment_push": PersonaType.CHALLENGER
                }
            },
            "MemoryAgent": {
                "primary_personas": [PersonaType.INDIAN_MYSTIC, PersonaType.BRITISH_GUARDIAN],
                "context_mappings": {
                    "memory_capture": PersonaType.INDIAN_MYSTIC,
                    "memory_summary": PersonaType.BRITISH_GUARDIAN,
                    "emotional_memory": PersonaType.INDIAN_MYSTIC,
                    "factual_memory": PersonaType.BRITISH_GUARDIAN
                }
            }
        }
    
    @staticmethod
    def dynamic_persona_selection(
        agent_type: str,
        context: Dict[str, Any]
    ) -> PersonaType:
        """
        Dynamically select persona based on agent and context.
        
        Args:
            agent_type: The type of agent making the request
            context: Current context including user state, time, emotion
            
        Returns:
            Selected PersonaType
        """
        mapping = PersonaIntegrationPatterns.agent_persona_mapping()
        agent_config = mapping.get(agent_type, {})
        
        # Check for emotional overrides first
        if "emotional_state" in context and "emotional_overrides" in agent_config:
            for emotion, persona in agent_config["emotional_overrides"].items():
                if emotion in context["emotional_state"]:
                    return persona
        
        # Check context-specific mappings
        if "context_type" in context and "context_mappings" in agent_config:
            if context["context_type"] in agent_config["context_mappings"]:
                return agent_config["context_mappings"][context["context_type"]]
        
        # Check time-based preferences
        if "time_of_day" in context and "time_preferences" in agent_config:
            time_period = PersonaIntegrationPatterns._get_time_period(context["time_of_day"])
            if time_period in agent_config["time_preferences"]:
                return agent_config["time_preferences"][time_period]
        
        # Default to primary persona
        if "primary_personas" in agent_config and agent_config["primary_personas"]:
            return agent_config["primary_personas"][0]
        
        # Final fallback
        return PersonaType.BRITISH_GUARDIAN
    
    @staticmethod
    def _get_time_period(time_str: str) -> str:
        """Convert time to period (morning, midday, evening)."""
        try:
            hour = datetime.strptime(time_str, "%H:%M").hour
            if hour < 12:
                return "morning"
            elif hour < 17:
                return "midday"
            else:
                return "evening"
        except:
            return "midday"


class PersonaPromptEngineering:
    """Advanced prompt engineering techniques for personas."""
    
    @staticmethod
    def enhance_with_context(
        base_prompt: str,
        user_context: Dict[str, Any]
    ) -> str:
        """
        Enhance base persona prompt with user-specific context.
        
        Args:
            base_prompt: The base system prompt for the persona
            user_context: User-specific context to inject
            
        Returns:
            Enhanced prompt with context
        """
        context_additions = []
        
        # Add user preference context
        if "user_preferences" in user_context:
            prefs = user_context["user_preferences"]
            context_additions.append(
                f"\nUser Preferences:"
                f"\n- Communication style: {prefs.get('communication_style', 'balanced')}"
                f"\n- Humor tolerance: {prefs.get('humor_level', 'moderate')}"
                f"\n- Directness preference: {prefs.get('directness', 'moderate')}"
            )
        
        # Add historical context
        if "interaction_history" in user_context:
            history = user_context["interaction_history"]
            context_additions.append(
                f"\nRecent Context:"
                f"\n- Previous topic: {history.get('last_topic', 'general')}"
                f"\n- Mood trend: {history.get('mood_trend', 'stable')}"
                f"\n- Engagement level: {history.get('engagement', 'normal')}"
            )
        
        # Add current state
        if "current_state" in user_context:
            state = user_context["current_state"]
            context_additions.append(
                f"\nCurrent State:"
                f"\n- Energy level: {state.get('energy', 'moderate')}"
                f"\n- Stress indicators: {state.get('stress', 'normal')}"
                f"\n- Time pressure: {state.get('time_pressure', 'relaxed')}"
            )
        
        # Combine base prompt with context
        enhanced_prompt = base_prompt
        if context_additions:
            enhanced_prompt += "\n\n### Dynamic Context ###"
            enhanced_prompt += "".join(context_additions)
            enhanced_prompt += "\n\nAdjust your responses based on this context while maintaining your core personality."
        
        return enhanced_prompt
    
    @staticmethod
    def create_voice_modulation_instructions(
        persona_type: PersonaType,
        emotional_context: str
    ) -> Dict[str, Any]:
        """
        Create specific voice modulation instructions for ElevenLabs.
        
        Args:
            persona_type: The persona being used
            emotional_context: The emotional context of the interaction
            
        Returns:
            Voice modulation parameters
        """
        base_settings = {
            PersonaType.BRITISH_GUARDIAN: {
                "base_stability": 0.75,
                "base_clarity": 0.85,
                "base_warmth": 0.7
            },
            PersonaType.INDIAN_MYSTIC: {
                "base_stability": 0.90,
                "base_clarity": 0.70,
                "base_warmth": 0.95
            },
            PersonaType.SOUTHERN_SAGE: {
                "base_stability": 0.85,
                "base_clarity": 0.75,
                "base_warmth": 0.80
            },
            PersonaType.CHALLENGER: {
                "base_stability": 0.65,
                "base_clarity": 0.90,
                "base_warmth": 0.40
            }
        }
        
        emotional_adjustments = {
            "supportive": {"warmth": +0.1, "stability": +0.05},
            "challenging": {"clarity": +0.1, "stability": -0.1},
            "celebratory": {"warmth": +0.15, "stability": -0.15},
            "contemplative": {"stability": +0.1, "clarity": -0.05},
            "urgent": {"clarity": +0.15, "stability": -0.05}
        }
        
        # Get base settings
        settings = base_settings[persona_type].copy()
        
        # Apply emotional adjustments
        if emotional_context in emotional_adjustments:
            adjustments = emotional_adjustments[emotional_context]
            for param, adjustment in adjustments.items():
                if param in settings:
                    settings[param] = max(0, min(1, settings[param] + adjustment))
        
        return {
            "voice_modulation": settings,
            "emotional_context": emotional_context,
            "prosody_hints": PersonaPromptEngineering._get_prosody_hints(persona_type, emotional_context)
        }
    
    @staticmethod
    def _get_prosody_hints(persona_type: PersonaType, emotional_context: str) -> List[str]:
        """Get prosody hints for voice synthesis."""
        hints = []
        
        if persona_type == PersonaType.BRITISH_GUARDIAN:
            hints.extend(["clear articulation", "upward inflection on questions", "crisp consonants"])
        elif persona_type == PersonaType.INDIAN_MYSTIC:
            hints.extend(["gentle flow", "soft consonants", "extended vowels on key words"])
        elif persona_type == PersonaType.SOUTHERN_SAGE:
            hints.extend(["relaxed pace", "slight drawl", "emphasis through pauses"])
        elif persona_type == PersonaType.CHALLENGER:
            hints.extend(["sharp delivery", "emphasis through speed changes", "dramatic pauses"])
        
        if emotional_context == "supportive":
            hints.append("warm undertones")
        elif emotional_context == "challenging":
            hints.append("pointed delivery")
        
        return hints


# Example of full integration
def demonstrate_full_integration():
    """Demonstrate complete persona integration flow."""
    
    # 1. Initial context
    user_context = {
        "agent_type": "ExecutiveAgent",
        "context_type": "daily_summary",
        "time_of_day": "07:30",
        "user_state": {
            "energy": "low",
            "recent_success": False,
            "pending_tasks": 12
        },
        "user_preferences": {
            "communication_style": "encouraging",
            "humor_level": "light",
            "directness": "moderate"
        }
    }
    
    # 2. Select persona
    selector = PersonaSelector()
    persona = selector.select_persona(
        context_type=user_context["context_type"],
        time_of_day="morning",
        user_state=user_context["user_state"],
        agent_type=user_context["agent_type"]
    )
    
    # 3. Enhance prompt with context
    enhanced_prompt = PersonaPromptEngineering.enhance_with_context(
        persona.system_prompt,
        user_context
    )
    
    # 4. Get voice modulation settings
    voice_settings = PersonaPromptEngineering.create_voice_modulation_instructions(
        persona.persona_type,
        "supportive"  # Due to low energy
    )
    
    # 5. Apply consistency rules
    consistency_manager = PersonaConsistencyManager()
    sample_text = "Good morning! I see you have quite a few tasks today."
    consistent_text = consistency_manager.apply_consistency_rules(
        sample_text,
        persona
    )
    
    return {
        "selected_persona": persona.persona_type.value,
        "enhanced_prompt": enhanced_prompt,
        "voice_settings": voice_settings,
        "formatted_text": consistent_text,
        "elevenlabs_config": {
            "voice_id": persona.elevenlabs_voice_id,
            "model_id": persona.voice_settings["model_id"],
            "voice_settings": {
                **persona.voice_settings,
                **voice_settings["voice_modulation"]
            }
        }
    }


if __name__ == "__main__":
    # Run examples
    print("=== Morning Summary Example ===")
    print(json.dumps(PersonaUsageExamples.morning_summary_example(), indent=2))
    
    print("\n=== Full Integration Demo ===")
    print(json.dumps(demonstrate_full_integration(), indent=2))