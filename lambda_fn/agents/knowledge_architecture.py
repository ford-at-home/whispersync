"""Unified Knowledge Architecture for WhisperSync Agents.

This module provides a shared knowledge system that:
- Learns from all agent interactions
- Identifies cross-agent patterns and insights
- Enables knowledge transfer between agents
- Supports persona-based responses
- Grows and evolves with usage
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from collections import defaultdict
import networkx as nx
import boto3

logger = logging.getLogger(__name__)

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Configuration
KNOWLEDGE_GRAPH_TABLE = os.environ.get('UNIFIED_KNOWLEDGE_GRAPH_TABLE', 'WhisperSync-KnowledgeGraph')
INSIGHTS_TABLE = os.environ.get('UNIFIED_INSIGHTS_TABLE', 'WhisperSync-Insights')
PATTERNS_TABLE = os.environ.get('UNIFIED_PATTERNS_TABLE', 'WhisperSync-Patterns')


@dataclass
class KnowledgeNode:
    """Node in the knowledge graph representing a concept, entity, or pattern."""
    
    node_id: str
    node_type: str  # concept, entity, pattern, insight
    content: str
    
    # Metadata
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    importance_score: float = 0.5
    
    # Connections
    connected_nodes: Dict[str, float] = field(default_factory=dict)  # node_id -> strength
    
    # Source tracking
    source_agents: List[str] = field(default_factory=list)
    source_contexts: List[str] = field(default_factory=list)
    
    # Evolution
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    
    def strengthen_connection(self, other_node_id: str, amount: float = 0.1):
        """Strengthen connection to another node."""
        current = self.connected_nodes.get(other_node_id, 0.0)
        self.connected_nodes[other_node_id] = min(1.0, current + amount)
    
    def update_importance(self, access_context: str):
        """Update importance based on access patterns."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        
        # Importance increases with access frequency and recency
        recency_factor = 1.0 / (1 + (datetime.utcnow() - self.created_at).days)
        frequency_factor = min(1.0, self.access_count / 100)
        self.importance_score = (recency_factor + frequency_factor) / 2


@dataclass
class CrossAgentInsight:
    """Insights that emerge from cross-agent patterns."""
    
    insight_id: str
    insight_type: str  # behavioral, temporal, relational, systemic
    description: str
    
    # Supporting evidence
    supporting_patterns: List[str] = field(default_factory=list)
    agent_sources: List[str] = field(default_factory=list)
    confidence: float = 0.5
    
    # Temporal aspects
    first_observed: datetime = field(default_factory=datetime.utcnow)
    last_confirmed: datetime = field(default_factory=datetime.utcnow)
    observation_count: int = 1
    
    # Impact
    affected_areas: List[str] = field(default_factory=list)  # work, personal, spiritual
    actionability: float = 0.5  # How actionable is this insight
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)


@dataclass
class UnifiedPattern:
    """Pattern that spans across multiple agents and contexts."""
    
    pattern_id: str
    pattern_name: str
    pattern_type: str  # behavioral, cyclical, causal, correlational
    
    # Pattern definition
    trigger_conditions: List[str] = field(default_factory=list)
    manifestations: Dict[str, List[str]] = field(default_factory=dict)  # agent -> observations
    
    # Strength and validity
    occurrence_count: int = 0
    strength: float = 0.5
    last_observed: Optional[datetime] = None
    
    # Cross-agent relevance
    relevant_agents: List[str] = field(default_factory=list)
    cross_references: Dict[str, str] = field(default_factory=dict)  # agent -> specific pattern
    
    # Predictive power
    predictions_made: int = 0
    predictions_accurate: int = 0
    predictive_confidence: float = 0.0


