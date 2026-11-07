"""OvernightMVPAgent - Transform ideas into fully-structured GitHub projects.

Core responsibilities:
- Analyze ideas and extract technical requirements
- Generate complete project structures with working code
- Create professional GitHub repositories with proper metadata
- Add CI/CD workflows and appropriate licensing
- Track repository creation history for portfolio management
- Focus on weekend-buildable AWS architectures
"""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

import boto3
from github import Github
from github.GithubException import GithubException

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
secrets_client = boto3.client('secretsmanager')
s3_client = boto3.client('s3')

# Get configuration from environment
README_TEMPLATE_BUCKET = os.environ.get('README_TEMPLATE_BUCKET', 'whispersync-templates')
DEFAULT_VISIBILITY = os.environ.get('DEFAULT_REPO_VISIBILITY', 'public')


def get_github_token() -> str:
    """Retrieve GitHub token from Secrets Manager."""
    try:
        secret_name = os.environ.get('GITHUB_TOKEN_SECRET', 'github/personal_token')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve GitHub token: {e}")
        raise


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager."""
    try:
        secret_name = os.environ.get('ANTHROPIC_SECRET_NAME', 'anthropic/api_key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve Anthropic API key: {e}")
        raise


async def analyze_idea(transcript: str) -> Dict[str, Any]:
    """Use Claude to analyze the idea and generate project details.
    
    Args:
        transcript: The idea transcript
        
    Returns:
        Project details including name, description, and architecture
    """
    try:
        from anthropic import Anthropic
        
        api_key = get_anthropic_api_key()
        anthropic = Anthropic(api_key=api_key)
        
        prompt = f"""Analyze this idea and create a GitHub project plan.

Idea transcript: "{transcript}"

Generate:
1. A short, memorable project name (lowercase, hyphens, no spaces)
2. A one-line description (under 100 chars)
3. A detailed description (2-3 paragraphs)
4. An MVP architecture using AWS services
5. 3-5 initial implementation tasks

Focus on what could realistically be built in a weekend using serverless AWS services.

Respond in JSON format:
{{
    "project_name": "voice-mood-tracker",
    "short_description": "Track your mood through voice analysis",
    "detailed_description": "Multiple paragraphs...",
    "aws_architecture": {{
        "services": [
            {{"name": "Lambda", "purpose": "Voice processing", "runtime": "Python 3.11"}},
            {{"name": "DynamoDB", "purpose": "Store mood history"}},
            {{"name": "S3", "purpose": "Audio file storage"}},
            {{"name": "API Gateway", "purpose": "REST API for mobile app"}}
        ],
        "estimated_cost": "$5-10/month for light usage",
        "complexity": "Medium"
    }},
    "implementation_tasks": [
        "Set up Lambda function for audio processing",
        "Create DynamoDB schema for mood entries",
        "Build REST API with API Gateway",
        "Implement basic sentiment analysis",
        "Create simple web UI for testing"
    ],
    "tech_stack": ["Python", "AWS Lambda", "DynamoDB", "React"],
    "target_users": "People interested in mental health tracking"
}}"""

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.7,  # Some creativity for project ideas
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            raise ValueError("No valid JSON in response")
            
    except Exception as e:
        logger.error(f"Failed to analyze idea: {e}")
        # Return a basic structure
        return {
            "project_name": "new-project-idea",
            "short_description": "An innovative project idea",
            "detailed_description": transcript,
            "aws_architecture": {
                "services": [
                    {"name": "Lambda", "purpose": "Core processing"},
                    {"name": "DynamoDB", "purpose": "Data storage"}
                ],
                "estimated_cost": "TBD",
                "complexity": "TBD"
            },
            "implementation_tasks": [
                "Define project requirements",
                "Set up AWS infrastructure",
                "Implement core functionality",
                "Add tests and documentation"
            ],
            "tech_stack": ["Python", "AWS"],
            "target_users": "TBD"
        }


def generate_initial_code_structure(project_details: Dict[str, Any]) -> Dict[str, str]:
    """Generate initial code files based on tech stack.
    
    Args:
        project_details: Analyzed project details including tech_stack
        
    Returns:
        Dictionary mapping file paths to content
    """
    structure = {}
    tech_stack = project_details.get('tech_stack', ['python'])
    
    # Python project structure
    if 'python' in [t.lower() for t in tech_stack]:
        structure['requirements.txt'] = """# Core dependencies
boto3>=1.26.0
python-dotenv>=1.0.0
requests>=2.31.0
pydantic>=2.0.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0

# Development
black>=23.7.0
flake8>=6.1.0
mypy>=1.5.0
"""
        
        structure['src/__init__.py'] = '"""Main package for {}."""

__version__ = "0.1.0"
'.format(project_details['project_name'])
        
        structure['src/main.py'] = '''"""Main entry point for {}."""\n\nimport logging\nimport os\nfrom typing import Dict, Any\n\nlogging.basicConfig(level=logging.INFO)\nlogger = logging.getLogger(__name__)\n\n\ndef main() -> None:\n    """Main function."""\n    logger.info("Starting {}...")\n    # TODO: Implement main logic\n    pass\n\n\nif __name__ == "__main__":\n    main()\n'''.format(project_details['project_name'], project_details['project_name'])
        
        structure['tests/__init__.py'] = ''
        structure['tests/test_main.py'] = '''"""Tests for main module."""\n\nimport pytest\nfrom src.main import main\n\n\ndef test_main():\n    """Test main function."""\n    # TODO: Implement tests\n    assert True\n'''
        
        structure['.gitignore'] = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
.env

# Testing
.coverage
.pytest_cache/
htmlcov/
.tox/
.mypy_cache/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Build
build/
dist/
*.egg-info/
"""
    
    # JavaScript/Node.js project structure
    if any(tech.lower() in ['javascript', 'node', 'react', 'vue', 'typescript'] for tech in tech_stack):
        structure['package.json'] = '''{{\n  "name": "{}",\n  "version": "0.1.0",\n  "description": "{}",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js",\n    "test": "jest",\n    "dev": "nodemon index.js"\n  }},\n  "keywords": [],\n  "author": "",\n  "license": "MIT",\n  "dependencies": {{}},\n  "devDependencies": {{\n    "jest": "^29.0.0",\n    "nodemon": "^3.0.0"\n  }}\n}}'''.format(project_details['project_name'], project_details['short_description'])
        
        structure['index.js'] = '''// Main entry point for {}\n\nconsole.log('Starting {}...');\n\n// TODO: Implement main logic\n'''.format(project_details['project_name'], project_details['project_name'])
        
        structure['.gitignore'] = """# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm

# Environment
.env
.env.local
.env.*.local

# Testing
coverage/
.nyc_output/

# Build
dist/
build/
*.log

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
"""
    
    # AWS CDK if mentioned
    if any('cdk' in tech.lower() or 'aws' in tech.lower() for tech in tech_stack):
        structure['cdk.json'] = '''{{\n  "app": "python3 app.py",\n  "context": {{\n    "@aws-cdk/aws-apigateway:usagePlanKeyOrderInsensitiveId": true,\n    "@aws-cdk/core:stackRelativeExports": true,\n    "@aws-cdk/aws-lambda:recognizeVersionProps": true\n  }}\n}}'''
        
        structure['app.py'] = '''#!/usr/bin/env python3\nimport os\nimport aws_cdk as cdk\nfrom infrastructure.main_stack import MainStack\n\napp = cdk.App()\nMainStack(app, "{}-stack",\n    env=cdk.Environment(\n        account=os.getenv('CDK_DEFAULT_ACCOUNT'),\n        region=os.getenv('CDK_DEFAULT_REGION')\n    )\n)\n\napp.synth()\n'''.format(project_details['project_name'])
    
    # GitHub Actions workflow
    structure['.github/workflows/ci.yml'] = '''name: CI\n\non:\n  push:\n    branches: [ main ]\n  pull_request:\n    branches: [ main ]\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    \n    steps:\n    - uses: actions/checkout@v3\n    \n    - name: Set up Python\n      uses: actions/setup-python@v4\n      with:\n        python-version: '3.11'\n    \n    - name: Install dependencies\n      run: |\n        python -m pip install --upgrade pip\n        pip install -r requirements.txt\n    \n    - name: Run tests\n      run: |\n        pytest\n'''
    
    return structure


