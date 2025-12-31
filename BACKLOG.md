# Feature Backlog

## Planned Features (in priority order)

### 1. Save user preferences
- Save last location + filter preferences in localStorage
- Remembers: zip code, work hours filter, threshold, duration, days

### 2. Weather integration
- Show temp (high/low) and % chance of rain for windows within 7 days
- Use Weather.gov (NWS) API - free, no key, no rate limits
- Display inline with each window entry

### 3. GPS location (future)
- Auto-detect user location from device

### 4. Branding/domain (future)
- Custom domain styling when deployed to own domain

### 5. Configurable work hours
- Default to 9-5 M-F
- Allow user to override start/end times

### 6. Calendar view for windows
- Calendar-style view showing tide windows across days/weeks

## Bug Fixes / Improvements

### Remove 30-minute minimum duration constraint
- Currently min duration input has `min="30"` - remove this arbitrary limit
- Users should be able to search for shorter windows if desired

---

## Completed Features

- Tide dashboard with 30/60/90 day forecasts
- Daylight filtering (extended twilight)
- Work hours filter (outside M-F 9-5)
- Imperial/Metric toggle
- First light / Last light indicators
- Mobile responsive layout
- Day of week on tide cards
- Tide window finder with 6-minute resolution data
- Daily cache refresh via GitHub Actions
- Low tide time display (shows time of minimum tide in each window)
- Multi-location support via zip code (`/location` endpoint)
  - Enter US zip code to find nearest NOAA station
  - Shows station name and distance
  - Handles time zones relative to station location
  - Filters for reference stations only (type="R") for reliable predictions
- Multi-station caching
  - Caches tide readings by station ID (20-hour TTL)
  - Persists station list for overnight refresh
  - `/cache-stats` endpoint to view cached stations
