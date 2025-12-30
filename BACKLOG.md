# Feature Backlog

## Planned Features

### 1. Add day of week to tide cards
Display the day of the week (e.g., "SAT") alongside the date on each tide entry.

### 2. Tide window finder
Redesign to allow specifying a target tide height and duration, then show all days/times that satisfy the criteria.
- Will need all tide height data, not just highs and lows
- Apply daylight and work hour filters
- Example: "Show me all times when tide is below 1ft for at least 2 hours"

### 3. Configurable work hours
- Default to 9-5 M-F
- Allow user to override start/end times
- Persist preference (cookie or URL params)

### 4. Multi-location support
Enable tide data for any location in the US.
- Station selector or search
- Remember last selected location
- May need to look up twilight times for each location's coordinates

---

## Completed Features
- Tide dashboard with 30/60/90 day forecasts
- Daylight filtering (extended twilight)
- Work hours filter (outside M-F 9-5)
- Imperial/Metric toggle
- First light / Last light indicators
- Mobile responsive layout
