# Mirenku Development Makefile
.PHONY: help install dev-install lint format test clean build run pre-commit

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "${CYAN}Mirenku Development Commands${NC}"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "${GREEN}%-15s${NC} %s\n", $$1, $$2}'

install: ## Install production dependencies
	@echo "${YELLOW}Installing production dependencies...${NC}"
	pip install --upgrade pip
	pip install -r requirements.txt

dev-install: install ## Install development dependencies
	@echo "${YELLOW}Installing development dependencies...${NC}"
	pip install -e ".[dev]"
	pre-commit install
	@echo "${GREEN}✓ Development environment ready!${NC}"

lint: ## Run linting checks
	@echo "${YELLOW}Running linting checks...${NC}"
	ruff check src tests
	mypy src --ignore-missing-imports
	bandit -r src -ll -i B101,B601

format: ## Format code with ruff
	@echo "${YELLOW}Formatting code...${NC}"
	ruff format src tests
	ruff check src tests --fix
	@echo "${GREEN}✓ Code formatted!${NC}"

test: ## Run all tests
	@echo "${YELLOW}Running tests...${NC}"
	pytest tests/ -v --cov=src --cov-report=term-missing

test-unit: ## Run unit tests only
	@echo "${YELLOW}Running unit tests...${NC}"
	pytest tests/ -v -m unit

test-integration: ## Run integration tests only
	@echo "${YELLOW}Running integration tests...${NC}"
	pytest tests/ -v -m integration

test-coverage: ## Run tests with coverage report
	@echo "${YELLOW}Running tests with coverage...${NC}"
	pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "${GREEN}✓ Coverage report generated in htmlcov/${NC}"

clean: ## Clean build artifacts
	@echo "${YELLOW}Cleaning build artifacts...${NC}"
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "${GREEN}✓ Cleaned!${NC}"

build: clean ## Build executable with PyInstaller
	@echo "${YELLOW}Building executable...${NC}"
	pyinstaller mirenku.spec
	@echo "${GREEN}✓ Build complete! Check dist/ directory${NC}"

run: ## Run the application
	@echo "${CYAN}Starting Mirenku...${NC}"
	python src/main.py

pre-commit: ## Run pre-commit hooks on all files
	@echo "${YELLOW}Running pre-commit hooks...${NC}"
	pre-commit run --all-files

update-deps: ## Update dependencies to latest versions
	@echo "${YELLOW}Updating dependencies...${NC}"
	pip-compile --upgrade requirements.in
	pip-compile --upgrade requirements-dev.in
	pip install -r requirements.txt
	@echo "${GREEN}✓ Dependencies updated!${NC}"

security: ## Run security checks
	@echo "${YELLOW}Running security checks...${NC}"
	bandit -r src -f json -o security-report.json
	safety check --json
	@echo "${GREEN}✓ Security check complete!${NC}"

docs: ## Generate documentation
	@echo "${YELLOW}Generating documentation...${NC}"
	sphinx-build -b html docs docs/_build
	@echo "${GREEN}✓ Documentation built in docs/_build${NC}"

release: ## Prepare a new release
	@echo "${YELLOW}Preparing release...${NC}"
	@read -p "Enter version number (e.g., 0.3.2): " VERSION; \
	echo "Updating version to $$VERSION..."; \
	sed -i "s/__version__ = .*/__version__ = \"$$VERSION\"/" src/__init__.py; \
	git add -A; \
	git commit -m "Release v$$VERSION"; \
	git tag -a "v$$VERSION" -m "Release version $$VERSION"; \
	echo "${GREEN}✓ Release v$$VERSION prepared! Run 'git push --tags' to publish${NC}"

# Windows-specific commands (use with Git Bash or WSL)
ifeq ($(OS),Windows_NT)
    PYTHON := python
    RM := del /F /Q
    RMDIR := rmdir /S /Q
else
    PYTHON := python3
    RM := rm -f
    RMDIR := rm -rf
endif
