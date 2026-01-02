from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, Form, Query, Request, Response
from fastapi.responses import HTMLResponse

from app.services.cache import get_cache_stats, refresh_cache
from app.services.geocoding import GeocodingError, geocode_zip
from app.services.location_windows import TideWindow as LocationTideWindow
from app.services.location_windows import find_tide_windows_for_station
from app.services.locations import (
    Location,
    get_all_locations,
    get_location_by_id,
    get_locations_with_coordinates,
)
from app.services.preferences import (
    UserPreferences,
    clear_preferences,
    load_preferences,
    save_preferences,
)
from app.services.stations import StationWithDistance, find_nearest_station
from app.services.tides import ProcessedTide, TideCard, get_tide_cards
from app.services.weather import (
    WindowWeather,
    get_hourly_forecasts,
    get_weather_for_window,
)
from app.services.windows import TideWindow, find_tide_windows


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the cache on startup for all known stations."""
    await refresh_cache()
    yield


app = FastAPI(title="Pipeline", version="0.1.0", lifespan=lifespan)


def _calculate_ahead_hours(window_start: datetime) -> int:
    """Calculate AheadHour parameter for NWS weather link.

    Returns hours from now to (window_start - 6 hours), capped at 100.
    """
    # Handle timezone-aware datetimes
    if window_start.tzinfo is not None:
        now = datetime.now(window_start.tzinfo)
    else:
        now = datetime.now()
    # Use window start minus 6 hours to position 48-hour window
    target_time = window_start - timedelta(hours=6)
    hours_ahead = (target_time - now).total_seconds() / 3600
    # Cap at 100 hours max, minimum 0
    return max(0, min(100, int(hours_ahead)))


def _generate_weather_url(lat: float, lon: float, ahead_hours: int) -> str:
    """Generate NWS forecast URL with temp, wind, and precip display."""
    return (
        f"https://forecast.weather.gov/MapClick.php"
        f"?w0=t&w3=sfcwind&w3u=1&w5=pop"
        f"&AheadHour={ahead_hours}"
        f"&FcstType=graphical"
        f"&textField1={lat}&textField2={lon}"
    )


@app.post("/refresh-tides")
async def refresh_tides() -> dict[str, Any]:
    """Force refresh the tide cache. Called by scheduled job."""
    return await refresh_cache()


@app.get("/cache-stats")
async def cache_stats() -> dict[str, Any]:
    """View cache statistics including known stations."""
    return get_cache_stats()


def get_current_time() -> datetime:
    return datetime.now()


def get_greeting(name: str) -> str:
    if not name.strip():
        name = "anonymous"

    hour = get_current_time().hour

    if 6 <= hour < 12:
        return f"Good morning {name}"
    elif 12 <= hour < 18:
        return f"Good afternoon {name}"
    elif 18 <= hour < 22:
        return f"Good evening {name}"
    else:
        return f"Go to bed {name}"


@app.get("/", response_class=HTMLResponse)
def landing_page() -> str:
    """Landing page with navigation to main features."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tidepooling.org</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
                text-align: center;
            }
            h1 {
                color: #1a5f7a;
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .tagline {
                color: #666;
                font-size: 1.2em;
                margin-bottom: 40px;
            }
            .nav-buttons {
                display: flex;
                flex-direction: column;
                gap: 15px;
                max-width: 400px;
                margin: 0 auto;
            }
            .nav-btn {
                display: block;
                padding: 20px 30px;
                background: #1a5f7a;
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                text-decoration: none;
                font-size: 1.2em;
                transition: background 0.2s;
            }
            .nav-btn:hover {
                background: #145a6e;
            }
            .nav-btn.secondary {
                background: #666;
            }
            .nav-btn.secondary:hover {
                background: #555;
            }
            @media (max-width: 768px) {
                h1 {
                    font-size: 2em;
                }
                .nav-buttons {
                    flex-direction: column;
                }
                .nav-btn {
                    padding: 15px 20px;
                    font-size: 1em;
                }
            }
        </style>
    </head>
    <body>
        <h1>Tidepooling.org</h1>
        <p class="tagline">Find the best low tide windows for tidepooling</p>

        <div class="nav-buttons">
            <a href="/directory" class="nav-btn">Tidepooling Directory</a>
            <a href="/location" class="nav-btn">Location Window</a>
            <a href="/windows" class="nav-btn">La Jolla Window</a>
            <a href="/tides" class="nav-btn">Tides</a>
            <a href="/cache-stats" class="nav-btn secondary">Cache Stats</a>
        </div>
    </body>
    </html>
    """


@app.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, World"}


@app.get("/greet", response_class=HTMLResponse)
def greet_form() -> str:
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Greeting</title>
    </head>
    <body>
        <h1>Welcome</h1>
        <form method="post">
            <label for="name">Enter your name:</label>
            <input type="text" id="name" name="name">
            <button type="submit">Submit</button>
        </form>
    </body>
    </html>
    """


@app.post("/greet", response_class=HTMLResponse)
def greet_submit(name: str = Form("")) -> str:
    greeting = get_greeting(name)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Greeting</title>
    </head>
    <body>
        <h1>{greeting}</h1>
        <a href="/greet">Try again</a>
    </body>
    </html>
    """


def _render_tide_entry(tide: ProcessedTide, metric: bool) -> str:
    """Render a single tide entry as HTML."""
    return f"""
        <div class="tide-entry">
            <div class="tide-date">{tide.formatted_date}</div>
            <div class="tide-time">{tide.formatted_time}</div>
            <div class="tide-twilight">
                <span class="twilight-label">{tide.twilight_label}</span>
                <span class="twilight-time">{tide.twilight_time}</span>
            </div>
            <div class="tide-height">{tide.height_display(metric)}</div>
        </div>
    """


def _render_tide_card(card: TideCard, metric: bool) -> str:
    """Render a tide card as HTML."""
    highest_html = "".join(_render_tide_entry(t, metric) for t in card.highest_tides)
    lowest_html = "".join(_render_tide_entry(t, metric) for t in card.lowest_tides)

    highest_limited_msg = ""
    if card.highest_count_limited:
        count = len(card.highest_tides)
        suffix = "s" if count != 1 else ""
        highest_limited_msg = f'<p class="limited-msg">Only {count} tide{suffix} match filter</p>'

    lowest_limited_msg = ""
    if card.lowest_count_limited:
        count = len(card.lowest_tides)
        suffix = "s" if count != 1 else ""
        lowest_limited_msg = f'<p class="limited-msg">Only {count} tide{suffix} match filter</p>'

    return f"""
        <div class="tide-card">
            <h2>{card.period_days} Day Forecast</h2>
            <div class="tide-columns">
                <div class="tide-column">
                    <h3>Highest Tides</h3>
                    {highest_html}
                    {highest_limited_msg}
                </div>
                <div class="tide-column">
                    <h3>Lowest Tides</h3>
                    {lowest_html}
                    {lowest_limited_msg}
                </div>
            </div>
        </div>
    """


@app.get("/tides", response_class=HTMLResponse)
async def tide_dashboard(
    units: str = Query("imperial"),
    work_filter: str = Query("on"),
) -> str:
    """Tide dashboard showing highest and lowest daylight tides."""
    metric = units.lower() == "metric"
    work_filter_on = work_filter.lower() == "on"
    cards = await get_tide_cards(work_filter=work_filter_on)

    cards_html = "".join(_render_tide_card(card, metric) for card in cards)

    # Build URLs preserving other parameters
    work_param = "on" if work_filter_on else "off"
    units_param = "metric" if metric else "imperial"

    units_toggle_url = f"/tides?units={'metric' if not metric else 'imperial'}&work_filter={work_param}"
    units_toggle_text = "Switch to Metric" if not metric else "Switch to Imperial"
    current_units = "m" if metric else "ft"

    work_toggle_url = f"/tides?units={units_param}&work_filter={'off' if work_filter_on else 'on'}"
    work_toggle_text = "Show All Daylight" if work_filter_on else "Outside Work Hours Only"
    work_filter_status = "Outside work hours" if work_filter_on else "All daylight"

    # NOAA link with 31-day range
    today = datetime.now()
    end_date = today + timedelta(days=31)
    noaa_url = f"https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=9410230&bdate={today.strftime('%Y%m%d')}&edate={end_date.strftime('%Y%m%d')}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tide Dashboard - San Diego</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            h1 {{
                color: #1a5f7a;
            }}
            .controls {{
                margin-bottom: 20px;
            }}
            .toggle-btn {{
                padding: 10px 20px;
                background: #1a5f7a;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                margin-right: 5px;
            }}
            .limited-msg {{
                color: #888;
                font-size: 12px;
                font-style: italic;
                margin-top: 10px;
            }}
            .unit-label {{
                margin-left: 10px;
                color: #666;
            }}
            .tide-cards {{
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
            }}
            .tide-card {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                flex: 1;
                min-width: 300px;
            }}
            .tide-card h2 {{
                margin-top: 0;
                color: #1a5f7a;
                border-bottom: 2px solid #1a5f7a;
                padding-bottom: 10px;
            }}
            .tide-columns {{
                display: flex;
                gap: 20px;
            }}
            .tide-column {{
                flex: 1;
            }}
            .tide-column h3 {{
                color: #333;
                font-size: 14px;
                text-transform: uppercase;
                margin-bottom: 15px;
            }}
            .tide-entry {{
                margin-bottom: 15px;
                padding: 10px;
                background: #f9f9f9;
                border-radius: 5px;
            }}
            .tide-date {{
                font-weight: bold;
                color: #333;
            }}
            .tide-time {{
                color: #666;
                font-size: 14px;
            }}
            .tide-height {{
                font-size: 18px;
                font-weight: bold;
                color: #1a5f7a;
                margin-top: 5px;
            }}
            .tide-twilight {{
                font-size: 13px;
                color: #666;
                margin-top: 3px;
            }}
            .twilight-label {{
                display: inline-block;
                padding: 2px 6px;
                background: #ffd700;
                color: #333;
                border-radius: 3px;
                font-size: 11px;
                margin-right: 5px;
            }}
            .twilight-time {{
                color: #888;
            }}
            @media (max-width: 768px) {{
                .controls {{
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}
                .toggle-btn {{
                    display: block;
                    text-align: center;
                    margin-right: 0;
                }}
                .unit-label {{
                    margin-left: 0;
                    text-align: center;
                }}
                .tide-cards {{
                    flex-direction: column;
                }}
                .tide-card {{
                    min-width: auto;
                    width: 100%;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>Tide Dashboard - San Diego</h1>
        <p>Top 3 highest and lowest tides during daylight hours</p>

        <div class="controls">
            <a href="{units_toggle_url}" class="toggle-btn">{units_toggle_text}</a>
            <span class="unit-label">Current: {current_units}</span>
            <a href="{work_toggle_url}" class="toggle-btn">{work_toggle_text}</a>
            <span class="unit-label">Filter: {work_filter_status}</span>
        </div>

        <div class="tide-cards">
            {cards_html}
        </div>

        <p style="margin-top: 30px;">
            <a href="/windows">Switch to Tide Window Finder</a> |
            <a href="{noaa_url}" target="_blank">View on NOAA</a>
        </p>
    </body>
    </html>
    """


def _render_window_entry(
    window: TideWindow,
    metric: bool,
    weather: WindowWeather | None = None,
    station_id: str = "9410230",
    lat: float = 32.8328,
    lon: float = -117.2713,
) -> str:
    """Render a single tide window as HTML."""
    weather_html = ""
    if weather:
        ahead_hours = _calculate_ahead_hours(window.start_time)
        weather_url = _generate_weather_url(lat, lon, ahead_hours)
        weather_text = f"{weather.temp_display(metric)}  {weather.precip_display()}"
        weather_html = (
            f'<div class="window-weather">'
            f'<a href="{weather_url}" class="weather-link" target="_blank">'
            f"{weather_text}</a></div>"
        )
    window_date = window.start_time.strftime("%Y%m%d")
    noaa_url = (
        f"https://tidesandcurrents.noaa.gov/noaatidepredictions.html"
        f"?id={station_id}&bdate={window_date}&edate={window_date}"
    )
    return f"""
        <div class="window-entry">
            <div class="window-date">{window.formatted_date}</div>
            <div class="window-time">{window.formatted_time_range}</div>
            <div class="window-duration">{window.duration_display}</div>
            <div class="window-height">Low: {window.min_height_display(metric)}</div>
            <div class="window-light">{window.relevant_light_display}</div>{weather_html}
            <div class="window-noaa"><a href="{noaa_url}" target="_blank">View on NOAA</a></div>
        </div>
    """


@app.get("/windows", response_class=HTMLResponse)
async def tide_windows(
    request: Request,
    max_height: float | None = Query(None),
    min_duration: int | None = Query(None),
    units: str | None = Query(None),
    work_filter: str | None = Query(None),
    days: int | None = Query(None),
    reset: bool = Query(False),
) -> Response:
    """Tide window finder showing periods below a height threshold."""
    # Load saved preferences
    prefs = load_preferences(request)

    # Handle reset
    if reset:
        prefs = UserPreferences()

    # Use query params if provided, otherwise use saved preferences
    max_height = max_height if max_height is not None else prefs.max_height
    min_duration = min_duration if min_duration is not None else prefs.min_duration
    units = units if units is not None else prefs.units
    work_filter = work_filter if work_filter is not None else prefs.work_filter
    days = days if days is not None else prefs.days

    metric = units.lower() == "metric"
    work_filter_on = work_filter.lower() == "on"

    windows = await find_tide_windows(
        max_height_ft=max_height,
        min_duration_minutes=min_duration,
        daylight_only=True,
        work_filter=work_filter_on,
        days=days,
    )

    # Fetch weather for La Jolla (default zip 92037)
    forecasts = []
    weather_lat = 32.8328  # Default La Jolla coordinates
    weather_lon = -117.2713
    try:
        location = await geocode_zip("92037")
        weather_lat = location.latitude
        weather_lon = location.longitude
        forecasts = await get_hourly_forecasts(weather_lat, weather_lon)
    except GeocodingError:
        pass  # Weather will just not be shown

    # Update preferences (keep zip_code from saved prefs)
    new_prefs = UserPreferences(
        zip_code=prefs.zip_code,
        max_height=max_height,
        min_duration=min_duration,
        days=days,
        units=units,
        work_filter=work_filter,
    )

    # Render windows with weather
    def render_with_weather(w: TideWindow) -> str:
        weather = get_weather_for_window(forecasts, w.start_time, w.end_time)
        return _render_window_entry(w, metric, weather, lat=weather_lat, lon=weather_lon)

    windows_html = "".join(render_with_weather(w) for w in windows)
    if not windows:
        windows_html = '<p class="no-results">No tide windows match your criteria.</p>'

    # Build form values
    work_param = "on" if work_filter_on else "off"
    units_param = "metric" if metric else "imperial"
    height_unit = "m" if metric else "ft"
    display_height = max_height * 0.3048 if metric else max_height

    base_params = f"max_height={max_height}&min_duration={min_duration}&days={days}"
    new_work_filter = "off" if work_filter_on else "on"
    work_toggle_url = f"/windows?{base_params}&units={units_param}&work_filter={new_work_filter}"
    work_toggle_text = "Show all daylight tides" if work_filter_on else "Show outside work hours only"
    work_filter_status = "Outside work hours" if work_filter_on else "All daylight tides"

    new_units = "metric" if not metric else "imperial"
    units_toggle_url = f"/windows?{base_params}&units={new_units}&work_filter={work_param}"
    units_toggle_text = "Switch to metric" if not metric else "Switch to imperial"
    units_display = "m" if metric else "ft"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tide Window Finder - San Diego</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            h1 {{
                color: #1a5f7a;
            }}
            .search-form {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .form-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
                gap: 15px;
                align-items: end;
                margin-bottom: 15px;
            }}
            .form-group {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            .form-group label {{
                font-size: 14px;
                color: #666;
            }}
            .form-group input, .form-group select {{
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                width: 100%;
                box-sizing: border-box;
            }}
            .form-group input[type="number"] {{
                max-width: 100px;
            }}
            .toggle-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                padding-top: 15px;
                border-top: 1px solid #eee;
                margin-bottom: 15px;
            }}
            .toggle-item {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .toggle-label {{
                font-weight: 500;
                color: #333;
            }}
            .toggle-link {{
                font-size: 13px;
                color: #1a5f7a;
                text-decoration: none;
            }}
            .toggle-link:hover {{
                text-decoration: underline;
            }}
            .search-btn {{
                padding: 10px 30px;
                background: #1a5f7a;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }}
            .reset-link {{
                margin-left: 15px;
                color: #888;
                font-size: 14px;
            }}
            .results {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .results h2 {{
                margin-top: 0;
                color: #1a5f7a;
            }}
            .window-entry {{
                display: flex;
                gap: 20px;
                padding: 15px;
                background: #f9f9f9;
                border-radius: 5px;
                margin-bottom: 10px;
                flex-wrap: wrap;
            }}
            .window-date {{
                font-weight: bold;
                color: #333;
                min-width: 150px;
            }}
            .window-time {{
                color: #666;
                min-width: 140px;
            }}
            .window-duration {{
                color: #1a5f7a;
                font-weight: bold;
                min-width: 80px;
            }}
            .window-height {{
                color: #888;
            }}
            .window-light {{
                color: #b8860b;
                font-size: 14px;
            }}
            .window-weather {{
                color: #2e7d32;
                font-size: 14px;
                width: 100%;
                margin-top: 5px;
            }}
            .weather-link {{
                color: inherit;
                text-decoration: none;
            }}
            .weather-link:hover {{
                text-decoration: underline;
            }}
            .window-noaa {{
                font-size: 13px;
                width: 100%;
                margin-top: 5px;
            }}
            .window-noaa a {{
                color: #1a5f7a;
            }}
            .no-results {{
                color: #888;
                font-style: italic;
            }}
            .result-count {{
                color: #666;
                margin-bottom: 15px;
            }}
            @media (max-width: 768px) {{
                .form-grid {{
                    grid-template-columns: repeat(3, 1fr);
                }}
                .toggle-row {{
                    flex-direction: column;
                    gap: 10px;
                }}
                .window-entry {{
                    flex-direction: column;
                    gap: 5px;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>Tide Window Finder - San Diego</h1>
        <p>Find times when the tide is below your target height</p>

        <form class="search-form" method="get" action="/windows">
            <input type="hidden" name="units" value="{units_param}">
            <input type="hidden" name="work_filter" value="{work_param}">
            <div class="form-grid">
                <div class="form-group">
                    <label for="max_height">Tides below ({height_unit})</label>
                    <input type="number" id="max_height" name="max_height"
                           value="{display_height:.1f}" step="0.1">
                </div>
                <div class="form-group">
                    <label for="min_duration">Min duration</label>
                    <input type="number" id="min_duration" name="min_duration"
                           value="{min_duration}" step="1" min="0">
                </div>
                <div class="form-group">
                    <label for="days">Days</label>
                    <select id="days" name="days">
                        <option value="30" {"selected" if days == 30 else ""}>30</option>
                        <option value="60" {"selected" if days == 60 else ""}>60</option>
                        <option value="90" {"selected" if days == 90 else ""}>90</option>
                    </select>
                </div>
            </div>
            <div class="toggle-row">
                <div class="toggle-item">
                    <span class="toggle-label">Units: {units_display}</span>
                    <a href="{units_toggle_url}" class="toggle-link">{units_toggle_text}</a>
                </div>
                <div class="toggle-item">
                    <span class="toggle-label">Showing: {work_filter_status}</span>
                    <a href="{work_toggle_url}" class="toggle-link">{work_toggle_text}</a>
                </div>
            </div>
            <button type="submit" class="search-btn">Search</button>
            <a href="/windows?reset=true" class="reset-link">Reset to defaults</a>
        </form>

        <div class="results">
            <h2>Results</h2>
            <p class="result-count">{len(windows)} window{"s" if len(windows) != 1 else ""} found</p>
            {windows_html}
        </div>

        <p style="margin-top: 30px;"><a href="/tides">Switch to Top Tides Dashboard</a></p>
    </body>
    </html>
    """

    # Create response and save preferences
    response = HTMLResponse(content=html_content)
    if reset:
        clear_preferences(response)
    else:
        save_preferences(response, new_prefs)
    return response


def _render_location_window_entry(
    window: LocationTideWindow,
    metric: bool,
    weather: WindowWeather | None = None,
    station_id: str = "9410230",
    lat: float = 32.8328,
    lon: float = -117.2713,
) -> str:
    """Render a single location-based tide window as HTML."""
    weather_html = ""
    if weather:
        ahead_hours = _calculate_ahead_hours(window.start_time)
        weather_url = _generate_weather_url(lat, lon, ahead_hours)
        weather_text = f"{weather.temp_display(metric)}  {weather.precip_display()}"
        weather_html = (
            f'<div class="window-weather">'
            f'<a href="{weather_url}" class="weather-link" target="_blank">'
            f"{weather_text}</a></div>"
        )
    window_date = window.start_time.strftime("%Y%m%d")
    noaa_url = (
        f"https://tidesandcurrents.noaa.gov/noaatidepredictions.html"
        f"?id={station_id}&bdate={window_date}&edate={window_date}"
    )
    return f"""
        <div class="window-entry">
            <div class="window-date">{window.formatted_date}</div>
            <div class="window-time">{window.formatted_time_range}</div>
            <div class="window-duration">{window.duration_display}</div>
            <div class="window-height">Low: {window.min_height_display(metric)}</div>
            <div class="window-light">{window.relevant_light_display}</div>{weather_html}
            <div class="window-noaa"><a href="{noaa_url}" target="_blank">View on NOAA</a></div>
        </div>
    """


@app.get("/location", response_class=HTMLResponse)
async def location_tide_windows(
    request: Request,
    zip_code: str | None = Query(None),
    max_height: float | None = Query(None),
    min_duration: int | None = Query(None),
    units: str | None = Query(None),
    work_filter: str | None = Query(None),
    days: int | None = Query(None),
    reset: bool = Query(False),
) -> Response:
    """Location-based tide window finder."""
    # Load saved preferences
    prefs = load_preferences(request)

    # Handle reset
    if reset:
        prefs = UserPreferences()

    # Use query params if provided, otherwise use saved preferences
    zip_code = zip_code if zip_code is not None else prefs.zip_code
    max_height = max_height if max_height is not None else prefs.max_height
    min_duration = min_duration if min_duration is not None else prefs.min_duration
    units = units if units is not None else prefs.units
    work_filter = work_filter if work_filter is not None else prefs.work_filter
    days = days if days is not None else prefs.days

    metric = units.lower() == "metric"
    work_filter_on = work_filter.lower() == "on"

    # Build common params for URLs
    units_param = "metric" if metric else "imperial"
    work_param = "on" if work_filter_on else "off"
    height_unit = "m" if metric else "ft"
    display_height = max_height * 0.3048 if metric else max_height

    # Update preferences
    new_prefs = UserPreferences(
        zip_code=zip_code,
        max_height=max_height,
        min_duration=min_duration,
        days=days,
        units=units,
        work_filter=work_filter,
    )

    # Default content when no zip code entered
    station_info_html = ""
    windows_html = '<p class="no-results">Enter a zip code to find tide windows near you.</p>'
    error_html = ""
    station_result: StationWithDistance | None = None

    if zip_code:
        try:
            # Geocode the zip code
            location = await geocode_zip(zip_code)

            # Find nearest station
            station_result = await find_nearest_station(
                location.latitude, location.longitude
            )
            station = station_result.station

            # Get tide windows for this station
            # Pass user coordinates to find closest station for low tide data
            windows = await find_tide_windows_for_station(
                station=station,
                max_height_ft=max_height,
                min_duration_minutes=min_duration,
                daylight_only=True,
                work_filter=work_filter_on,
                days=days,
                user_latitude=location.latitude,
                user_longitude=location.longitude,
            )

            # Fetch weather for station location (where user will be tidepooling)
            forecasts = await get_hourly_forecasts(
                station.latitude, station.longitude
            )

            # Render station info
            distance_display = station_result.distance_display(metric)
            station_info_html = f"""
                <div class="station-info">
                    <h3>{station.name}</h3>
                    <p>Station ID: {station.id} | {station.state}</p>
                    <p>Station is {distance_display} away</p>
                    <p>Timezone: {station.timezone_abbr}</p>
                </div>
            """

            # Render windows with weather
            def render_with_weather(w: LocationTideWindow) -> str:
                weather = get_weather_for_window(forecasts, w.start_time, w.end_time)
                return _render_location_window_entry(
                    w, metric, weather, station.id,
                    lat=station.latitude, lon=station.longitude
                )

            windows_html = "".join(render_with_weather(w) for w in windows)
            if not windows:
                windows_html = '<p class="no-results">No tide windows match your criteria.</p>'
            else:
                count = len(windows)
                suffix = "s" if count != 1 else ""
                windows_html = f'<p class="result-count">{count} window{suffix} found</p>' + windows_html

        except GeocodingError as e:
            error_html = f'<p class="error-message">Error: {e}</p>'

    # Build toggle URLs
    base_params = f"zip_code={zip_code}&max_height={max_height}&min_duration={min_duration}&days={days}"
    new_work_filter = "off" if work_filter_on else "on"
    work_toggle_url = f"/location?{base_params}&units={units_param}&work_filter={new_work_filter}"
    work_toggle_text = "Show all daylight tides" if work_filter_on else "Show outside work hours only"
    work_filter_status = "Outside work hours" if work_filter_on else "All daylight tides"

    new_units = "metric" if not metric else "imperial"
    units_toggle_url = f"/location?{base_params}&units={new_units}&work_filter={work_param}"
    units_toggle_text = "Switch to metric" if not metric else "Switch to imperial"
    units_display = "m" if metric else "ft"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tide Window Finder by Location</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            h1 {{
                color: #1a5f7a;
            }}
            .search-form {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .form-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
                gap: 15px;
                align-items: end;
                margin-bottom: 15px;
            }}
            .form-group {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            .form-group label {{
                font-size: 14px;
                color: #666;
            }}
            .form-group input, .form-group select {{
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                width: 100%;
                box-sizing: border-box;
            }}
            .form-group input[type="number"] {{
                max-width: 100px;
            }}
            .toggle-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                padding-top: 15px;
                border-top: 1px solid #eee;
                margin-bottom: 15px;
            }}
            .toggle-item {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .toggle-label {{
                font-weight: 500;
                color: #333;
            }}
            .toggle-link {{
                font-size: 13px;
                color: #1a5f7a;
                text-decoration: none;
            }}
            .toggle-link:hover {{
                text-decoration: underline;
            }}
            .search-btn {{
                padding: 10px 30px;
                background: #1a5f7a;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }}
            .reset-link {{
                margin-left: 15px;
                color: #888;
                font-size: 14px;
            }}
            .station-info {{
                background: #e8f4f8;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            .station-info h3 {{
                margin: 0 0 10px 0;
                color: #1a5f7a;
            }}
            .station-info p {{
                margin: 5px 0;
                color: #555;
            }}
            .results {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .results h2 {{
                margin-top: 0;
                color: #1a5f7a;
            }}
            .window-entry {{
                display: flex;
                gap: 20px;
                padding: 15px;
                background: #f9f9f9;
                border-radius: 5px;
                margin-bottom: 10px;
                flex-wrap: wrap;
            }}
            .window-date {{
                font-weight: bold;
                color: #333;
                min-width: 150px;
            }}
            .window-time {{
                color: #666;
                min-width: 160px;
            }}
            .window-duration {{
                color: #1a5f7a;
                font-weight: bold;
                min-width: 80px;
            }}
            .window-height {{
                color: #888;
            }}
            .window-light {{
                color: #b8860b;
                font-size: 14px;
            }}
            .window-weather {{
                color: #2e7d32;
                font-size: 14px;
                width: 100%;
                margin-top: 5px;
            }}
            .weather-link {{
                color: inherit;
                text-decoration: none;
            }}
            .weather-link:hover {{
                text-decoration: underline;
            }}
            .window-noaa {{
                font-size: 13px;
                width: 100%;
                margin-top: 5px;
            }}
            .window-noaa a {{
                color: #1a5f7a;
            }}
            .no-results {{
                color: #888;
                font-style: italic;
            }}
            .result-count {{
                color: #666;
                margin-bottom: 15px;
            }}
            .error-message {{
                color: #c00;
                background: #fee;
                padding: 10px 15px;
                border-radius: 5px;
                margin-bottom: 15px;
            }}
            @media (max-width: 768px) {{
                .form-grid {{
                    grid-template-columns: repeat(2, 1fr);
                }}
                .toggle-row {{
                    flex-direction: column;
                    gap: 10px;
                }}
                .window-entry {{
                    flex-direction: column;
                    gap: 5px;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>Tide Window Finder by Location</h1>
        <p>Enter a zip code to find tide windows near any US coastal location</p>

        <form class="search-form" method="get" action="/location">
            <input type="hidden" name="units" value="{units_param}">
            <input type="hidden" name="work_filter" value="{work_param}">
            <div class="form-grid">
                <div class="form-group">
                    <label for="zip_code">Zip Code</label>
                    <input type="text" id="zip_code" name="zip_code"
                           value="{zip_code}" placeholder="e.g., 92037" maxlength="5" pattern="[0-9]{{5}}">
                </div>
                <div class="form-group">
                    <label for="max_height">Tides below ({height_unit})</label>
                    <input type="number" id="max_height" name="max_height"
                           value="{display_height:.1f}" step="0.1">
                </div>
                <div class="form-group">
                    <label for="min_duration">Min duration</label>
                    <input type="number" id="min_duration" name="min_duration"
                           value="{min_duration}" step="1" min="0">
                </div>
                <div class="form-group">
                    <label for="days">Days</label>
                    <select id="days" name="days">
                        <option value="30" {"selected" if days == 30 else ""}>30</option>
                        <option value="60" {"selected" if days == 60 else ""}>60</option>
                        <option value="90" {"selected" if days == 90 else ""}>90</option>
                    </select>
                </div>
            </div>
            <div class="toggle-row">
                <div class="toggle-item">
                    <span class="toggle-label">Units: {units_display}</span>
                    <a href="{units_toggle_url}" class="toggle-link">{units_toggle_text}</a>
                </div>
                <div class="toggle-item">
                    <span class="toggle-label">Showing: {work_filter_status}</span>
                    <a href="{work_toggle_url}" class="toggle-link">{work_toggle_text}</a>
                </div>
            </div>
            <button type="submit" class="search-btn">Search</button>
            <a href="/location?reset=true" class="reset-link">Reset to defaults</a>
        </form>

        {error_html}
        {station_info_html}

        <div class="results">
            <h2>Results</h2>
            {windows_html}
        </div>

        <p style="margin-top: 30px;"><a href="/windows">Switch to La Jolla Tide Windows</a></p>
    </body>
    </html>
    """

    # Create response and save preferences
    response = HTMLResponse(content=html_content)
    if reset:
        clear_preferences(response)
    else:
        save_preferences(response, new_prefs)
    return response


def _render_location_list_item(loc: Location) -> str:
    """Render a location as a list item."""
    no_coords_class = "" if loc.has_coordinates else " no-coords"
    no_coords_badge = "" if loc.has_coordinates else '<span class="unmapped-badge">Not on map</span>'

    return f"""
        <a href="/location/{loc.id}" class="location-item{no_coords_class}">
            <div class="location-name">{loc.name}</div>
            <div class="location-city">{loc.city}, {loc.county} County</div>
            {no_coords_badge}
        </a>
    """


@app.get("/directory", response_class=HTMLResponse)
async def directory_page() -> str:
    """Directory page with map and list of tidepooling locations."""
    all_locations = get_all_locations()
    locations_with_coords = get_locations_with_coordinates()

    # Generate marker data for JavaScript
    markers_js = []
    for loc in locations_with_coords:
        # Escape quotes in name for JS
        safe_name = loc.name.replace('"', '\\"').replace("'", "\\'")
        markers_js.append(
            f'{{lat: {loc.coordinates.lat}, lon: {loc.coordinates.lon}, '
            f'name: "{safe_name}", id: "{loc.id}"}}'
        )
    markers_data = "[" + ",".join(markers_js) + "]"

    # Generate location list HTML
    locations_html = "".join(_render_location_list_item(loc) for loc in all_locations)

    # Stats for display
    total_count = len(all_locations)
    mapped_count = len(locations_with_coords)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tidepooling Directory - Southern California</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: #f5f5f5;
            }}
            .header {{
                background: #1a5f7a;
                color: white;
                padding: 15px 20px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 1.5em;
            }}
            .header p {{
                margin: 5px 0 0 0;
                opacity: 0.9;
                font-size: 0.9em;
            }}
            #map {{
                width: 100%;
                height: 50vh;
                min-height: 300px;
            }}
            .content {{
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
            }}
            .stats {{
                color: #666;
                margin-bottom: 15px;
                font-size: 0.9em;
            }}
            .location-list {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 15px;
            }}
            .location-item {{
                display: block;
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-decoration: none;
                color: inherit;
                transition: box-shadow 0.2s, transform 0.2s;
            }}
            .location-item:hover {{
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                transform: translateY(-2px);
            }}
            .location-item.no-coords {{
                border-left: 3px solid #ffa500;
            }}
            .location-name {{
                font-weight: 600;
                color: #1a5f7a;
                margin-bottom: 5px;
            }}
            .location-city {{
                color: #666;
                font-size: 0.9em;
            }}
            .unmapped-badge {{
                display: inline-block;
                background: #ffa500;
                color: white;
                font-size: 0.75em;
                padding: 2px 6px;
                border-radius: 3px;
                margin-top: 8px;
            }}
            .back-link {{
                display: inline-block;
                margin-top: 20px;
                color: #1a5f7a;
            }}
            .leaflet-popup-content {{
                margin: 10px 15px;
            }}
            .popup-name {{
                font-weight: 600;
                color: #1a5f7a;
                margin-bottom: 8px;
            }}
            .popup-link {{
                display: inline-block;
                background: #1a5f7a;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                text-decoration: none;
                font-size: 0.9em;
            }}
            .popup-link:hover {{
                background: #145a6e;
            }}
            @media (max-width: 768px) {{
                .header h1 {{
                    font-size: 1.3em;
                }}
                #map {{
                    height: 40vh;
                }}
                .location-list {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Tidepooling Directory</h1>
            <p>Southern California tidepooling locations</p>
        </div>

        <div id="map"></div>

        <div class="content">
            <div class="stats">
                {total_count} locations ({mapped_count} on map)
            </div>
            <div class="location-list">
                {locations_html}
            </div>
            <a href="/" class="back-link">&larr; Back to Home</a>
        </div>

        <script>
            // Initialize map centered on Southern California
            var map = L.map('map').setView([33.2, -117.4], 9);

            // Add OpenStreetMap tiles
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap'
            }}).addTo(map);

            // Location markers data
            var locations = {markers_data};

            // Add markers
            locations.forEach(function(loc) {{
                var marker = L.marker([loc.lat, loc.lon]).addTo(map);
                marker.bindPopup(
                    '<div class="popup-name">' + loc.name + '</div>' +
                    '<a href="/location/' + loc.id + '" class="popup-link">View Details</a>'
                );
            }});

            // Fit map to show all markers if there are any
            if (locations.length > 0) {{
                var group = L.featureGroup(locations.map(function(loc) {{
                    return L.marker([loc.lat, loc.lon]);
                }}));
                map.fitBounds(group.getBounds().pad(0.1));
            }}
        </script>
    </body>
    </html>
    """


def _format_list_html(items: list[str], title: str) -> str:
    """Format a list of items as HTML with a title."""
    if not items:
        return ""
    items_html = "".join(f"<li>{item}</li>" for item in items)
    return f"""
        <div class="info-section">
            <h3>{title}</h3>
            <ul>{items_html}</ul>
        </div>
    """


@app.get("/location/{location_id}", response_class=HTMLResponse)
async def location_detail_page(location_id: str) -> Response:
    """Detail page for a single tidepooling location."""
    location = get_location_by_id(location_id)

    if location is None:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Location Not Found</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 50px auto;
                        padding: 20px;
                        text-align: center;
                    }}
                    h1 {{ color: #c00; }}
                    a {{ color: #1a5f7a; }}
                </style>
            </head>
            <body>
                <h1>404 - Location Not Found</h1>
                <p>The location "{location_id}" does not exist.</p>
                <a href="/directory">&larr; Back to Directory</a>
            </body>
            </html>
            """,
            status_code=404,
        )

    # Build map HTML if coordinates exist
    map_html = ""
    map_script = ""
    if location.has_coordinates:
        lat = location.coordinates.lat
        lon = location.coordinates.lon
        map_html = '<div id="location-map"></div>'
        map_script = f"""
        <script>
            var map = L.map('location-map').setView([{lat}, {lon}], 14);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap'
            }}).addTo(map);
            L.marker([{lat}, {lon}]).addTo(map);
        </script>
        """
    else:
        map_html = '<div class="no-map">Coordinates not available for this location</div>'

    # Build info sections
    aka_html = ""
    if location.also_known_as:
        aka_text = ", ".join(location.also_known_as)
        aka_html = f'<p class="aka">Also known as: {aka_text}</p>'

    tide_height_html = ""
    if location.best_tide_height_ft is not None:
        tide_height_html = f"""
            <div class="info-item">
                <span class="info-label">Best Tide Height</span>
                <span class="info-value">{location.best_tide_height_ft} ft or lower</span>
            </div>
        """

    season_html = ""
    if location.best_season:
        season_html = f"""
            <div class="info-item">
                <span class="info-label">Best Season</span>
                <span class="info-value">{location.best_season}</span>
            </div>
        """

    difficulty_html = ""
    if location.access_difficulty:
        diff = location.access_difficulty
        difficulty_html = f"""
            <div class="info-item">
                <span class="info-label">Access Difficulty</span>
                <span class="info-value difficulty-{diff}">{diff.title()}</span>
            </div>
        """

    tips_html = _format_list_html(location.tips, "Tips")
    marine_life_html = _format_list_html(location.marine_life, "Marine Life")
    amenities_html = _format_list_html(location.amenities, "Amenities")

    sources_text = ", ".join(location.sources)

    # Status warning for closed locations
    status_html = ""
    if location.status:
        status_html = f'<div class="status-warning">{location.status}</div>'

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{location.name} - Tidepooling</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                * {{
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: #f5f5f5;
                }}
                .header {{
                    background: #1a5f7a;
                    color: white;
                    padding: 15px 20px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 1.5em;
                }}
                .header .location-meta {{
                    margin: 5px 0 0 0;
                    opacity: 0.9;
                    font-size: 0.9em;
                }}
                .aka {{
                    font-style: italic;
                    color: rgba(255,255,255,0.8);
                    font-size: 0.85em;
                    margin: 5px 0 0 0;
                }}
                #location-map {{
                    width: 100%;
                    height: 250px;
                }}
                .no-map {{
                    background: #eee;
                    padding: 40px 20px;
                    text-align: center;
                    color: #666;
                }}
                .content {{
                    padding: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .status-warning {{
                    background: #c00;
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    font-weight: 600;
                }}
                .description {{
                    font-size: 1.1em;
                    line-height: 1.6;
                    color: #333;
                    margin-bottom: 25px;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 25px;
                }}
                .info-item {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .info-label {{
                    display: block;
                    font-size: 0.85em;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .info-value {{
                    font-weight: 600;
                    color: #1a5f7a;
                }}
                .difficulty-easy {{ color: #2e7d32; }}
                .difficulty-moderate {{ color: #f57c00; }}
                .difficulty-difficult {{ color: #c62828; }}
                .info-section {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .info-section h3 {{
                    margin: 0 0 15px 0;
                    color: #1a5f7a;
                    font-size: 1.1em;
                }}
                .info-section ul {{
                    margin: 0;
                    padding-left: 20px;
                }}
                .info-section li {{
                    margin-bottom: 8px;
                    color: #444;
                }}
                .sources {{
                    color: #888;
                    font-size: 0.85em;
                    margin-top: 25px;
                }}
                .back-link {{
                    display: inline-block;
                    margin-top: 20px;
                    color: #1a5f7a;
                }}
                @media (max-width: 768px) {{
                    .header h1 {{
                        font-size: 1.3em;
                    }}
                    #location-map {{
                        height: 200px;
                    }}
                    .info-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{location.name}</h1>
                <div class="location-meta">{location.city}, {location.county} County</div>
                {aka_html}
            </div>

            {map_html}

            <div class="content">
                {status_html}

                <p class="description">{location.description}</p>

                <div class="info-grid">
                    {tide_height_html}
                    {season_html}
                    {difficulty_html}
                </div>

                {tips_html}
                {marine_life_html}
                {amenities_html}

                <p class="sources">Sources: {sources_text}</p>

                <a href="/directory" class="back-link">&larr; Back to Directory</a>
            </div>

            {map_script}
        </body>
        </html>
        """
    )
