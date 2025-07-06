"""ExecutiveAssistantAgent - Intelligent professional life management with Theory of Mind.

Core responsibilities:
- Maintain weekly work logs with AI-powered summaries
- Track professional identity evolution via Theory of Mind
- Analyze productivity patterns and flag important items
- Generate executive-level insights from work transcripts
- Provide strategic recommendations based on historical patterns
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Configuration
THEORY_OF_MIND_TABLE = os.environ.get('THEORY_OF_MIND_TABLE', 'ExecutiveAssistant-TheoryOfMind')
USER_ID = os.environ.get('USER_ID', 'default')  # Support multi-user in future


@dataclass
class TheoryOfMind:
    """Structured representation of the agent's understanding of the user."""
    
    # Core identity
    identity: Dict[str, Any] = None
    
    # Temporal context
    temporal_context: Dict[str, Any] = None
    
    # Decision model
    decision_model: Dict[str, Any] = None
    
    # Meta information
    last_updated: str = None
    update_count: int = 0
    confidence_score: float = 0.5
    
    def __post_init__(self):
        """Initialize with defaults if not provided."""
        if self.identity is None:
            self.identity = {
                "core_values": [],
                "professional_identity": "Professional",
                "skills_focus": [],
                "confidence": 0.5
            }
        
        if self.temporal_context is None:
            self.temporal_context = {
                "current_week": {
                    "week_of": datetime.now().strftime("%Y-%m-%d"),
                    "stated_goals": [],
                    "detected_themes": [],
                    "energy_level": "unknown"
                },
                "current_quarter": {
                    "projects": [],
                    "key_relationships": {}
                },
                "long_term_arcs": {}
            }
        
        if self.decision_model is None:
            self.decision_model = {
                "time_allocation_preferences": {
                    "deep_work": 0.4,
                    "meetings": 0.3,
                    "learning": 0.2,
                    "networking": 0.1
                },
                "project_evaluation_criteria": []
            }
        
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'user_id': USER_ID,
            'identity': self.identity,
            'temporal_context': self.temporal_context,
            'decision_model': self.decision_model,
            'last_updated': self.last_updated,
            'update_count': self.update_count,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TheoryOfMind':
        """Create from dictionary."""
        return cls(
            identity=data.get('identity'),
            temporal_context=data.get('temporal_context'),
            decision_model=data.get('decision_model'),
            last_updated=data.get('last_updated'),
            update_count=data.get('update_count', 0),
            confidence_score=data.get('confidence_score', 0.5)
        )


class TheoryOfMindManager:
    """Manages the Theory of Mind data structure in DynamoDB."""
    
    def __init__(self):
        self.table = dynamodb.Table(THEORY_OF_MIND_TABLE)
    
    def load(self) -> TheoryOfMind:
        """Load Theory of Mind from DynamoDB."""
        try:
            response = self.table.get_item(Key={'user_id': USER_ID})
            if 'Item' in response:
                return TheoryOfMind.from_dict(response['Item'])
            else:
                # Initialize new Theory of Mind
                logger.info("Initializing new Theory of Mind")
                return TheoryOfMind()
        except Exception as e:
            logger.error(f"Failed to load Theory of Mind: {e}")
            return TheoryOfMind()
    
    def save(self, theory: TheoryOfMind) -> None:
        """Save Theory of Mind to DynamoDB."""
        try:
            theory.last_updated = datetime.utcnow().isoformat()
            theory.update_count += 1
            
            self.table.put_item(Item=theory.to_dict())
            logger.info(f"Saved Theory of Mind (update #{theory.update_count})")
        except Exception as e:
            logger.error(f"Failed to save Theory of Mind: {e}")


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager."""
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve Anthropic API key: {e}")
        raise


async def analyze_transcript_with_context(
    transcript: str,
    theory: TheoryOfMind
) -> Dict[str, Any]:
    """Analyze transcript using Theory of Mind as context.
    
    Args:
        transcript: Work-related transcript
        theory: Current Theory of Mind
        
    Returns:
        Analysis results including any updates to theory
    """
    try:
        from anthropic import Anthropic
        
        api_key = get_anthropic_api_key()
        anthropic = Anthropic(api_key=api_key)
        
        # Prepare context about the user
        context = f"""You are an executive assistant with deep knowledge of your user.

