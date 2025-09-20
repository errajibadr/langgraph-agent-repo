# LangGraph Agent Repository Makefile

.PHONY: help install-deps test lint format frontend dev-frontend clean

# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'



install-deps: ## Install all project dependencies
	uv sync --all-packages
# Installation targets
i: install-deps ## Alias for install-deps target

install-frontend: ## Install frontend dependencies
	uv sync --package frontend
i/f: install-frontend

install-ai-engine: ## Install ai-engine dependencies
	uv sync --package ai_engine
i/ai: install-ai-engine



# Frontend targets
frontend: ## Launch the Streamlit frontend interface
	uv run frontend
f: frontend

dev-frontend: ## Run frontend in development mode with auto-reload
	cd packages/frontend && streamlit run src/frontend/app.py --server.runOnSave true
f/dev: dev-frontend
f/d: dev-frontend

# Testing targets
test: ## Run all tests
	uv run pytest

test-ai-engine: ## Test the ai-engine package
	cd packages/ai_engine && uv run python -m pytest

test-custom-model: ## Test the custom chat model
	cd packages/ai_engine && uv run python models/custom_chat_model.py

# Linting and formatting targets
lint: ## Run linting checks
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

# Development targets
clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Docker targets (if needed later)
build-docker: ## Build Docker containers
	docker-compose build

run-docker: ## Run Docker containers
	docker-compose up

# Environment setup
setup-env: ## Set up development environment
	@echo "Setting up development environment..."
	@echo "1. Install dependencies:"
	@echo "   make install-deps"
	@echo "2. Set environment variables:"
	@echo "   export LLM_PROVIDER=custom"
	@echo "   export API_KEY=your_api_key"
	@echo "   export BASE_URL=https://api.openai.com/v1"
	@echo "   export MODEL_NAME=gpt-3.5-turbo"
	@echo "3. Run frontend:"
	@echo "   make frontend"


docker/langgraph-up:
	@docker compose -f infra/docker/langgraph.docker-compose.yaml --env-file .env -p langgraph-selfhosted up -d
lup: docker/langgraph-up

## Stop LangGraph services  
docker/langgraph-down:
	@docker compose -f infra/docker/langgraph.docker-compose.yaml --env-file .env -p langgraph-selfhosted down
ldown: docker/langgraph-down