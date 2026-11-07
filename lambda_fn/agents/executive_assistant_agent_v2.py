"""ExecutiveAssistantAgent V2 - Enhanced with granular category evolution and learning.

Core enhancements:
- Granular category system that evolves with usage patterns
- Knowledge graph that learns relationships between concepts
- Persona voice integration hooks for authentic communication
- Progressive refinement of Theory of Mind through interactions
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import asyncio
from collections import defaultdict
import hashlib

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

from .base import BaseAgent, requires_aws, AgentError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Configuration
THEORY_OF_MIND_TABLE = os.environ.get('THEORY_OF_MIND_TABLE', 'ExecutiveAssistant-TheoryOfMind')
CATEGORY_EVOLUTION_TABLE = os.environ.get('CATEGORY_EVOLUTION_TABLE', 'ExecutiveAssistant-CategoryEvolution')
KNOWLEDGE_GRAPH_TABLE = os.environ.get('KNOWLEDGE_GRAPH_TABLE', 'ExecutiveAssistant-KnowledgeGraph')
USER_ID = os.environ.get('USER_ID', 'default')


@dataclass
class CategoryNode:
    """Represents a category node in the evolving hierarchy."""
    
    id: str
    name: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    usage_count: int = 0
    last_used: Optional[str] = None
    confidence: float = 0.5
    keywords: List[str] = field(default_factory=list)
    related_categories: Dict[str, float] = field(default_factory=dict)  # category_id -> strength
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def increase_confidence(self, amount: float = 0.1) -> None:
        """Increase confidence up to 1.0."""
        self.confidence = min(1.0, self.confidence + amount)
    
    def decay_confidence(self, amount: float = 0.05) -> None:
        """Decay confidence over time, minimum 0.1."""
        self.confidence = max(0.1, self.confidence - amount)


@dataclass
class GranularCategory:
    """Hierarchical category system that evolves with usage."""
    
    # Core work categories with granular subcategories
    work_categories: Dict[str, CategoryNode] = field(default_factory=dict)
    
    # Personal boundary categories
    personal_categories: Dict[str, CategoryNode] = field(default_factory=dict)
    
    # Workflow and process categories
    workflow_categories: Dict[str, CategoryNode] = field(default_factory=dict)
    
    # Dynamic category relationships
    category_graph: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Evolution metrics
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize default category structure."""
        if not self.work_categories:
            # Initialize work categories with granular hierarchy
            self._init_work_categories()
        
        if not self.personal_categories:
            self._init_personal_categories()
        
        if not self.workflow_categories:
            self._init_workflow_categories()
    
    def _init_work_categories(self):
        """Initialize default work category hierarchy."""
        # Product work
        product_id = self._create_category("work.product", "Product Development")
        self._create_category("work.product.planning", "Planning", product_id)
        self._create_category("work.product.design", "Design", product_id)
        self._create_category("work.product.implementation", "Implementation", product_id)
        self._create_category("work.product.testing", "Testing", product_id)
        self._create_category("work.product.launch", "Launch", product_id)
        
        # Engineering work
        eng_id = self._create_category("work.engineering", "Engineering")
        self._create_category("work.engineering.architecture", "Architecture", eng_id)
        self._create_category("work.engineering.coding", "Coding", eng_id)
        self._create_category("work.engineering.debugging", "Debugging", eng_id)
        self._create_category("work.engineering.refactoring", "Refactoring", eng_id)
        self._create_category("work.engineering.documentation", "Documentation", eng_id)
        
        # Leadership work
        lead_id = self._create_category("work.leadership", "Leadership")
        self._create_category("work.leadership.strategy", "Strategy", lead_id)
        self._create_category("work.leadership.team", "Team Management", lead_id)
        self._create_category("work.leadership.mentoring", "Mentoring", lead_id)
        self._create_category("work.leadership.hiring", "Hiring", lead_id)
        
        # Communication work
        comm_id = self._create_category("work.communication", "Communication")
        self._create_category("work.communication.meetings", "Meetings", comm_id)
        self._create_category("work.communication.presentations", "Presentations", comm_id)
        self._create_category("work.communication.writing", "Writing", comm_id)
        self._create_category("work.communication.stakeholder", "Stakeholder Management", comm_id)
    
    def _init_personal_categories(self):
        """Initialize personal boundary categories."""
        # Boundaries
        bound_id = self._create_category("personal.boundaries", "Boundaries")
        self._create_category("personal.boundaries.time", "Time Boundaries", bound_id)
        self._create_category("personal.boundaries.energy", "Energy Boundaries", bound_id)
        self._create_category("personal.boundaries.emotional", "Emotional Boundaries", bound_id)
        self._create_category("personal.boundaries.worklife", "Work-Life Balance", bound_id)
        
        # Health
        health_id = self._create_category("personal.health", "Health")
        self._create_category("personal.health.physical", "Physical Health", health_id)
        self._create_category("personal.health.mental", "Mental Health", health_id)
        self._create_category("personal.health.sleep", "Sleep & Recovery", health_id)
        
        # Growth
        growth_id = self._create_category("personal.growth", "Personal Growth")
        self._create_category("personal.growth.learning", "Learning", growth_id)
        self._create_category("personal.growth.skills", "Skill Development", growth_id)
        self._create_category("personal.growth.mindset", "Mindset", growth_id)
    
    def _init_workflow_categories(self):
        """Initialize workflow and process categories."""
        # Time management
        time_id = self._create_category("workflow.time", "Time Management")
        self._create_category("workflow.time.planning", "Planning", time_id)
        self._create_category("workflow.time.prioritization", "Prioritization", time_id)
        self._create_category("workflow.time.deepwork", "Deep Work", time_id)
        self._create_category("workflow.time.breaks", "Breaks & Recovery", time_id)
        
        # Process
        proc_id = self._create_category("workflow.process", "Process")
        self._create_category("workflow.process.automation", "Automation", proc_id)
        self._create_category("workflow.process.optimization", "Optimization", proc_id)
        self._create_category("workflow.process.delegation", "Delegation", proc_id)
        
        # Tools
        tools_id = self._create_category("workflow.tools", "Tools & Systems")
        self._create_category("workflow.tools.productivity", "Productivity Tools", tools_id)
        self._create_category("workflow.tools.communication", "Communication Tools", tools_id)
        self._create_category("workflow.tools.development", "Development Tools", tools_id)
    
    def _create_category(self, id: str, name: str, parent_id: Optional[str] = None) -> str:
        """Create a category node."""
        node = CategoryNode(
            id=id,
            name=name,
            parent_id=parent_id,
            last_used=datetime.utcnow().isoformat()
        )
        
        # Determine which category dict to use based on prefix
        if id.startswith("work."):
            self.work_categories[id] = node
        elif id.startswith("personal."):
            self.personal_categories[id] = node
        elif id.startswith("workflow."):
            self.workflow_categories[id] = node
        
        # Update parent's children if applicable
        if parent_id:
            parent = self._get_category(parent_id)
            if parent and id not in parent.children:
                parent.children.append(id)
        
        return id
    
    def _get_category(self, category_id: str) -> Optional[CategoryNode]:
        """Get category by ID from any category dict."""
        return (self.work_categories.get(category_id) or 
                self.personal_categories.get(category_id) or 
                self.workflow_categories.get(category_id))
    
    def evolve_category(self, transcript: str, detected_themes: List[str]) -> List[str]:
        """Evolve categories based on transcript and themes.
        
        Returns list of relevant category IDs.
        """
        relevant_categories = []
        
        # Analyze transcript for category indicators
        lower_transcript = transcript.lower()
        
        # Check all categories for relevance
        all_categories = {
            **self.work_categories,
            **self.personal_categories,
            **self.workflow_categories
        }
        
        for cat_id, category in all_categories.items():
            relevance_score = 0.0
            
            # Check keywords
            for keyword in category.keywords:
                if keyword.lower() in lower_transcript:
                    relevance_score += 0.3
            
            # Check category name
            if category.name.lower() in lower_transcript:
                relevance_score += 0.5
            
            # Check themes alignment
            for theme in detected_themes:
                if theme.lower() in category.name.lower():
                    relevance_score += 0.4
            
            # If relevant, update usage and confidence
            if relevance_score > 0.5:
                category.usage_count += 1
                category.last_used = datetime.utcnow().isoformat()
                category.increase_confidence(relevance_score * 0.1)
                relevant_categories.append(cat_id)
                
                # Update category relationships
                for other_cat in relevant_categories[:-1]:
                    if other_cat != cat_id:
                        category.related_categories[other_cat] = \
                            category.related_categories.get(other_cat, 0.0) + 0.1
        
        # Record evolution event
        self.evolution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "detected_categories": relevant_categories,
            "themes": detected_themes,
            "transcript_preview": transcript[:100]
        })
        
        # Potentially create new categories if patterns emerge
        self._check_for_emerging_categories(detected_themes, relevant_categories)
        
        return relevant_categories
    
    def _check_for_emerging_categories(self, themes: List[str], existing_cats: List[str]):
        """Check if new categories should emerge from usage patterns."""
        # This is where ML could identify new category needs
        # For now, we'll use simple heuristics
        
        # If themes don't match well with existing categories, consider new ones
        unmatched_themes = []
        for theme in themes:
            theme_matched = False
            for cat_id in existing_cats:
                cat = self._get_category(cat_id)
                if cat and theme.lower() in cat.name.lower():
                    theme_matched = True
                    break
            
            if not theme_matched:
                unmatched_themes.append(theme)
        
        # Log potential new categories for manual review
        if unmatched_themes:
            logger.info(f"Potential new categories needed for themes: {unmatched_themes}")
    
    def get_category_insights(self) -> Dict[str, Any]:
        """Get insights about category usage and evolution."""
        all_categories = {
            **self.work_categories,
            **self.personal_categories,
            **self.workflow_categories
        }
        
        # Calculate usage statistics
        total_usage = sum(cat.usage_count for cat in all_categories.values())
        
        # Find most used categories
        most_used = sorted(
            all_categories.items(),
            key=lambda x: x[1].usage_count,
            reverse=True
        )[:10]
        
        # Find strongest relationships
        relationships = []
        for cat_id, cat in all_categories.items():
            for related_id, strength in cat.related_categories.items():
                if strength > 0.3:  # Significant relationship
                    relationships.append({
                        "from": cat_id,
                        "to": related_id,
                        "strength": strength
                    })
        
        return {
            "total_categories": len(all_categories),
            "total_usage": total_usage,
            "most_used_categories": [
                {"id": cat_id, "name": cat.name, "usage": cat.usage_count}
                for cat_id, cat in most_used
            ],
            "strong_relationships": sorted(
                relationships,
                key=lambda x: x["strength"],
                reverse=True
            )[:20],
            "evolution_events": len(self.evolution_history)
        }


