# Pipeline

Tide window finder web application built with FastAPI. Helps find optimal low-tide windows for coastal activities by analyzing NOAA tide prediction data.

## Features

- **Tide Dashboard** (`/tides`) - 30/60/90 day tide forecasts for La Jolla
- **Window Finder** (`/windows`) - Find continuous windows where tide stays below a threshold
- **Location Search** (`/location`) - Enter any US zip code to find tide windows for the nearest NOAA station
- **Filters** - Work hours filter (outside M-F 9-5), daylight only, minimum duration
- **Units** - Toggle between imperial (ft/miles) and metric (m/km)
- **Light Times** - Shows first/last light times for each window
- **Saved Preferences** - Remembers your settings (zip code, filters, units) in cookies

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /tides` | Tide dashboard with forecasts |
| `GET /windows` | Tide window finder for La Jolla |
| `GET /location` | Location-based tide windows (zip code) |
| `GET /cache-stats` | View cached stations and refresh times |
| `POST /refresh-tides` | Force refresh cache (called by scheduled job) |

## Setup

```bash
# Create virtual environment (requires Python 3.12+)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## Development

```bash
# Run the server locally
uvicorn app.main:app --reload

# Run tests
pytest

# Run linting
ruff check .
```

## Architecture

See [architecture.md](architecture.md) for detailed architecture documentation.

### Key Services

- **NOAA API** - Fetches 6-minute interval tide predictions
- **Geocoding** - Converts zip codes to coordinates via Zippopotam.us
- **Station Lookup** - Finds nearest NOAA reference station
- **Caching** - Multi-station cache with 20-hour TTL, persists station list for overnight refresh

### Data Flow

```
Zip Code → Geocode → Find Nearest Station → Fetch/Cache Readings → Find Windows → Display
```
