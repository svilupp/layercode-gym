.PHONY: help app tunnel format lint lint-fix typecheck test check check-all install dev clean build publish

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  make app         - Start the FastHTML app with auto-reload"
	@echo "  make tunnel      - Start the Layercode tunnel"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format      - Format code with ruff"
	@echo "  make lint        - Lint code with ruff (check only)"
	@echo "  make lint-fix    - Lint and auto-fix issues with ruff"
	@echo "  make typecheck   - Run ty type checking"
	@echo "  make test        - Run pytest tests"
	@echo "  make check       - Run format + lint + typecheck"
	@echo "  make check-all   - Run format + lint + typecheck + tests"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install production dependencies"
	@echo "  make dev         - Install all dependencies including dev tools"
	@echo "  make clean       - Remove Python cache files"

# Start the FastHTML app with auto-reload
app:
	UVICORN_RELOAD=1 uv run python main.py

# Start the Cloudflare tunnel
tunnel:
	cloudflared --url http://localhost:8000 --loglevel debug

# Format code with ruff
format:
	@echo "Formatting code with ruff..."
	uv run ruff format .

# Lint code with ruff (check only)
lint:
	@echo "Linting code with ruff..."
	uv run ruff check .

# Lint and auto-fix issues with ruff
lint-fix:
	@echo "Linting and fixing code with ruff..."
	uv run ruff check --fix .

# Type check with ty
typecheck:
	@echo "Type checking with ty..."
	uv run ty check src/ tests/

# Run tests with pytest
test:
	@echo "Running tests with pytest..."
	uv run pytest

# Run format, lint, and typecheck
check: format lint typecheck
	@echo ""
	@echo "✓ All checks passed!"

# Run all checks including tests
check-all: format lint typecheck test
	@echo ""
	@echo "✓ All checks and tests passed!"

# Install production dependencies only
install:
	uv sync

# Install all dependencies including dev tools
dev:
	uv sync --extra dev


build:
	rm -rf dist/
	uv build

publish: build
	uv publish

# Clean Python cache files
clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Clean complete!"