@dataclass
class EnhancedTheoryOfMind:
    """Enhanced Theory of Mind with knowledge architecture and persona hooks."""
    
    # Core identity (from v1)
    identity: Dict[str, Any] = None
    temporal_context: Dict[str, Any] = None
    decision_model: Dict[str, Any] = None
    
    # Enhanced knowledge architecture
    knowledge_graph: Dict[str, List[str]] = None  # concept -> related concepts
    learned_patterns: Dict[str, Dict[str, Any]] = None  # pattern type -> details
    category_system: GranularCategory = None
    
    # Persona voice settings
    persona_voice: Dict[str, Any] = None
    
    # Meta information
    last_updated: str = None
    update_count: int = 0
    confidence_score: float = 0.5
    learning_rate: float = 0.1  # How quickly the system adapts
    
    def __post_init__(self):
        """Initialize with enhanced defaults."""
        # Initialize v1 defaults
        if self.identity is None:
            self.identity = {
                "core_values": [],
                "professional_identity": "Professional",
                "skills_focus": [],
                "confidence": 0.5,
                # New identity aspects
                "work_style": "balanced",
                "communication_preferences": [],
                "growth_edges": []
            }
        
        if self.temporal_context is None:
            self.temporal_context = {
                "current_week": {
                    "week_of": datetime.now().strftime("%Y-%m-%d"),
                    "stated_goals": [],
                    "detected_themes": [],
                    "energy_level": "unknown",
                    "category_focus": []  # Which categories are active
                },
                "current_quarter": {
                    "projects": [],
                    "key_relationships": {},
                    "strategic_priorities": []
                },
                "long_term_arcs": {},
                "pattern_observations": []  # Noticed patterns over time
            }
        
        if self.decision_model is None:
            self.decision_model = {
                "time_allocation_preferences": {
                    "deep_work": 0.4,
                    "meetings": 0.3,
                    "learning": 0.2,
                    "networking": 0.1
                },
                "project_evaluation_criteria": [],
                "energy_management": {
                    "peak_hours": [],
                    "recovery_needs": {},
                    "sustainability_factors": []
                }
            }
        
        # Initialize enhanced features
        if self.knowledge_graph is None:
            self.knowledge_graph = defaultdict(list)
        
        if self.learned_patterns is None:
            self.learned_patterns = {
                "work_patterns": {},
                "communication_patterns": {},
                "stress_patterns": {},
                "growth_patterns": {}
            }
        
        if self.category_system is None:
            self.category_system = GranularCategory()
        
        if self.persona_voice is None:
            self.persona_voice = {
                "tone": "professional_warm",  # professional_warm, direct, supportive, analytical
                "formality": 0.7,  # 0-1 scale
                "emoji_usage": False,
                "communication_style": "balanced",  # balanced, concise, detailed
                "preferred_frameworks": []  # Mental models this person uses
            }
        
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()
    
    def learn_from_interaction(self, transcript: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Learn and evolve from each interaction.
        
        Returns learning insights.
        """
        learning_insights = {
            "patterns_detected": [],
            "knowledge_connections": [],
            "category_evolution": [],
            "confidence_changes": {}
        }
        
        # Evolve categories
        detected_categories = self.category_system.evolve_category(
            transcript, 
            analysis.get('detected_themes', [])
        )
        learning_insights["category_evolution"] = detected_categories
        
        # Update knowledge graph
        themes = analysis.get('detected_themes', [])
        for i, theme in enumerate(themes):
            for other_theme in themes[i+1:]:
                if other_theme not in self.knowledge_graph[theme]:
                    self.knowledge_graph[theme].append(other_theme)
                if theme not in self.knowledge_graph[other_theme]:
                    self.knowledge_graph[other_theme].append(theme)
        
        # Detect patterns
        self._detect_patterns(transcript, analysis, learning_insights)
        
        # Update confidence based on consistency
        self._update_confidence(analysis, learning_insights)
        
        return learning_insights
    
    def _detect_patterns(self, transcript: str, analysis: Dict[str, Any], insights: Dict[str, Any]):
        """Detect behavioral and work patterns."""
        # Work timing patterns
        current_hour = datetime.utcnow().hour
        energy = analysis.get('energy_indicators', 'unknown')
        
        if energy != 'unknown':
            work_patterns = self.learned_patterns["work_patterns"]
            hour_key = f"hour_{current_hour}"
            
            if hour_key not in work_patterns:
                work_patterns[hour_key] = {"high": 0, "moderate": 0, "low": 0, "stressed": 0}
            
            work_patterns[hour_key][energy] += 1
            
            # Check if this hour consistently shows high energy
            total = sum(work_patterns[hour_key].values())
            if total > 5 and work_patterns[hour_key]["high"] / total > 0.6:
                insights["patterns_detected"].append(f"High energy period detected around hour {current_hour}")
        
        # Communication patterns
        if "meeting" in transcript.lower() or "call" in transcript.lower():
            comm_patterns = self.learned_patterns["communication_patterns"]
            comm_patterns["meeting_mentions"] = comm_patterns.get("meeting_mentions", 0) + 1
        
        # Stress patterns
        if analysis.get('urgency_level') == 'high' or energy == 'stressed':
            stress_patterns = self.learned_patterns["stress_patterns"]
            stress_patterns["high_urgency_count"] = stress_patterns.get("high_urgency_count", 0) + 1
            
            # Track what themes correlate with stress
            for theme in analysis.get('detected_themes', []):
                stress_patterns[f"theme_{theme}"] = stress_patterns.get(f"theme_{theme}", 0) + 1
    
    def _update_confidence(self, analysis: Dict[str, Any], insights: Dict[str, Any]):
        """Update confidence scores based on consistency."""
        # Check if current observations align with our model
        alignment = analysis.get('alignment_with_goals', 'neutral')
        
        if alignment == 'aligned':
            self.confidence_score = min(1.0, self.confidence_score + self.learning_rate * 0.1)
            insights["confidence_changes"]["overall"] = "+0.1 (aligned behavior)"
        elif alignment == 'misaligned':
            # Misalignment might mean our model needs updating
            self.confidence_score = max(0.3, self.confidence_score - self.learning_rate * 0.05)
            insights["confidence_changes"]["overall"] = "-0.05 (model adjustment needed)"
    
    def get_personalized_response(self, base_response: str) -> str:
        """Apply persona voice settings to response.
        
        This is a hook for future persona integration.
        """
        # For now, return base response
        # In future, this would transform the response based on persona settings
        return base_response
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'user_id': USER_ID,
            'identity': self.identity,
            'temporal_context': self.temporal_context,
            'decision_model': self.decision_model,
            'knowledge_graph': dict(self.knowledge_graph),
            'learned_patterns': self.learned_patterns,
            'category_system': {
                'work_categories': {k: asdict(v) for k, v in self.category_system.work_categories.items()},
                'personal_categories': {k: asdict(v) for k, v in self.category_system.personal_categories.items()},
                'workflow_categories': {k: asdict(v) for k, v in self.category_system.workflow_categories.items()},
                'evolution_history': self.category_system.evolution_history[-100:]  # Keep last 100 events
            },
            'persona_voice': self.persona_voice,
            'last_updated': self.last_updated,
            'update_count': self.update_count,
            'confidence_score': self.confidence_score,
            'learning_rate': self.learning_rate
        }


class ExecutiveAssistantAgentV2(BaseAgent):
    """Enhanced Executive Assistant with learning and evolution capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tom_table = dynamodb.Table(THEORY_OF_MIND_TABLE)
        self.category_table = dynamodb.Table(CATEGORY_EVOLUTION_TABLE)
        self.knowledge_table = dynamodb.Table(KNOWLEDGE_GRAPH_TABLE)
    
    def load_theory_of_mind(self) -> EnhancedTheoryOfMind:
        """Load enhanced Theory of Mind from DynamoDB."""
        try:
            response = self.tom_table.get_item(Key={'user_id': USER_ID})
            if 'Item' in response:
                # Reconstruct category system
                cat_data = response['Item'].get('category_system', {})
                category_system = GranularCategory()
                
                # Restore categories
                for cat_dict in ['work_categories', 'personal_categories', 'workflow_categories']:
                    if cat_dict in cat_data:
                        for cat_id, cat_info in cat_data[cat_dict].items():
                            node = CategoryNode(**cat_info)
                            getattr(category_system, cat_dict)[cat_id] = node
                
                category_system.evolution_history = cat_data.get('evolution_history', [])
                
                # Create enhanced theory
                theory = EnhancedTheoryOfMind(
                    identity=response['Item'].get('identity'),
                    temporal_context=response['Item'].get('temporal_context'),
                    decision_model=response['Item'].get('decision_model'),
                    knowledge_graph=response['Item'].get('knowledge_graph'),
                    learned_patterns=response['Item'].get('learned_patterns'),
                    category_system=category_system,
                    persona_voice=response['Item'].get('persona_voice'),
                    last_updated=response['Item'].get('last_updated'),
                    update_count=response['Item'].get('update_count', 0),
                    confidence_score=response['Item'].get('confidence_score', 0.5),
                    learning_rate=response['Item'].get('learning_rate', 0.1)
                )
                return theory
            else:
                logger.info("Initializing new Enhanced Theory of Mind")
                return EnhancedTheoryOfMind()
        except Exception as e:
            logger.error(f"Failed to load Theory of Mind: {e}")
            return EnhancedTheoryOfMind()
    
    def save_theory_of_mind(self, theory: EnhancedTheoryOfMind) -> None:
        """Save enhanced Theory of Mind to DynamoDB."""
        try:
            theory.last_updated = datetime.utcnow().isoformat()
            theory.update_count += 1
            
            self.tom_table.put_item(Item=theory.to_dict())
            logger.info(f"Saved Enhanced Theory of Mind (update #{theory.update_count})")
            
            # Also store category insights separately for analytics
            insights = theory.category_system.get_category_insights()
            self.category_table.put_item(
                Item={
                    'user_id': USER_ID,
                    'timestamp': theory.last_updated,
                    'insights': insights
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to save Theory of Mind: {e}")
    
    async def analyze_with_learning(
        self,
        transcript: str,
        theory: EnhancedTheoryOfMind
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Analyze transcript and learn from it.
        
        Returns (analysis, learning_insights).
        """
        # First, get base analysis (reuse v1 logic)
        from .executive_assistant_agent import analyze_transcript_with_context
        analysis = await analyze_transcript_with_context(transcript, theory)
        
        # Then apply learning
        learning_insights = theory.learn_from_interaction(transcript, analysis)
        
        # Enhance analysis with category information
        analysis['detected_categories'] = learning_insights['category_evolution']
        analysis['category_insights'] = theory.category_system.get_category_insights()
        
        # Apply persona voice to key insights
        if analysis.get('key_insights'):
            analysis['key_insights'] = [
                theory.get_personalized_response(insight)
                for insight in analysis['key_insights']
            ]
        
        return analysis, learning_insights
    
    @requires_aws
    def process_transcript(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcript with enhanced learning capabilities."""
        transcript = event['transcript']
        s3_bucket = event['bucket']
        s3_key = event['key']
        
        # Load current theory
        theory = self.load_theory_of_mind()
        logger.info(f"Loaded Enhanced Theory of Mind (confidence: {theory.confidence_score})")
        
        # Run async analysis with learning
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Analyze and learn
            analysis, learning_insights = loop.run_until_complete(
                self.analyze_with_learning(transcript, theory)
            )
            
            # Save updated theory
            self.save_theory_of_mind(theory)
            
            # Create enhanced executive document
            document = self._create_enhanced_document(
                transcript, analysis, theory, learning_insights,
                {"s3_key": s3_key, "processing_timestamp": datetime.utcnow().isoformat()}
            )
            
            # Store results
            output_key = s3_key.replace('transcripts/', 'outputs/executive_assistant_v2/').replace('.txt', '_enhanced.json')
            self.store_result(document, output_key)
            
            # Log significant learnings
            if learning_insights.get('patterns_detected'):
                logger.info(f"New patterns detected: {learning_insights['patterns_detected']}")
            
            return {
                "status": "success",
                "output_key": output_key,
                "categories_detected": len(analysis.get('detected_categories', [])),
                "learning_occurred": bool(learning_insights.get('patterns_detected'))
            }
            
        finally:
            loop.close()
    
    def _create_enhanced_document(
        self,
        transcript: str,
        analysis: Dict[str, Any],
        theory: EnhancedTheoryOfMind,
        learning_insights: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create enhanced executive document with learning insights."""
        # Start with base document structure
        from .executive_assistant_agent import create_executive_document
        base_doc = create_executive_document(transcript, analysis, theory, metadata)
        
        # Enhance with v2 features
        base_doc['enhanced_analysis'] = {
            'detected_categories': analysis.get('detected_categories', []),
            'category_hierarchy': self._build_category_hierarchy(analysis.get('detected_categories', [])),
            'learning_insights': learning_insights,
            'knowledge_connections': self._find_knowledge_connections(
                analysis.get('detected_themes', []),
                theory.knowledge_graph
            ),
            'pattern_observations': theory.learned_patterns
        }
        
        # Add actionable insights based on patterns
        base_doc['intelligent_recommendations'] = self._generate_recommendations(
            analysis, theory, learning_insights
        )
        
        return base_doc
    
    def _build_category_hierarchy(self, category_ids: List[str]) -> Dict[str, Any]:
        """Build hierarchical view of detected categories."""
        hierarchy = {}
        
        for cat_id in category_ids:
            parts = cat_id.split('.')
            current = hierarchy
            
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        return hierarchy
    
    def _find_knowledge_connections(
        self,
        themes: List[str],
        knowledge_graph: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Find connections in knowledge graph."""
        connections = []
        
        for theme in themes:
            if theme in knowledge_graph:
                for connected in knowledge_graph[theme]:
                    connections.append({
                        "from": theme,
                        "to": connected,
                        "type": "theme_correlation"
                    })
        
        return connections[:10]  # Top 10 connections
    
    def _generate_recommendations(
        self,
        analysis: Dict[str, Any],
        theory: EnhancedTheoryOfMind,
        learning_insights: Dict[str, Any]
    ) -> List[str]:
        """Generate intelligent recommendations based on patterns."""
        recommendations = []
        
        # Energy-based recommendations
        energy = analysis.get('energy_indicators', 'unknown')
        if energy == 'low' or energy == 'stressed':
            recommendations.append(
                "Consider scheduling recovery time. Your energy indicators suggest fatigue."
            )
        
        # Category-based recommendations
        categories = analysis.get('detected_categories', [])
        if 'work.engineering.debugging' in categories and energy != 'high':
            recommendations.append(
                "Debugging work detected during non-peak energy. Consider rescheduling complex debugging to high-energy periods."
            )
        
        # Pattern-based recommendations
        patterns = learning_insights.get('patterns_detected', [])
        for pattern in patterns:
            if 'High energy period' in pattern:
                recommendations.append(
                    f"Leverage your {pattern} for critical work and deep thinking tasks."
                )
        
        # Goal alignment recommendations
        if analysis.get('alignment_with_goals') == 'misaligned':
            recommendations.append(
                "This work appears misaligned with stated goals. Consider if this is a necessary deviation or requires goal adjustment."
            )
        
        return recommendations


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for ExecutiveAssistantV2."""
    agent = ExecutiveAssistantAgentV2()
    
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
                'message': 'Transcripts processed with enhanced learning',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }