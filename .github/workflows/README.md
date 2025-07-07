# CI/CD Pipeline Documentation

This directory contains GitHub Actions workflows for the WhisperSync project's CI/CD pipeline.

## Workflows

### 1. PR Validation (`pr-validation.yml`)

**Triggers**: On all pull request events (opened, synchronized, reopened)

**Purpose**: Validates code quality, runs tests, and ensures PR meets merge criteria

**Jobs**:
- **Lint**: Runs flake8 and black formatting checks
- **Test**: Runs unit tests with pytest on Python 3.11 and 3.12
- **CDK Validation**: Validates AWS CDK synthesis
- **Security**: Runs Trivy vulnerability scanner

**Features**:
- Matrix testing across Python versions
- Code coverage reporting with Codecov
- Test result annotations on PR
- Caching for faster builds
- Automatic cancellation of redundant runs

### 2. Integration Tests (`integration-tests.yml`)

**Triggers**: 
- Pull requests to main
- Pushes to main
- Manual workflow dispatch

**Purpose**: Tests integration with AWS services

**Jobs**:
- Runs integration tests requiring AWS credentials
- Executes slow tests only on main branch
- Cleans up test resources automatically

**Required Secrets**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `TEST_S3_BUCKET`
- `TEST_GITHUB_TOKEN`

### 3. Release (`release.yml`)

**Triggers**: Pushes to main branch

**Purpose**: Automatically creates versioned releases

**Features**:
- Semantic versioning based on commit messages
- Automatic changelog generation
- GitHub release creation
- Version file updates via PR

**Commit Message Convention**:
- `feat:` - Minor version bump
- `fix:` - Patch version bump
- `BREAKING CHANGE:` or `!:` - Major version bump

## Configuration Files

### `dependabot.yml`
- Automated dependency updates for Python, npm, and GitHub Actions
- Weekly schedule (Mondays at 8 AM)
- Grouped by ecosystem with PR limits

### `CODEOWNERS`
- Automatic review assignment based on file paths
- Team-based ownership for different components
- Security team reviews for sensitive files

## Required GitHub Secrets

| Secret Name | Description | Required For |
|------------|-------------|--------------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Integration tests, CDK |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Integration tests, CDK |
| `AWS_REGION` | AWS region (e.g., us-east-1) | Integration tests, CDK |
| `TEST_S3_BUCKET` | S3 bucket for integration tests | Integration tests |
| `TEST_GITHUB_TOKEN` | GitHub PAT for API tests | Integration tests |

## Setting Up Secrets

1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each required secret

## Branch Protection Rules

Recommended settings for `main` branch:

1. Require pull request reviews (1-2 reviewers)
2. Dismiss stale reviews on new commits
3. Require status checks:
   - `PR Validation Status`
   - `Integration Tests`
4. Require branches to be up to date
5. Include administrators in restrictions

## Workflow Usage

### Running Tests Locally

```bash
# Run unit tests
make test-unit

# Run integration tests (requires AWS credentials)
AWS_PROFILE=test make test-integ

# Run all tests
make test
```

### Manual Workflow Trigger

```bash
# Trigger integration tests manually
gh workflow run integration-tests.yml
```

### Debugging Failed Workflows

1. Check the Actions tab for detailed logs
2. Download artifacts for test results
3. Re-run failed jobs with debug logging
4. Check secret configuration if authentication fails

## Best Practices

1. **Commit Messages**: Use conventional commits for automatic versioning
2. **PR Titles**: Be descriptive for changelog generation
3. **Test Coverage**: Maintain >80% coverage
4. **Security**: Never commit secrets or credentials
5. **Performance**: Keep PR checks under 5 minutes

## Troubleshooting

### Common Issues

1. **Cache misses**: Check if requirements files changed
2. **CDK synth failures**: Ensure CDK dependencies are installed
3. **Integration test failures**: Verify AWS credentials and permissions
4. **Release failures**: Check commit message format

### Support

- Create issues with the `ci/cd` label
- Check workflow run logs for detailed error messages
- Contact the DevOps team for infrastructure issues