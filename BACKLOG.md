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

### 4. Add reference stations
- Allow users to select from known reference stations directly

### 5. Use closest station (including subordinate) for low tide time
- Currently only reference stations (type="R") are used for everything
- Subordinate stations (type="S") can return high/low predictions but not 6-minute interval data
- Change: Find closest station (reference OR subordinate) for the "lowest tide" time display
- Keep using closest reference station for the 6-minute tide window calculations
- This gives more accurate low tide times when a subordinate station is closer to the user

### 6. Map confirmation for location
- Show a map to confirm the location searched for
- Helps users verify the correct station was found

### 7. 24-hour time filter option
- Add option to show all 24 hours (no work hours filter)
- Currently only filters for outside work hours

### 8. Fix Celsius range formatting
- Current display of "-1-0C" is hard to read
- Improve formatting for negative to positive temperature ranges (e.g., "-1 to 0°C")

### 9. Tidepooling locations directory (enhancements)
- ~~Aggregate known tidepooling locations from web sources~~ (done)
- ~~Create `/directory` page with Leaflet/OSM map~~ (done)
- ~~Create `/location/{id}` detail pages~~ (done)
- Pending: Review and resolve 5 potential duplicate pairs manually
- Pending: Add coordinates to 14 locations missing them
- Future: Search bar to focus map
- Future: Driving directions deep link (native maps app)
- Future: Expand beyond SoCal (Central CA, Northern CA, other states)
- Future: User-contributed locations (requires database)

---

## Completed Features

- Tidepooling locations directory
  - `/directory` page with Leaflet/OpenStreetMap interactive map
  - `/location/{id}` detail pages for each location
  - 62 Southern California locations (48 with coordinates)
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
- Weather source links
  - Weather text is clickable, links to NWS forecast page
  - Shows temp, wind, and precipitation for location
  - AheadHour param positions 48-hour window near tide window time
  - Links open in new tab, underline on hover
