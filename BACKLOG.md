# Feature Backlog

## Planned Features (in priority order)

### BUG
- Scripps got created as a subordinate station in the nightly cache refresh.  Not sure we should code of this but maybe it's a data point, reference stations appear to be just numbers and sub stations appear to be TWC### for example.

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
- ~~Review and resolve 3 potential duplicate pairs manually~~ (done)
- ~~Add coordinates to all locations~~ (done - all 51 locations now have coordinates)
- Future: Search bar to focus map
- Future: Driving directions deep link (native maps app)
- Future: Expand beyond SoCal (Central CA, Northern CA, other states)
- Future: User-contributed locations (requires database)

### 10. User Analytics
- Something to see where our users are and how many users we have and what they use

### 11. Site architecture refactor + UI/UX (mobile-first)

**Architecture changes:**
- Merge landing page + directory + search into single home page (`/`)
- Merge location detail + windows into `/spot/:id`
- Add `/learn` for educational content
- Delete `/windows` (La Jolla specific - replaced by spot-based windows)
- Delete `/location` (search moves to home page)
- Delete `/directory` (merged into home)
- Hide `/tides` and `/cache-stats` from nav (keep URLs for admin)
- No reference to "stations" in UI - implementation details hidden

**Page structure:**
```
/              Home = Explore (search + map + spot list)
/spot/:id      Location detail + tide windows
/learn         Educational content (what is tidepooling, etiquette, gear)
/go            QR redirect (smart, GPS-aware in future)
/go/:code      QR redirect for specific locations
```

**Technical refactor:**
- Set up Jinja2 templates with base.html
- Add Pico CSS for "homemade but beautiful" aesthetic
- Shared header/nav across all pages
- localStorage for recent locations (last 5)

**UI/UX improvements:**
- Two-speed interface: hero for first-timers, recent locations for regulars
- Warm color palette (teal primary, coral accent)
- Nunito font for headings
- Friendly microcopy
- Eco-first messaging for credibility

See design-direction.md for full details.

**Status:** Phase 1 complete (Jinja2 templates, Pico CSS, new route structure)

### 11a. Smart Search Bar ("Find a Spot")

Three user journeys supported:
1. **Expert tidepooler** → Types spot name → Autocomplete → Clicks → Goes to `/spot/{id}`
2. **Trip planner** → Types town/zip/address → Map repositions → Explores pins
3. **Novice** → Zooms/pans map manually → Browses cards below

**Search bar behavior:**
- Recognizes spot names → shows autocomplete dropdown → navigates directly
- Recognizes locations (zip/town) → repositions map → user explores pins

**"Search anchor" for card filtering (at scale):**
- When user searches a location, that becomes their "anchor point"
- Cards filter to spots within ~50 miles of anchor, sorted by distance
- Cards show: "Shell Beach · 8 mi from your search"
- Map can pan freely without affecting card list (map viewport ≠ search location)
- "Showing spots near San Diego ✕" chip to clear anchor and show all
- Before any search: all cards shown, sorted alphabetically

**Implementation phases:**
- [x] Phase 1: Autocomplete for known spots (names + cities + also-known-as aliases)
- [ ] Phase 2: Zip/town geocoding to reposition map + anchor-based card filtering
- [ ] Phase 3: "Near me" geolocation button

### 12. PWA support
- Add manifest.json and service worker
- Enable "Add to home screen" on mobile
- Offline caching of location data
- Do this AFTER UI improvements (first impressions matter for installed apps)

### 13. Crowdsourcing: Suggest edits
- "Suggest an edit" button on each location page
- Simple form: category + freetext
- Submissions emailed for review
- No database needed initially

### 14. Crowdsourcing: GPS-gated new location submissions
- "Add a location" button (mobile only)
- Requires GPS permission - user must be physically present
- Auto-check for duplicates within 100m
- Form: name + optional description/tips
- Optional photo capture
- Submissions emailed with Google Maps link for quick verification
- See crowdsource.md for full design

