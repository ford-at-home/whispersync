"""Comprehensive Prompt Engineering Templates for WhisperSync.

This module contains optimized prompt templates for various AI tasks across
the WhisperSync system. Each template is carefully crafted for Claude 3.5 Sonnet
with specific techniques for maximum effectiveness.

PROMPT ENGINEERING PRINCIPLES:
1. Clear Task Definition: Explicit instructions with examples
2. Structured Output: JSON formatting for reliable parsing
3. Context Awareness: Include relevant background information
4. Error Handling: Graceful degradation instructions
5. Safety Boundaries: Built-in ethical constraints
6. Few-Shot Learning: Examples for complex tasks
7. Chain-of-Thought: Step-by-step reasoning where beneficial

WHY CENTRALIZED PROMPTS:
- Consistency across all AI interactions
- Easy optimization and A/B testing
- Version control for prompt evolution
- Reusability across different contexts
- Performance monitoring per template
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from string import Template
from enum import Enum

class PromptCategory(Enum):
    """Categories of prompts in the system."""
    
    CLASSIFICATION = "classification"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    REASONING = "reasoning"
    EXTRACTION = "extraction"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    PERSONALIZATION = "personalization"


@dataclass
class PromptTemplate:
    """Structured prompt template with metadata."""
    
    template_id: str
    name: str
    category: PromptCategory
    description: str
    
    # Template components
    system_context: str
    task_instruction: str
    input_format: str
    output_format: str
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    # Configuration
    temperature: float = 0.3
    max_tokens: int = 2000
    stop_sequences: List[str] = field(default_factory=list)
    
    # Performance tracking
    avg_latency_ms: Optional[float] = None
    success_rate: Optional[float] = None
    version: str = "1.0"


class PromptLibrary:
    """Central library of all prompt templates."""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize all prompt templates."""
        
        # Transcript Classification
        self.templates["transcript_classification"] = PromptTemplate(
            template_id="transcript_classification",
            name="Advanced Transcript Classification",
            category=PromptCategory.CLASSIFICATION,
            description="Comprehensive multi-dimensional transcript analysis",
            system_context="""You are an advanced transcript analysis system specializing in understanding voice memos.
Your role is to analyze transcripts across multiple dimensions to enable intelligent routing and processing.
You have deep understanding of human communication patterns, emotional nuance, and contextual cues.""",
            task_instruction="""Analyze the provided voice transcript across these dimensions:

1. PRIMARY INTENT - The fundamental goal the user is trying to achieve
2. CONTENT TYPES - Categories of content present (can be multiple)
3. EMOTIONAL TONE - The emotional context and state
4. COMPLEXITY LEVEL - How complex the processing requirements are
5. TEMPORAL FOCUS - The time orientation of the content
6. KEY ENTITIES - Important people, places, projects, or concepts
7. THEMES - Core topics or areas of focus
8. SUGGESTED ACTIONS - What the system should do with this information
9. ROUTING RECOMMENDATION - Which agent(s) should process this
10. USER STATE INDICATORS - What this reveals about the user's current state
11. ANOMALY FLAGS - Any unusual patterns or concerning indicators""",
            input_format="""Transcript: "${transcript}"

${context_info}""",
            output_format="""{
    "primary_intent": "documentation|reflection|ideation|planning|problem_solving|social|learning|creative",
    "content_types": ["work_task", "personal_memory", "technical_idea", etc.],
    "emotional_tone": "excited|content|neutral|frustrated|anxious|reflective|celebratory|melancholic",
    "complexity": "simple|moderate|complex|highly_complex",
    "temporal_focus": "past|present|future|timeless",
    "confidence_scores": {
        "intent": 0.0-1.0,
        "emotion": 0.0-1.0,
        "complexity": 0.0-1.0
    },
    "key_entities": [
        {"type": "person|place|project|concept", "name": "...", "significance": "..."}
    ],
    "themes": ["theme1", "theme2", ...],
    "suggested_actions": [
        {"action": "...", "reason": "...", "priority": "high|medium|low"}
    ],
    "routing_recommendation": {
        "primary_agent": "work|memory|github|multiple",
        "secondary_agents": [],
        "processing_strategy": "standard|parallel|sequential|conditional"
    },
    "user_state_indicators": {
        "stress_level": 0.0-1.0,
        "energy_level": 0.0-1.0,
        "focus_area": "...",
        "emotional_needs": "..."
    },
    "anomaly_flags": ["flag1", "flag2", ...]
}""",
            examples=[
                {
                    "input": "I just had the most amazing meeting with Sarah about the new product launch. We're going to revolutionize how people think about task management. I need to remember to follow up with the design team tomorrow.",
                    "output": {
                        "primary_intent": "documentation",
                        "content_types": ["work_task", "planning", "social_interaction"],
                        "emotional_tone": "excited",
                        "complexity": "moderate",
                        "key_entities": [
                            {"type": "person", "name": "Sarah", "significance": "meeting participant"},
                            {"type": "project", "name": "product launch", "significance": "main topic"}
                        ]
                    }
                }
            ],
            temperature=0.3,
            max_tokens=2500
        )
        
        # Emotional Analysis
        self.templates["emotional_analysis"] = PromptTemplate(
            template_id="emotional_analysis",
            name="Deep Emotional Analysis",
            category=PromptCategory.ANALYSIS,
            description="Comprehensive emotional intelligence analysis",
            system_context="""You are an emotional intelligence expert with deep understanding of human psychology.
You analyze voice transcripts to understand emotional states, needs, and trajectories.
Your analysis helps provide appropriate support and responses.""",
            task_instruction="""Perform a deep emotional analysis of this voice transcript:

1. Identify PRIMARY EMOTIONS using Plutchik's wheel (rate 0.0-1.0 for each):
   - Joy, Trust, Fear, Surprise, Sadness, Disgust, Anger, Anticipation

2. Identify SECONDARY EMOTIONS (combinations):
   - Love (joy+trust), Awe (fear+surprise), Remorse (sadness+disgust), etc.

3. Assess EMOTIONAL COMPLEXITY:
   - Clarity: How clear vs mixed/conflicted the emotions are
   - Intensity: Overall strength of emotions
   - Stability: How stable vs volatile

4. Provide DEEPER INSIGHTS:
   - Underlying emotional needs
   - Potential triggers mentioned
   - Coping mechanisms being used
   - Stress indicators present
   - Subtext and unexpressed emotions

5. CONTEXTUAL UNDERSTANDING:
   - Why they might be feeling this way
   - What support might be helpful
   - Any concerning patterns""",
            input_format="""Transcript: "${transcript}"

Linguistic Analysis: ${linguistic_analysis}

Context: ${context}""",
            output_format="""{
    "primary_emotions": {
        "joy": 0.0-1.0,
        "trust": 0.0-1.0,
        "fear": 0.0-1.0,
        "surprise": 0.0-1.0,
        "sadness": 0.0-1.0,
        "disgust": 0.0-1.0,
        "anger": 0.0-1.0,
        "anticipation": 0.0-1.0
    },
    "secondary_emotions": {
        "love": 0.0-1.0,
        "awe": 0.0-1.0,
        "remorse": 0.0-1.0,
        "optimism": 0.0-1.0,
        "submission": 0.0-1.0
    },
    "emotional_complexity": {
        "clarity": 0.0-1.0,
        "intensity": 0.0-1.0,
        "stability": 0.0-1.0
    },
    "deeper_insights": {
        "emotional_needs": ["need1", "need2"],
        "triggers": ["trigger1", "trigger2"],
        "coping_mechanisms": ["mechanism1", "mechanism2"],
        "stress_indicators": ["indicator1", "indicator2"],
        "unexpressed_emotions": ["emotion1", "emotion2"]
    },
    "contextual_understanding": {
        "probable_causes": ["cause1", "cause2"],
        "support_recommendations": ["recommendation1", "recommendation2"],
        "concerning_patterns": ["pattern1", "pattern2"]
    }
}""",
            temperature=0.3,
            max_tokens=2000
        )
        
        # User Pattern Analysis
        self.templates["user_pattern_analysis"] = PromptTemplate(
            template_id="user_pattern_analysis",
            name="User Behavior Pattern Analysis",
            category=PromptCategory.REASONING,
            description="Identify patterns and predict user behavior",
            system_context="""You are a behavioral analysis expert specializing in understanding user patterns.
You identify recurring behaviors, predict future actions, and provide insights for personalization.
Your analysis respects user privacy while providing valuable insights.""",
            task_instruction="""Analyze this user's interaction history to identify patterns and make predictions:

1. BEHAVIORAL PATTERNS:
   - Recurring themes or topics
   - Typical interaction times
   - Communication style preferences
   - Workflow patterns

2. EMOTIONAL PATTERNS:
   - Mood cycles or trajectories
   - Stress triggers and patterns
   - Positive reinforcement sources

3. PREDICTIONS:
   - Likely next actions or topics
   - Optimal interaction times
   - Potential needs or challenges

4. PERSONALIZATION INSIGHTS:
   - Communication style adjustments
   - Timing recommendations
   - Support strategies

5. ANOMALY DETECTION:
   - Unusual patterns
   - Potential concerns
   - Changes from baseline""",
            input_format="""User History Summary:
${history_summary}

Recent Interactions:
${recent_interactions}

Current State:
${current_state}""",
            output_format="""{
    "behavioral_patterns": [
        {
            "pattern_type": "temporal|topical|workflow|social",
            "description": "...",
            "frequency": "daily|weekly|sporadic",
            "confidence": 0.0-1.0
        }
    ],
    "emotional_patterns": {
        "dominant_emotions": ["emotion1", "emotion2"],
        "mood_cycles": "description",
        "stress_patterns": ["pattern1", "pattern2"],
        "positive_triggers": ["trigger1", "trigger2"]
    },
    "predictions": {
        "next_likely_topics": ["topic1", "topic2"],
        "optimal_interaction_windows": ["morning", "evening"],
        "upcoming_needs": ["need1", "need2"],
        "confidence": 0.0-1.0
    },
    "personalization_recommendations": {
        "communication_style": "formal|casual|supportive|direct",
        "preferred_response_length": "brief|moderate|detailed",
        "emotional_support_level": "minimal|moderate|high",
        "proactivity": "reactive|balanced|proactive"
    },
    "anomaly_flags": [
        {
            "type": "behavioral|emotional|temporal",
            "description": "...",
            "severity": "low|medium|high",
            "recommendation": "..."
        }
    ]
}""",
            temperature=0.4,
            max_tokens=2500
        )
        
        # Multi-Agent Synthesis
        self.templates["multi_agent_synthesis"] = PromptTemplate(
            template_id="multi_agent_synthesis",
            name="Multi-Agent Result Synthesis",
            category=PromptCategory.SYNTHESIS,
            description="Synthesize outputs from multiple agents into coherent summary",
            system_context="""You are a master synthesizer who combines outputs from multiple specialized agents.
Your role is to create coherent, actionable summaries that capture the essence of all agent contributions.
You identify connections, resolve conflicts, and provide unified recommendations.""",
            task_instruction="""Synthesize these multi-agent processing results:

1. KEY FINDINGS:
   - Identify the most important discoveries from each agent
   - Highlight surprising or significant insights

2. CONNECTIONS:
   - Find relationships between different agent outputs
   - Identify reinforcing or complementary insights

3. CONFLICT RESOLUTION:
   - Identify any conflicting information
   - Provide reasoned resolution or explanation

4. UNIFIED RECOMMENDATIONS:
   - Combine agent recommendations into coherent action plan
   - Prioritize based on impact and feasibility

5. SUMMARY:
   - Create a brief, coherent narrative of the overall outcome
   - Ensure it's understandable to the end user""",
            input_format="""Agent Outputs:
${agent_outputs}

Original Context:
${original_context}""",
            output_format="""{
    "key_findings": [
        {
            "agent": "agent_name",
            "finding": "...",
            "significance": "high|medium|low"
        }
    ],
    "connections": [
        {
            "agents": ["agent1", "agent2"],
            "connection_type": "reinforces|complements|extends",
            "description": "..."
        }
    ],
    "resolutions": [
        {
            "conflict": "description of conflict",
            "resolution": "how it was resolved",
            "confidence": 0.0-1.0
        }
    ],
    "unified_recommendations": [
        {
            "action": "...",
            "reason": "...",
            "priority": "high|medium|low",
            "contributing_agents": ["agent1", "agent2"]
        }
    ],
    "executive_summary": "Brief narrative summary for the user"
}""",
            temperature=0.5,
            max_tokens=3000
        )
        
        # Persona Voice Generation
        self.templates["persona_voice_generation"] = PromptTemplate(
            template_id="persona_voice_generation",
            name="Persona-Based Response Generation",
            category=PromptCategory.GENERATION,
            description="Generate responses in specific persona voices",
            system_context="""You are a voice synthesis expert who can embody different personas.
You maintain consistent personality traits while communicating information naturally.
Each persona has unique characteristics that must shine through in the response.""",
            task_instruction="""Transform this content into the specified persona's voice:

PERSONA CHARACTERISTICS:
${persona_description}

GUIDELINES:
1. Maintain the persona's unique voice and style consistently
2. Communicate the content clearly without losing meaning
3. Use appropriate emotional tone for the persona
4. Include signature phrases or speech patterns if relevant
5. Adjust vocabulary and sentence structure to match persona
6. Ensure the response feels natural and authentic""",
            input_format="""Content to communicate:
"${content}"

Context: ${context}

Persona Details:
${persona_details}""",
            output_format="""Generate the response directly in the persona's voice.
Do not include any meta-commentary or explanations.
The response should feel like it's naturally coming from the persona.""",
            temperature=0.7,  # Higher for personality
            max_tokens=1500
        )
        
        # Learning Extraction
        self.templates["learning_extraction"] = PromptTemplate(
            template_id="learning_extraction",
            name="Learning Extraction from Feedback",
            category=PromptCategory.EXTRACTION,
            description="Extract actionable learnings from user feedback",
            system_context="""You are a learning specialist who extracts valuable insights from user feedback.
You identify what went wrong or right, why it happened, and how to improve.
Your analysis enables continuous system improvement.""",
            task_instruction="""Analyze this user feedback to extract learnings:

1. WHAT HAPPENED:
   - Identify specifically what went wrong or right
   - Distinguish between user preference and system error

2. ROOT CAUSE ANALYSIS:
   - Why did the system respond this way?
   - What assumptions or rules led to this outcome?

3. LEARNING EXTRACTION:
   - What specific lesson can be learned?
   - Is this a one-off issue or systematic?

4. IMPROVEMENT STRATEGY:
   - How can similar issues be prevented?
   - What specific changes would help?

5. CONFIDENCE ASSESSMENT:
   - How confident are we in this learning?
   - What additional data would increase confidence?""",
            input_format="""Interaction Context:
${interaction_context}

User Feedback:
${user_feedback}

System Response That Triggered Feedback:
${system_response}""",
            output_format="""{
    "what_happened": {
        "issue_type": "error|misunderstanding|preference|success",
        "specific_issue": "...",
        "severity": "low|medium|high"
    },
    "root_cause": {
        "primary_cause": "...",
        "contributing_factors": ["factor1", "factor2"],
        "system_assumption": "what the system incorrectly assumed"
    },
    "learning": {
        "lesson": "specific lesson learned",
        "domain": "routing|classification|emotional_response|other",
        "is_systematic": true|false,
        "pattern_description": "if systematic, describe the pattern"
    },
    "improvement_strategy": {
        "immediate_action": "...",
        "long_term_change": "...",
        "validation_method": "how to verify improvement"
    },
    "confidence_assessment": {
        "confidence": 0.0-1.0,
        "reasoning": "why this confidence level",
        "additional_data_needed": ["data1", "data2"]
    }
}""",
            temperature=0.3,
            max_tokens=2000
        )
        
        # Routing Decision
        self.templates["intelligent_routing"] = PromptTemplate(
            template_id="intelligent_routing",
            name="Intelligent Agent Routing",
            category=PromptCategory.REASONING,
            description="Determine optimal agent routing for transcripts",
            system_context="""You are a routing expert who determines the best agent(s) to handle voice transcripts.
You understand the capabilities of each agent and match content to the most appropriate handlers.
Your decisions optimize for accuracy, efficiency, and user satisfaction.""",
            task_instruction="""Determine the optimal routing for this transcript:

AVAILABLE AGENTS:
- work: Professional activities, meetings, tasks, accomplishments
- memory: Personal experiences, emotions, reflections, life events
- github: Project ideas, code concepts, technical innovations

ROUTING STRATEGIES:
- single: One agent handles everything
- parallel: Multiple agents work simultaneously on different aspects
- sequential: Agents process in order, passing results
- conditional: Routing depends on initial analysis

Consider:
1. Content analysis and primary themes
2. Complexity and processing requirements
3. User patterns and preferences
4. Potential for multi-agent value""",
            input_format="""Transcript: "${transcript}"

Classification: ${classification}

User Context: ${user_context}

Recent Routing History: ${routing_history}""",
            output_format="""{
    "routing_decision": {
        "primary_agent": "work|memory|github",
        "secondary_agents": ["agent1", "agent2"],
        "strategy": "single|parallel|sequential|conditional",
        "confidence": 0.0-1.0
    },
    "reasoning": {
        "primary_factors": ["factor1", "factor2"],
        "agent_rationale": {
            "agent_name": "why this agent was chosen"
        },
        "strategy_rationale": "why this processing strategy"
    },
    "segment_allocation": {
        "agent_name": "relevant portion of transcript or 'full'"
    },
    "expected_outcomes": {
        "agent_name": "what we expect this agent to produce"
    },
    "fallback_plan": {
        "condition": "if primary routing fails",
        "alternative": "backup routing strategy"
    }
}""",
            temperature=0.4,
            max_tokens=1500
        )
        
        # Knowledge Validation
        self.templates["knowledge_validation"] = PromptTemplate(
            template_id="knowledge_validation",
            name="Knowledge Item Validation",
            category=PromptCategory.VALIDATION,
            description="Validate learned knowledge for accuracy and safety",
            system_context="""You are a knowledge validation expert who ensures learned patterns are accurate, safe, and beneficial.
You check for biases, errors, and ethical concerns while validating the usefulness of knowledge.""",
            task_instruction="""Validate this learned knowledge item:

VALIDATION CRITERIA:
1. Accuracy: Is the knowledge factually correct?
2. Applicability: When and where does this apply?
3. Safety: Are there any harmful implications?
4. Bias: Does this show unfair bias?
5. Ethics: Does this align with ethical principles?
6. Usefulness: Will this improve user experience?

PROVIDE:
- Validation result (approved/rejected/needs_modification)
- Specific concerns if any
- Modifications needed if applicable
- Confidence in validation""",
            input_format="""Knowledge Item:
${knowledge_item}

Supporting Evidence:
${supporting_evidence}

Context of Learning:
${learning_context}""",
            output_format="""{
    "validation_result": "approved|rejected|needs_modification",
    "validation_scores": {
        "accuracy": 0.0-1.0,
        "safety": 0.0-1.0,
        "bias_free": 0.0-1.0,
        "ethical": 0.0-1.0,
        "useful": 0.0-1.0
    },
    "concerns": [
        {
            "type": "accuracy|safety|bias|ethics|applicability",
            "description": "...",
            "severity": "low|medium|high"
        }
    ],
    "modifications_needed": [
        {
            "aspect": "what needs changing",
            "current": "current state",
            "suggested": "suggested change",
            "reason": "why this change"
        }
    ],
    "applicability_boundaries": {
        "applies_when": ["condition1", "condition2"],
        "does_not_apply": ["exception1", "exception2"]
    },
    "confidence": 0.0-1.0,
    "additional_validation_needed": true|false
}""",
            temperature=0.2,  # Lower for validation
            max_tokens=2000
        )
    
    def get_prompt(self, template_id: str, variables: Dict[str, Any]) -> str:
        """Get a formatted prompt from template.
        
        Args:
            template_id: ID of the template to use
            variables: Variables to substitute in the template
            
        Returns:
            Formatted prompt ready for use
        """
        
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        # Format input
        input_text = Template(template.input_format).safe_substitute(variables)
        
        # Build complete prompt
        prompt = f"""{template.system_context}

{template.task_instruction}

{input_text}

Expected Output Format:
{template.output_format}"""
        
        # Add examples if provided and requested
        if template.examples and variables.get("include_examples", False):
            examples_text = "\n\nExamples:\n"
            for i, example in enumerate(template.examples[:2], 1):
                examples_text += f"\nExample {i}:\nInput: {example['input']}\nOutput: {json.dumps(example['output'], indent=2)}\n"
            
            prompt = prompt.replace("\n\nExpected Output Format:", examples_text + "\nExpected Output Format:")
        
        return prompt
    
    def get_template_config(self, template_id: str) -> Dict[str, Any]:
        """Get configuration for a template.
        
        Args:
            template_id: ID of the template
            
        Returns:
            Configuration dictionary for Claude API
        """
        
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        config = {
            "temperature": template.temperature,
            "max_tokens": template.max_tokens,
            "anthropic_version": "bedrock-2023-05-31",
            "model": "anthropic.claude-3-5-sonnet-20241022-v2:0"
        }
        
        if template.stop_sequences:
            config["stop_sequences"] = template.stop_sequences
        
        return config
    
    def update_performance_metrics(self, template_id: str, 
                                 latency_ms: float, success: bool) -> None:
        """Update performance metrics for a template.
        
        Args:
            template_id: ID of the template
            latency_ms: Execution time in milliseconds
            success: Whether the execution was successful
        """
        
        if template_id not in self.templates:
            return
        
        template = self.templates[template_id]
        
        # Update average latency
        if template.avg_latency_ms is None:
            template.avg_latency_ms = latency_ms
        else:
            # Exponential moving average
            template.avg_latency_ms = 0.9 * template.avg_latency_ms + 0.1 * latency_ms
        
        # Update success rate
        if template.success_rate is None:
            template.success_rate = 1.0 if success else 0.0
        else:
            # Exponential moving average
            template.success_rate = 0.95 * template.success_rate + 0.05 * (1.0 if success else 0.0)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for all templates."""
        
        report = {
            "templates": {},
            "summary": {
                "total_templates": len(self.templates),
                "avg_latency_ms": 0.0,
                "avg_success_rate": 0.0
            }
        }
        
        total_latency = 0.0
        total_success = 0.0
        measured_templates = 0
        
        for template_id, template in self.templates.items():
            if template.avg_latency_ms is not None:
                measured_templates += 1
                total_latency += template.avg_latency_ms
                total_success += template.success_rate or 0.0
                
                report["templates"][template_id] = {
                    "name": template.name,
                    "category": template.category.value,
                    "avg_latency_ms": round(template.avg_latency_ms, 2),
                    "success_rate": round(template.success_rate or 0.0, 3),
                    "version": template.version
                }
        
        if measured_templates > 0:
            report["summary"]["avg_latency_ms"] = round(total_latency / measured_templates, 2)
            report["summary"]["avg_success_rate"] = round(total_success / measured_templates, 3)
        
        return report


# Global instance
prompt_library = PromptLibrary()