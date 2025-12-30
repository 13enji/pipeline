# Architecture

This document captures the architecture decisions for this project.

## Overview

A data dashboard web application that fetches data from external APIs and displays it to users. Built with a specification-driven development workflow using BDD (Behavior-Driven Development).

## Stack

| Category | Tool | Purpose |
|----------|------|---------|
| Editor | VS Code + Claude Code | Local development |
| Code Hosting | GitHub | Repository, issues, pull requests |
| Project Management | GitHub Projects | Kanban board for task tracking |
| Framework | FastAPI | Python web framework |
| Unit/Integration Tests | pytest + httpx | Code-level testing |
| Feature Tests (BDD) | pytest-bdd | Gherkin specs as executable tests |
| CI/CD | GitHub Actions | Run tests on every push |
| Hosting | Railway | Public deployment |
| Database | Supabase (PostgreSQL) | When needed (deferred) |

## Development Workflow

```
┌─────────────────────────────────────────────────────┐
│  1. Describe feature in plain English               │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  2. Claude Code formalizes into Gherkin spec        │
│     (Given-When-Then scenarios)                     │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  3. Review and approve specs                        │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  4. Claude Code generates step definitions          │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  5. Claude Code implements code to pass tests       │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  6. Push to GitHub                                  │
│     → GitHub Actions runs tests                     │
│     → Railway deploys if tests pass                 │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
pipeline/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── routers/             # API route handlers
│   │   └── __init__.py
│   ├── services/            # Business logic, external API calls
│   │   └── __init__.py
│   └── models/              # Pydantic models for request/response
│       └── __init__.py
├── features/                # Gherkin feature specifications
│   └── *.feature
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared pytest fixtures
│   ├── unit/                # Unit tests
│   │   └── __init__.py
│   └── step_defs/           # pytest-bdd step definitions
│       └── __init__.py
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions workflow
├── pyproject.toml           # Project config and dependencies
├── architecture.md          # This file
└── README.md
```

## Testing Strategy

### Test Layers

| Layer | Location | Purpose | Tools |
|-------|----------|---------|-------|
| Unit | `tests/unit/` | Test individual functions in isolation | pytest |
| Integration | `tests/unit/` | Test API endpoints with mocked dependencies | pytest + httpx |
| Feature | `features/` + `tests/step_defs/` | Test user-facing behavior from specs | pytest-bdd |

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only feature tests
pytest tests/step_defs/

# Run with coverage
pytest --cov=app
```

## CI/CD Pipeline

### GitHub Actions

On every push:
1. Check out code
2. Set up Python
3. Install dependencies
4. Run linting (ruff)
5. Run all tests (pytest)
6. Report results

### Railway Deployment

- Connected to GitHub repository
- Auto-deploys `main` branch when CI passes
- Environment variables configured in Railway dashboard

## External Integrations

### APIs (Planned)
- Data source APIs (TBD based on dashboard requirements)
- Potentially maps API for geographic data

### Database (Deferred)
- Supabase (PostgreSQL) when persistent storage is needed
- Will be used for caching API responses and user preferences

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | FastAPI | Modern, async (good for API calls), excellent docs, Python |
| BDD Tool | pytest-bdd | Gherkin syntax, integrates with pytest ecosystem |
| Hosting | Railway | Simple deployment, good DX, no infrastructure management |
| No self-hosting | Managed services only | Solo developer, minimize ops burden |
| Database deferred | Start without | Prove pipeline first, add when needed |

## Future Considerations

- **Authentication**: Supabase Auth when user accounts are needed
- **Caching**: Redis or in-memory caching for API responses
- **Maps**: Integration TBD (Mapbox, Leaflet, Google Maps)
- **Monitoring**: Railway provides basic metrics; may add Sentry for error tracking