### 15. SEO
- Meta tags (title, description, og:image per page)
- Structured data (JSON-LD for locations)
- Sitemap.xml
- robots.txt
- Semantic HTML (comes naturally with Pico CSS)

### 16. QR codes and redirect system
- `/go` - Smart redirect (GPS-aware in future, home for now)
- `/go/:code` - Redirect based on code lookup (e.g., `/go/crystal-cove-parking`)
- Config file maps codes to destinations (changeable without reprinting QR)
- Future: GPS permission → redirect to nearest spot
- Track scan analytics
- Generate printable QR codes for each location

### 17. Simple bot/scraper blocking
- Check User-Agent header for browser signatures
- Whitelist known good bots (Googlebot, Bingbot, social media crawlers)
- Return 403 for obvious scrapers (python-requests, curl, empty UA)
- Low priority - mainly to prevent lazy scraping

### 18. Funny idea to add personality
- For page not found, serve a cartoon fish the same way that amazon serves pictures of dogs

### 19. If a user visits a location page in a window, then tell them how long they have left, whether the tide is coming in or going out, when it will start coming in, safety etc.

### 20. When a user visits a page, they should be greated with 'The next great time to tidepool here is....' and will with the next window.
- as well as all the windows still on that page.

### other notes on the new site navigation and information
- Spot pages do not need to list the station where they are getting tide information
- should consider crediting NOAA at the bottom of every page (as well as link to the window?)
- because its easier to explore spots and a lot of spots are not cached at the moment, it means that the page load speeds are slow.  Should we consider caching all stations (reference and / or sub stations) always? Will NOAA allow this load on their system? Once a night?
- The filter for 'outside work hours' isn't clear which is selected, lets discuss whether we remove the work hours concept completely
- The window descrtiption needs more styling at least 'SAT JAN 3RD 2026' all the same font, all the same size is not readable.  Day of the week will be more important if we choose to remove the work hours filter
- Add some styling / iconography for weather for a window, could consider doing the same for 'last light' too.
- Eventually the tide window filter should default to the 'ideal tide height' value if we have it but the height should remian as an option
- Probably don't need to number of days ahead as an option, we should probably just do it for 90 days and then have the ability for the user to 'show more', which we could then go away and fetch from NOAA
- grey text on the spot banner 'alos know as' does not show well.
- I have to scroll quite a long way down (past 12 tide windows) to realize that there is other information (other than the tide windows) at the bottom of the page 'Tips' etc.  We should solve this somehow.
- Map pins on the map have a solid blue highlight that obstructs the map.
- The zoom button in the top right seems to be corupt, +- are not in the boxes.
- 51 locations (51 on map).  I think we should lose the concept of on map.  Lets assume that all locations will have coordinates and appear on the map, once they have been 'promoted' to 'production'.
- tide pool etiquette - remove 'touch gently' I don't think anything should be touched at all.  Remove 'replace rocks' I don't think we should be disturbing habitat.
- Consider adding a 'about' page to make the site feel personal and not coorproate
- Feature: or maybe just some info, the best tide generally (phase of the moon) will be the same for all of the usa.  We could consider having 2 levels of timing 'Genrally for all spots on the 3rd - 5th of Jan and then 17th - 19th Jan' and specific times for each location.  So the landing page could be something grabbing like.....10 days till your next tidepooling window'.  I think this is the level at which I would not mind implementing an export to calendar function, with a link back to the site 'Where are you going to go?'
- please make sure that you update all the docs to relfect our new architecture and please make sure that you talk to me about any additional tests / types of tests / frameworks we might need.

---

## Completed Features

- Tidepooling locations directory
  - `/directory` page with Leaflet/OpenStreetMap interactive map
  - `/location/{id}` detail pages for each location
  - 51 Southern California locations (all with coordinates)
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