def generate_readme(project_details: Dict[str, Any], transcript: str) -> str:
    """Generate a comprehensive README.md for the project.
    
    Args:
        project_details: Analyzed project details
        transcript: Original idea transcript
        
    Returns:
        Markdown content for README.md
    """
    readme = f"""# {project_details['project_name']}

{project_details['short_description']}

## 🎯 Vision

{project_details['detailed_description']}

## 💡 Original Idea

> "{transcript}"

## 🏗️ MVP Architecture (AWS)

This project is designed to be built in a weekend using serverless AWS services.

### Services Used

"""
    
    # Add services table
    if project_details['aws_architecture']['services']:
        readme += "| Service | Purpose | Details |\n"
        readme += "|---------|---------|----------|\n"
        for service in project_details['aws_architecture']['services']:
            details = service.get('runtime', service.get('type', ''))
            readme += f"| {service['name']} | {service['purpose']} | {details} |\n"
    
    readme += f"""

### Architecture Diagram

```
[Mobile App / Web UI]
        ↓
[API Gateway]
        ↓
[Lambda Functions]
        ↓
[DynamoDB / S3]
```

### Estimated Costs
{project_details['aws_architecture'].get('estimated_cost', 'TBD')}

### Complexity Level
{project_details['aws_architecture'].get('complexity', 'TBD')}

## 🚀 Getting Started

### Prerequisites
- AWS Account
- Python 3.11+
- AWS CLI configured
- Node.js (for CDK)

### Quick Deploy

```bash
# Clone the repository
git clone https://github.com/yourusername/{project_details['project_name']}.git
cd {project_details['project_name']}

# Install dependencies
pip install -r requirements.txt

# Deploy to AWS
cdk deploy
```

## 📋 Implementation Roadmap

"""
    
    # Add tasks as checklist
    for i, task in enumerate(project_details['implementation_tasks'], 1):
        readme += f"- [ ] **Phase {i}**: {task}\n"
    
    readme += f"""

## 🛠️ Tech Stack

"""
    
    # Add tech stack badges
    for tech in project_details['tech_stack']:
        badge_tech = tech.replace(' ', '%20')
        readme += f"![{tech}](https://img.shields.io/badge/{badge_tech}-blue) "
    
    readme += f"""

## 🎯 Target Users

{project_details['target_users']}

## 🤝 Contributing

This project was born from a voice memo idea! Contributions are welcome:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Created with [WhisperSync](https://github.com/whispersync/whispersync) OvernightMVPAgent
- Powered by AWS serverless architecture
- Idea captured on {datetime.now().strftime('%B %d, %Y')}

---

*Built with ❤️ from a voice memo*
"""
    
    return readme


def generate_license(license_type: str, author: str) -> Optional[str]:
    """Generate license content based on type.
    
    Args:
        license_type: Type of license (mit, apache-2.0, gpl-3.0)
        author: Repository owner name
        
    Returns:
        License content or None if unknown type
    """
    import datetime
    year = datetime.datetime.now().year
    
    licenses = {
        'mit': f"""MIT License

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
IMPORTED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.""",
        'apache-2.0': f"""Copyright {year} {author}

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.""",
        'gpl-3.0': f"""Copyright (C) {year} {author}

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details."""
    }
    
    return licenses.get(license_type)


