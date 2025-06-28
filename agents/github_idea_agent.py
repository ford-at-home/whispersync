"""GitHub Idea Agent.

# PURPOSE & PHILOSOPHY:
# This agent serves as an AI-powered project generator that transforms spontaneous
# voice ideas into fully-structured, production-ready GitHub repositories. It's
# designed around the principle that great ideas often come at unexpected moments,
# and the friction of manual setup prevents many ideas from becoming reality.

# CORE DESIGN DECISIONS:
# 1. Comprehensive Repositories: Creates complete project structure, not just README
# 2. AI-Powered Naming: Generates descriptive, SEO-friendly repository names
# 3. Technology Detection: Analyzes ideas to select appropriate tech stacks
# 4. Boilerplate Generation: Creates initial code, configs, and documentation
# 5. GitHub Integration: Full API usage for repos, topics, licenses, files

# WHY GITHUB FOCUS:
# - GitHub is the de facto standard for open source and portfolio projects
# - Repository structure and metadata affect discoverability and adoption
# - Proper setup (README, license, CI) signals professionalism to collaborators
# - GitHub Actions enable immediate CI/CD setup

# BUSINESS VALUE:
# - Transforms "shower thoughts" into actionable projects
# - Reduces time-to-first-commit from hours to minutes
# - Ensures consistent, professional repository structure
# - Maintains project history for portfolio and learning purposes
# - Enables rapid prototyping and experimentation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import logging
import os
import time
import re
from dataclasses import dataclass

try:
    import boto3
    from github import Github  # PyGithub library for GitHub API interaction
    from strands import Agent, tool
    from strands_tools import http_request
except ImportError:  # pragma: no cover - optional for local testing
    # WHY GRACEFUL IMPORTS: Allows local development without full dependency stack.
    # GitHub agent can still function in "dry-run" mode for testing.
    boto3 = None
    Github = None
    Agent = None
    http_request = None

    # Mock decorator for testing without strands
    def tool(func):
        return func


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class RepositorySpec:
    """Specification for a new repository.
    
    WHY DATACLASS: Provides type safety and automatic validation for complex
    repository configuration. This structure captures everything needed to
    create a complete, professional GitHub repository.
    
    FIELDS EXPLAINED:
    - name: Repository name (validated for GitHub compatibility)
    - description: Short description for GitHub and search engines
    - readme_content: Complete README.md with all standard sections
    - tech_stack: Technologies used (affects .gitignore, CI, etc.)
    - features: Planned features for README and issue templates
    - structure: Complete file tree with actual code content
    - license: License type (mit, apache-2.0, gpl-3.0, none)
    - topics: GitHub topics for discoverability
    - is_private: Visibility setting
    """

    name: str                           # GitHub-compatible repository name
    description: str                    # Short description (max 200 chars)
    readme_content: str                 # Complete README.md content
    tech_stack: List[str]              # Technologies (Python, React, etc.)
    features: List[str]                # Planned features
    structure: Dict[str, str]          # file path -> content mapping
    license: str                       # License type
    topics: List[str]                  # GitHub topics for discovery
    is_private: bool                   # Repository visibility


class GitHubIdeaAgent:
    """Agent specialized in transforming ideas into GitHub repositories.
    
    WHY SEPARATE GITHUB AGENT:
    - GitHub API integration requires specialized knowledge (tokens, rate limits, etc.)
    - Repository creation is complex multi-step process (files, topics, license)
    - Project analysis requires understanding of tech stacks and conventions
    - Failure modes are different from memory/work agents (API limits, naming conflicts)
    
    DESIGN PATTERNS:
    - Builder Pattern: Constructs repositories step-by-step
    - Factory Pattern: Creates different project types based on content analysis
    - Template Method: Consistent repository structure regardless of tech stack
    """

    def __init__(
        self, bucket: str = None, bedrock_client=None, github_token: str = None
    ):
        """Initialize the GitHub idea agent.

        Args:
            bucket: S3 bucket name for storage (defaults to 'voice-mcp')
            bedrock_client: Optional Bedrock client for testing/mocking
            github_token: Optional GitHub token (for testing, production uses Secrets Manager)
            
        WHY MULTIPLE AUTH OPTIONS: Testing needs direct token, production uses
        Secrets Manager for security. Optional parameters enable flexible testing.
        """
        self.bucket = bucket or "voice-mcp"
        # WHY MULTIPLE AWS CLIENTS: Different services for different purposes
        self.s3 = boto3.client("s3") if boto3 else None      # Repository history storage
        self.sm = boto3.client("secretsmanager") if boto3 else None  # GitHub token retrieval
        self.bedrock = bedrock_client or (
            boto3.client("bedrock-runtime") if boto3 else None
        )
        self._github_token = github_token  # For testing only

        # Create agent with specialized tools
        # WHY STRANDS AGENT: Provides conversational interface that can intelligently
        # analyze project ideas and choose appropriate tools for repository creation.
        if Agent:
            self.agent = Agent(
                system_prompt="""You are a GitHub repository specialist with expertise in:
                - Analyzing project ideas and extracting technical requirements
                - Generating descriptive and SEO-friendly repository names
                - Creating comprehensive README files with proper structure
                - Identifying appropriate technology stacks and dependencies
                - Designing initial project structures and boilerplate code
                - Selecting appropriate licenses based on project intent
                - Creating GitHub Actions workflows for CI/CD
                
                When processing ideas:
                1. Extract the core concept and its potential applications
                2. Identify the best technology stack for implementation
                3. Generate a catchy, descriptive repository name
                4. Create a comprehensive README with all standard sections
                5. Design an initial project structure with key files
                6. Add appropriate GitHub topics for discoverability
                
                Be creative but practical in your implementations.""",
                # WHY THESE TOOLS: Cover complete repository lifecycle:
                # create_repository_from_idea: Core functionality for new repos
                # analyze_similar_repos: Market research and inspiration
                # generate_project_structure: Technical architecture planning
                # search_repository_history: Learn from past projects
                # update_repository: Maintenance and improvement
                tools=[
                    self.create_repository_from_idea,
                    self.analyze_similar_repos,
                    self.generate_project_structure,
                    self.search_repository_history,
                    self.update_repository,
                ],
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            )
        else:
            self.agent = None

    @tool
    def create_repository_from_idea(
        self, transcript: str, is_private: bool = False
    ) -> Dict[str, Any]:
        """Transform a voice idea into a fully-structured GitHub repository.

        This is the core method that takes raw voice ideas and creates complete,
        professional GitHub repositories with proper structure, documentation,
        and initial code.
        
        WHY COMPLETE REPOSITORIES:
        - Reduces friction from idea to first commit
        - Professional appearance attracts collaborators and users
        - Proper structure prevents technical debt from day one
        - Documentation and examples guide future development

        Args:
            transcript: The idea transcript to transform into a repo
            is_private: Whether to create a private repository (default: public)

        Returns:
            Dictionary containing:
            - repo: Full repository name (owner/name)
            - url: GitHub repository URL
            - description: Repository description
            - tech_stack: Technologies used
            - features: Planned features
            - files_created: Number of files created
            - topics: GitHub topics added
            - status: Creation status (success/failed)
        """
        if not self.s3 or not self.sm:
            # WHY GRACEFUL DEGRADATION: Testing environments may not have AWS.
            # Return structured response for validation without actual repository creation.
            logger.warning("AWS services unavailable; returning dry-run response")
            return {
                "repo": "dry-run/test-repo",
                "url": "https://github.com/dry-run/test-repo",
                "status": "dry-run",
            }

        if not Github:
            # WHY CHECK PYGITHUB: Library might not be available in test environments
            logger.warning("PyGithub unavailable; returning dry-run response")
            return {
                "repo": "dry-run/test-repo",
                "url": "https://github.com/dry-run/test-repo",
                "status": "dry-run",
            }

        # Analyze idea and generate comprehensive repository specification
        # WHY AI ANALYSIS: Voice ideas are often vague or incomplete. Claude can
        # extract intent, suggest tech stacks, and fill in missing details.
        repo_spec = self._analyze_idea(transcript, is_private)

        # Get GitHub token and initialize API client
        token = self._get_token()
        gh = Github(token)
        user = gh.get_user()  # Get authenticated user for repository creation

        # Create repository with optimal settings
        logger.info(f"Creating repository: {repo_spec.name}")

        try:
            # WHY THESE SETTINGS:
            # - has_issues=True: Enables project management and bug tracking
            # - has_wiki=False: README is sufficient for most projects
            # - has_downloads=True: Enables release distribution
            # - auto_init=False: We create our own comprehensive initial structure
            repo = user.create_repo(
                name=repo_spec.name,
                description=repo_spec.description,
                private=repo_spec.is_private,
                has_issues=True,   # Enable issue tracking
                has_wiki=False,    # README-centric documentation
                has_downloads=True, # Enable releases
                auto_init=False,   # We control initial files
            )

            # Add comprehensive README as the foundation
            # WHY README FIRST: GitHub displays README prominently, and it sets
            # the tone for the entire project. A good README attracts contributors.
            repo.create_file(
                "README.md",
                "Initial commit: Add comprehensive README",
                repo_spec.readme_content,
            )

            # Add other files from structure
            # WHY SEPARATE COMMITS: Each file gets its own commit for clear history.
            # This makes it easier to understand what each file does.
            for file_path, content in repo_spec.structure.items():
                if file_path != "README.md":  # Already added
                    # Generate meaningful commit messages
                    commit_message = f"Add {file_path}"
                    if "/" in file_path:
                        commit_message = f"Add {os.path.basename(file_path)}"

                    repo.create_file(file_path, commit_message, content)

            # Add topics for discoverability
            # WHY TOPICS: GitHub topics enable discovery through search and trending.
            # They're essential for open source project visibility.
            if repo_spec.topics:
                repo.replace_topics(repo_spec.topics)

            # Add license for legal clarity
            # WHY LICENSE: Open source projects need clear licensing to be usable.
            # Even simple projects benefit from license clarity.
            if repo_spec.license and repo_spec.license != "none":
                self._add_license(repo, repo_spec.license)

            # Store comprehensive repository metadata for tracking and analysis
            # WHY STORE METADATA: Enables analysis of idea-to-repo patterns,
            # tracks project evolution, and supports portfolio management.
            metadata = {
                "repo_full_name": repo.full_name,
                "repo_url": repo.html_url,
                "created_at": repo.created_at.isoformat(),
                "original_idea": transcript,        # Link back to voice idea
                "tech_stack": repo_spec.tech_stack, # Technologies used
                "features": repo_spec.features,     # Planned features
                "topics": repo_spec.topics,         # GitHub topics
                "is_private": repo_spec.is_private, # Visibility
                "files_created": list(repo_spec.structure.keys()), # Initial structure
            }

            # Append to repository creation history
            # WHY JSONL HISTORY: Tracks all repositories created, enabling analysis
            # of patterns, success rates, and idea evolution over time.
            history_key = "github/history.jsonl"
            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=history_key)
                existing_history = obj["Body"].read().decode()
            except Exception:
                existing_history = ""  # First repository

            updated_history = existing_history + json.dumps(metadata) + "\n"

            self.s3.put_object(
                Bucket=self.bucket,
                Key=history_key,
                Body=updated_history.encode("utf-8"),
                ContentType="application/x-ndjson",
            )

            # Store detailed specification for future reference and analysis
            # WHY DETAILED SPECS: Enables learning from successful patterns,
            # debugging failed repositories, and improving AI analysis over time.
            spec_key = f"github/specs/{repo_spec.name}-spec.json"
            self.s3.put_object(
                Bucket=self.bucket,
                Key=spec_key,
                Body=json.dumps(
                    {"spec": repo_spec.__dict__, "metadata": metadata}, indent=2
                ).encode("utf-8"),
                ContentType="application/json",
            )

            logger.info(f"Successfully created repository: {repo.html_url}")

            return {
                "repo": repo.full_name,
                "url": repo.html_url,
                "description": repo_spec.description,
                "tech_stack": repo_spec.tech_stack,
                "features": repo_spec.features,
                "files_created": len(repo_spec.structure),
                "topics": repo_spec.topics,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Repository creation failed: {e}")
            return {"error": str(e), "repo_name": repo_spec.name, "status": "failed"}

    @tool
    def analyze_similar_repos(
        self, idea_description: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find and analyze similar repositories for inspiration.

        Args:
            idea_description: Description of the project idea
            max_results: Maximum number of similar repos to analyze

        Returns:
            List of similar repositories with insights
        """
        if not Github:
            return []

        try:
            token = self._get_token()
            gh = Github(token)

            # Extract key terms for search
            search_terms = self._extract_search_terms(idea_description)
            search_query = " ".join(search_terms[:3])  # Top 3 terms

            # Search for similar repositories
            repos = gh.search_repositories(query=search_query, sort="stars")

            similar_repos = []
            for repo in list(repos)[:max_results]:
                similar_repos.append(
                    {
                        "name": repo.full_name,
                        "url": repo.html_url,
                        "description": repo.description,
                        "stars": repo.stargazers_count,
                        "language": repo.language,
                        "topics": repo.get_topics(),
                        "insights": self._analyze_repo_for_insights(repo),
                    }
                )

            return similar_repos

        except Exception as e:
            logger.error(f"Similar repo analysis failed: {e}")
            return []

    @tool
    def generate_project_structure(
        self, idea: str, tech_stack: List[str]
    ) -> Dict[str, str]:
        """Generate a complete project structure based on the idea and tech stack.

        Args:
            idea: Project idea description
            tech_stack: List of technologies to use

        Returns:
            Dictionary mapping file paths to their content
        """
        if not self.bedrock:
            # Basic structure without AI
            return {
                "README.md": f"# Project\n\n{idea}\n",
                "src/main.py": "# Main application file\n",
                ".gitignore": "*.pyc\n__pycache__/\n.env\n",
            }

        structure = self._generate_structure_with_ai(idea, tech_stack)
        return structure

    @tool
    def search_repository_history(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search through previously created repositories.

        Args:
            query: Search query
            filters: Optional filters (tech_stack, date_range, is_private)

        Returns:
            List of matching repositories from history
        """
        if not self.s3:
            return []

        matches = []

        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key="github/history.jsonl")
            history = obj["Body"].read().decode()

            for line in history.strip().split("\n"):
                if not line:
                    continue

                repo_data = json.loads(line)

                # Apply filters
                if filters:
                    if "tech_stack" in filters:
                        required_tech = set(filters["tech_stack"])
                        repo_tech = set(repo_data.get("tech_stack", []))
                        if not required_tech.issubset(repo_tech):
                            continue

                    if "is_private" in filters:
                        if repo_data.get("is_private") != filters["is_private"]:
                            continue

                # Check query match
                searchable_text = " ".join(
                    [
                        repo_data.get("repo_full_name", ""),
                        repo_data.get("original_idea", ""),
                        " ".join(repo_data.get("tech_stack", [])),
                        " ".join(repo_data.get("features", [])),
                    ]
                ).lower()

                if query.lower() in searchable_text:
                    matches.append(
                        {
                            "repo": repo_data["repo_full_name"],
                            "url": repo_data["repo_url"],
                            "created_at": repo_data["created_at"],
                            "idea_preview": repo_data["original_idea"][:100] + "...",
                            "tech_stack": repo_data.get("tech_stack", []),
                            "features": repo_data.get("features", []),
                        }
                    )

            # Sort by recency
            matches.sort(key=lambda x: x["created_at"], reverse=True)
            return matches[:10]

        except Exception as e:
            logger.error(f"History search failed: {e}")
            return []

    @tool
    def update_repository(
        self, repo_name: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing repository with new content or settings.

        Args:
            repo_name: Name of the repository (owner/name format)
            updates: Dictionary of updates (files, description, topics, etc.)

        Returns:
            Dictionary with update status
        """
        if not Github:
            return {"status": "error", "message": "GitHub unavailable"}

        try:
            token = self._get_token()
            gh = Github(token)
            repo = gh.get_repo(repo_name)

            results = {"updated": []}

            # Update description
            if "description" in updates:
                repo.edit(description=updates["description"])
                results["updated"].append("description")

            # Update topics
            if "topics" in updates:
                repo.replace_topics(updates["topics"])
                results["updated"].append("topics")

            # Update files
            if "files" in updates:
                for file_path, content in updates["files"].items():
                    try:
                        # Try to get existing file
                        file = repo.get_contents(file_path)
                        repo.update_file(
                            file_path, f"Update {file_path}", content, file.sha
                        )
                    except:
                        # File doesn't exist, create it
                        repo.create_file(file_path, f"Add {file_path}", content)
                    results["updated"].append(f"file:{file_path}")

            results["status"] = "success"
            results["repo_url"] = repo.html_url

            return results

        except Exception as e:
            logger.error(f"Repository update failed: {e}")
            return {"status": "error", "message": str(e)}

    def _get_token(self) -> str:
        """Get GitHub token from Secrets Manager or test configuration.
        
        WHY SECRETS MANAGER: Production GitHub tokens should never be in code
        or environment variables. Secrets Manager provides secure, rotatable
        token storage with access logging.
        
        WHY FALLBACK PATTERN: Testing needs direct token injection, but
        production should always use Secrets Manager for security.
        """
        if self._github_token:
            # Test mode - token injected directly
            return self._github_token

        if not self.sm:
            raise RuntimeError("Secrets Manager unavailable and no test token provided")

        # Production mode - fetch from Secrets Manager
        secret_name = os.environ.get("GITHUB_SECRET_NAME", "github/personal_token")
        response = self.sm.get_secret_value(SecretId=secret_name)
        return response.get("SecretString", "")

    def _analyze_idea(self, transcript: str, is_private: bool) -> RepositorySpec:
        """Analyze an idea and generate a repository specification.
        
        WHY SEPARATE METHOD: Isolates AI interaction for easier testing and
        potential model switching. The complex prompt engineering is centralized.
        
        ANALYSIS INCLUDES:
        - Repository naming (GitHub-compatible, descriptive, SEO-friendly)
        - Technology stack selection (based on project requirements)
        - Feature planning (realistic scope for initial version)
        - Project structure (files, directories, initial code)
        - License selection (based on project intent and best practices)
        - Topic generation (for GitHub discoverability)
        """
        if not self.bedrock:
            # Fallback without AI - create basic but functional repository
            # WHY FALLBACK: System should work even when AI is unavailable.
            # Basic structure is better than no repository at all.
            timestamp = int(time.time())
            return RepositorySpec(
                name=f"voice-idea-{timestamp}",
                description="Created from voice memo",
                readme_content=f"# Voice Idea {timestamp}\n\n{transcript}\n",
                tech_stack=["python"],  # Safe default
                features=["voice-generated"],
                structure={
                    "README.md": f"# Voice Idea {timestamp}\n\n{transcript}\n",
                    ".gitignore": "*.pyc\n__pycache__/\n",  # Basic Python gitignore
                },
                license="mit",           # Permissive default
                topics=["voice-memo", "idea"],
                is_private=is_private,
            )

        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 3000,
                        "messages": [
                            {
                                "role": "user",
                                # WHY THIS PROMPT STRUCTURE:
                        # - Specific deliverables ensure complete repository creation
                        # - Examples guide AI toward GitHub best practices
                        # - Character limits ensure compatibility with GitHub constraints
                        # - JSON format enables reliable parsing
                        "content": f"""Analyze this project idea and generate a complete repository specification:

Idea: {transcript}

Generate:
1. A catchy, descriptive repository name (lowercase, hyphens, max 100 chars)
2. A compelling description (max 200 chars)
3. Identify the best technology stack
4. List 3-5 key features to implement
5. Create a comprehensive README.md with:
   - Project title and description
   - Features list
   - Installation instructions
   - Usage examples
   - Technology stack
   - Contributing guidelines
   - License section
6. Generate initial project structure with at least:
   - Main application file
   - Configuration file (if applicable)
   - .gitignore file
   - GitHub Actions workflow (if applicable)
   - Any other essential files
7. Suggest appropriate license (mit, apache-2.0, gpl-3.0, or none)
8. List 5-10 relevant GitHub topics

Respond in JSON format with keys: name, description, readme_content, tech_stack, features, structure (object with file paths as keys), license, topics""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            spec_data = json.loads(result.get("content", [{}])[0].get("text", "{}"))

            return RepositorySpec(
                name=self._sanitize_repo_name(
                    spec_data.get("name", f"voice-idea-{int(time.time())}")
                ),
                description=spec_data.get("description", "Created from voice memo")[
                    :200
                ],
                readme_content=spec_data.get(
                    "readme_content", f"# Project\n\n{transcript}\n"
                ),
                tech_stack=spec_data.get("tech_stack", ["python"]),
                features=spec_data.get("features", []),
                structure=spec_data.get("structure", {"README.md": "# Project\n"}),
                license=spec_data.get("license", "mit"),
                topics=spec_data.get("topics", ["voice-generated"])[:10],
                is_private=is_private,
            )

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            timestamp = int(time.time())
            return RepositorySpec(
                name=f"voice-idea-{timestamp}",
                description="Created from voice memo",
                readme_content=f"# Voice Idea {timestamp}\n\n{transcript}\n",
                tech_stack=["python"],
                features=["voice-generated"],
                structure={
                    "README.md": f"# Voice Idea {timestamp}\n\n{transcript}\n",
                    ".gitignore": "*.pyc\n__pycache__/\n",
                },
                license="mit",
                topics=["voice-memo", "idea"],
                is_private=is_private,
            )

    def _sanitize_repo_name(self, name: str) -> str:
        """Sanitize repository name to meet GitHub requirements."""
        # Convert to lowercase and replace spaces/underscores with hyphens
        name = name.lower().replace(" ", "-").replace("_", "-")
        # Remove any characters that aren't alphanumeric or hyphens
        name = re.sub(r"[^a-z0-9-]", "", name)
        # Remove multiple consecutive hyphens
        name = re.sub(r"-+", "-", name)
        # Remove leading/trailing hyphens
        name = name.strip("-")
        # Ensure it's not empty and within length limits
        if not name:
            name = f"voice-idea-{int(time.time())}"
        return name[:100]

    def _add_license(self, repo, license_type: str):
        """Add a license file to the repository."""
        license_templates = {
            "mit": """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.""",
            "apache-2.0": """Apache License Version 2.0""",  # Simplified for brevity
            "gpl-3.0": """GNU General Public License v3.0""",  # Simplified for brevity
        }

        if license_type in license_templates:
            import datetime

            content = license_templates[license_type].format(
                year=datetime.datetime.now().year, author=repo.owner.login
            )
            repo.create_file("LICENSE", f"Add {license_type.upper()} license", content)

    def _extract_search_terms(self, text: str) -> List[str]:
        """Extract key search terms from text."""
        # Simple implementation - in production, use NLP
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "them",
            "their",
            "this",
            "that",
            "these",
            "those",
        }

        words = text.lower().split()
        terms = [w for w in words if w not in common_words and len(w) > 2]

        # Sort by frequency
        term_counts = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1

        sorted_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)
        return [term for term, _ in sorted_terms]

    def _analyze_repo_for_insights(self, repo) -> Dict[str, Any]:
        """Extract insights from a repository."""
        insights = {
            "popularity": (
                "high"
                if repo.stargazers_count > 1000
                else "medium" if repo.stargazers_count > 100 else "low"
            ),
            "activity": "active" if repo.pushed_at else "inactive",
            "community": (
                "large"
                if repo.forks_count > 50
                else "medium" if repo.forks_count > 10 else "small"
            ),
            "key_files": [],
        }

        try:
            # Check for key files
            contents = repo.get_contents("")
            for content in contents:
                if content.name in [
                    "README.md",
                    "LICENSE",
                    ".github/workflows",
                    "package.json",
                    "requirements.txt",
                    "Dockerfile",
                ]:
                    insights["key_files"].append(content.name)
        except:
            pass

        return insights

    def _generate_structure_with_ai(
        self, idea: str, tech_stack: List[str]
    ) -> Dict[str, str]:
        """Generate project structure using AI."""
        try:
            tech_stack_str = ", ".join(tech_stack)
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2000,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""Generate a complete project structure for:

Idea: {idea}
Tech Stack: {tech_stack_str}

Create the initial file structure with actual code content (not placeholders).
Include all necessary configuration files, main application files, and a basic implementation.

Respond in JSON format where keys are file paths and values are the file contents.""",
                            }
                        ],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            structure = json.loads(result.get("content", [{}])[0].get("text", "{}"))
            return structure

        except Exception as e:
            logger.error(f"Structure generation failed: {e}")
            return {
                "README.md": f"# Project\n\n{idea}\n",
                "src/main.py": "# Main application file\n",
                ".gitignore": "*.pyc\n__pycache__/\n.env\n",
            }

    def __call__(self, prompt: str) -> Any:
        """Make the agent callable for Strands compatibility."""
        if self.agent:
            return self.agent(prompt)
        else:
            return {"message": "Agent not available", "prompt": prompt}


# Create singleton instance for Lambda efficiency
# WHY SINGLETON: GitHub agent maintains API client state and rate limiting
# information that should persist across Lambda invocations.
github_idea_agent = None


def get_github_idea_agent(bucket: str = None) -> GitHubIdeaAgent:
    """Get or create the GitHub idea agent instance.
    
    Implements singleton pattern for Lambda container reuse. The agent,
    its GitHub API client, and AWS clients persist across invocations
    when the container is warm, improving performance and respecting
    GitHub API rate limits.
    """
    global github_idea_agent
    if github_idea_agent is None:
        github_idea_agent = GitHubIdeaAgent(bucket=bucket)
    return github_idea_agent


# Legacy compatibility
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy handler function for backward compatibility."""
    agent = get_github_idea_agent(bucket=payload.get("bucket"))
    return agent.create_repository_from_idea(
        transcript=payload.get("transcript", ""), is_private=False
    )


# Tool wrapper for orchestrator use
@tool
def github_tool(transcript: str) -> Dict[str, Any]:
    """Transform project ideas into GitHub repositories.

    This tool handles project ideas, code concepts, and any technical
    inspirations. It creates fully-structured repositories with README files,
    initial code, and appropriate configuration.
    
    WHY SEPARATE TOOL FUNCTION:
    - Clean interface for orchestrator integration
    - Wraps conversational agent with simple function signature
    - Enables testing without full agent complexity
    - Follows Strands tool pattern for multi-agent coordination
    """
    agent = get_github_idea_agent()
    # WHY THIS PROMPT: Provides clear instruction for the agent to understand
    # the task. Agent can then choose appropriate tool (create_repository_from_idea, etc.)
    prompt = f"Create a GitHub repository from this idea: {transcript}"
    return agent(prompt)
