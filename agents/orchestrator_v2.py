"""Orchestrator V2 - Clean routing logic for three memory buckets.

This is a complete reimplementation of the orchestrator that cleanly routes
voice transcripts to one of three memory buckets:
1. Cool New Ideas → GitHub repository creation
2. Tactical Reflections → Work journal insights
3. Personal Memories → Emotionally-aware diary

DESIGN PHILOSOPHY:
- Clear separation of concerns
- AI-first classification with graceful fallbacks
- Multi-agent support for complex thoughts
- Learning from user feedback
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import boto3

from .memory_classifier import (
    MemoryClassifier, MemoryBucket, ClassificationResult
)
from .diary_processor import DiaryProcessor
from .base import BaseAgent
from .utils import (
    ProcessingMetrics, AgentResult, generate_correlation_id,
    PerformanceMonitor, ValidationUtils
)

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Represents a routing decision for a transcript."""
    primary_agent: str
    primary_bucket: MemoryBucket
    confidence: float
    secondary_agents: List[Tuple[str, float]]  # [(agent, confidence), ...]
    reasoning: str
    requires_confirmation: bool
    processing_hints: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'primary_agent': self.primary_agent,
            'primary_bucket': self.primary_bucket.value,
            'confidence': self.confidence,
            'secondary_agents': self.secondary_agents,
            'reasoning': self.reasoning,
            'requires_confirmation': self.requires_confirmation,
            'processing_hints': self.processing_hints
        }


