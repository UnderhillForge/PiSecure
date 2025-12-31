# PiSecure Development Makefile
.PHONY: help install install-dev test lint format clean build docs serve-docs docker-build docker-run

# Default target
help: ## Show this help message
	@echo "PiSecure Development Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Installation
install: ## Install PiSecure in development mode
	pip install -e .

install-dev: ## Install with development dependencies
	pip install -e ".[dev]"

install-full: ## Install with all optional dependencies
	pip install -e ".[full]"

# Testing
test: ## Run all tests
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=pisecure --cov-report=html --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/unit/

test-integration: ## Run integration tests only
	pytest tests/integration/

test-mock: ## Run tests with mock hardware
	PISECURE_MOCK_HARDWARE=1 pytest

# Code Quality
lint: ## Run all linting tools
	flake8 pisecure/
	mypy pisecure/

format: ## Format code with black and isort
	black pisecure/
	isort pisecure/

format-check: ## Check code formatting without changes
	black --check pisecure/
	isort --check-only pisecure/

# Documentation
docs: ## Build documentation
	cd docs && sphinx-build -b html . _build/html

docs-auto: ## Build docs and auto-reload on changes
	cd docs && sphinx-autobuild . _build/html

serve-docs: ## Serve documentation locally
	cd docs/_build/html && python -m http.server 8000

# Docker
docker-build: ## Build Docker image
	docker build -t pisecure .

docker-run: ## Run PiSecure in Docker container
	docker run --rm -it pisecure

docker-test: ## Run tests in Docker
	docker run --rm pisecure pytest

# Build & Distribution
build: ## Build distribution packages
	python -m build

build-check: ## Check build without creating files
	python setup.py check

# Cleanup
clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	rm -rf pisecure/__pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-all: clean ## Clean everything including docs and docker
	rm -rf docs/_build/
	docker system prune -f

# Development workflow
dev-setup: ## Set up development environment
	pre-commit install
	pip install -e ".[dev]"

dev-test: lint test-cov ## Run full development test suite

# CI/CD simulation
ci: dev-test build ## Simulate CI pipeline

# Quick development commands
run: ## Run PiSecure CLI
	python -m pisecure

mine: ## Start mining demo
	python -m pisecure mine

status: ## Show system status
	python -m pisecure status

# Utility
deps-update: ## Update all dependencies
	pip install --upgrade pip
	pip install --upgrade -e ".[dev]"

deps-freeze: ## Freeze current dependencies to requirements.txt
	pip freeze > requirements-frozen.txt

# Git helpers
git-clean: ## Clean untracked files (be careful!)
	git clean -fdx

git-status: ## Show git status with useful info
	@echo "=== Git Status ==="
	git status --short
	@echo
	@echo "=== Recent Commits ==="
	git log --oneline -5
	@echo
	@echo "=== Branch Info ==="
	git branch -v

# Hardware testing (requires Raspberry Pi)
hw-test: ## Run hardware-specific tests
	@echo "Testing hardware verification..."
	python -c "from pisecure.core.hardware import HardwareVerifier; v=HardwareVerifier(); print('HW Check:', v.verify_mining_eligibility())"

	@echo "Testing device fingerprint..."
	python -c "from pisecure.identity.fingerprint import DeviceFingerprint; f=DeviceFingerprint(); print('Fingerprint:', f.generate_fingerprint()[:32] + '...')"

# Release helpers
version-bump-patch: ## Bump patch version
	@echo "Current version: $$(python -c "import pisecure; print(pisecure.__version__)")"
	@echo "Update version in pisecure/__init__.py and setup.py"

version-bump-minor: ## Bump minor version
	@echo "Current version: $$(python -c "import pisecure; print(pisecure.__version__)")"
	@echo "Update version in pisecure/__init__.py and setup.py"

version-check: ## Check version consistency
	@echo "Package version: $$(python -c "import pisecure; print(pisecure.__version__)")"
	@echo "Setup.py version: $$(python setup.py --version)"

# Performance testing
perf-test: ## Run performance benchmarks
	@echo "Running performance tests..."
	pytest tests/ -k "perf" --tb=short

# Security testing
security-scan: ## Run security vulnerability scan
	@echo "Running security scan..."
	# Add security scanning tools like bandit, safety, etc.
	# bandit -r pisecure/
	# safety check

# Environment info
info: ## Show development environment info
	@echo "=== PiSecure Development Info ==="
	@echo "Python: $$(python --version)"
	@echo "Pip: $$(pip --version)"
	@echo "Platform: $$(python -c "import platform; print(platform.platform())")"
	@echo "PiSecure: $$(python -c "import pisecure; print(pisecure.__version__)" 2>/dev/null || echo "Not installed")"
	@echo
	@echo "=== Installed Packages ==="
	pip list | grep -E "(pisecure|cryptography|pytest|black|mypy)" || echo "Key packages not found"

# Help for specific targets
help-%: ## Show help for a specific target
	@grep -E '^$*:.*?## .*$$' $(MAKEFILE_LIST) | grep "$*" | awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'