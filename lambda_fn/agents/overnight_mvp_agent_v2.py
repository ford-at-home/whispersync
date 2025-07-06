"""OvernightMVPAgent V2 - Enhanced with persona voice and learning architecture.

Core enhancements:
- Persona voice integration for authentic project descriptions
- Learning from past projects to improve future suggestions
- Pattern recognition for successful project characteristics
- Knowledge graph of technologies and their relationships
- Intelligent project complexity estimation based on history
"""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, asdict, field
import asyncio
from collections import defaultdict

import boto3
from github import Github
from github.GithubException import GithubException

from .base import BaseAgent, requires_aws, AgentError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
secrets_client = boto3.client('secretsmanager')
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Configuration
PROJECT_PATTERNS_TABLE = os.environ.get('PROJECT_PATTERNS_TABLE', 'OvernightMVP-ProjectPatterns')
TECH_KNOWLEDGE_TABLE = os.environ.get('TECH_KNOWLEDGE_TABLE', 'OvernightMVP-TechKnowledge')
README_TEMPLATE_BUCKET = os.environ.get('README_TEMPLATE_BUCKET', 'whispersync-templates')
DEFAULT_VISIBILITY = os.environ.get('DEFAULT_REPO_VISIBILITY', 'public')


@dataclass
class ProjectPattern:
    """Learned patterns from successful projects."""
    
    pattern_id: str
    pattern_type: str  # architecture, tech_stack, project_type
    description: str
    
    # Pattern details
    success_indicators: List[str] = field(default_factory=list)
    common_technologies: List[str] = field(default_factory=list)
    typical_complexity: str = "medium"  # low, medium, high
    
    # Usage tracking
    times_used: int = 0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None
    
    # Associations
    related_patterns: List[str] = field(default_factory=list)
    example_projects: List[str] = field(default_factory=list)  # GitHub URLs


@dataclass
class TechnologyKnowledge:
    """Knowledge about technologies and their relationships."""
    
    tech_name: str
    category: str  # language, framework, service, tool
    
    # Compatibility and relationships
    works_well_with: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)  # Dependencies
    
    # Usage patterns
    common_use_cases: List[str] = field(default_factory=list)
    learning_curve: str = "medium"  # low, medium, high
    weekend_friendly: bool = True
    
    # Cost implications
    cost_category: str = "low"  # free, low, medium, high
    scaling_concerns: List[str] = field(default_factory=list)
    
    # Success metrics
    projects_created: int = 0
    average_complexity: float = 5.0
    success_stories: List[str] = field(default_factory=list)


@dataclass
class PersonaVoice:
    """Persona settings for project generation."""
    
    tone: str = "enthusiastic_builder"  # enthusiastic_builder, pragmatic_engineer, creative_innovator
    complexity_preference: str = "balanced"  # simple, balanced, ambitious
    documentation_style: str = "comprehensive"  # minimal, balanced, comprehensive
    
    # Communication preferences
    use_emojis: bool = True
    use_metaphors: bool = True
    technical_depth: float = 0.7  # 0-1 scale
    
    # Project preferences
    preferred_stack: List[str] = field(default_factory=list)
    avoided_technologies: List[str] = field(default_factory=list)
    focus_areas: List[str] = field(default_factory=list)  # AI, web, mobile, data, automation
    
    # Naming conventions
    naming_style: str = "descriptive"  # descriptive, creative, minimal
    prefix_patterns: List[str] = field(default_factory=list)  # Common prefixes like "smart-", "auto-"


