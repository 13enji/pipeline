from datetime import datetime

from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse

from app.services.tides import ProcessedTide, TideCard, get_tide_cards

app = FastAPI(title="Pipeline", version="0.1.0")


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
    </body>
    </html>
    """
