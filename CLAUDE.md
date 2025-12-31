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

### Development Workflow (MUST FOLLOW)

**IMPORTANT: Always follow this BDD process for new features. Do not skip steps.**

1. **Interview** — Ask user clarifying questions about the feature
2. **Specify** — Write Gherkin spec in `features/*.feature`
3. **Approve** — User reviews and approves the spec before any implementation
4. **Implement** — Write step definitions in `tests/step_defs/`, then implement code
5. **Test** — Run pytest to verify all scenarios pass
6. **Document** — Update README.md, architecture.md, and BACKLOG.md as needed
7. **Deploy** — Run `git pull`, commit, push → GitHub Actions CI → Railway auto-deploys on success

Never write implementation code before the Gherkin spec is approved.
Always run `git pull` before committing to avoid conflicts with overnight sync jobs.

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
