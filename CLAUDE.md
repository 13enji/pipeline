# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (requires Python 3.12+)
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run server locally
uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/step_defs/test_hello.py

# Run a specific test
pytest tests/step_defs/test_hello.py::test_hello_endpoint

# Lint
ruff check .

# Fix lint issues
ruff check --fix .
```

## Architecture

This is a FastAPI data dashboard that fetches data from external APIs. It uses **specification-driven development** with BDD (pytest-bdd).

### Development Workflow

1. User describes feature in plain English
2. Claude Code writes Gherkin spec in `features/*.feature`
3. User reviews/approves the spec
4. Claude Code generates step definitions in `tests/step_defs/`
5. Claude Code implements code to pass tests
6. Push triggers GitHub Actions CI → Railway auto-deploys on success

### Key Directories

- `app/` — FastAPI application (main.py is entry point)
- `features/` — Gherkin feature specifications (Given-When-Then)
- `tests/step_defs/` — pytest-bdd step definitions that execute feature specs

### Testing Layers

| Layer | Location | Purpose |
|-------|----------|---------|
| Feature/BDD | `features/` + `tests/step_defs/` | User-facing behavior from Gherkin specs |
| Unit | `tests/unit/` | Individual functions |
| Integration | `tests/` | API endpoints with TestClient |

### Deployment

- **CI**: GitHub Actions runs `ruff check` and `pytest` on every push
- **Hosting**: Railway auto-deploys `main` branch when CI passes
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
