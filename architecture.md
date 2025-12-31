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
| CDN/DDOS | Cloudflare | DNS, SSL, DDOS protection, www redirect |
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
│       ├── preferences.py   # Cookie-based user preferences
│       ├── stations.py      # NOAA station lookup
│       ├── weather.py       # NWS weather forecasts
│       ├── tides.py         # Tide processing for dashboard
│       ├── twilight.py      # Dawn/dusk calculations
│       ├── windows.py       # Window finding for La Jolla
│       └── locations.py     # Tidepooling locations data service
├── data/                    # Persisted cache data (committed)
│   ├── known_stations.json  # Seed stations for overnight refresh
│   └── tidepooling_locations_raw.json  # Tidepooling location directory data
├── features/                # Gherkin feature specifications
│   ├── directory.feature    # Tidepooling locations directory
│   ├── landing.feature      # Landing page
│   ├── location.feature     # Location-based tide windows
│   ├── noaa_links.feature   # NOAA source data links
│   ├── preferences.feature  # User preferences
│   ├── tides.feature        # Tide dashboard
│   ├── weather.feature      # Weather integration
│   ├── weather_links.feature # Weather source links
│   └── windows.feature      # Window finder
├── tests/
│   ├── conftest.py          # Shared pytest fixtures
│   ├── unit/                # Unit tests
│   │   └── test_weather.py
│   └── step_defs/           # pytest-bdd step definitions
│       ├── test_directory.py
│       ├── test_landing.py
│       ├── test_location.py
│       ├── test_noaa_links.py
│       ├── test_preferences.py
│       ├── test_tides.py
│       ├── test_weather.py
│       ├── test_weather_links.py
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

### Weather (NWS / Weather.gov)

Base URL: `https://api.weather.gov`

Two-step API call:
1. `/points/{lat},{lon}` - Get grid point and forecast URL
2. `/gridpoints/{office}/{x},{y}/forecast/hourly` - Get hourly forecasts

- Free, no API key required, no rate limits
- Provides 7 days of hourly forecasts
- Returns temperature and precipitation probability per hour
- 60-minute cache TTL (weather changes frequently)
- **Location**: Weather is fetched for the tide station coordinates, not the user's search location (user will be AT the station for tidepooling)

**Weather Source Links**: Weather text is clickable, linking to the NWS graphical forecast page:
```
https://forecast.weather.gov/MapClick.php?w0=t&w3=sfcwind&w5=pop&AheadHour={hours}&FcstType=graphical&textField1={lat}&textField2={lon}
```
- `w0=t` - Show temperature
- `w3=sfcwind` - Show surface wind
- `w5=pop` - Show probability of precipitation
- `AheadHour` - Positions the 48-hour window near the tide window (capped at 100 hours)

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
│  File: data/known_stations.json (committed to repo) │
│  Content: [{station_id, name, state, lat, lon}, ...]│
│  Seed: La Jolla station always included             │
│  Purpose: Track stations for overnight refresh      │
└─────────────────────────────────────────────────────┘
```

### Cache Flow

1. **On Request**: Check if station is cached and valid (< 20 hours old)
2. **Cache Miss**: Fetch from NOAA API, add to cache, persist station ID to `known_stations.json`
3. **Overnight Refresh**: GitHub Actions calls `/refresh-tides` to refresh all known stations
4. **Overnight Sync**: GitHub Actions fetches station list from `/cache-stats` and commits to repo
5. **Startup**: Warms cache with La Jolla data
6. **On Deploy**: Uses committed `known_stations.json` which includes all synced stations

### Station Persistence Decision

**Problem**: Railway deploys create fresh containers, so runtime-discovered stations were lost.

**Chosen Solution**: Overnight GitHub Actions sync

The overnight job fetches the station list from Railway and commits it back to the repo.
This ensures all discovered stations persist across deploys.

| Alternative | Why Discounted |
|-------------|----------------|
| Railway Volumes | Requires paid plan ($5/month), not available on free tier |
| Real-time GitHub sync | More complex, requires GitHub token in Railway env |
| Database (Supabase) | More setup, adds dependency for simple key-value storage |
| Manual periodic commit | Error-prone, requires human intervention |

**Tradeoff**: If a deploy happens between station discovery and overnight sync, that station is temporarily lost (but re-discovered on next search). This is acceptable because:
- La Jolla (seed station) is always preserved
- Deploys are infrequent
- Lost stations are re-added on first user search

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/cache-stats` | GET | View cached stations with full metadata for sync |
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
- Custom domain: tidepooling.org (via Cloudflare)

### Cloudflare Configuration

- Domain registered and DNS hosted on Cloudflare
- Proxy enabled for DDOS protection
- SSL/TLS mode: Full (strict)
- Redirect rule: www.tidepooling.org → tidepooling.org (301)
- Railway free tier allows 1 custom domain; www redirect handled by Cloudflare

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
| User Preferences | Cookies | Server-side rendering, no flash of defaults, 1-year expiry |
| Weather Data | NWS API | Free, no rate limits, hourly forecasts, 60-min cache |
| Maps | Leaflet + OpenStreetMap | Free, no API key, swappable for Mapbox/Google later |
| Design Approach | Mobile-first | Responsive CSS with mobile as default, desktop enhancements |
| Location Data | Static JSON | Simple for now, database later for user contributions |

## Tidepooling Locations Directory

### Overview

The directory provides a browsable list of tidepooling locations in Southern California with an interactive map.

### Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/directory` | GET | Map + list of all locations |
| `/location/{id}` | GET | Individual location detail page |

### Data Source

Location data is stored in `data/tidepooling_locations_raw.json`, aggregated from multiple sources:
- lajollamom.com
- sandiego.org
- californiabeaches.com
- tidepooling.info
- outdoorsocal.com
- california.com
- localanchor.com
- funorangecountyparks.com

### Map Integration

- **Library**: Leaflet 1.9.4
- **Tiles**: OpenStreetMap (no API key required)
- **Markers**: Click to show popup → click popup to navigate to detail page
- **Bounds**: Auto-fit to show all markers with padding

### Location Data Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | URL-safe identifier |
| name | string | Display name |
| also_known_as | string[] | Alternative names |
| city, county, region | string | Location hierarchy |
| coordinates | {lat, lon} | GPS coordinates (nullable) |
| description | string | Overview text |
| best_tide_height_ft | float | Recommended max tide height |
| best_season | string | Best months to visit |
| tips | string[] | Visitor tips |
| marine_life | string[] | Species commonly seen |
| amenities | string[] | Available facilities |
| access_difficulty | string | easy/moderate/difficult |
| sources | string[] | Data sources |
| status | string | Closure notices (optional) |
