# Whispersync Makefile
# Voice Memo MCP Agent System Testing and Development

.PHONY: help install test test-unit test-integration test-local clean lint format

# Default target
help:
	@echo "Whispersync - Voice Memo MCP Agent System"
	@echo ""
	@echo "Available targets:"
	@echo "  install         - Install Python dependencies"
	@echo "  test            - Run all tests (unit + integration)"
	@echo "  test-unit       - Run unit tests with pytest"
	@echo "  test-integration - Run integration tests"
	@echo "  test-local      - Run local test runner with sample data"
	@echo "  lint            - Run code linting"
	@echo "  format          - Format code with black"
	@echo "  clean           - Clean up test artifacts and cache"
	@echo "  help            - Show this help message"

# Install dependencies
install:
	@echo "Installing dependencies..."
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install strands-agents

# Run all tests
test: test-unit test-integration

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	.venv/bin/python -m pytest tests/unit/ -v --cov=agents --cov=lambda_fn --cov-report=term-missing

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	.venv/bin/python -m pytest tests/integration/ -v

# Run local test runner with sample data
test-local:
	@echo "Running local test runner with sample data..."
	python3 scripts/local_test_runner.py test_data/transcripts/work/test.txt

# Code linting
lint:
	@echo "Running linting..."
	.venv/bin/flake8 agents/ lambda_fn/ scripts/ tests/
	.venv/bin/black --check agents/ lambda_fn/ scripts/ tests/

# Code formatting
format:
	@echo "Formatting code..."
	.venv/bin/black agents/ lambda_fn/ scripts/ tests/

# Clean up
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