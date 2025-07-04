"""Memory Classifier - Intelligent routing for voice transcripts.

This module determines which memory bucket a transcript belongs to:
1. Cool New Ideas → GitHub repository creation
2. Tactical Reflections → Work insights and progress tracking  
3. Personal Memories → Diary with emotional context

DESIGN PHILOSOPHY:
- Context is everything - analyze not just keywords but emotional tone
- Ambiguity resolution - when uncertain, look for subtle cues
- Multi-label support - some thoughts span multiple categories
- Learning from patterns - adapt to user's speaking style
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

import boto3
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class MemoryBucket(Enum):
    """The three core memory buckets."""
    COOL_IDEAS = "cool_ideas"        # Project ideas → GitHub
    TACTICAL = "tactical"            # Work reflections → Work journal
    PERSONAL = "personal"            # Personal memories → Diary


@dataclass
class ClassificationResult:
    """Result of memory classification."""
    primary_bucket: MemoryBucket
    confidence: float
    secondary_buckets: List[Tuple[MemoryBucket, float]]  # Other possible classifications
    reasoning: str
    key_indicators: List[str]
    suggested_tags: List[str]
    
    def needs_user_confirmation(self) -> bool:
        """Check if confidence is too low and needs user input."""
        return self.confidence < 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'primary_bucket': self.primary_bucket.value,
            'confidence': self.confidence,
            'secondary_buckets': [(b.value, c) for b, c in self.secondary_buckets],
            'reasoning': self.reasoning,
            'key_indicators': self.key_indicators,
            'suggested_tags': self.suggested_tags,
            'needs_confirmation': self.needs_user_confirmation()
        }


class MemoryClassifier:
    """Intelligent classifier for routing voice transcripts to memory buckets."""
    
    def __init__(self, anthropic_api_key: str):
        """Initialize the memory classifier.
        
        Args:
            anthropic_api_key: API key for Claude
        """
        self.anthropic = Anthropic(api_key=anthropic_api_key)
        
        # Pattern definitions for each bucket
        self.cool_ideas_patterns = {
            'keywords': [
                'build', 'create', 'app', 'tool', 'project', 'idea', 'what if',
                'could make', 'should build', 'new feature', 'startup', 'product',
                'website', 'platform', 'service', 'api', 'library', 'framework'
            ],
            'phrases': [
                r'I want to (build|create|make)',
                r'(idea|thought) for (a|an)',
                r'what if (I|we) (built|created)',
                r'new (app|tool|project|product)',
                r'(cool|interesting|awesome) idea',
                r'we could (build|make|create)'
            ],
            'sentiment': ['excited', 'creative', 'innovative', 'ambitious']
        }
        
        self.tactical_patterns = {
            'keywords': [
                'work', 'meeting', 'client', 'task', 'project', 'deadline',
                'completed', 'finished', 'progress', 'bug', 'fixed', 'implemented',
                'review', 'deploy', 'release', 'team', 'sprint', 'planning'
            ],
            'phrases': [
                r'(completed|finished|done with)',
                r'working on',
                r'need to (finish|complete|do)',
                r'(bug|issue|problem) (fixed|solved)',
                r'meeting (with|about)',
                r'(client|customer|user) (feedback|request)',
                r'(deployed|released|shipped)'
            ],
            'sentiment': ['productive', 'focused', 'analytical', 'professional']
        }
        
        self.personal_patterns = {
            'keywords': [
                'remember', 'felt', 'feeling', 'moment', 'family', 'friend',
                'love', 'happy', 'sad', 'beautiful', 'grateful', 'memory',
                'today', 'yesterday', 'childhood', 'life', 'heart', 'soul'
            ],
            'phrases': [
                r'I (felt|feel)',
                r'(made me|makes me) (feel|think)',
                r'(beautiful|amazing|wonderful) (moment|day|time)',
                r'(family|friend|loved one)',
                r'reminds me of',
                r'I (love|loved|miss)',
                r'grateful for',
                r'(childhood|past) memory'
            ],
            'sentiment': ['emotional', 'nostalgic', 'reflective', 'personal']
        }
    
    async def classify(self, transcript: str) -> ClassificationResult:
        """Classify a transcript into the appropriate memory bucket.
        
        Args:
            transcript: The voice transcript to classify
            
        Returns:
            ClassificationResult with bucket assignment and metadata
        """
        # First, try rule-based classification
        rule_based = self._rule_based_classification(transcript)
        
        # Then enhance with AI for nuanced understanding
        ai_enhanced = await self._ai_classification(transcript, rule_based)
        
        # Combine both approaches for final decision
        final_result = self._combine_classifications(rule_based, ai_enhanced)
        
        logger.info(
            f"Classified transcript to {final_result.primary_bucket.value} "
            f"with confidence {final_result.confidence:.2f}"
        )
        
        return final_result
    
    def _rule_based_classification(self, transcript: str) -> Dict[MemoryBucket, float]:
        """Apply rule-based classification using patterns.
        
        Args:
            transcript: The voice transcript
            
        Returns:
            Dictionary mapping buckets to confidence scores
        """
        scores = {
            MemoryBucket.COOL_IDEAS: 0.0,
            MemoryBucket.TACTICAL: 0.0,
            MemoryBucket.PERSONAL: 0.0
        }
        
        transcript_lower = transcript.lower()
        word_count = len(transcript.split())
        
        # Score based on keyword matches
        for bucket, patterns in [
            (MemoryBucket.COOL_IDEAS, self.cool_ideas_patterns),
            (MemoryBucket.TACTICAL, self.tactical_patterns),
            (MemoryBucket.PERSONAL, self.personal_patterns)
        ]:
            # Keyword scoring
            keyword_matches = sum(
                1 for keyword in patterns['keywords']
                if keyword in transcript_lower
            )
            scores[bucket] += keyword_matches * 0.1
            
            # Phrase pattern scoring
            for pattern in patterns['phrases']:
                if re.search(pattern, transcript_lower):
                    scores[bucket] += 0.2
        
        # Normalize scores
        total_score = sum(scores.values())
        if total_score > 0:
            scores = {k: v/total_score for k, v in scores.items()}
        
        return scores
    
    async def _ai_classification(
        self, 
        transcript: str, 
        rule_scores: Dict[MemoryBucket, float]
    ) -> Dict[str, Any]:
        """Use Claude for nuanced classification.
        
        Args:
            transcript: The voice transcript
            rule_scores: Initial scores from rule-based classification
            
        Returns:
            AI analysis results
        """
        # Prepare context about initial classification
        initial_guess = max(rule_scores.items(), key=lambda x: x[1])
        
        prompt = f"""Analyze this voice transcript and classify it into one of three categories:

