"""GitHub Idea Agent - Minimal Working Version.

# PURPOSE:
# Creates GitHub repositories from voice memos with minimal setup.
# Focuses on core functionality: extract idea, create repo, add README.

# DESIGN DECISIONS:
# 1. Simple Implementation: Create basic repo with README only
# 2. Basic Name Generation: Simple slugify without AI complexity
# 3. Minimal Dependencies: Use only PyGithub and boto3
# 4. Error Handling: Graceful failures with meaningful error messages
# 5. Public by Default: All repos created as public

# MVP FEATURES:
# - Extract project idea from transcript
# - Generate safe repository name
# - Create public GitHub repository
# - Add basic README with idea description
# - Return success response with repo URL
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import json
import logging
import os
import time
import re

try:
    import boto3
    from github import Github  # PyGithub library for GitHub API interaction
except ImportError:  # pragma: no cover - optional for local testing
    # WHY GRACEFUL IMPORTS: Allows local development without full dependency stack.
    # GitHub agent can still function in "dry-run" mode for testing.
    boto3 = None
    Github = None


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GitHubIdeaAgent:
    """Minimal GitHub repository creation agent.
    
    Creates basic GitHub repositories from voice transcripts with:
    - Simple name generation (slugify)
    - Basic README with idea description
    - Public repository by default
    - Error handling for common failures
    """

    def __init__(
        self, bucket: str = None, github_token: str = None
    ):
        """Initialize the GitHub idea agent.

        Args:
            bucket: S3 bucket name for storage (defaults to 'voice-mcp')
            github_token: Optional GitHub token (for testing, production uses Secrets Manager)
        """
        # Use configuration for bucket name
        try:
            from .config import get_config
            config = get_config()
            self.bucket = bucket or config.aws.bucket_name
        except ImportError:
            # Fallback if config not available
            self.bucket = bucket or "voice-mcp"
        
        # AWS clients for token retrieval and history storage
        self.s3 = boto3.client("s3") if boto3 else None
        self.sm = boto3.client("secretsmanager") if boto3 else None
        self._github_token = github_token  # For testing only

    def create_repository_from_idea(
        self, transcript: str, is_private: bool = False
    ) -> Dict[str, Any]:
        """Create a basic GitHub repository from a voice transcript.

        Args:
            transcript: The idea transcript to transform into a repo
            is_private: Whether to create a private repository (default: public)

        Returns:
            Dictionary containing:
            - repo: Full repository name (owner/name)
            - url: GitHub repository URL
            - description: Repository description
            - status: Creation status (success/failed/dry-run)
        """
        if not self.s3 or not self.sm:
            logger.warning("AWS services unavailable; returning dry-run response")
            return {
                "repo": "dry-run/test-repo",
                "url": "https://github.com/dry-run/test-repo",
                "status": "dry-run",
            }

        if not Github:
            logger.warning("PyGithub unavailable; returning dry-run response")
            return {
                "repo": "dry-run/test-repo",
                "url": "https://github.com/dry-run/test-repo",
                "status": "dry-run",
            }

        try:
            # Extract basic info from transcript
            repo_name = self._generate_repo_name(transcript)
            description = self._extract_description(transcript)
            readme_content = self._generate_readme(transcript, repo_name)

            # Get GitHub token and initialize API client
            token = self._get_token()
            gh = Github(token)
            user = gh.get_user()

            # Create repository with basic settings
            logger.info(f"Creating repository: {repo_name}")
            repo = user.create_repo(
                name=repo_name,
                description=description,
                private=is_private,
                has_issues=True,
                has_wiki=False,
                has_downloads=True,
                auto_init=False,
            )

            # Add README file
            repo.create_file(
                "README.md",
                "Initial commit: Add README",
                readme_content,
            )

            # Store basic history for tracking
            self._store_creation_history(repo, transcript)

            logger.info(f"Successfully created repository: {repo.html_url}")

            return {
                "repo": repo.full_name,
                "url": repo.html_url,
                "description": description,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Repository creation failed: {e}")
            return {"error": str(e), "status": "failed"}


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

    def _generate_repo_name(self, transcript: str) -> str:
        """Generate a repository name from the transcript."""
        # Extract key words from transcript
        words = re.findall(r'\b\w+\b', transcript.lower())
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their', 'this', 'that', 'these', 'those', 'want', 'create', 'build', 'make', 'project', 'app', 'application', 'system', 'tool', 'program'}
        
        # Filter out common words and take first 3-4 meaningful words
        meaningful_words = [word for word in words if word not in common_words and len(word) > 2]
        
        if not meaningful_words:
            # Fallback to timestamp-based name
            return f"voice-idea-{int(time.time())}"
        
        # Take first 3-4 words and create repo name
        name_words = meaningful_words[:3]
        repo_name = '-'.join(name_words)
        
        return self._sanitize_repo_name(repo_name)
    
    def _extract_description(self, transcript: str) -> str:
        """Extract a brief description from the transcript."""
        # Take first sentence or first 100 characters
        sentences = re.split(r'[.!?]', transcript.strip())
        if sentences and len(sentences[0]) > 10:
            description = sentences[0].strip()
        else:
            description = transcript[:100].strip()
        
        if not description:
            description = "Created from voice memo"
        
        return description[:200]  # GitHub description limit
    
    def _generate_readme(self, transcript: str, repo_name: str) -> str:
        """Generate a basic README from the transcript."""
        # Create a simple but informative README
        title = repo_name.replace('-', ' ').title()
        
        readme = f"""# {title}

## Description

{transcript}

## Installation

```bash
# Clone the repository
git clone https://github.com/USERNAME/{repo_name}.git
cd {repo_name}

# Install dependencies (if any)
# pip install -r requirements.txt
```

## Usage

```bash
# Add usage instructions here
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT

---

*This project was created from a voice memo using WhisperSync.*
"""
        
        return readme
    
    def _store_creation_history(self, repo, transcript: str) -> None:
        """Store basic repository creation history."""
        if not self.s3:
            return
        
        try:
            # Extract data safely from repo object
            metadata = {
                "repo_full_name": str(repo.full_name),
                "repo_url": str(repo.html_url),
                "created_at": str(repo.created_at.isoformat() if hasattr(repo.created_at, 'isoformat') else repo.created_at),
                "original_idea": transcript,
                "is_private": bool(repo.private),
            }
            
            # Append to history file
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
            
        except Exception as e:
            logger.warning(f"Failed to store creation history: {e}")

    def __call__(self, prompt: str) -> Dict[str, Any]:
        """Make the agent callable for compatibility."""
        # Extract transcript from prompt
        transcript = prompt.replace("Create a GitHub repository from this idea: ", "")
        return self.create_repository_from_idea(transcript, is_private=False)


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
def github_tool(transcript: str) -> Dict[str, Any]:
    """Transform project ideas into GitHub repositories.

    This tool handles project ideas and creates basic repositories with:
    - Simple name generation from transcript
    - Basic README with idea description
    - Public repository by default
    """
    agent = get_github_idea_agent()
    return agent.create_repository_from_idea(transcript, is_private=False)
