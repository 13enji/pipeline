# Feature Backlog

## Planned Features (in priority order)

### 1. GPS location (future)
- Auto-detect user location from device

### 2. Configurable work hours
- Default to 9-5 M-F
- Allow user to override start/end times
- Time-of-day filters: morning only, afternoon only, weekends only
- Multiple selections allowed (e.g., "mornings and weekends")

### 3. Calendar view for windows
- Calendar-style view showing tide windows across days/weeks

### 4. Map confirmation for location
- Show a map to confirm the location searched for
- Helps users verify the correct station was found

### 5. 24-hour time filter option
- Add option to show all 24 hours (no work hours filter)
- Currently only filters for outside work hours

### 6. Fix Celsius range formatting
- Current display of "-1-0C" is hard to read
- Improve formatting for negative to positive temperature ranges (e.g., "-1 to 0°C")

### 7. Add schema validation tests for tidepooling locations JSON
- Validate all required fields are present on each location
- Check stats match actual counts (total_locations, by_county, with/without coordinates)
- Ensure no duplicate IDs
- Validate coordinates are valid lat/lon when present

### 8. Filter for active/current NOAA stations only
- Some NOAA stations are defunct but still appear in the API (e.g., Oceanside Harbor 9410396)
- Add logic to only include stations that are currently operational
- Should apply to both reference and subordinate station lookups

### 9. Tidepooling locations directory (enhancements)
- ~~Aggregate known tidepooling locations from web sources~~ (done)
- ~~Create `/directory` page with Leaflet/OSM map~~ (done)
- ~~Create `/location/{id}` detail pages~~ (done)
- ~~Review and resolve 3 potential duplicate pairs manually~~ (done - merged into 57 locations)
- Pending: Add coordinates to 11 locations missing them
- Future: Search bar to focus map
- Future: Driving directions deep link (native maps app)
- Future: Expand beyond SoCal (Central CA, Northern CA, other states)
- Future: User-contributed locations (requires database)

### 10. User Analystics
- Something to see where our users are and how many users we have and what they use

---

## Completed Features

- Tidepooling locations directory
  - `/directory` page with Leaflet/OpenStreetMap interactive map
  - `/location/{id}` detail pages for each location
  - 57 Southern California locations (46 with coordinates)
  - Mobile-first responsive design
  - Data aggregated from 8+ sources
- NOAA source data links
  - /tides: Link to NOAA with 31-day range from today
  - /windows and /location: Link per window to NOAA for that day
  - Links open in new tab
- Landing page at root URL
  - Navigation buttons: Location Window, La Jolla Window, Tides, Cache Stats
  - Mobile responsive design
- Custom domain and DDOS protection
  - Domain registered via Cloudflare (tidepooling.org)
  - Cloudflare proxy provides DDOS mitigation
  - SSL/TLS encryption to Railway
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
  - Uses reference stations for window calculations (6-minute data)
- Multi-station caching
  - Caches tide readings by station ID (20-hour TTL)
  - Persists station list for overnight refresh
  - `/cache-stats` endpoint to view cached stations and predictions
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
- Weather source links
  - Weather text is clickable, links to NWS forecast page
  - Shows temp, wind, and precipitation for location
  - AheadHour param positions 48-hour window near tide window time
  - Links open in new tab, underline on hover
- Subordinate station support for low tide times
  - Uses closest station (reference OR subordinate) for low tide time/height
  - Window boundaries still calculated from closest reference station (6-minute data)
  - More accurate low tide times when subordinate station is closer to user
  - High/low predictions cached with same TTL as 6-minute data
  - Falls back to reference station data if no subordinate low found in window
