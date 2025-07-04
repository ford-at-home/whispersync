# WhisperSync Voice Personas

This directory contains the voice persona system for WhisperSync, providing distinct AI personalities through ElevenLabs voice synthesis.

## 🎭 The Four Personas

### 1. British Guardian 🇬🇧
- **Voice**: Chipper, informative British accent
- **Purpose**: Morning/evening summaries and daily guidance
- **Character**: Like a trusted BBC presenter mixed with a longtime friend
- **Best for**: Daily summaries, task management, celebrations

### 2. Indian Mystic 🧘
- **Voice**: Gentle, poetic with philosophical depth
- **Purpose**: Emotional/diary reflections and spiritual insights
- **Character**: Wise elder with meditation guide qualities
- **Best for**: Emotional processing, life reflections, deeper insights

### 3. Southern Sage 🤠
- **Voice**: Gravelly, grounded Southern drawl
- **Purpose**: Value-based nudges and common-sense guidance
- **Character**: Experienced elder with practical wisdom
- **Best for**: Value conflicts, practical advice, life lessons

### 4. The Challenger 😈
- **Voice**: Sarcastic, combative with sharp wit
- **Purpose**: Calls out contradictions and pushes growth
- **Character**: The friend who loves you enough to call your BS
- **Best for**: Breaking procrastination, accountability, facing truths

## 📁 Directory Structure

```
personas/
├── README.md                    # This file
├── prompts/                     # System prompts and configurations
│   ├── __init__.py             # Package initialization
│   ├── british_guardian.py     # British Guardian persona
│   ├── indian_mystic.py        # Indian Mystic persona
│   ├── southern_sage.py        # Southern Sage persona
│   ├── challenger.py           # The Challenger persona
│   ├── persona_config.py       # Master configuration and selection
│   └── usage_guide.py          # Examples and integration patterns
└── (future additions)
    ├── voice_synthesis/        # ElevenLabs integration
    ├── persona_memory/         # Persona-specific memories
    └── adaptation/             # Learning and adaptation logic
```

## 🚀 Quick Start

### Basic Usage

```python
from personas.prompts import PersonaSelector, get_persona_for_context

# Get persona for morning summary
persona, system_prompt = get_persona_for_context(
    context="morning_summary",
    time_of_day="morning",
    user_state={"energy": "moderate"}
)

# Use the system prompt with your LLM
response = llm.generate(
    system_prompt=system_prompt,
    user_input="Give me my morning summary"
)
```

### Agent Integration

```python
from personas.prompts import PersonaSelector, PersonaType

class ExecutiveAgent:
    def __init__(self):
        self.persona_selector = PersonaSelector()
    
    def generate_summary(self, context):
        # Select appropriate persona
        persona = self.persona_selector.select_persona(
            context_type="daily_summary",
            agent_type="ExecutiveAgent",
            time_of_day=context.get("time"),
            emotional_tone=context.get("mood")
        )
        
        # Use persona for response generation
        return self.create_response_with_persona(persona)
```

## 🎯 Persona Selection Logic

The system intelligently selects personas based on:

1. **Context Type**: What kind of interaction is needed
2. **Time of Day**: Morning energy vs evening reflection
3. **Emotional State**: High-intensity emotions trigger specific personas
4. **Agent Type**: Each agent has preferred personas
5. **User History**: Past interactions influence selection

### Selection Priority

1. Emotional overrides (e.g., grief → Indian Mystic)
2. Context-specific mappings
3. Agent preferences
4. Time-based adjustments
5. Default fallbacks

## 🔧 Configuration

### Voice Settings

Each persona has specific ElevenLabs voice settings:

```python
"voice_settings": {
    "stability": 0.75,        # Voice consistency
    "similarity_boost": 0.80, # Match target voice
    "style": 0.6,            # Style strength
    "use_speaker_boost": True # Enhanced clarity
}
```

### Context Templates

Personas include templates for common situations:

```python
BRITISH_GUARDIAN_CONTEXT_INJECTION = {
    "morning_summary": {
        "energy_level": "bright",
        "focus": "forward_looking",
        "template": "Good morning! It's {time}..."
    }
}
```

## 🎨 Customization

### Adding Context Templates

```python
# In persona file (e.g., british_guardian.py)
BRITISH_GUARDIAN_CONTEXT_INJECTION["new_context"] = {
    "energy_level": "moderate",
    "focus": "specific_purpose",
    "template": "Your template here..."
}
```

### Adjusting Personality Rules

Each persona has 10 core rules that define its behavior. Modify these in the respective persona file:

```python
BRITISH_GUARDIAN_PERSONALITY_RULES = """
1. ALWAYS maintain British English spelling
2. Use time-appropriate energy
...
"""
```

## 🧪 Testing Personas

### Example Test

```python
from personas.prompts.usage_guide import PersonaUsageExamples

# Test morning summary
result = PersonaUsageExamples.morning_summary_example()
print(f"Persona: {result['persona']}")
print(f"Response: {result['response']}")
```

### Voice Consistency Check

```python
from personas.prompts import PersonaConsistencyManager

manager = PersonaConsistencyManager()
text = "I realize this might favor your organization"
british_text = manager._apply_british_consistency(text)
# Output: "I realise this might favour your organisation"
```

## 🔊 ElevenLabs Integration

### Voice IDs

Replace placeholder IDs in `persona_config.py`:

```python
"elevenlabs_voice_id": "actual_voice_id_here"
```

### Voice Synthesis

```python
# Pseudo-code for ElevenLabs integration
voice_output = elevenlabs_client.synthesize(
    text=response,
    voice_id=persona.elevenlabs_voice_id,
    voice_settings=persona.voice_settings
)
```

## 📚 Best Practices

1. **Persona Consistency**: Don't switch personas mid-conversation unless necessary
2. **Emotional Awareness**: Let emotional context override default selections
3. **Time Sensitivity**: Adjust energy levels based on time of day
4. **Cultural Sensitivity**: Ensure personas remain respectful and authentic
5. **Fallback Grace**: Always have appropriate fallback responses

## 🔮 Future Enhancements

- [ ] Persona adaptation based on user feedback
- [ ] Custom persona creation interface
- [ ] Multi-language persona variants
- [ ] Emotional state learning
- [ ] Voice cloning for personalization
- [ ] Real-time voice modulation
- [ ] Persona interaction memories

## 🤝 Contributing

When adding new personas:

1. Create a new file in `prompts/` following the existing pattern
2. Define all required components (system prompt, contexts, examples, etc.)
3. Add to `persona_config.py` registry
4. Update `__init__.py` exports
5. Add usage examples to `usage_guide.py`
6. Test voice consistency and selection logic

Remember: Each persona should be distinct, memorable, and serve a clear purpose in the user's journey.