@dataclass
class ProjectKnowledgeBase:
    """Knowledge base that learns from all projects."""
    
    # Pattern recognition
    project_patterns: Dict[str, ProjectPattern] = field(default_factory=dict)
    
    # Technology knowledge
    tech_knowledge: Dict[str, TechnologyKnowledge] = field(default_factory=dict)
    
    # Success metrics
    total_projects: int = 0
    successful_projects: int = 0
    average_complexity: float = 5.0
    
    # Common themes
    idea_categories: Dict[str, int] = field(default_factory=dict)  # category -> count
    popular_architectures: List[Dict[str, Any]] = field(default_factory=list)
    
    # Learning insights
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def learn_from_project(self, project_details: Dict[str, Any], success: bool = True) -> Dict[str, Any]:
        """Learn from a new project creation."""
        learning_report = {
            "patterns_reinforced": [],
            "new_patterns": [],
            "tech_updates": [],
            "insights_gained": []
        }
        
        self.total_projects += 1
        if success:
            self.successful_projects += 1
        
        # Update technology knowledge
        for tech in project_details.get('tech_stack', []):
            if tech not in self.tech_knowledge:
                self.tech_knowledge[tech] = TechnologyKnowledge(
                    tech_name=tech,
                    category=self._categorize_technology(tech)
                )
            
            tech_know = self.tech_knowledge[tech]
            tech_know.projects_created += 1
            
            # Learn relationships
            for other_tech in project_details.get('tech_stack', []):
                if other_tech != tech and other_tech not in tech_know.works_well_with:
                    tech_know.works_well_with.append(other_tech)
            
            learning_report["tech_updates"].append(f"Updated knowledge for {tech}")
        
        # Identify patterns
        complexity = project_details.get('aws_architecture', {}).get('complexity', 'medium')
        
        # Architecture pattern
        arch_pattern_id = f"arch_{len(project_details.get('aws_architecture', {}).get('services', []))}services_{complexity}"
        if arch_pattern_id not in self.project_patterns:
            self.project_patterns[arch_pattern_id] = ProjectPattern(
                pattern_id=arch_pattern_id,
                pattern_type="architecture",
                description=f"{complexity} complexity with {len(project_details.get('aws_architecture', {}).get('services', []))} services",
                typical_complexity=complexity
            )
            learning_report["new_patterns"].append(arch_pattern_id)
        
        pattern = self.project_patterns[arch_pattern_id]
        pattern.times_used += 1
        pattern.last_used = datetime.utcnow()
        if success:
            pattern.success_rate = (pattern.success_rate * (pattern.times_used - 1) + 1) / pattern.times_used
        
        # Update idea categories
        idea_category = self._categorize_idea(project_details.get('project_name', ''))
        self.idea_categories[idea_category] = self.idea_categories.get(idea_category, 0) + 1
        
        # Generate insights
        if self.total_projects % 10 == 0:  # Every 10 projects
            insight = f"After {self.total_projects} projects: Most common stack is {self._most_common_stack()}"
            self.insights.append(insight)
            learning_report["insights_gained"].append(insight)
        
        return learning_report
    
    def _categorize_technology(self, tech: str) -> str:
        """Categorize a technology."""
        tech_lower = tech.lower()
        
        if tech_lower in ['python', 'javascript', 'typescript', 'go', 'rust']:
            return "language"
        elif tech_lower in ['react', 'vue', 'django', 'fastapi', 'express']:
            return "framework"
        elif 'aws' in tech_lower or tech_lower in ['lambda', 's3', 'dynamodb', 'ec2']:
            return "service"
        else:
            return "tool"
    
    def _categorize_idea(self, project_name: str) -> str:
        """Categorize project idea."""
        name_lower = project_name.lower()
        
        if any(word in name_lower for word in ['ai', 'ml', 'smart', 'intelligent']):
            return "ai_ml"
        elif any(word in name_lower for word in ['api', 'service', 'backend']):
            return "backend"
        elif any(word in name_lower for word in ['app', 'mobile', 'ios', 'android']):
            return "mobile"
        elif any(word in name_lower for word in ['dashboard', 'admin', 'portal']):
            return "web"
        elif any(word in name_lower for word in ['bot', 'automation', 'workflow']):
            return "automation"
        else:
            return "general"
    
    def _most_common_stack(self) -> str:
        """Find most common technology stack."""
        tech_counts = defaultdict(int)
        for tech_name, tech in self.tech_knowledge.items():
            tech_counts[tech_name] = tech.projects_created
        
        if tech_counts:
            return max(tech_counts, key=tech_counts.get)
        return "Python + AWS"
    
    def recommend_architecture(self, idea_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend architecture based on learned patterns."""
        recommendations = {
            "suggested_stack": [],
            "architecture_pattern": None,
            "complexity_estimate": "medium",
            "success_likelihood": 0.7,
            "similar_projects": []
        }
        
        # Find similar successful patterns
        idea_category = self._categorize_idea(idea_analysis.get('project_name', ''))
        
        # Recommend proven technology combinations
        proven_combos = []
        for tech_name, tech in self.tech_knowledge.items():
            if tech.projects_created > 3 and tech.weekend_friendly:
                proven_combos.append({
                    "tech": tech_name,
                    "score": tech.projects_created * (0.8 if tech.learning_curve == "low" else 0.5)
                })
        
        # Sort by score and take top technologies
        proven_combos.sort(key=lambda x: x["score"], reverse=True)
        recommendations["suggested_stack"] = [combo["tech"] for combo in proven_combos[:5]]
        
        # Find best architecture pattern
        applicable_patterns = [
            p for p in self.project_patterns.values()
            if p.pattern_type == "architecture" and p.success_rate > 0.6
        ]
        
        if applicable_patterns:
            best_pattern = max(applicable_patterns, key=lambda p: p.success_rate * p.times_used)
            recommendations["architecture_pattern"] = best_pattern.description
            recommendations["complexity_estimate"] = best_pattern.typical_complexity
            recommendations["success_likelihood"] = best_pattern.success_rate
        
        return recommendations


class OvernightMVPAgentV2(BaseAgent):
    """Enhanced MVP Agent with learning and persona capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patterns_table = dynamodb.Table(PROJECT_PATTERNS_TABLE)
        self.tech_table = dynamodb.Table(TECH_KNOWLEDGE_TABLE)
        self.knowledge_base = self.load_knowledge_base()
        self.persona = self.load_persona_settings()
    
    def load_knowledge_base(self) -> ProjectKnowledgeBase:
        """Load knowledge base from DynamoDB."""
        try:
            # Load project patterns
            patterns = {}
            response = self.patterns_table.scan()
            for item in response.get('Items', []):
                pattern = ProjectPattern(**item)
                patterns[pattern.pattern_id] = pattern
            
            # Load tech knowledge
            tech_knowledge = {}
            response = self.tech_table.scan()
            for item in response.get('Items', []):
                tech = TechnologyKnowledge(**item)
                tech_knowledge[tech.tech_name] = tech
            
            # Create knowledge base
            kb = ProjectKnowledgeBase()
            kb.project_patterns = patterns
            kb.tech_knowledge = tech_knowledge
            
            # Load metrics from S3 history
            self._load_historical_metrics(kb)
            
            return kb
            
        except Exception as e:
            logger.warning(f"Failed to load knowledge base: {e}")
            return ProjectKnowledgeBase()
    
    def load_persona_settings(self) -> PersonaVoice:
        """Load persona settings."""
        # In future, this would load from user preferences
        # For now, return defaults with some personality
        return PersonaVoice(
            tone="enthusiastic_builder",
            use_emojis=True,
            preferred_stack=["Python", "AWS Lambda", "DynamoDB", "React"],
            focus_areas=["automation", "productivity", "ai_ml"]
        )
    
    def _load_historical_metrics(self, kb: ProjectKnowledgeBase):
        """Load metrics from historical projects."""
        try:
            # Read history file
            history_key = 'github/overnight_mvp_history.jsonl'
            obj = s3_client.get_object(Bucket=self.bucket, Key=history_key)
            content = obj['Body'].read().decode('utf-8')
            
            for line in content.strip().split('\n'):
                if line:
                    entry = json.loads(line)
                    kb.total_projects += 1
                    
                    # Learn from each historical project
                    project_details = {
                        'project_name': entry.get('repo_url', '').split('/')[-1],
                        'tech_stack': entry.get('tech_stack', []),
                        'aws_architecture': entry.get('aws_architecture', {})
                    }
                    kb.learn_from_project(project_details)
                    
        except Exception as e:
            logger.info(f"No historical data to load: {e}")
    
    def save_knowledge_base(self):
        """Save knowledge base updates."""
        try:
            # Save patterns
            for pattern in self.knowledge_base.project_patterns.values():
                pattern_dict = asdict(pattern)
                if pattern.last_used:
                    pattern_dict['last_used'] = pattern.last_used.isoformat()
                self.patterns_table.put_item(Item=pattern_dict)
            
            # Save tech knowledge
            for tech in self.knowledge_base.tech_knowledge.values():
                self.tech_table.put_item(Item=asdict(tech))
                
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")
    
    async def analyze_idea_with_learning(self, transcript: str) -> Dict[str, Any]:
        """Analyze idea with learning and persona application."""
        # Get base analysis
        from .overnight_mvp_agent import analyze_idea
        base_analysis = await analyze_idea(transcript)
        
        # Apply knowledge base recommendations
        recommendations = self.knowledge_base.recommend_architecture(base_analysis)
        
        # Enhance with learned patterns
        if recommendations['suggested_stack']:
            # Merge with original stack, preferring proven technologies
            original_stack = set(base_analysis.get('tech_stack', []))
            suggested_stack = set(recommendations['suggested_stack'])
            base_analysis['tech_stack'] = list(original_stack | suggested_stack)[:6]
        
        # Apply persona voice to descriptions
        base_analysis = self.apply_persona_voice(base_analysis)
        
        # Add learning insights
        base_analysis['learning_applied'] = {
            'architecture_recommendation': recommendations['architecture_pattern'],
            'complexity_estimate': recommendations['complexity_estimate'],
            'success_likelihood': recommendations['success_likelihood'],
            'based_on_projects': self.knowledge_base.total_projects
        }
        
        return base_analysis
    
    def apply_persona_voice(self, project_details: Dict[str, Any]) -> Dict[str, Any]:
        """Apply persona voice to project details."""
        if self.persona.tone == "enthusiastic_builder":
            # Add enthusiasm to descriptions
            project_details['short_description'] = self._add_enthusiasm(
                project_details.get('short_description', '')
            )
            
            # Add emojis if enabled
            if self.persona.use_emojis:
                project_details['project_name'] = self._add_project_emoji(
                    project_details['project_name']
                )
        
        elif self.persona.tone == "pragmatic_engineer":
            # Focus on practical aspects
            project_details['detailed_description'] = self._make_pragmatic(
                project_details.get('detailed_description', '')
            )
        
        # Apply naming style
        if self.persona.naming_style == "creative":
            project_details['project_name'] = self._make_creative_name(
                project_details['project_name']
            )
        
        return project_details
    
    def _add_enthusiasm(self, text: str) -> str:
        """Add enthusiastic tone to text."""
        enthusiasm_words = {
            "Track": "🚀 Track",
            "Build": "⚡ Build",
            "Create": "✨ Create",
            "Manage": "🎯 Manage"
        }
        
        for word, replacement in enthusiasm_words.items():
            text = text.replace(word, replacement)
        
        return text
    
    def _add_project_emoji(self, name: str) -> str:
        """Add relevant emoji to project name."""
        # Don't modify the actual repo name, this is for display
        return name
    
    def _make_pragmatic(self, text: str) -> str:
        """Make description more pragmatic."""
        # Add practical considerations
        if "MVP" not in text:
            text += "\n\nBuilt with a focus on rapid deployment and minimal operational overhead."
        return text
    
    def _make_creative_name(self, name: str) -> str:
        """Make project name more creative."""
        # Keep original for now - in future could suggest alternatives
        return name
    
    def generate_enhanced_readme(
        self,
        project_details: Dict[str, Any],
        transcript: str,
        learning_insights: Dict[str, Any]
    ) -> str:
        """Generate README with persona voice and learning insights."""
        # Start with base README
        from .overnight_mvp_agent import generate_readme
        base_readme = generate_readme(project_details, transcript)
        
        # Add learning insights section
        insights_section = f"""
## 🧠 AI-Powered Architecture Insights

Based on analysis of {self.knowledge_base.total_projects} similar projects:

- **Recommended Architecture**: {learning_insights.get('architecture_recommendation', 'Standard serverless pattern')}
- **Complexity Estimate**: {learning_insights.get('complexity_estimate', 'Medium')}
- **Success Likelihood**: {learning_insights.get('success_likelihood', 0.7):.0%}

### Why This Architecture?
"""
        
        if self.knowledge_base.insights:
            insights_section += "\n".join(f"- {insight}" for insight in self.knowledge_base.insights[-3:])
        
        # Insert insights section after architecture
        readme_parts = base_readme.split("## 🚀 Getting Started")
        if len(readme_parts) == 2:
            base_readme = readme_parts[0] + insights_section + "\n## 🚀 Getting Started" + readme_parts[1]
        
        # Apply persona touches
        if self.persona.use_metaphors:
            base_readme = base_readme.replace(
                "This project is designed to be built in a weekend",
                "This project is designed to go from idea to reality in a weekend sprint 🏃‍♂️"
            )
        
        return base_readme
    
    def track_project_success(self, project_url: str, metrics: Dict[str, Any]):
        """Track project success for learning."""
        # This would be called later to track how projects perform
        # For now, log the intent
        logger.info(f"Tracking success metrics for {project_url}: {metrics}")
    
    @requires_aws
    def process_idea(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process idea with enhanced learning capabilities."""
        transcript = event['transcript']
        s3_bucket = event['bucket']
        s3_key = event['key']
        
        logger.info(f"Processing idea with V2 agent from {s3_key}")
        
        # Run async analysis with learning
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Analyze with learning
            project_details = loop.run_until_complete(
                self.analyze_idea_with_learning(transcript)
            )
            
            learning_insights = project_details.pop('learning_applied', {})
            
            # Generate enhanced README
            readme_content = self.generate_enhanced_readme(
                project_details, transcript, learning_insights
            )
            
            # Create GitHub repository (reuse v1 logic)
            github_token = self.get_github_token()
            g = Github(github_token)
            user = g.get_user()
            
            # Create repository with enhanced details
            repo_name = project_details['project_name']
            
            # Check if exists
            try:
                existing_repo = user.get_repo(repo_name)
                repo_name = f"{repo_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            except:
                pass
            
            repo = user.create_repo(
                name=repo_name,
                description=project_details['short_description'],
                private=(DEFAULT_VISIBILITY == 'private'),
                has_issues=True,
                has_projects=True,
                auto_init=False
            )
            
            logger.info(f"Created repository: {repo.html_url}")
            
            # Create files (reuse v1 logic for structure)
            from .overnight_mvp_agent import generate_initial_code_structure
            code_structure = generate_initial_code_structure(project_details)
            
            # Add README
            repo.create_file(
                path="README.md",
                message="Initial commit - AI-enhanced project from voice memo 🎙️",
                content=readme_content
            )
            
            # Add all project files
            for file_path, content in code_structure.items():
                try:
                    repo.create_file(
                        path=file_path,
                        message=f"Add {file_path}",
                        content=content
                    )
                except Exception as e:
                    logger.warning(f"Failed to create {file_path}: {e}")
            
            # Learn from this project
            learning_report = self.knowledge_base.learn_from_project(project_details)
            self.save_knowledge_base()
            
            # Create comprehensive result
            result = {
                'status': 'success',
                'project_name': repo_name,
                'repository_url': repo.html_url,
                'description': project_details['short_description'],
                'tech_stack': project_details['tech_stack'],
                'learning_applied': learning_insights,
                'learning_report': learning_report,
                'persona_applied': {
                    'tone': self.persona.tone,
                    'style': self.persona.naming_style
                },
                'knowledge_base_stats': {
                    'total_projects': self.knowledge_base.total_projects,
                    'success_rate': (self.knowledge_base.successful_projects / 
                                   max(self.knowledge_base.total_projects, 1))
                },
                'original_transcript': transcript,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Store result
            output_key = s3_key.replace('transcripts/', 'outputs/overnight_mvp_v2/').replace('.txt', '_enhanced.json')
            self.store_result(result, output_key)
            
            # Update history
            self._update_project_history(repo, project_details, learning_insights)
            
            return {
                "status": "success",
                "output_key": output_key,
                "repo_url": repo.html_url,
                "learning_occurred": bool(learning_report.get('new_patterns'))
            }
            
        finally:
            loop.close()
    
    def _update_project_history(self, repo: Any, project_details: Dict[str, Any], learning: Dict[str, Any]):
        """Update project history with enhanced data."""
        history_key = 'github/overnight_mvp_v2_history.jsonl'
        
        try:
            obj = s3_client.get_object(Bucket=self.bucket, Key=history_key)
            existing = obj['Body'].read().decode('utf-8')
        except s3_client.exceptions.NoSuchKey:
            existing = ''
        
        history_entry = {
            'repo_full_name': repo.full_name,
            'repo_url': repo.html_url,
            'created_at': repo.created_at.isoformat(),
            'tech_stack': project_details['tech_stack'],
            'aws_architecture': project_details['aws_architecture'],
            'learning_applied': learning,
            'persona_settings': asdict(self.persona),
            'knowledge_base_version': self.knowledge_base.total_projects
        }
        
        updated = existing + json.dumps(history_entry) + '\n'
        s3_client.put_object(
            Bucket=self.bucket,
            Key=history_key,
            Body=updated.encode('utf-8'),
            ContentType='application/x-ndjson'
        )


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager."""
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve Anthropic API key: {e}")
        raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for OvernightMVPV2."""
    agent = OvernightMVPAgentV2()
    
    try:
        # Process each record
        results = []
        for record in event['Records']:
            message = json.loads(record['body'])
            result = agent.process_idea(message)
            results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Ideas processed with enhanced learning',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }