# Feature Backlog

## Planned Features (in priority order)

### 1. GPS location (future)
- Auto-detect user location from device

### 2. Branding/domain (future)
- Custom domain styling when deployed to own domain

### 3. Configurable work hours
- Default to 9-5 M-F
- Allow user to override start/end times
- Time-of-day filters: morning only, afternoon only, weekends only
- Multiple selections allowed (e.g., "mornings and weekends")

### 4. Calendar view for windows
- Calendar-style view showing tide windows across days/weeks

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
- Overnight station sync to git repo
  - GitHub Actions syncs discovered stations back to repo
  - Stations persist across Railway deploys
- Removed minimum duration constraint
  - Users can now set any duration (including 0 minutes)
- User preferences saved in cookies
  - Remembers: zip code, threshold, min duration, days, units, work filter
  - Shared between /windows and /location pages
  - Reset to defaults button available
- Weather integration for tide windows
  - Shows temperature range and precipitation chance for windows within 7 days
  - Uses NWS (Weather.gov) API - free, no rate limits
  - 60-minute cache TTL for weather data
  - Displays inline with each window entry