def create_github_issues(repo: Any, project_details: Dict[str, Any]) -> List[str]:
    """Create initial GitHub issues for the project.
    
    Args:
        repo: GitHub repository object
        project_details: Project details
        
    Returns:
        List of created issue URLs
    """
    issue_urls = []
    
    try:
        # Create milestone for MVP
        milestone = repo.create_milestone(
            title="MVP Release",
            description="Initial working version with core functionality"
        )
        
        # Create issues for each task
        for i, task in enumerate(project_details['implementation_tasks'], 1):
            issue = repo.create_issue(
                title=f"[MVP-{i}] {task}",
                body=f"""## Task Description
{task}

## Acceptance Criteria
- [ ] Implementation complete
- [ ] Tests written
- [ ] Documentation updated

## Technical Details
Related to {project_details['project_name']} MVP implementation.

### Relevant AWS Services
{', '.join([s['name'] for s in project_details['aws_architecture']['services']])}
""",
                milestone=milestone,
                labels=['enhancement', 'mvp']
            )
            issue_urls.append(issue.html_url)
            logger.info(f"Created issue: {issue.title}")
            
        # Create a tracking issue
        tracking_issue = repo.create_issue(
            title="🎯 MVP Implementation Tracking",
            body=f"""## Overview
This issue tracks the implementation of the {project_details['project_name']} MVP.

## Tasks
{chr(10).join([f"- #{i+1} {task}" for i, task in enumerate(project_details['implementation_tasks'])])}

## Architecture
- **Services**: {', '.join([s['name'] for s in project_details['aws_architecture']['services']])}
- **Complexity**: {project_details['aws_architecture']['complexity']}
- **Estimated Cost**: {project_details['aws_architecture']['estimated_cost']}

## Progress
Track progress in the individual issues linked above.
""",
            milestone=milestone,
            labels=['tracking', 'mvp']
        )
        issue_urls.append(tracking_issue.html_url)
        
    except Exception as e:
        logger.error(f"Failed to create issues: {e}")
    
    return issue_urls


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SQS events from OvernightMVP queue.
    
    Args:
        event: SQS event containing transcript
        context: Lambda context
        
    Returns:
        Processing result
    """
    try:
        # Process each record (usually just one)
        for record in event['Records']:
            # Parse message
            message = json.loads(record['body'])
            transcript = message['transcript']
            s3_bucket = message['bucket']
            s3_key = message['key']
            
            logger.info(f"Processing idea from {s3_key}")
            
            # Run async analysis
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Analyze the idea
                project_details = loop.run_until_complete(analyze_idea(transcript))
                
                # Generate README content
                readme_content = generate_readme(project_details, transcript)
                
                # Create GitHub repository
                github_token = get_github_token()
                g = Github(github_token)
                user = g.get_user()
                
                # Check if repo already exists
                repo_name = project_details['project_name']
                try:
                    existing_repo = user.get_repo(repo_name)
                    logger.warning(f"Repository {repo_name} already exists")
                    # Add number suffix
                    repo_name = f"{repo_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                except:
                    pass  # Repo doesn't exist, good to go
                
                # Create repository
                repo = user.create_repo(
                    name=repo_name,
                    description=project_details['short_description'],
                    private=(DEFAULT_VISIBILITY == 'private'),
                    has_issues=True,
                    has_projects=True,
                    auto_init=False
                )
                
                logger.info(f"Created repository: {repo.html_url}")
                
                # Generate complete project structure
                code_structure = generate_initial_code_structure(project_details)
                
                # Create README first
                repo.create_file(
                    path="README.md",
                    message="Initial commit - Project idea from voice memo",
                    content=readme_content
                )
                
                # Add all project files
                for file_path, content in code_structure.items():
                    try:
                        # Generate meaningful commit messages
                        if '/' in file_path:
                            commit_msg = f"Add {os.path.basename(file_path)}"
                        else:
                            commit_msg = f"Add {file_path}"
                        
                        repo.create_file(
                            path=file_path,
                            message=commit_msg,
                            content=content
                        )
                        logger.info(f"Created file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to create {file_path}: {e}")
                
                # Add license file
                license_type = project_details.get('license', 'mit')
                if license_type and license_type != 'none':
                    license_content = generate_license(license_type, repo.owner.login)
                    if license_content:
                        repo.create_file(
                            path="LICENSE",
                            message=f"Add {license_type.upper()} license",
                            content=license_content
                        )
                
                # Add GitHub topics for discoverability
                topics = project_details.get('topics', ['voice-generated', 'weekend-project'])
                if topics:
                    try:
                        repo.replace_topics(topics[:10])  # GitHub limits to 20 topics
                        logger.info(f"Added topics: {topics}")
                    except Exception as e:
                        logger.warning(f"Failed to add topics: {e}")
                
                # Create initial issues
                issue_urls = create_github_issues(repo, project_details)
                
                # Store comprehensive result
                result = {
                    'status': 'success',
                    'project_name': repo_name,
                    'repository_url': repo.html_url,
                    'description': project_details['short_description'],
                    'issues_created': len(issue_urls),
                    'issue_urls': issue_urls,
                    'aws_services': [s['name'] for s in project_details['aws_architecture']['services']],
                    'tech_stack': project_details['tech_stack'],
                    'topics': topics,
                    'license': license_type,
                    'files_created': len(code_structure) + 2,  # +2 for README and LICENSE
                    'original_transcript': transcript,
                    'processed_at': datetime.utcnow().isoformat()
                }
                
                # Store in repository history for tracking and analysis
                history_key = 'github/overnight_mvp_history.jsonl'
                try:
                    # Get existing history
                    obj = s3_client.get_object(Bucket=s3_bucket, Key=history_key)
                    existing_history = obj['Body'].read().decode('utf-8')
                except s3_client.exceptions.NoSuchKey:
                    existing_history = ''
                
                # Append new entry
                history_entry = {
                    'repo_full_name': repo.full_name,
                    'repo_url': repo.html_url,
                    'created_at': repo.created_at.isoformat(),
                    'original_idea': transcript,
                    'tech_stack': project_details['tech_stack'],
                    'aws_architecture': project_details['aws_architecture'],
                    'topics': topics,
                    'implementation_tasks': project_details['implementation_tasks']
                }
                
                updated_history = existing_history + json.dumps(history_entry) + '\n'
                s3_client.put_object(
                    Bucket=s3_bucket,
                    Key=history_key,
                    Body=updated_history.encode('utf-8'),
                    ContentType='application/x-ndjson'
                )
                
                # Store detailed result
                output_key = s3_key.replace('transcripts/', 'outputs/overnight_mvp/').replace('.txt', '_result.json')
                s3_client.put_object(
                    Bucket=s3_bucket,
                    Key=output_key,
                    Body=json.dumps(result, indent=2),
                    ContentType='application/json',
                    Metadata={
                        'repo_name': repo_name,
                        'tech_stack': ','.join(project_details['tech_stack']),
                        'aws_services': ','.join([s['name'] for s in project_details['aws_architecture']['services']])
                    }
                )
                
                logger.info(f"Successfully created project: {repo_name} with {len(code_structure)} files")
                
            finally:
                loop.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Ideas processed successfully'})
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }