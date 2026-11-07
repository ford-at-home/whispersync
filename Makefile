# Whispersync Makefile
# Voice Memo MCP Agent System Testing and Development
#
# WHY THIS EXISTS:
# - Standardizes development workflow across team members
# - Provides single entry point for all common operations
# - Ensures consistent environment setup and testing procedures
# - Reduces cognitive load by documenting available commands
# - Makes CI/CD integration simpler with standardized targets

# WHY .PHONY: Declares targets that don't create files with the same name
# This prevents make from getting confused if files named 'test', 'install', etc. exist
.PHONY: help install test test-unit test-integ test-integration test-local clean lint format

# Default target
# WHY: Shows available commands when developer runs 'make' without arguments
# This improves discoverability and reduces need to read the Makefile
help:
	@echo "Whispersync - Voice Memo MCP Agent System"
	@echo ""
	@echo "Available targets:"
	@echo "  install         - Install Python dependencies"
	@echo "  test            - Run all tests (unit + integration)"
	@echo "  test-unit       - Run unit tests with pytest"
	@echo "  test-integ      - Run integration tests (alias for test-integration)"
	@echo "  test-integration - Run integration tests"
	@echo "  test-local      - Run local test runner with sample data"
	@echo "  lint            - Run code linting"
	@echo "  format          - Format code with black"
	@echo "  clean           - Clean up test artifacts and cache"
	@echo "  help            - Show this help message"

# Install dependencies
# WHY: Creates isolated Python environment to avoid system package conflicts
# WHY python3 -m venv: Uses built-in venv module for portability
# WHY .venv: Standard name that most IDEs auto-detect for Python interpreter
# WHY strands-agents separate: Not in requirements.txt to allow flexibility during development
install:
	@echo "Installing dependencies..."
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install strands-agents

# Run all tests
# WHY: Single command for CI/CD and pre-commit validation
# WHY order matters: Unit tests first (faster) then integration (slower)
test: test-unit test-integration

# Run unit tests
# WHY: Tests individual components in isolation for fast feedback
# WHY check .venv: Supports both venv and system Python for flexibility
# WHY --cov: Measures code coverage to identify untested code paths
# WHY --cov-report=term-missing: Shows which lines aren't covered
# WHY -v: Verbose output helps debug test failures
test-unit:
	@echo "Running unit tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python -m pytest tests/unit/ -v --cov=agents --cov=lambda_fn --cov-report=term-missing; \
	else \
		python -m pytest tests/unit/ -v --cov=agents --cov=lambda_fn --cov-report=term-missing; \
	fi

# Run integration tests (alias)
# WHY: Common abbreviation that developers expect
test-integ: test-integration

# Run integration tests
# WHY: Tests full pipeline with real AWS resources
# WHY no coverage: Integration tests focus on behavior, not code coverage
# WHY separate from unit: Can be run independently, may require AWS credentials
test-integration:
	@echo "Running integration tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python -m pytest tests/integration/ -v; \
	else \
		python -m pytest tests/integration/ -v; \
	fi

# Run local test runner with sample data
# WHY: Rapid development feedback without AWS infrastructure
# WHY work/test.txt: Default example helps new developers understand data flow
# WHY python3 direct: Simpler for quick tests, assumes dependencies installed
test-local:
	@echo "Running local test runner with sample data..."
	python3 scripts/local_test_runner.py test_data/transcripts/work/test.txt

# Code linting
# WHY: Enforces code quality standards before commits
# WHY flake8: Catches Python style violations and potential bugs
# WHY black --check: Verifies code formatting without changing files
# WHY order: flake8 first (finds bugs), then black (style only)
lint:
	@echo "Running linting..."
	.venv/bin/flake8 agents/ lambda_fn/ scripts/ tests/
	.venv/bin/black --check agents/ lambda_fn/ scripts/ tests/

# Code formatting
# WHY: Consistent code style reduces cognitive load and PR review friction
# WHY black: Opinionated formatter eliminates style debates
# WHY all directories: Ensures entire codebase maintains consistency
format:
	@echo "Formatting code..."
	.venv/bin/black agents/ lambda_fn/ scripts/ tests/

# Clean up
# WHY: Removes all generated files for fresh start or before commits
# WHY rm -rf .venv: Full environment reset for dependency issues
# WHY __pycache__: Python bytecode can cause import issues
# WHY .pytest_cache: Test cache can hide flaky tests
# WHY .coverage/htmlcov: Coverage reports should be regenerated
# WHY find commands: Recursively clean all subdirectories
# WHY 2>/dev/null || true: Prevents errors from stopping clean process
# WHY dist/build: Package artifacts from potential future packaging
clean:
	@echo "Cleaning up..."
	rm -rf .venv
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true 