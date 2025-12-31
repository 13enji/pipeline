from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse

from app.services.cache import get_tide_readings, refresh_cache
from app.services.tides import ProcessedTide, TideCard, get_tide_cards
from app.services.windows import TideWindow, find_tide_windows


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the cache on startup."""
    await get_tide_readings()
    yield


app = FastAPI(title="Pipeline", version="0.1.0", lifespan=lifespan)


@app.post("/refresh-tides")
async def refresh_tides() -> dict[str, Any]:
    """Force refresh the tide cache. Called by scheduled job."""
    return await refresh_cache()


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

        <p style="margin-top: 30px;"><a href="/windows">Switch to Tide Window Finder</a></p>
    </body>
    </html>
    """


def _render_window_entry(window: TideWindow, metric: bool) -> str:
    """Render a single tide window as HTML."""
    return f"""
        <div class="window-entry">
            <div class="window-date">{window.formatted_date}</div>
            <div class="window-time">{window.formatted_time_range}</div>
            <div class="window-duration">{window.duration_display}</div>
            <div class="window-height">
                Low: {window.min_height_display(metric)}
            </div>
        </div>
    """


@app.get("/windows", response_class=HTMLResponse)
async def tide_windows(
    max_height: float = Query(-1.0),
    min_duration: int = Query(60),
    units: str = Query("imperial"),
    work_filter: str = Query("on"),
    days: int = Query(90),
) -> str:
    """Tide window finder showing periods below a height threshold."""
    metric = units.lower() == "metric"
    work_filter_on = work_filter.lower() == "on"

    windows = await find_tide_windows(
        max_height_ft=max_height,
        min_duration_minutes=min_duration,
        daylight_only=True,
        work_filter=work_filter_on,
        days=days,
    )

    windows_html = "".join(_render_window_entry(w, metric) for w in windows)
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

    return f"""
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
                           value="{min_duration}" step="30" min="30" max="480">
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