class KnowledgeArchitecture:
    """Unified knowledge system for all WhisperSync agents."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.insights: Dict[str, CrossAgentInsight] = {}
        self.patterns: Dict[str, UnifiedPattern] = {}
        
        # Tables
        self.graph_table = dynamodb.Table(KNOWLEDGE_GRAPH_TABLE)
        self.insights_table = dynamodb.Table(INSIGHTS_TABLE)
        self.patterns_table = dynamodb.Table(PATTERNS_TABLE)
        
        # Load existing knowledge
        self._load_knowledge()
    
    def _load_knowledge(self):
        """Load knowledge from DynamoDB."""
        try:
            # Load nodes
            response = self.graph_table.scan()
            for item in response.get('Items', []):
                node = self._deserialize_node(item)
                self.nodes[node.node_id] = node
                self.graph.add_node(node.node_id, data=node)
            
            # Rebuild graph edges
            for node_id, node in self.nodes.items():
                for connected_id, strength in node.connected_nodes.items():
                    if connected_id in self.nodes:
                        self.graph.add_edge(node_id, connected_id, weight=strength)
            
            # Load insights
            response = self.insights_table.scan()
            for item in response.get('Items', []):
                insight = self._deserialize_insight(item)
                self.insights[insight.insight_id] = insight
            
            # Load patterns
            response = self.patterns_table.scan()
            for item in response.get('Items', []):
                pattern = self._deserialize_pattern(item)
                self.patterns[pattern.pattern_id] = pattern
                
            logger.info(f"Loaded knowledge: {len(self.nodes)} nodes, {len(self.insights)} insights, {len(self.patterns)} patterns")
            
        except Exception as e:
            logger.warning(f"Failed to load knowledge: {e}")
    
    def add_knowledge(
        self,
        content: str,
        node_type: str,
        source_agent: str,
        context: Dict[str, Any]
    ) -> KnowledgeNode:
        """Add new knowledge to the system."""
        # Create node ID based on content hash
        node_id = f"{node_type}_{hash(content) % 1000000}"
        
        if node_id in self.nodes:
            # Update existing node
            node = self.nodes[node_id]
            node.access_count += 1
            node.update_importance(source_agent)
            if source_agent not in node.source_agents:
                node.source_agents.append(source_agent)
        else:
            # Create new node
            node = KnowledgeNode(
                node_id=node_id,
                node_type=node_type,
                content=content,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                source_agents=[source_agent],
                source_contexts=[json.dumps(context)]
            )
            self.nodes[node_id] = node
            self.graph.add_node(node_id, data=node)
        
        # Find and create connections
        self._create_connections(node, context)
        
        # Check for emerging patterns
        self._check_patterns(node, source_agent, context)
        
        # Generate insights if applicable
        self._generate_insights(node, source_agent, context)
        
        return node
    
    def _create_connections(self, node: KnowledgeNode, context: Dict[str, Any]):
        """Create connections to related nodes."""
        # Find semantically related nodes
        related_nodes = self._find_related_nodes(node.content, node.node_type)
        
        for related_id, similarity in related_nodes:
            if related_id != node.node_id:
                # Create bidirectional connection
                node.strengthen_connection(related_id, similarity)
                self.nodes[related_id].strengthen_connection(node.node_id, similarity)
                
                # Update graph
                self.graph.add_edge(node.node_id, related_id, weight=similarity)
                self.graph.add_edge(related_id, node.node_id, weight=similarity)
    
    def _find_related_nodes(self, content: str, node_type: str) -> List[Tuple[str, float]]:
        """Find nodes related to the given content."""
        related = []
        content_lower = content.lower()
        
        for node_id, node in self.nodes.items():
            if node_id == f"{node_type}_{hash(content) % 1000000}":
                continue
            
            # Simple similarity based on shared words
            node_content_lower = node.content.lower()
            shared_words = set(content_lower.split()) & set(node_content_lower.split())
            
            if shared_words:
                similarity = len(shared_words) / max(len(content_lower.split()), len(node_content_lower.split()))
                if similarity > 0.2:  # Threshold
                    related.append((node_id, similarity))
        
        # Sort by similarity and return top 5
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:5]
    
    def _check_patterns(self, node: KnowledgeNode, source_agent: str, context: Dict[str, Any]):
        """Check if this node contributes to any patterns."""
        # Look for temporal patterns
        if 'timestamp' in context:
            self._check_temporal_patterns(node, source_agent, context)
        
        # Look for behavioral patterns
        if node.node_type == 'behavior' or 'action' in context:
            self._check_behavioral_patterns(node, source_agent, context)
        
        # Look for causal patterns
        if 'cause' in context or 'effect' in context:
            self._check_causal_patterns(node, source_agent, context)
    
    def _check_temporal_patterns(self, node: KnowledgeNode, source_agent: str, context: Dict[str, Any]):
        """Check for time-based patterns."""
        # Example: Check if certain activities happen at certain times
        hour = datetime.fromisoformat(context['timestamp']).hour
        
        pattern_id = f"temporal_hour_{hour}_{node.node_type}"
        
        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = UnifiedPattern(
                pattern_id=pattern_id,
                pattern_name=f"{node.node_type} at hour {hour}",
                pattern_type="temporal",
                trigger_conditions=[f"hour == {hour}"],
                relevant_agents=[source_agent]
            )
        
        pattern = self.patterns[pattern_id]
        pattern.occurrence_count += 1
        pattern.last_observed = datetime.utcnow()
        
        if source_agent not in pattern.manifestations:
            pattern.manifestations[source_agent] = []
        pattern.manifestations[source_agent].append(node.content[:50])
        
        # Update strength based on consistency
        pattern.strength = min(1.0, pattern.occurrence_count / 10)
    
    def _check_behavioral_patterns(self, node: KnowledgeNode, source_agent: str, context: Dict[str, Any]):
        """Check for behavioral patterns."""
        # This would analyze behavior sequences and identify patterns
        pass
    
    def _check_causal_patterns(self, node: KnowledgeNode, source_agent: str, context: Dict[str, Any]):
        """Check for cause-effect patterns."""
        # This would track causal relationships
        pass
    
    def _generate_insights(self, node: KnowledgeNode, source_agent: str, context: Dict[str, Any]):
        """Generate cross-agent insights."""
        # Check if this node, combined with others, reveals insights
        
        # Example: Work-life balance insight
        if source_agent == "ExecutiveAssistant" and "overtime" in node.content.lower():
            # Check if SpiritualAdvisor has related stress indicators
            stress_nodes = [n for n in self.nodes.values() 
                          if "SpiritualAdvisor" in n.source_agents and "stress" in n.content.lower()]
            
            if stress_nodes:
                insight_id = "work_life_balance_concern"
                if insight_id not in self.insights:
                    self.insights[insight_id] = CrossAgentInsight(
                        insight_id=insight_id,
                        insight_type="behavioral",
                        description="Overtime work correlating with increased stress levels",
                        agent_sources=["ExecutiveAssistant", "SpiritualAdvisor"],
                        affected_areas=["work", "personal"],
                        recommendations=[
                            "Consider setting firmer work boundaries",
                            "Schedule regular breaks and recovery time",
                            "Monitor energy levels during extended work periods"
                        ]
                    )
                else:
                    # Update existing insight
                    insight = self.insights[insight_id]
                    insight.observation_count += 1
                    insight.last_confirmed = datetime.utcnow()
                    insight.confidence = min(1.0, insight.observation_count / 5)
    
    def query_knowledge(
        self,
        query_type: str,
        query_params: Dict[str, Any],
        requesting_agent: str
    ) -> Dict[str, Any]:
        """Query the knowledge system."""
        results = {
            "nodes": [],
            "insights": [],
            "patterns": [],
            "recommendations": []
        }
        
        if query_type == "related_to":
            # Find nodes related to a concept
            content = query_params.get("content", "")
            related = self._find_related_nodes(content, "any")
            results["nodes"] = [self.nodes[node_id] for node_id, _ in related if node_id in self.nodes]
        
        elif query_type == "insights_for_agent":
            # Get insights relevant to an agent
            results["insights"] = [
                insight for insight in self.insights.values()
                if requesting_agent in insight.agent_sources or 
                   any(area in insight.affected_areas for area in query_params.get("areas", []))
            ]
        
        elif query_type == "active_patterns":
            # Get currently active patterns
            cutoff = datetime.utcnow() - timedelta(days=7)
            results["patterns"] = [
                pattern for pattern in self.patterns.values()
                if pattern.last_observed and pattern.last_observed > cutoff
            ]
        
        elif query_type == "recommendations":
            # Get personalized recommendations
            results["recommendations"] = self._generate_recommendations(
                requesting_agent,
                query_params.get("context", {})
            )
        
        return results
    
    def _generate_recommendations(self, agent: str, context: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations based on knowledge."""
        recommendations = []
        
        # Check relevant insights
        for insight in self.insights.values():
            if agent in insight.agent_sources and insight.confidence > 0.6:
                recommendations.extend(insight.recommendations)
        
        # Check active patterns
        for pattern in self.patterns.values():
            if agent in pattern.relevant_agents and pattern.strength > 0.7:
                if pattern.pattern_type == "temporal":
                    recommendations.append(
                        f"Pattern detected: {pattern.pattern_name}. Consider optimizing for this timing."
                    )
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:5]  # Top 5 recommendations
    
    def apply_persona_transformation(
        self,
        content: str,
        persona_settings: Dict[str, Any]
    ) -> str:
        """Transform content based on persona settings."""
        # This is a hook for persona-based content transformation
        # Would integrate with a more sophisticated NLG system
        
        tone = persona_settings.get("tone", "neutral")
        
        if tone == "warm_encouraging":
            # Add encouraging phrases
            if "challenge" in content.lower():
                content = content.replace("challenge", "growth opportunity")
        
        elif tone == "direct_practical":
            # Remove fluff, focus on actionables
            content = content.replace("might consider", "should")
            content = content.replace("perhaps", "")
        
        return content
    
    def get_agent_knowledge_summary(self, agent_name: str) -> Dict[str, Any]:
        """Get knowledge summary for a specific agent."""
        agent_nodes = [n for n in self.nodes.values() if agent_name in n.source_agents]
        agent_insights = [i for i in self.insights.values() if agent_name in i.agent_sources]
        agent_patterns = [p for p in self.patterns.values() if agent_name in p.relevant_agents]
        
        return {
            "agent": agent_name,
            "total_contributions": len(agent_nodes),
            "insights_generated": len(agent_insights),
            "patterns_involved": len(agent_patterns),
            "top_concepts": self._get_top_concepts(agent_nodes),
            "knowledge_growth": self._calculate_knowledge_growth(agent_nodes)
        }
    
    def _get_top_concepts(self, nodes: List[KnowledgeNode]) -> List[Dict[str, Any]]:
        """Get most important concepts from nodes."""
        # Sort by importance and access count
        sorted_nodes = sorted(
            nodes,
            key=lambda n: n.importance_score * n.access_count,
            reverse=True
        )
        
        return [
            {
                "content": node.content[:100],
                "type": node.node_type,
                "importance": node.importance_score,
                "connections": len(node.connected_nodes)
            }
            for node in sorted_nodes[:5]
        ]
    
    def _calculate_knowledge_growth(self, nodes: List[KnowledgeNode]) -> Dict[str, Any]:
        """Calculate how knowledge is growing over time."""
        if not nodes:
            return {"growth_rate": 0.0, "trend": "stable"}
        
        # Group by date
        nodes_by_date = defaultdict(int)
        for node in nodes:
            date_key = node.created_at.date()
            nodes_by_date[date_key] += 1
        
        # Calculate growth trend
        dates = sorted(nodes_by_date.keys())
        if len(dates) < 2:
            return {"growth_rate": 0.0, "trend": "insufficient_data"}
        
        # Simple growth calculation
        recent_avg = sum(nodes_by_date[d] for d in dates[-7:]) / min(7, len(dates))
        older_avg = sum(nodes_by_date[d] for d in dates[:-7]) / max(1, len(dates) - 7)
        
        growth_rate = (recent_avg - older_avg) / max(older_avg, 1)
        
        trend = "growing" if growth_rate > 0.1 else "stable" if growth_rate > -0.1 else "declining"
        
        return {
            "growth_rate": growth_rate,
            "trend": trend,
            "recent_daily_average": recent_avg,
            "total_days": len(dates)
        }
    
    def save(self):
        """Save knowledge to DynamoDB."""
        try:
            # Save nodes
            for node in self.nodes.values():
                self.graph_table.put_item(Item=self._serialize_node(node))
            
            # Save insights
            for insight in self.insights.values():
                self.insights_table.put_item(Item=self._serialize_insight(insight))
            
            # Save patterns
            for pattern in self.patterns.values():
                self.patterns_table.put_item(Item=self._serialize_pattern(pattern))
                
            logger.info(f"Saved knowledge: {len(self.nodes)} nodes, {len(self.insights)} insights, {len(self.patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge: {e}")
    
    def _serialize_node(self, node: KnowledgeNode) -> Dict[str, Any]:
        """Serialize node for storage."""
        data = asdict(node)
        data['created_at'] = node.created_at.isoformat()
        data['last_accessed'] = node.last_accessed.isoformat()
        return data
    
    def _deserialize_node(self, data: Dict[str, Any]) -> KnowledgeNode:
        """Deserialize node from storage."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return KnowledgeNode(**data)
    
    def _serialize_insight(self, insight: CrossAgentInsight) -> Dict[str, Any]:
        """Serialize insight for storage."""
        data = asdict(insight)
        data['first_observed'] = insight.first_observed.isoformat()
        data['last_confirmed'] = insight.last_confirmed.isoformat()
        return data
    
    def _deserialize_insight(self, data: Dict[str, Any]) -> CrossAgentInsight:
        """Deserialize insight from storage."""
        data['first_observed'] = datetime.fromisoformat(data['first_observed'])
        data['last_confirmed'] = datetime.fromisoformat(data['last_confirmed'])
        return CrossAgentInsight(**data)
    
    def _serialize_pattern(self, pattern: UnifiedPattern) -> Dict[str, Any]:
        """Serialize pattern for storage."""
        data = asdict(pattern)
        if pattern.last_observed:
            data['last_observed'] = pattern.last_observed.isoformat()
        return data
    
    def _deserialize_pattern(self, data: Dict[str, Any]) -> UnifiedPattern:
        """Deserialize pattern from storage."""
        if data.get('last_observed'):
            data['last_observed'] = datetime.fromisoformat(data['last_observed'])
        return UnifiedPattern(**data)


# Singleton instance for shared access
_knowledge_instance: Optional[KnowledgeArchitecture] = None


def get_knowledge_architecture() -> KnowledgeArchitecture:
    """Get or create the singleton knowledge architecture instance."""
    global _knowledge_instance
    if _knowledge_instance is None:
        _knowledge_instance = KnowledgeArchitecture()
    return _knowledge_instance


# Convenience functions for agents
def add_agent_knowledge(
    content: str,
    node_type: str,
    source_agent: str,
    context: Dict[str, Any]
) -> KnowledgeNode:
    """Add knowledge from an agent."""
    ka = get_knowledge_architecture()
    return ka.add_knowledge(content, node_type, source_agent, context)


def query_agent_knowledge(
    query_type: str,
    query_params: Dict[str, Any],
    requesting_agent: str
) -> Dict[str, Any]:
    """Query knowledge for an agent."""
    ka = get_knowledge_architecture()
    return ka.query_knowledge(query_type, query_params, requesting_agent)


def get_agent_insights(agent_name: str) -> List[CrossAgentInsight]:
    """Get insights relevant to an agent."""
    ka = get_knowledge_architecture()
    return [i for i in ka.insights.values() if agent_name in i.agent_sources]


def save_knowledge():
    """Save the knowledge architecture."""
    ka = get_knowledge_architecture()
    ka.save()