Current Understanding:
- Professional Identity: {theory.identity.get('professional_identity')}
- Core Values: {', '.join(theory.identity.get('core_values', []))}
- Skills Focus: {', '.join(theory.identity.get('skills_focus', []))}

This Week's Context:
- Stated Goals: {', '.join(theory.temporal_context['current_week'].get('stated_goals', []))}
- Detected Themes: {', '.join(theory.temporal_context['current_week'].get('detected_themes', []))}
- Energy Level: {theory.temporal_context['current_week'].get('energy_level')}

Current Projects: {', '.join(theory.temporal_context['current_quarter'].get('projects', []))}

Time Allocation Preferences:
{json.dumps(theory.decision_model['time_allocation_preferences'], indent=2)}"""

        prompt = f"""{context}

New Transcript: "{transcript}"

Analyze this transcript and provide:
1. Executive summary (what happened/what's important)
2. Key insights about the user's current state
3. Action items or things needing attention
4. Whether this reveals any changes in goals, priorities, or state
5. How this fits with their current week/quarter context

BE CAUTIOUS about suggesting changes to the core understanding. Only suggest updates if there's strong, clear evidence of a fundamental shift.

Respond in JSON format:
{{
    "executive_summary": "Brief summary",
    "key_insights": ["insight1", "insight2"],
    "action_items": ["item1", "item2"],
    "urgency_level": "high|medium|low",
    "detected_themes": ["theme1", "theme2"],
    "energy_indicators": "high|moderate|low|stressed",
    "alignment_with_goals": "aligned|neutral|misaligned",
    "suggested_theory_updates": {{
        "should_update": false,
        "confidence": 0.0,
        "proposed_changes": {{}}
    }},
    "contextual_notes": "How this fits with current projects/goals"
}}"""

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        result = json.loads(content)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze transcript: {e}")
        return {
            "executive_summary": transcript[:200] + "..." if len(transcript) > 200 else transcript,
            "key_insights": ["Analysis failed - see transcript"],
            "action_items": [],
            "urgency_level": "medium",
            "detected_themes": [],
            "energy_indicators": "unknown",
            "alignment_with_goals": "neutral",
            "suggested_theory_updates": {"should_update": False},
            "contextual_notes": "Analysis error occurred"
        }


def update_theory_if_needed(
    theory: TheoryOfMind,
    analysis: Dict[str, Any]
) -> Tuple[TheoryOfMind, bool]:
    """Update Theory of Mind if analysis suggests it's needed.
    
    Args:
        theory: Current Theory of Mind
        analysis: Analysis results
        
    Returns:
        Tuple of (updated theory, whether it was updated)
    """
    updates = analysis.get('suggested_theory_updates', {})
    
    if not updates.get('should_update', False):
        return theory, False
    
    # High threshold for updates (0.8 confidence required)
    if updates.get('confidence', 0) < 0.8:
        logger.info(f"Skipping theory update due to low confidence: {updates.get('confidence')}")
        return theory, False
    
    # Apply proposed changes cautiously
    proposed = updates.get('proposed_changes', {})
    
    # Update current week context (more permissive)
    if 'current_week' in proposed:
        week_updates = proposed['current_week']
        if 'detected_themes' in week_updates:
            theory.temporal_context['current_week']['detected_themes'] = week_updates['detected_themes']
        if 'energy_level' in week_updates:
            theory.temporal_context['current_week']['energy_level'] = week_updates['energy_level']
    
    # Update identity (very restrictive)
    if 'identity' in proposed and updates.get('confidence', 0) > 0.9:
        identity_updates = proposed['identity']
        # Only update if explicitly confirmed
        logger.warning(f"High-confidence identity update proposed: {identity_updates}")
        # For now, we don't auto-update identity
    
    return theory, True


def create_executive_document(
    transcript: str,
    analysis: Dict[str, Any],
    theory: TheoryOfMind,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Create executive documentation of the transcript.
    
    Args:
        transcript: Original transcript
        analysis: Analysis results
        theory: Current Theory of Mind
        metadata: Additional metadata
        
    Returns:
        Executive document
    """
    now = datetime.utcnow()
    
    document = {
        "document_type": "executive_summary",
        "timestamp": now.isoformat(),
        "week_of": now.strftime("%Y-W%U"),
        "original_transcript": transcript,
        "executive_summary": analysis['executive_summary'],
        "key_insights": analysis['key_insights'],
        "action_items": analysis['action_items'],
        "urgency_level": analysis['urgency_level'],
        "contextual_analysis": {
            "detected_themes": analysis['detected_themes'],
            "energy_indicators": analysis['energy_indicators'],
            "alignment_with_goals": analysis['alignment_with_goals'],
            "contextual_notes": analysis['contextual_notes']
        },
        "theory_of_mind_snapshot": {
            "professional_identity": theory.identity.get('professional_identity'),
            "current_projects": theory.temporal_context['current_quarter'].get('projects', []),
            "weekly_goals": theory.temporal_context['current_week'].get('stated_goals', []),
            "confidence_in_understanding": theory.confidence_score
        },
        "metadata": metadata
    }
    
    # Add flags for important items
    flags = []
    if analysis['urgency_level'] == 'high':
        flags.append("HIGH_PRIORITY")
    if analysis['alignment_with_goals'] == 'misaligned':
        flags.append("GOAL_MISALIGNMENT")
    if analysis['energy_indicators'] in ['low', 'stressed']:
        flags.append("ENERGY_CONCERN")
    
    if flags:
        document['flags'] = flags
    
    return document


def append_to_weekly_log(
    transcript: str,
    analysis: Dict[str, Any],
    s3_bucket: str
) -> Dict[str, Any]:
    """Append analyzed transcript to weekly work log.
    
    Args:
        transcript: Original transcript
        analysis: Analysis results
        s3_bucket: S3 bucket for storage
        
    Returns:
        Log update result
    """
    now = datetime.utcnow()
    year, week, _ = now.isocalendar()
    log_key = f"work/weekly_logs/{year}-W{week:02d}.md"
    
    # Get existing log or create new
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=log_key)
        content = response['Body'].read().decode('utf-8')
        logger.info(f"Retrieved existing log: {log_key}")
    except s3_client.exceptions.NoSuchKey:
        content = f"# Work Journal - {year} Week {week}\n\n"
        logger.info(f"Created new log: {log_key}")
    
    # Format entry
    entry = f"""
## {now.strftime('%Y-%m-%d %H:%M')} UTC

**Categories:** {', '.join(analysis.get('detected_themes', ['general']))}  
**Sentiment:** {analysis.get('energy_indicators', 'moderate')}
**Urgency:** {analysis.get('urgency_level', 'medium')}

### Original Transcript
{transcript}

### Executive Summary
{analysis['executive_summary']}

### Key Insights
{chr(10).join(f'- {insight}' for insight in analysis['key_insights'])}

### Action Items
{chr(10).join(f'- [ ] {item}' for item in analysis['action_items'])}

---
"""
    
    content += entry
    
    # Save updated log
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=log_key,
        Body=content.encode('utf-8'),
        ContentType='text/markdown',
        Metadata={
            'week': str(week),
            'year': str(year),
            'entry_count': str(content.count('## 20')),
            'last_updated': now.isoformat()
        }
    )
    
    return {
        'log_key': log_key,
        'week': f"{year}-W{week:02d}",
        'entry_added': True
    }


def generate_weekly_summary(
    week: int,
    year: int,
    s3_bucket: str,
    theory: TheoryOfMind
) -> Dict[str, Any]:
    """Generate AI-powered weekly summary.
    
    Args:
        week: Week number
        year: Year
        s3_bucket: S3 bucket
        theory: Current Theory of Mind
        
    Returns:
        Weekly summary
    """
    log_key = f"work/weekly_logs/{year}-W{week:02d}.md"
    
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=log_key)
        content = response['Body'].read().decode('utf-8')
        
        # Use Claude to generate comprehensive summary
        from anthropic import Anthropic
        api_key = get_anthropic_api_key()
        anthropic = Anthropic(api_key=api_key)
        
        prompt = f"""Generate a comprehensive weekly summary from these work journal entries.

Context about the person:
- Professional Identity: {theory.identity.get('professional_identity')}
- Current Projects: {', '.join(theory.temporal_context['current_quarter'].get('projects', []))}

Week: {year}-W{week:02d}

Journal Content:
{content}

Include:
1. Executive summary (3-4 sentences)
2. Major highlights and accomplishments
3. Key insights about work patterns and themes
4. Progress on current projects
5. Recommendations for next week

Respond in JSON format with keys: week, summary, highlights, insights, project_progress, recommendations"""

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = json.loads(response.content[0].text)
        
        # Store summary
        summary_key = f"work/weekly_summaries/{year}-W{week:02d}-summary.json"
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=summary_key,
            Body=json.dumps(result, indent=2),
            ContentType='application/json'
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate weekly summary: {e}")
        return {
            'week': f"{year}-W{week:02d}",
            'summary': 'Summary generation failed',
            'error': str(e)
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SQS events from ExecutiveAssistant queue.
    
    Combines work journal functionality with Theory of Mind management.
    
    Args:
        event: SQS event containing transcript
        context: Lambda context
        
    Returns:
        Processing result
    """
    try:
        # Initialize Theory of Mind manager
        tom_manager = TheoryOfMindManager()
        
        # Process each record
        for record in event['Records']:
            # Parse message
            message = json.loads(record['body'])
            transcript = message['transcript']
            s3_bucket = message['bucket']
            s3_key = message['key']
            categories = message.get('all_categories', [])
            
            logger.info(f"Processing work transcript from {s3_key}")
            
            # Load current Theory of Mind
            theory = tom_manager.load()
            logger.info(f"Loaded Theory of Mind (confidence: {theory.confidence_score})")
            
            # Run async analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Analyze transcript with context
                analysis = loop.run_until_complete(
                    analyze_transcript_with_context(transcript, theory)
                )
                
                # Update Theory of Mind if needed
                updated_theory, was_updated = update_theory_if_needed(theory, analysis)
                
                if was_updated:
                    tom_manager.save(updated_theory)
                    logger.info("Theory of Mind updated based on new insights")
                
                # Append to weekly work log (from v1 functionality)
                log_result = append_to_weekly_log(
                    transcript=transcript,
                    analysis=analysis,
                    s3_bucket=s3_bucket
                )
                
                # Create executive document
                document = create_executive_document(
                    transcript=transcript,
                    analysis=analysis,
                    theory=updated_theory,
                    metadata={
                        's3_key': s3_key,
                        'categories': categories,
                        'processing_timestamp': datetime.utcnow().isoformat(),
                        'work_log': log_result
                    }
                )
                
                # Store document in S3
                output_key = s3_key.replace('transcripts/', 'outputs/executive_assistant/').replace('.txt', '_summary.json')
                s3_client.put_object(
                    Bucket=s3_bucket,
                    Key=output_key,
                    Body=json.dumps(document, indent=2),
                    ContentType='application/json',
                    Metadata={
                        'urgency_level': analysis['urgency_level'],
                        'has_action_items': str(bool(analysis['action_items'])),
                        'alignment': analysis['alignment_with_goals'],
                        'work_week': log_result['week']
                    }
                )
                
                logger.info(f"Created executive document: {output_key}")
                
                # Generate weekly summary if it's end of week (Friday) or requested
                now = datetime.utcnow()
                if now.weekday() == 4:  # Friday
                    year, week, _ = now.isocalendar()
                    weekly_summary = generate_weekly_summary(week, year, s3_bucket, updated_theory)
                    logger.info(f"Generated weekly summary for {year}-W{week:02d}")
                
                # If high priority, could trigger additional notifications here
                if document.get('flags') and 'HIGH_PRIORITY' in document['flags']:
                    logger.warning(f"HIGH PRIORITY item detected: {analysis['executive_summary']}")
                
            finally:
                loop.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Transcripts processed successfully'})
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }