# Feature Backlog

## Planned Features (in priority order)

### 1. Multi-location support (zip code) - IN PROGRESS
- User enters zip code to find nearest NOAA station
- Show station name and distance from entered location
- Handle time zones relative to station location
- Toggle distance units (miles/km) with existing metric setting
- See `features/location.feature` for spec

### 2. Save user preferences
- Save last location + filter preferences in localStorage
- Remembers: zip code, work hours filter, threshold, duration, days

### 3. Weather integration
- Show temp (high/low) and % chance of rain for windows within 7 days
- Use Weather.gov (NWS) API - free, no key, no rate limits
- Display inline with each window entry

### 4. GPS location (future)
- Auto-detect user location from device

### 5. Branding/domain (future)
- Custom domain styling when deployed to own domain

### 6. Configurable work hours
- Default to 9-5 M-F
- Allow user to override start/end times

### 7. Calendar view for windows
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