class OrchestratorV2:
    """Clean orchestrator for routing voice transcripts to memory buckets."""
    
    def __init__(
        self,
        anthropic_api_key: str,
        github_token: Optional[str] = None,
        s3_bucket: str = "voice-mcp",
        correlation_id: Optional[str] = None
    ):
        """Initialize the orchestrator.
        
        Args:
            anthropic_api_key: API key for Claude
            github_token: GitHub personal access token
            s3_bucket: S3 bucket for storage
            correlation_id: Request correlation ID
        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self.classifier = MemoryClassifier(anthropic_api_key=anthropic_api_key)
        self.s3_bucket = s3_bucket
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3')
        
        # Agent configuration
        self.agent_config = {
            'diary': {
                'processor': DiaryProcessor(
                    anthropic_api_key=anthropic_api_key,
                    s3_bucket=s3_bucket
                ),
                'bucket': MemoryBucket.PERSONAL
            },
            'work': {
                'bucket': MemoryBucket.TACTICAL,
                'requires': ['boto3']
            },
            'github': {
                'bucket': MemoryBucket.COOL_IDEAS,
                'requires': ['github_token']
            }
        }
        
        # Store tokens
        self.github_token = github_token
        self.anthropic_api_key = anthropic_api_key
        
        logger.info(f"Initialized OrchestratorV2 with correlation_id: {self.correlation_id}")
    
    async def route_transcript(
        self,
        transcript: str,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Route a transcript to the appropriate memory bucket and agent.
        
        Args:
            transcript: Voice transcript to route
            source_metadata: Optional metadata about the source
            
        Returns:
            Complete routing and processing results
        """
        with PerformanceMonitor("transcript_routing") as monitor:
            # Validate input
            is_valid, error_msg = ValidationUtils.validate_transcript(transcript)
            if not is_valid:
                logger.error(f"Invalid transcript: {error_msg}")
                return self._error_response(error_msg)
            
            # Classify the transcript
            try:
                classification = await self.classifier.classify(transcript)
                monitor.add_metric("classification_confidence", classification.confidence)
                
            except Exception as e:
                logger.error(f"Classification failed: {e}")
                return self._error_response(f"Classification failed: {str(e)}")
            
            # Make routing decision
            routing_decision = self._make_routing_decision(classification)
            
            # Log routing decision
            logger.info(
                f"Routing decision: {routing_decision.primary_agent} "
                f"(confidence: {routing_decision.confidence:.2f})"
            )
            
            # Process with appropriate agent(s)
            processing_results = await self._process_with_agents(
                transcript=transcript,
                routing_decision=routing_decision,
                classification=classification,
                source_metadata=source_metadata
            )
            
            # Prepare final response
            response = {
                'status': 'success',
                'correlation_id': self.correlation_id,
                'routing_decision': routing_decision.to_dict(),
                'classification': classification.to_dict(),
                'processing_results': processing_results,
                'metrics': monitor.get_metrics(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store results for analytics
            await self._store_routing_results(response)
            
            return response
    
    def _make_routing_decision(self, classification: ClassificationResult) -> RoutingDecision:
        """Convert classification to routing decision.
        
        Args:
            classification: Classification result
            
        Returns:
            Routing decision with agent mapping
        """
        # Map buckets to agents
        bucket_to_agent = {
            MemoryBucket.COOL_IDEAS: 'github',
            MemoryBucket.TACTICAL: 'work',
            MemoryBucket.PERSONAL: 'diary'
        }
        
        primary_agent = bucket_to_agent[classification.primary_bucket]
        
        # Handle secondary agents for multi-faceted content
        secondary_agents = []
        for bucket, confidence in classification.secondary_buckets:
            if confidence > 0.3:  # Only consider significant secondary classifications
                agent = bucket_to_agent[bucket]
                secondary_agents.append((agent, confidence))
        
        # Determine if confirmation is needed
        requires_confirmation = (
            classification.confidence < 0.7 or  # Low confidence
            (len(secondary_agents) > 0 and 
             any(conf > 0.6 for _, conf in secondary_agents))  # Strong secondary
        )
        
        # Add processing hints based on classification
        processing_hints = {
            'tags': classification.suggested_tags,
            'key_indicators': classification.key_indicators,
            'emotional_content': any(
                indicator in ['emotional', 'personal', 'feeling']
                for indicator in classification.key_indicators
            )
        }
        
        return RoutingDecision(
            primary_agent=primary_agent,
            primary_bucket=classification.primary_bucket,
            confidence=classification.confidence,
            secondary_agents=secondary_agents,
            reasoning=classification.reasoning,
            requires_confirmation=requires_confirmation,
            processing_hints=processing_hints
        )
    
    async def _process_with_agents(
        self,
        transcript: str,
        routing_decision: RoutingDecision,
        classification: ClassificationResult,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process transcript with appropriate agent(s).
        
        Args:
            transcript: Voice transcript
            routing_decision: Routing decision
            classification: Classification result
            source_metadata: Optional source metadata
            
        Returns:
            Processing results from all agents
        """
        results = {}
        
        # Process with primary agent
        primary_result = await self._invoke_agent(
            agent_name=routing_decision.primary_agent,
            transcript=transcript,
            classification=classification,
            metadata=source_metadata
        )
        results[routing_decision.primary_agent] = primary_result
        
        # Process with secondary agents if confidence is high enough
        if routing_decision.secondary_agents:
            for agent_name, confidence in routing_decision.secondary_agents:
                if confidence > 0.4:  # Threshold for secondary processing
                    logger.info(
                        f"Also processing with {agent_name} "
                        f"(secondary confidence: {confidence:.2f})"
                    )
                    
                    secondary_result = await self._invoke_agent(
                        agent_name=agent_name,
                        transcript=transcript,
                        classification=classification,
                        metadata=source_metadata,
                        is_secondary=True
                    )
                    results[f"{agent_name}_secondary"] = secondary_result
        
        return results
    
    async def _invoke_agent(
        self,
        agent_name: str,
        transcript: str,
        classification: ClassificationResult,
        metadata: Optional[Dict[str, Any]] = None,
        is_secondary: bool = False
    ) -> Dict[str, Any]:
        """Invoke a specific agent.
        
        Args:
            agent_name: Name of the agent to invoke
            transcript: Voice transcript
            classification: Classification result
            metadata: Optional metadata
            is_secondary: Whether this is a secondary processing
            
        Returns:
            Agent processing result
        """
        try:
            # Special handling for diary agent (direct processing)
            if agent_name == 'diary':
                processor = self.agent_config['diary']['processor']
                
                entry = await processor.process_transcript(
                    transcript=transcript,
                    source_metadata={
                        'classification': classification.to_dict(),
                        'is_secondary': is_secondary,
                        **(metadata or {})
                    }
                )
                
                return {
                    'status': 'success',
                    'agent': 'diary',
                    'result': {
                        'entry_date': entry.date,
                        'summary': entry.summary,
                        'emotions': entry.emotions,
                        'significance_score': entry.significance_score,
                        'tags': entry.tags
                    }
                }
            
            # Placeholder for other agents
            # In production, these would invoke actual agent implementations
            elif agent_name == 'work':
                return await self._process_work_transcript(
                    transcript, classification, metadata
                )
            
            elif agent_name == 'github':
                return await self._process_github_idea(
                    transcript, classification, metadata
                )
            
            else:
                logger.error(f"Unknown agent: {agent_name}")
                return {
                    'status': 'error',
                    'agent': agent_name,
                    'error': f'Unknown agent: {agent_name}'
                }
                
        except Exception as e:
            logger.error(f"Agent {agent_name} processing failed: {e}")
            return {
                'status': 'error',
                'agent': agent_name,
                'error': str(e)
            }
    
    async def _process_work_transcript(
        self,
        transcript: str,
        classification: ClassificationResult,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process work-related transcript.
        
        This is a placeholder for the actual work agent implementation.
        """
        # TODO: Implement actual work journal processing
        return {
            'status': 'success',
            'agent': 'work',
            'result': {
                'message': 'Work journal processing not yet implemented',
                'transcript_preview': transcript[:100] + '...' if len(transcript) > 100 else transcript,
                'suggested_categories': ['development', 'meeting', 'planning'],
                'tags': classification.suggested_tags
            }
        }
    
    async def _process_github_idea(
        self,
        transcript: str,
        classification: ClassificationResult,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process GitHub project idea.
        
        This is a placeholder for the actual GitHub agent implementation.
        """
        # TODO: Implement actual GitHub repository creation
        return {
            'status': 'success',
            'agent': 'github',
            'result': {
                'message': 'GitHub repository creation not yet implemented',
                'suggested_repo_name': 'awesome-new-project',
                'suggested_description': transcript[:100],
                'tags': classification.suggested_tags
            }
        }
    
    async def _store_routing_results(self, results: Dict[str, Any]) -> None:
        """Store routing results for analytics and learning.
        
        Args:
            results: Complete routing and processing results
        """
        try:
            # Create analytics key
            timestamp = datetime.utcnow()
            key = (
                f"analytics/routing/{timestamp.strftime('%Y/%m/%d')}/"
                f"{self.correlation_id}.json"
            )
            
            # Store results
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(results, indent=2),
                ContentType='application/json',
                Metadata={
                    'correlation_id': self.correlation_id,
                    'primary_bucket': results['routing_decision']['primary_bucket'],
                    'confidence': str(results['routing_decision']['confidence'])
                }
            )
            
            logger.info(f"Stored routing analytics: {key}")
            
        except Exception as e:
            logger.error(f"Failed to store routing results: {e}")
            # Don't fail the main processing
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response.
        
        Args:
            error_message: Error message
            
        Returns:
            Error response dictionary
        """
        return {
            'status': 'error',
            'error': error_message,
            'correlation_id': self.correlation_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_routing_stats(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get routing statistics for analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Routing statistics
        """
        # TODO: Implement analytics aggregation from S3
        return {
            'period_days': days,
            'total_routed': 0,
            'bucket_distribution': {
                'cool_ideas': 0,
                'tactical': 0,
                'personal': 0
            },
            'confidence_distribution': {
                'high': 0,  # > 0.8
                'medium': 0,  # 0.6 - 0.8
                'low': 0  # < 0.6
            },
            'multi_agent_percentage': 0
        }


# Convenience function for Lambda integration
async def route_transcript(
    transcript: str,
    anthropic_api_key: str,
    github_token: Optional[str] = None,
    source_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Route a transcript using the orchestrator.
    
    Args:
        transcript: Voice transcript
        anthropic_api_key: API key for Claude
        github_token: Optional GitHub token
        source_metadata: Optional source metadata
        
    Returns:
        Complete routing and processing results
    """
    orchestrator = OrchestratorV2(
        anthropic_api_key=anthropic_api_key,
        github_token=github_token
    )
    
    return await orchestrator.route_transcript(
        transcript=transcript,
        source_metadata=source_metadata
    )


# Example usage
async def main():
    """Example of using the clean orchestrator."""
    orchestrator = OrchestratorV2(
        anthropic_api_key="your-api-key",
        github_token="your-github-token"
    )
    
    # Test transcripts
    test_cases = [
        # Cool idea
        "I have an idea for a mobile app that tracks your mood throughout "
        "the day and suggests activities based on how you're feeling",
        
        # Tactical work
        "Today I finished the API integration and deployed to staging. "
        "The client was happy with the demo",
        
        # Personal memory  
        "Walking through the park today reminded me of summers with grandma. "
        "She always had the best stories about her childhood"
    ]
    
    for transcript in test_cases:
        print(f"\nProcessing: {transcript[:60]}...")
        result = await orchestrator.route_transcript(transcript)
        
        routing = result['routing_decision']
        print(f"Routed to: {routing['primary_agent']} ({routing['primary_bucket']})")
        print(f"Confidence: {routing['confidence']:.2f}")
        print(f"Reasoning: {routing['reasoning']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())