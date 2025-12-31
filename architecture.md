# Architecture

This document captures the architecture decisions for this project.

## Overview

A tide window finder web application that fetches data from NOAA's Tides & Currents API and helps users find optimal low-tide windows for coastal activities. Built with a specification-driven development workflow using BDD (Behavior-Driven Development).

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
| Tide Data | NOAA Tides & Currents API | 6-minute interval tide predictions |
| Geocoding | Zippopotam.us API | Zip code to coordinates |
| Twilight | Astral library | Civil dawn/dusk calculations |

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
│   └── services/            # Business logic, external API calls
│       ├── cache.py         # Multi-station tide data caching
│       ├── geocoding.py     # Zip code to coordinates
│       ├── location_windows.py  # Location-based window finding
│       ├── noaa.py          # NOAA API client
│       ├── stations.py      # NOAA station lookup
│       ├── tides.py         # Tide processing for dashboard
│       ├── twilight.py      # Dawn/dusk calculations
│       └── windows.py       # Window finding for La Jolla
├── data/                    # Persisted cache data (gitignored)
│   └── known_stations.json  # Stations to refresh overnight
├── features/                # Gherkin feature specifications
│   ├── location.feature     # Location-based tide windows
│   ├── tides.feature        # Tide dashboard
│   └── windows.feature      # Window finder
├── tests/
│   ├── conftest.py          # Shared pytest fixtures
│   └── step_defs/           # pytest-bdd step definitions
│       ├── test_location.py
│       ├── test_tides.py
│       └── test_windows.py
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions workflow
├── pyproject.toml           # Project config and dependencies
├── architecture.md          # This file
├── BACKLOG.md               # Feature backlog
├── CLAUDE.md                # Claude Code instructions
└── README.md
```

## External Integrations

### NOAA Tides & Currents API

Base URL: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`

Used for:
- **6-minute interval predictions** - High-resolution tide height data
- **Station metadata** - List of tide prediction stations

Important notes:
- Only **reference stations** (type="R") return predictions with MLLW datum
- Subordinate stations (type="S") have no datum data and will fail
- Maximum 31 days per request for 6-minute data (we batch requests)

### Station Lookup

Base URL: `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json`

- Fetches all tide prediction stations
- Filters to reference stations only (type="R")
- Uses Haversine formula to find nearest station to coordinates

### Geocoding (Zippopotam.us)

Base URL: `https://api.zippopotam.us/us/{zip_code}`

- Free, no API key required
- Returns latitude/longitude for US zip codes

## Caching Architecture

### Multi-Station Cache

```
┌─────────────────────────────────────────────────────┐
│  In-Memory Cache (per station)                      │
│  ─────────────────────────────────                  │
│  Key: station_id                                    │
│  Value: {readings, fetched_at, timezone}            │
│  TTL: 20 hours                                      │
└─────────────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  Persistent Station List                            │
│  ─────────────────────────────────                  │
│  File: data/known_stations.json                     │
│  Content: [{station_id, timezone_name}, ...]        │
│  Purpose: Track stations for overnight refresh      │
└─────────────────────────────────────────────────────┘
```

### Cache Flow

1. **On Request**: Check if station is cached and valid (< 20 hours old)
2. **Cache Miss**: Fetch from NOAA API, add to cache, persist station ID
3. **Overnight Refresh**: `/refresh-tides` refreshes all known stations
4. **Startup**: Warms cache with La Jolla data

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/cache-stats` | GET | View cached stations and refresh times |
| `/refresh-tides` | POST | Force refresh all known stations |

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

### Scheduled Jobs

- **Daily cache refresh**: GitHub Actions workflow calls `/refresh-tides` endpoint

### Railway Deployment

- Connected to GitHub repository
- Auto-deploys `main` branch when CI passes
- Environment variables configured in Railway dashboard
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | FastAPI | Modern, async (good for API calls), excellent docs, Python |
| BDD Tool | pytest-bdd | Gherkin syntax, integrates with pytest ecosystem |
| Hosting | Railway | Simple deployment, good DX, no infrastructure management |
| Tide Data | NOAA API | Free, authoritative source, 6-minute resolution |
| Geocoding | Zippopotam.us | Free, no API key, simple |
| Caching | In-memory + file | Simple, no database needed, persists station list |
| Reference Stations Only | Filter type="R" | Subordinate stations don't return MLLW predictions |
