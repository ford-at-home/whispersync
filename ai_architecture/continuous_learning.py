"""Continuous Learning System for WhisperSync.

This module implements a sophisticated learning system that continuously improves
from user feedback, interaction patterns, and outcomes. It enables the AI to
adapt and personalize its responses over time while maintaining safety and ethics.

LEARNING COMPONENTS:
1. Feedback Processing: Direct user feedback and implicit signals
2. Pattern Recognition: Learning from successful/unsuccessful interactions
3. Model Adaptation: Adjusting AI behavior based on learnings
4. Knowledge Consolidation: Long-term memory and knowledge building
5. Performance Monitoring: Tracking improvement metrics
6. Safety Boundaries: Ensuring learning stays within ethical bounds

WHY CONTINUOUS LEARNING:
- Personalizes the experience for each user
- Improves accuracy and relevance over time
- Adapts to changing user needs and preferences
- Builds institutional knowledge from aggregate patterns
- Enables proactive assistance based on learned patterns
"""

from __future__ import annotations

import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import hashlib
import statistics

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback the system can receive."""
    
    EXPLICIT_POSITIVE = "explicit_positive"    # User said "good job"
    EXPLICIT_NEGATIVE = "explicit_negative"    # User said "that's wrong"
    IMPLICIT_POSITIVE = "implicit_positive"    # User used suggestion
    IMPLICIT_NEGATIVE = "implicit_negative"    # User ignored/rejected
    CORRECTION = "correction"                  # User provided correction
    PREFERENCE = "preference"                  # User stated preference
    RATING = "rating"                         # Numerical rating
    BEHAVIORAL = "behavioral"                  # Action-based feedback


class LearningDomain(Enum):
    """Domains where learning can be applied."""
    
    ROUTING = "routing"                       # Agent selection
    CLASSIFICATION = "classification"          # Content categorization
    EMOTIONAL_RESPONSE = "emotional_response"  # Emotional understanding
    LANGUAGE_STYLE = "language_style"         # Communication preferences
    TIMING_PATTERNS = "timing_patterns"       # When user interacts
    CONTENT_PREFERENCES = "content_preferences" # What user discusses
    WORKFLOW_OPTIMIZATION = "workflow_optimization" # Process improvements


@dataclass
class LearningInstance:
    """Single instance of learning from an interaction."""
    
    instance_id: str
    timestamp: datetime
    domain: LearningDomain
    
    # Context
    input_data: Dict[str, Any]
    system_response: Dict[str, Any]
    user_feedback: Dict[str, Any]
    
    # Learning extracted
    lesson_learned: str
    confidence: float  # 0-1 scale
    impact_score: float  # Importance of this learning
    
    # Application
    applied_count: int = 0
    success_rate: float = 0.0
    last_applied: Optional[datetime] = None


@dataclass
class KnowledgeItem:
    """Consolidated knowledge from multiple learning instances."""
    
    knowledge_id: str
    domain: LearningDomain
    description: str
    
    # Supporting evidence
    supporting_instances: List[str] = field(default_factory=list)  # Instance IDs
    contradicting_instances: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-1 scale based on evidence
    
    # Applicability
    applicable_conditions: Dict[str, Any] = field(default_factory=dict)
    exceptions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance
    application_count: int = 0
    success_rate: float = 0.0
    last_validated: Optional[datetime] = None
    
    # Status
    is_active: bool = True
    requires_review: bool = False


@dataclass
class UserModel:
    """Learned model of a specific user."""
    
    user_id: str
    created_at: datetime
    last_updated: datetime
    
    # Preferences
    communication_preferences: Dict[str, Any] = field(default_factory=dict)
    content_preferences: Dict[str, float] = field(default_factory=dict)  # topic -> affinity
    timing_preferences: Dict[str, float] = field(default_factory=dict)   # hour -> probability
    
    # Patterns
    behavioral_patterns: List[Dict[str, Any]] = field(default_factory=list)
    emotional_patterns: Dict[str, Any] = field(default_factory=dict)
    workflow_preferences: Dict[str, float] = field(default_factory=dict)
    
    # Performance metrics
    satisfaction_trend: List[float] = field(default_factory=list)  # Historical satisfaction
    engagement_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Personalization parameters
    personalization_level: float = 0.5  # 0=generic, 1=highly personalized
    adaptation_rate: float = 0.1  # How quickly to adapt to new patterns


class ContinuousLearningEngine:
    """Main continuous learning system."""
    
    def __init__(self, bedrock_client=None):
        """Initialize the learning engine."""
        self.bedrock = bedrock_client
        
        # Learning storage
        self.learning_instances: Dict[str, LearningInstance] = {}
        self.knowledge_base: Dict[str, KnowledgeItem] = {}
        self.user_models: Dict[str, UserModel] = {}
        
        # Learning processors
        self.feedback_processor = FeedbackProcessor()
        self.pattern_learner = PatternLearner()
        self.knowledge_consolidator = KnowledgeConsolidator()
        self.performance_monitor = PerformanceMonitor()
        
        # Safety and ethics
        self.safety_validator = SafetyValidator()
        self.bias_detector = BiasDetector()
        
        # Learning configuration
        self.min_confidence_threshold = 0.6
        self.min_instances_for_knowledge = 3
        self.knowledge_decay_rate = 0.01  # Per day
        
    def process_feedback(self, interaction_id: str, feedback: Dict[str, Any],
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user feedback and extract learnings.
        
        Args:
            interaction_id: ID of the interaction being evaluated
            feedback: User feedback (explicit or implicit)
            context: Context of the interaction
            
        Returns:
            Learning results and any immediate adjustments
        """
        
        # Classify feedback type
        feedback_type = self.feedback_processor.classify_feedback(feedback)
        
        # Extract learning based on feedback type
        if feedback_type in [FeedbackType.EXPLICIT_NEGATIVE, FeedbackType.CORRECTION]:
            learning = self._learn_from_mistake(interaction_id, feedback, context)
        elif feedback_type in [FeedbackType.EXPLICIT_POSITIVE, FeedbackType.IMPLICIT_POSITIVE]:
            learning = self._learn_from_success(interaction_id, feedback, context)
        elif feedback_type == FeedbackType.PREFERENCE:
            learning = self._learn_preference(interaction_id, feedback, context)
        else:
            learning = self._learn_from_behavior(interaction_id, feedback, context)
        
        # Validate learning for safety
        if not self.safety_validator.is_safe(learning):
            logger.warning(f"Learning rejected for safety: {learning}")
            return {"status": "rejected", "reason": "safety_violation"}
        
        # Store learning instance
        instance = self._create_learning_instance(learning, feedback, context)
        self.learning_instances[instance.instance_id] = instance
        
        # Update user model
        if "user_id" in context:
            self._update_user_model(context["user_id"], instance)
        
        # Check if we can consolidate into knowledge
        knowledge_updates = self.knowledge_consolidator.check_for_consolidation(
            instance, self.learning_instances, self.knowledge_base
        )
        
        # Apply immediate adjustments if high confidence
        immediate_adjustments = {}
        if instance.confidence > 0.8 and instance.impact_score > 0.7:
            immediate_adjustments = self._apply_immediate_learning(instance)
        
        return {
            "status": "processed",
            "learning_instance": asdict(instance),
            "knowledge_updates": knowledge_updates,
            "immediate_adjustments": immediate_adjustments,
            "user_model_updated": "user_id" in context
        }
    
    def _learn_from_mistake(self, interaction_id: str, feedback: Dict,
                          context: Dict) -> Dict[str, Any]:
        """Extract learning from negative feedback or corrections."""
        
        if self.bedrock:
            return self._ai_mistake_analysis(interaction_id, feedback, context)
        
        # Fallback rule-based learning
        learning = {
            "type": "mistake",
            "domain": self._identify_mistake_domain(feedback, context),
            "lesson": self._extract_mistake_lesson(feedback),
            "prevention_strategy": self._suggest_prevention(feedback, context)
        }
        
        return learning
    
    def _ai_mistake_analysis(self, interaction_id: str, feedback: Dict,
                           context: Dict) -> Dict[str, Any]:
        """Use AI to analyze mistakes and extract learnings."""
        
        prompt = f"""Analyze this user feedback about a mistake and extract learnings:

Interaction Context:
{json.dumps(context, indent=2)}

User Feedback:
{json.dumps(feedback, indent=2)}

Extract:
1. What specifically went wrong
2. Why the system made this mistake
3. What pattern or rule was violated
4. How to prevent similar mistakes
5. Confidence in this learning (0-1)
6. Impact/importance of fixing this (0-1)

Consider:
- Is this a one-off error or systematic issue?
- Does this reveal a gap in understanding?
- Are there edge cases we missed?

Respond in JSON format with keys: mistake_description, root_cause, violated_pattern, 
prevention_strategy, confidence, impact_score, learning_domain, is_systematic"""
        
        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1500,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response["body"].read())
            return json.loads(result.get("content", [{}])[0].get("text", "{}"))
            
        except Exception as e:
            logger.error(f"AI mistake analysis failed: {e}")
            return {}
    
    def _learn_from_success(self, interaction_id: str, feedback: Dict,
                          context: Dict) -> Dict[str, Any]:
        """Reinforce successful patterns."""
        
        learning = {
            "type": "success",
            "domain": self._identify_success_domain(context),
            "pattern_reinforced": self._extract_success_pattern(context),
            "conditions_for_success": self._extract_success_conditions(context),
            "replication_strategy": "Apply similar approach when conditions match"
        }
        
        return learning
    
    def _learn_preference(self, interaction_id: str, feedback: Dict,
                        context: Dict) -> Dict[str, Any]:
        """Learn user preferences."""
        
        preference_type = feedback.get("preference_type", "general")
        preference_value = feedback.get("preference_value")
        
        learning = {
            "type": "preference",
            "domain": LearningDomain.CONTENT_PREFERENCES,
            "preference_category": preference_type,
            "preferred_value": preference_value,
            "context_when_applicable": context.get("situation", "general")
        }
        
        return learning
    
    def _create_learning_instance(self, learning: Dict, feedback: Dict,
                                context: Dict) -> LearningInstance:
        """Create a learning instance from extracted learning."""
        
        # Determine domain
        domain_str = learning.get("domain", learning.get("learning_domain", "routing"))
        try:
            domain = LearningDomain(domain_str)
        except ValueError:
            domain = LearningDomain.ROUTING
        
        instance = LearningInstance(
            instance_id=self._generate_instance_id(learning),
            timestamp=datetime.utcnow(),
            domain=domain,
            input_data=context.get("input_data", {}),
            system_response=context.get("system_response", {}),
            user_feedback=feedback,
            lesson_learned=learning.get("lesson", str(learning)),
            confidence=learning.get("confidence", 0.5),
            impact_score=learning.get("impact_score", 0.5)
        )
        
        return instance
    
    def _update_user_model(self, user_id: str, instance: LearningInstance) -> None:
        """Update user model based on new learning."""
        
        if user_id not in self.user_models:
            self.user_models[user_id] = UserModel(
                user_id=user_id,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
        
        model = self.user_models[user_id]
        model.last_updated = datetime.utcnow()
        
        # Update based on domain
        if instance.domain == LearningDomain.LANGUAGE_STYLE:
            self._update_communication_preferences(model, instance)
        elif instance.domain == LearningDomain.CONTENT_PREFERENCES:
            self._update_content_preferences(model, instance)
        elif instance.domain == LearningDomain.TIMING_PATTERNS:
            self._update_timing_preferences(model, instance)
        elif instance.domain == LearningDomain.EMOTIONAL_RESPONSE:
            self._update_emotional_patterns(model, instance)
        
        # Update engagement metrics
        if instance.user_feedback.get("satisfaction"):
            model.satisfaction_trend.append(instance.user_feedback["satisfaction"])
            # Keep only last 100 ratings
            if len(model.satisfaction_trend) > 100:
                model.satisfaction_trend = model.satisfaction_trend[-100:]
    
    def get_personalized_parameters(self, user_id: str, 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Get personalized parameters for a user based on learnings.
        
        Args:
            user_id: User identifier
            context: Current context
            
        Returns:
            Personalized parameters to apply
        """
        
        if user_id not in self.user_models:
            return {"personalization_level": 0.0}
        
        model = self.user_models[user_id]
        
        # Build personalized parameters
        params = {
            "personalization_level": model.personalization_level,
            "communication_style": model.communication_preferences,
            "likely_topics": self._get_likely_topics(model, context),
            "optimal_timing": self._get_optimal_timing(model, context),
            "preferred_workflows": self._get_preferred_workflows(model, context),
            "emotional_considerations": model.emotional_patterns
        }
        
        # Apply knowledge base rules
        applicable_knowledge = self._find_applicable_knowledge(user_id, context)
        for knowledge in applicable_knowledge:
            params[f"knowledge_{knowledge.knowledge_id}"] = knowledge.description
        
        return params
    
    def _get_likely_topics(self, model: UserModel, context: Dict) -> List[str]:
        """Get likely topics based on user preferences."""
        
        # Sort topics by affinity
        sorted_topics = sorted(
            model.content_preferences.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Filter by context if available
        time_of_day = context.get("time_of_day", "day")
        
        # Return top topics
        return [topic for topic, _ in sorted_topics[:5]]
    
    def evaluate_learning_effectiveness(self, time_window_days: int = 30) -> Dict[str, Any]:
        """Evaluate how effective the learning system has been.
        
        Args:
            time_window_days: Days to look back
            
        Returns:
            Effectiveness metrics and insights
        """
        
        cutoff = datetime.utcnow() - timedelta(days=time_window_days)
        
        # Collect recent instances
        recent_instances = [
            instance for instance in self.learning_instances.values()
            if instance.timestamp > cutoff
        ]
        
        if not recent_instances:
            return {"message": "No learning instances in time window"}
        
        # Calculate metrics
        metrics = {
            "total_learnings": len(recent_instances),
            "learnings_by_domain": defaultdict(int),
            "average_confidence": statistics.mean(i.confidence for i in recent_instances),
            "average_impact": statistics.mean(i.impact_score for i in recent_instances),
            "applied_learnings": sum(1 for i in recent_instances if i.applied_count > 0),
            "successful_applications": sum(
                i.applied_count * i.success_rate for i in recent_instances
            ),
            "knowledge_items_created": len([
                k for k in self.knowledge_base.values()
                if k.last_validated and k.last_validated > cutoff
            ])
        }
        
        # Count by domain
        for instance in recent_instances:
            metrics["learnings_by_domain"][instance.domain.value] += 1
        
        # User satisfaction trend
        satisfaction_improvements = []
        for model in self.user_models.values():
            if len(model.satisfaction_trend) >= 10:
                early = statistics.mean(model.satisfaction_trend[:5])
                recent = statistics.mean(model.satisfaction_trend[-5:])
                improvement = recent - early
                satisfaction_improvements.append(improvement)
        
        if satisfaction_improvements:
            metrics["average_satisfaction_improvement"] = statistics.mean(satisfaction_improvements)
        
        # Generate insights
        insights = self._generate_effectiveness_insights(metrics, recent_instances)
        
        return {
            "metrics": dict(metrics),
            "insights": insights,
            "recommendations": self._generate_learning_recommendations(metrics, insights)
        }
    
    def _generate_effectiveness_insights(self, metrics: Dict, 
                                       instances: List[LearningInstance]) -> List[str]:
        """Generate insights about learning effectiveness."""
        
        insights = []
        
        # Overall learning rate
        daily_rate = metrics["total_learnings"] / 30
        insights.append(f"Learning at {daily_rate:.1f} instances per day")
        
        # Confidence insights
        if metrics["average_confidence"] < 0.5:
            insights.append("Low confidence in learnings - may need more explicit feedback")
        elif metrics["average_confidence"] > 0.8:
            insights.append("High confidence learnings - system is learning effectively")
        
        # Application insights
        application_rate = metrics["applied_learnings"] / metrics["total_learnings"]
        if application_rate < 0.3:
            insights.append("Low application rate - many learnings not being used")
        
        # Domain insights
        domain_counts = metrics["learnings_by_domain"]
        if domain_counts:
            top_domain = max(domain_counts.items(), key=lambda x: x[1])
            insights.append(f"Most learning in domain: {top_domain[0]}")
        
        # Satisfaction insights
        if "average_satisfaction_improvement" in metrics:
            improvement = metrics["average_satisfaction_improvement"]
            if improvement > 0.1:
                insights.append(f"User satisfaction improving (+{improvement:.1%})")
            elif improvement < -0.1:
                insights.append(f"User satisfaction declining ({improvement:.1%})")
        
        return insights
    
    def _generate_learning_recommendations(self, metrics: Dict, 
                                         insights: List[str]) -> List[str]:
        """Generate recommendations for improving learning."""
        
        recommendations = []
        
        # Based on metrics
        if metrics["average_confidence"] < 0.6:
            recommendations.append("Encourage more explicit user feedback")
            recommendations.append("Implement confidence-building through A/B testing")
        
        if metrics["applied_learnings"] / metrics["total_learnings"] < 0.5:
            recommendations.append("Review unapplied learnings for relevance")
            recommendations.append("Implement more aggressive learning application")
        
        # Based on domain distribution
        domain_counts = metrics["learnings_by_domain"]
        if len(domain_counts) < 3:
            recommendations.append("Expand learning to more domains")
        
        # Based on user satisfaction
        if "average_satisfaction_improvement" in metrics:
            if metrics["average_satisfaction_improvement"] < 0:
                recommendations.append("Focus on high-impact user pain points")
                recommendations.append("Increase personalization efforts")
        
        return recommendations
    
    def export_knowledge_base(self) -> Dict[str, Any]:
        """Export the knowledge base for backup or analysis."""
        
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "knowledge_items": [
                asdict(item) for item in self.knowledge_base.values()
            ],
            "total_items": len(self.knowledge_base),
            "active_items": sum(1 for item in self.knowledge_base.values() if item.is_active),
            "domains": list(set(
                item.domain.value for item in self.knowledge_base.values()
            ))
        }
    
    def _generate_instance_id(self, learning: Dict) -> str:
        """Generate unique ID for learning instance."""
        content = json.dumps(learning, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _identify_mistake_domain(self, feedback: Dict, context: Dict) -> str:
        """Identify which domain the mistake belongs to."""
        
        # Simple heuristic - can be improved
        if "routing" in str(feedback).lower():
            return LearningDomain.ROUTING.value
        elif "emotion" in str(feedback).lower():
            return LearningDomain.EMOTIONAL_RESPONSE.value
        else:
            return LearningDomain.CLASSIFICATION.value
    
    def _extract_mistake_lesson(self, feedback: Dict) -> str:
        """Extract the lesson from mistake feedback."""
        
        if "correction" in feedback:
            return f"Should have been: {feedback['correction']}"
        elif "message" in feedback:
            return feedback["message"]
        else:
            return "User indicated dissatisfaction with response"
    
    def _suggest_prevention(self, feedback: Dict, context: Dict) -> str:
        """Suggest how to prevent similar mistakes."""
        
        return "Adjust decision threshold and add validation check"
    
    def _apply_immediate_learning(self, instance: LearningInstance) -> Dict[str, Any]:
        """Apply high-confidence learning immediately."""
        
        adjustments = {
            "applied": True,
            "instance_id": instance.instance_id,
            "adjustments": []
        }
        
        # Domain-specific adjustments
        if instance.domain == LearningDomain.ROUTING:
            adjustments["adjustments"].append({
                "type": "routing_rule",
                "adjustment": "Update routing confidence threshold"
            })
        
        return adjustments
    
    def _find_applicable_knowledge(self, user_id: str, context: Dict) -> List[KnowledgeItem]:
        """Find knowledge items applicable to current context."""
        
        applicable = []
        
        for item in self.knowledge_base.values():
            if not item.is_active:
                continue
                
            # Check applicability conditions
            conditions_met = all(
                context.get(key) == value 
                for key, value in item.applicable_conditions.items()
            )
            
            if conditions_met:
                applicable.append(item)
        
        return applicable


class FeedbackProcessor:
    """Processes various types of user feedback."""
    
    def classify_feedback(self, feedback: Dict) -> FeedbackType:
        """Classify the type of feedback received."""
        
        # Explicit feedback
        if "rating" in feedback:
            return FeedbackType.RATING
        elif "correction" in feedback:
            return FeedbackType.CORRECTION
        elif any(word in str(feedback).lower() for word in ["good", "great", "perfect", "thanks"]):
            return FeedbackType.EXPLICIT_POSITIVE
        elif any(word in str(feedback).lower() for word in ["wrong", "bad", "incorrect", "no"]):
            return FeedbackType.EXPLICIT_NEGATIVE
        elif "preference" in feedback:
            return FeedbackType.PREFERENCE
        
        # Implicit feedback
        elif feedback.get("action") == "accepted":
            return FeedbackType.IMPLICIT_POSITIVE
        elif feedback.get("action") == "rejected":
            return FeedbackType.IMPLICIT_NEGATIVE
        else:
            return FeedbackType.BEHAVIORAL


class PatternLearner:
    """Learns patterns from multiple interactions."""
    
    def identify_patterns(self, instances: List[LearningInstance]) -> List[Dict[str, Any]]:
        """Identify patterns across learning instances."""
        
        patterns = []
        
        # Group by domain
        domain_groups = defaultdict(list)
        for instance in instances:
            domain_groups[instance.domain].append(instance)
        
        # Look for patterns in each domain
        for domain, domain_instances in domain_groups.items():
            if len(domain_instances) >= 3:
                pattern = self._extract_domain_pattern(domain, domain_instances)
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _extract_domain_pattern(self, domain: LearningDomain,
                               instances: List[LearningInstance]) -> Optional[Dict[str, Any]]:
        """Extract pattern from instances in a domain."""
        
        # Simple pattern extraction - can be enhanced
        if len(instances) < 3:
            return None
        
        # Look for common elements
        common_inputs = self._find_common_elements(
            [i.input_data for i in instances]
        )
        
        common_responses = self._find_common_elements(
            [i.system_response for i in instances]
        )
        
        if common_inputs or common_responses:
            return {
                "domain": domain.value,
                "pattern_type": "recurring",
                "common_inputs": common_inputs,
                "common_responses": common_responses,
                "instance_count": len(instances),
                "confidence": min(len(instances) / 10.0, 1.0)
            }
        
        return None
    
    def _find_common_elements(self, data_list: List[Dict]) -> Dict[str, Any]:
        """Find common elements across dictionaries."""
        
        if not data_list:
            return {}
        
        # Find keys present in all dictionaries
        common_keys = set(data_list[0].keys())
        for data in data_list[1:]:
            common_keys &= set(data.keys())
        
        # Find common values for common keys
        common_elements = {}
        for key in common_keys:
            values = [data[key] for data in data_list]
            if len(set(str(v) for v in values)) == 1:  # All same value
                common_elements[key] = values[0]
        
        return common_elements


class KnowledgeConsolidator:
    """Consolidates learning instances into knowledge items."""
    
    def check_for_consolidation(self, new_instance: LearningInstance,
                               all_instances: Dict[str, LearningInstance],
                               knowledge_base: Dict[str, KnowledgeItem]) -> List[Dict[str, Any]]:
        """Check if new instance enables knowledge consolidation."""
        
        updates = []
        
        # Find related instances
        related = self._find_related_instances(new_instance, all_instances)
        
        if len(related) >= 3:  # Minimum for consolidation
            # Check if we can create new knowledge
            knowledge = self._attempt_consolidation(new_instance, related)
            if knowledge:
                knowledge_base[knowledge.knowledge_id] = knowledge
                updates.append({
                    "action": "created",
                    "knowledge_id": knowledge.knowledge_id,
                    "description": knowledge.description
                })
        
        # Check if this contradicts existing knowledge
        contradictions = self._check_contradictions(new_instance, knowledge_base)
        for contradiction in contradictions:
            updates.append({
                "action": "contradiction",
                "knowledge_id": contradiction["knowledge_id"],
                "reason": contradiction["reason"]
            })
        
        return updates
    
    def _find_related_instances(self, instance: LearningInstance,
                               all_instances: Dict[str, LearningInstance]) -> List[LearningInstance]:
        """Find instances related to the given one."""
        
        related = []
        
        for other_id, other in all_instances.items():
            if other_id == instance.instance_id:
                continue
                
            # Same domain
            if other.domain != instance.domain:
                continue
            
            # Similar context or lesson
            similarity = self._calculate_similarity(instance, other)
            if similarity > 0.7:
                related.append(other)
        
        return related
    
    def _calculate_similarity(self, instance1: LearningInstance,
                            instance2: LearningInstance) -> float:
        """Calculate similarity between two instances."""
        
        # Simple similarity based on lesson learned
        # In production, use more sophisticated similarity metrics
        lesson1 = instance1.lesson_learned.lower()
        lesson2 = instance2.lesson_learned.lower()
        
        # Check for common words
        words1 = set(lesson1.split())
        words2 = set(lesson2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _attempt_consolidation(self, new_instance: LearningInstance,
                             related: List[LearningInstance]) -> Optional[KnowledgeItem]:
        """Attempt to create knowledge from related instances."""
        
        all_instances = [new_instance] + related
        
        # Calculate aggregate confidence
        avg_confidence = statistics.mean(i.confidence for i in all_instances)
        if avg_confidence < 0.6:
            return None
        
        # Extract common pattern
        common_pattern = self._extract_common_pattern(all_instances)
        if not common_pattern:
            return None
        
        # Create knowledge item
        knowledge = KnowledgeItem(
            knowledge_id=self._generate_knowledge_id(common_pattern),
            domain=new_instance.domain,
            description=common_pattern["description"],
            supporting_instances=[i.instance_id for i in all_instances],
            confidence=avg_confidence,
            applicable_conditions=common_pattern.get("conditions", {}),
            last_validated=datetime.utcnow()
        )
        
        return knowledge
    
    def _extract_common_pattern(self, instances: List[LearningInstance]) -> Optional[Dict[str, Any]]:
        """Extract common pattern from instances."""
        
        # Group lessons
        lessons = [i.lesson_learned for i in instances]
        
        # Find common theme (simplified)
        common_words = None
        for lesson in lessons:
            words = set(lesson.lower().split())
            if common_words is None:
                common_words = words
            else:
                common_words &= words
        
        if not common_words:
            return None
        
        return {
            "description": f"Pattern: {' '.join(common_words)}",
            "conditions": {},
            "evidence_count": len(instances)
        }
    
    def _check_contradictions(self, instance: LearningInstance,
                            knowledge_base: Dict[str, KnowledgeItem]) -> List[Dict[str, Any]]:
        """Check if instance contradicts existing knowledge."""
        
        contradictions = []
        
        # Simplified contradiction detection
        # In production, use more sophisticated logic
        
        return contradictions
    
    def _generate_knowledge_id(self, pattern: Dict) -> str:
        """Generate unique ID for knowledge item."""
        content = json.dumps(pattern, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:16]


class PerformanceMonitor:
    """Monitors learning system performance."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def track_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Track a performance metric."""
        timestamp = timestamp or datetime.utcnow()
        self.metrics[metric_name].append({"value": value, "timestamp": timestamp})
    
    def get_trend(self, metric_name: str, window_days: int = 7) -> Dict[str, Any]:
        """Get trend for a metric."""
        
        if metric_name not in self.metrics:
            return {"error": "Metric not found"}
        
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        recent_values = [
            m["value"] for m in self.metrics[metric_name]
            if m["timestamp"] > cutoff
        ]
        
        if not recent_values:
            return {"error": "No recent data"}
        
        return {
            "metric": metric_name,
            "window_days": window_days,
            "count": len(recent_values),
            "mean": statistics.mean(recent_values),
            "std": statistics.stdev(recent_values) if len(recent_values) > 1 else 0,
            "trend": self._calculate_trend(recent_values)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction."""
        
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear regression
        x = list(range(len(values)))
        y = values
        
        n = len(x)
        slope = (n * sum(x[i] * y[i] for i in range(n)) - sum(x) * sum(y)) / \
                (n * sum(x[i]**2 for i in range(n)) - sum(x)**2)
        
        if abs(slope) < 0.01:
            return "stable"
        elif slope > 0:
            return "improving"
        else:
            return "declining"


class SafetyValidator:
    """Validates learnings for safety and ethics."""
    
    def is_safe(self, learning: Dict[str, Any]) -> bool:
        """Check if a learning is safe to apply."""
        
        # Check for harmful patterns
        harmful_keywords = [
            "discriminate", "bias", "exclude", "ignore", "harassment",
            "privacy", "confidential", "illegal", "unethical"
        ]
        
        learning_text = json.dumps(learning).lower()
        
        for keyword in harmful_keywords:
            if keyword in learning_text:
                logger.warning(f"Potentially unsafe learning detected: {keyword}")
                return False
        
        # Additional safety checks can be added here
        
        return True


class BiasDetector:
    """Detects potential biases in learning patterns."""
    
    def check_for_bias(self, knowledge_base: Dict[str, KnowledgeItem]) -> List[Dict[str, Any]]:
        """Check knowledge base for potential biases."""
        
        biases = []
        
        # Group knowledge by domain
        domain_knowledge = defaultdict(list)
        for item in knowledge_base.values():
            domain_knowledge[item.domain].append(item)
        
        # Check for imbalances
        for domain, items in domain_knowledge.items():
            # Check for demographic biases
            demographic_bias = self._check_demographic_bias(items)
            if demographic_bias:
                biases.append(demographic_bias)
            
            # Check for confirmation bias
            confirmation_bias = self._check_confirmation_bias(items)
            if confirmation_bias:
                biases.append(confirmation_bias)
        
        return biases
    
    def _check_demographic_bias(self, items: List[KnowledgeItem]) -> Optional[Dict[str, Any]]:
        """Check for demographic biases in knowledge."""
        
        # Simplified check - in production use more sophisticated methods
        demographic_terms = ["age", "gender", "race", "nationality", "religion"]
        
        for item in items:
            description_lower = item.description.lower()
            for term in demographic_terms:
                if term in description_lower:
                    return {
                        "type": "potential_demographic_bias",
                        "knowledge_id": item.knowledge_id,
                        "term_found": term,
                        "severity": "medium"
                    }
        
        return None
    
    def _check_confirmation_bias(self, items: List[KnowledgeItem]) -> Optional[Dict[str, Any]]:
        """Check for confirmation bias in knowledge."""
        
        # Check if all knowledge points in same direction
        if len(items) > 5:
            # Simplified check
            positive_count = sum(1 for item in items if "positive" in item.description.lower())
            negative_count = sum(1 for item in items if "negative" in item.description.lower())
            
            if positive_count > len(items) * 0.8 or negative_count > len(items) * 0.8:
                return {
                    "type": "potential_confirmation_bias",
                    "domain": items[0].domain.value,
                    "skew": "positive" if positive_count > negative_count else "negative",
                    "severity": "low"
                }
        
        return None


class _update_communication_preferences:
    pass