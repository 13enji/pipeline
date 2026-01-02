# Tidepooling.org

Tide window finder web application built with FastAPI. Helps find optimal low-tide windows for coastal activities by analyzing NOAA tide prediction data.

**Live at: [tidepooling.org](https://tidepooling.org)**

## Features

- **Landing Page** (`/`) - Navigation to all app features
- **Tide Dashboard** (`/tides`) - 30/60/90 day tide forecasts for La Jolla
- **Window Finder** (`/windows`) - Find continuous windows where tide stays below a threshold
- **Location Search** (`/location`) - Enter any US zip code to find tide windows for the nearest NOAA station
- **Subordinate Station Support** - Low tide times use the closest station (reference OR subordinate) for better accuracy
- **Filters** - Work hours filter (outside M-F 9-5), daylight only, minimum duration
- **Units** - Toggle between imperial (ft/miles) and metric (m/km)
- **Light Times** - Shows first/last light times for each window
- **Weather Forecasts** - Temperature range and precipitation chance for windows within 7 days
- **Weather Links** - Click weather info to view NWS forecast page for that location/time
- **NOAA Links** - Direct links to NOAA tide predictions for each window
- **Saved Preferences** - Remembers your settings (zip code, filters, units) in cookies

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Landing page with navigation |
| `GET /tides` | Tide dashboard with forecasts |
| `GET /windows` | Tide window finder for La Jolla |
| `GET /location` | Location-based tide windows (zip code) |
| `GET /cache-stats` | View cached stations, predictions cache, and refresh times |
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

- **NOAA API** - Fetches 6-minute interval tide predictions and high/low predictions
- **Geocoding** - Converts zip codes to coordinates via Zippopotam.us
- **Station Lookup** - Finds nearest NOAA reference station (for windows) and nearest station of any type (for low tide)
- **Caching** - Multi-station cache with 20-hour TTL for both 6-minute readings and high/low predictions

### Data Flow

```
Zip Code → Geocode → Find Nearest Reference Station → Fetch/Cache 6-min Readings → Find Windows
                   → Find Nearest Station (any type) → Fetch/Cache High/Low → Enhance Windows with Low Tide
```
