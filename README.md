# OpenClaw

Secure Skill Lifecycle Manager - A zero-trust skill CI/CD pipeline for LLM-generated Python code.

## Overview

OpenClaw validates LLM-generated Python code through three security layers before allowing it into production:

1. **AST Gate** - Static analysis to reject forbidden imports, calls, and patterns
2. **Docker Sandbox** - Runtime isolation with strict resource limits
3. **Promotion Gates** - Replay, regression, and redteam testing

## Requirements

- Python 3.11+
- uv (package manager)
- Docker (for sandbox execution)

## Setup

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Run linter
uv run ruff check .
```

## Project Structure

```
openclaw/
├── src/           # Source code
├── tests/         # Test suite
├── skills/        # Built-in reference skills
├── skills_staging/ # Night mode output
├── skills_prod/   # Production skills
├── data/          # Runtime data (queue, registry, audit)
├── docker/        # Sandbox Dockerfile
└── spec/          # Specifications
```

## License

Proprietary