1. COOL_IDEAS: Project ideas, things to build, creative thoughts (→ GitHub repo)
2. TACTICAL: Work progress, tasks completed, professional reflections (→ Work journal)  
3. PERSONAL: Personal memories, feelings, life moments (→ Diary)

Transcript: "{transcript}"

Initial analysis suggests: {initial_guess[0].value} (confidence: {initial_guess[1]:.2f})

Please provide:
1. The correct category (COOL_IDEAS, TACTICAL, or PERSONAL)
2. Confidence level (0.0 to 1.0)
3. Brief reasoning (1-2 sentences)
4. Key indicators that led to this classification
5. Any suggested tags for this content

Respond in JSON format:
{{
    "category": "COOL_IDEAS|TACTICAL|PERSONAL",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation",
    "key_indicators": ["indicator1", "indicator2"],
    "suggested_tags": ["tag1", "tag2"],
    "secondary_category": "COOL_IDEAS|TACTICAL|PERSONAL|null",
    "secondary_confidence": 0.0-1.0
}}"""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0.3,  # Lower temperature for consistent classification
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            content = response.content[0].text
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group())
            else:
                logger.error("No JSON found in AI response")
                return {}
                
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {}
    
    def _combine_classifications(
        self,
        rule_scores: Dict[MemoryBucket, float],
        ai_result: Dict[str, Any]
    ) -> ClassificationResult:
        """Combine rule-based and AI classifications.
        
        Args:
            rule_scores: Scores from rule-based classification
            ai_result: Results from AI classification
            
        Returns:
            Final classification result
        """
        # Start with rule-based as baseline
        final_scores = rule_scores.copy()
        
        # If AI provided results, heavily weight them
        if ai_result and 'category' in ai_result:
            try:
                ai_bucket = MemoryBucket(ai_result['category'].lower())
                ai_confidence = float(ai_result.get('confidence', 0.7))
                
                # Boost the AI-selected category
                final_scores[ai_bucket] = (
                    final_scores[ai_bucket] * 0.3 + ai_confidence * 0.7
                )
                
                # Handle secondary category if present
                secondary_buckets = []
                if ai_result.get('secondary_category') and ai_result['secondary_category'] != 'null':
                    try:
                        secondary_bucket = MemoryBucket(ai_result['secondary_category'].lower())
                        secondary_conf = float(ai_result.get('secondary_confidence', 0.3))
                        secondary_buckets.append((secondary_bucket, secondary_conf))
                    except:
                        pass
                
            except Exception as e:
                logger.error(f"Error processing AI result: {e}")
        
        # Determine primary bucket
        primary_bucket = max(final_scores.items(), key=lambda x: x[1])
        
        # Get other buckets sorted by score
        other_buckets = sorted(
            [(b, s) for b, s in final_scores.items() if b != primary_bucket[0]],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Build result
        return ClassificationResult(
            primary_bucket=primary_bucket[0],
            confidence=primary_bucket[1],
            secondary_buckets=other_buckets,
            reasoning=ai_result.get('reasoning', 'Rule-based classification'),
            key_indicators=ai_result.get('key_indicators', []),
            suggested_tags=ai_result.get('suggested_tags', [])
        )
    
    def get_bucket_description(self, bucket: MemoryBucket) -> str:
        """Get human-friendly description of a memory bucket.
        
        Args:
            bucket: The memory bucket
            
        Returns:
            Description string
        """
        descriptions = {
            MemoryBucket.COOL_IDEAS: (
                "💡 Cool New Ideas - Project ideas and creative thoughts that "
                "will be turned into GitHub repositories"
            ),
            MemoryBucket.TACTICAL: (
                "📊 Tactical Reflections - Work progress, completed tasks, and "
                "professional insights for your work journal"
            ),
            MemoryBucket.PERSONAL: (
                "💭 Personal Memories - Life moments, feelings, and experiences "
                "preserved with emotional context in your diary"
            )
        }
        return descriptions.get(bucket, "Unknown bucket")


class MemoryRouter:
    """Routes classified memories to appropriate agents."""
    
    def __init__(self, classifier: MemoryClassifier):
        """Initialize the router.
        
        Args:
            classifier: Memory classifier instance
        """
        self.classifier = classifier
        self.lambda_client = boto3.client('lambda')
    
    async def route_transcript(
        self,
        transcript: str,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Route a transcript to the appropriate agent.
        
        Args:
            transcript: Voice transcript to route
            source_metadata: Optional metadata about the source
            
        Returns:
            Routing result with agent response
        """
        # Classify the transcript
        classification = await self.classifier.classify(transcript)
        
        # Map buckets to agent names
        agent_mapping = {
            MemoryBucket.COOL_IDEAS: 'github_agent',
            MemoryBucket.TACTICAL: 'work_agent',
            MemoryBucket.PERSONAL: 'diary_agent'
        }
        
        target_agent = agent_mapping[classification.primary_bucket]
        
        # Prepare routing result
        result = {
            'classification': classification.to_dict(),
            'target_agent': target_agent,
            'transcript': transcript,
            'source_metadata': source_metadata or {},
            'routing_timestamp': datetime.datetime.now().isoformat()
        }
        
        # If confidence is low, add confirmation request
        if classification.needs_user_confirmation():
            result['needs_confirmation'] = True
            result['confirmation_message'] = (
                f"I think this is a {classification.primary_bucket.value}, "
                f"but I'm only {classification.confidence*100:.0f}% confident. "
                f"Is this correct?"
            )
            
            # Add alternative suggestions
            if classification.secondary_buckets:
                alt_bucket = classification.secondary_buckets[0][0]
                result['alternative_suggestion'] = {
                    'bucket': alt_bucket.value,
                    'agent': agent_mapping[alt_bucket]
                }
        
        logger.info(
            f"Routing transcript to {target_agent} "
            f"(bucket: {classification.primary_bucket.value}, "
            f"confidence: {classification.confidence:.2f})"
        )
        
        return result


# Example usage
async def main():
    """Example of how to use the memory classifier."""
    classifier = MemoryClassifier(anthropic_api_key="your-api-key")
    
    # Test examples
    test_transcripts = [
        # Cool idea
        "I have this cool idea for an app that helps people track their " 
        "water intake and sends cute reminders with animal animations",
        
        # Tactical work
        "Today I finished implementing the authentication system and fixed "
        "three critical bugs in the payment processing module",
        
        # Personal memory
        "Just had dinner with mom and she told me stories about when I was "
        "little. It made me realize how much she sacrificed for our family",
        
        # Ambiguous (could be work or personal)
        "The presentation went really well today and everyone seemed happy "
        "with the results"
    ]
    
    for transcript in test_transcripts:
        print(f"\nTranscript: {transcript[:60]}...")
        result = await classifier.classify(transcript)
        print(f"Classification: {result.primary_bucket.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reasoning: {result.reasoning}")
        if result.secondary_buckets:
            print(f"Alternative: {result.secondary_buckets[0][0].value} "
                  f"({result.secondary_buckets[0][1]:.2f})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())