from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services.cache import get_cache_stats, refresh_cache
from app.services.geocoding import GeocodingError, geocode_zip
from app.services.location_windows import find_tide_windows_for_station
from app.services.locations import (
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
from app.services.stations import find_nearest_station
from app.services.tides import get_tide_cards
from app.services.weather import (
    get_hourly_forecasts,
    get_weather_for_window,
)
from app.services.windows import find_tide_windows


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the cache on startup for all known stations."""
    await refresh_cache()
    yield


app = FastAPI(title="Pipeline", version="0.1.0", lifespan=lifespan)

# Set up templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _calculate_ahead_hours(window_start: datetime) -> int:
    """Calculate AheadHour parameter for NWS weather link."""
    if window_start.tzinfo is not None:
        now = datetime.now(window_start.tzinfo)
    else:
        now = datetime.now()
    target_time = window_start - timedelta(hours=6)
    hours_ahead = (target_time - now).total_seconds() / 3600
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


# =============================================================================
# Main Pages (New Architecture)
# =============================================================================


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request) -> Response:
    """Home page with map and all locations."""
    import json

    all_locations = get_all_locations()
    locations_with_coords = get_locations_with_coordinates()

    # Generate marker data for JavaScript
    markers = []
    for loc in locations_with_coords:
        safe_name = loc.name.replace('"', '\\"').replace("'", "\\'")
        markers.append({
            "lat": loc.coordinates.lat,
            "lon": loc.coordinates.lon,
            "name": safe_name,
            "id": loc.id,
        })

    # Generate search index for autocomplete
    search_data = []
    for loc in all_locations:
        search_data.append({
            "id": loc.id,
            "name": loc.name,
            "city": loc.city,
            "county": loc.county,
            "aliases": loc.also_known_as or [],
        })

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "locations": all_locations,
            "markers_json": json.dumps(markers),
            "search_json": json.dumps(search_data),
            "total_count": len(all_locations),
            "mapped_count": len(locations_with_coords),
        },
    )


@app.get("/spot/{location_id}", response_class=HTMLResponse)
async def spot_page(
    request: Request,
    location_id: str,
    max_height: float | None = Query(None),
    min_duration: int | None = Query(None),
    units: str | None = Query(None),
    work_filter: str | None = Query(None),
    days: int | None = Query(None),
    reset: bool = Query(False),
) -> Response:
    """Location detail page with tide windows."""
    location = get_location_by_id(location_id)

    if location is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"message": f'Location "{location_id}" not found.'},
            status_code=404,
        )

    # Load saved preferences
    prefs = load_preferences(request)
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

    # Build common values
    units_param = "metric" if metric else "imperial"
    work_param = "on" if work_filter_on else "off"
    height_unit = "m" if metric else "ft"
    display_height = round(max_height * 0.3048, 1) if metric else max_height

    # Update preferences
    new_prefs = UserPreferences(
        zip_code=prefs.zip_code,
        max_height=max_height,
        min_duration=min_duration,
        days=days,
        units=units,
        work_filter=work_filter,
    )

    # Context for template
    context = {
        "location": location,
        "metric": metric,
        "units": units_param,
        "work_filter": work_param,
        "height_unit": height_unit,
        "display_height": display_height,
        "min_duration": min_duration,
        "days": days,
        "work_filter_status": "Outside work hours" if work_filter_on else "All daylight tides",
        "station": None,
        "station_distance": None,
        "windows": [],
        "error": None,
    }

    # Build toggle URLs
    base_params = f"max_height={max_height}&min_duration={min_duration}&days={days}"
    new_work = "off" if work_filter_on else "on"
    context["work_toggle_url"] = (
        f"/spot/{location_id}?{base_params}&units={units_param}&work_filter={new_work}"
    )
    context["work_toggle_text"] = (
        "Show all daylight" if work_filter_on else "Outside work hours only"
    )

    new_units = "metric" if not metric else "imperial"
    context["units_toggle_url"] = (
        f"/spot/{location_id}?{base_params}&units={new_units}&work_filter={work_param}"
    )
    context["units_toggle_text"] = "Switch to metric" if not metric else "Switch to imperial"

    # If location has coordinates, find tide windows
    if location.has_coordinates:
        try:
            lat = location.coordinates.lat
            lon = location.coordinates.lon

            # Find nearest station
            station_result = await find_nearest_station(lat, lon)
            station = station_result.station
            context["station"] = station
            context["station_distance"] = station_result.distance_display(metric)

            # Get tide windows
            windows = await find_tide_windows_for_station(
                station=station,
                max_height_ft=max_height,
                min_duration_minutes=min_duration,
                daylight_only=True,
                work_filter=work_filter_on,
                days=days,
                user_latitude=lat,
                user_longitude=lon,
            )

            # Fetch weather
            forecasts = await get_hourly_forecasts(lat, lon)

            # Enrich windows with weather and URLs
            enriched_windows = []
            for w in windows:
                weather = get_weather_for_window(forecasts, w.start_time, w.end_time)
                weather_url = None
                if weather:
                    ahead_hours = _calculate_ahead_hours(w.start_time)
                    weather_url = _generate_weather_url(lat, lon, ahead_hours)

                window_date = w.start_time.strftime("%Y%m%d")
                noaa_url = (
                    f"https://tidesandcurrents.noaa.gov/noaatidepredictions.html"
                    f"?id={station.id}&bdate={window_date}&edate={window_date}"
                )

                # Add attributes to window object
                w.weather = weather
                w.weather_url = weather_url
                w.noaa_url = noaa_url
                enriched_windows.append(w)

            context["windows"] = enriched_windows

        except Exception as e:
            context["error"] = str(e)
    else:
        context["error"] = (
            "This location doesn't have coordinates yet. "
            "We can't calculate tide windows without knowing where it is."
        )

    # Create response and save preferences
    response = templates.TemplateResponse(request=request, name="spot.html", context=context)
    if reset:
        clear_preferences(response)
    else:
        save_preferences(response, new_prefs)
    return response


@app.get("/learn", response_class=HTMLResponse)
async def learn_page(request: Request) -> Response:
    """Educational content about tidepooling."""
    return templates.TemplateResponse(request=request, name="learn.html", context={})


# =============================================================================
# Legacy Routes (kept for backwards compatibility, hidden from main nav)
# =============================================================================


@app.get("/directory", response_class=HTMLResponse)
async def directory_redirect() -> Response:
    """Redirect old /directory to home page."""
    return RedirectResponse(url="/", status_code=301)


@app.get("/location/{location_id}", response_class=HTMLResponse)
async def location_detail_redirect(location_id: str) -> Response:
    """Redirect old /location/{id} to /spot/{id}."""
    return RedirectResponse(url=f"/spot/{location_id}", status_code=301)


@app.get("/location", response_class=HTMLResponse)
async def location_search_redirect() -> Response:
    """Redirect old /location search to home page."""
    return RedirectResponse(url="/", status_code=301)


@app.get("/tides", response_class=HTMLResponse)
async def tide_dashboard(
    request: Request,
    units: str = Query("imperial"),
    work_filter: str = Query("on"),
) -> Response:
    """Tide dashboard showing highest and lowest daylight tides."""
    metric = units.lower() == "metric"
    work_filter_on = work_filter.lower() == "on"
    cards = await get_tide_cards(work_filter=work_filter_on)

    work_param = "on" if work_filter_on else "off"
    units_param = "metric" if metric else "imperial"

    # NOAA link with 31-day range
    today = datetime.now()
    end_date = today + timedelta(days=31)
    noaa_url = (
        f"https://tidesandcurrents.noaa.gov/noaatidepredictions.html"
        f"?id=9410230&bdate={today.strftime('%Y%m%d')}&edate={end_date.strftime('%Y%m%d')}"
    )

    # Build toggle URLs
    units_toggle = "metric" if not metric else "imperial"
    work_toggle = "off" if work_filter_on else "on"

    return templates.TemplateResponse(
        request=request,
        name="tides.html",
        context={
            "cards": cards,
            "metric": metric,
            "units_toggle_url": f"/tides?units={units_toggle}&work_filter={work_param}",
            "units_toggle_text": "Switch to Metric" if not metric else "Switch to Imperial",
            "work_toggle_url": f"/tides?units={units_param}&work_filter={work_toggle}",
            "work_toggle_text": "Show All Daylight" if work_filter_on else "Outside Work Hours Only",
            "work_filter_status": "Outside work hours" if work_filter_on else "All daylight",
            "noaa_url": noaa_url,
        },
    )


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
    prefs = load_preferences(request)
    if reset:
        prefs = UserPreferences()

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

    # Fetch weather for La Jolla
    weather_lat = 32.8328
    weather_lon = -117.2713
    forecasts = []
    try:
        location = await geocode_zip("92037")
        weather_lat = location.latitude
        weather_lon = location.longitude
        forecasts = await get_hourly_forecasts(weather_lat, weather_lon)
    except GeocodingError:
        pass

    # Enrich windows with weather
    for w in windows:
        weather = get_weather_for_window(forecasts, w.start_time, w.end_time)
        weather_url = None
        if weather:
            ahead_hours = _calculate_ahead_hours(w.start_time)
            weather_url = _generate_weather_url(weather_lat, weather_lon, ahead_hours)

        window_date = w.start_time.strftime("%Y%m%d")
        noaa_url = (
            f"https://tidesandcurrents.noaa.gov/noaatidepredictions.html"
            f"?id=9410230&bdate={window_date}&edate={window_date}"
        )

        w.weather = weather
        w.weather_url = weather_url
        w.noaa_url = noaa_url

    # Update preferences
    new_prefs = UserPreferences(
        zip_code=prefs.zip_code,
        max_height=max_height,
        min_duration=min_duration,
        days=days,
        units=units,
        work_filter=work_filter,
    )

    # Build params
    units_param = "metric" if metric else "imperial"
    work_param = "on" if work_filter_on else "off"
    height_unit = "m" if metric else "ft"
    display_height = round(max_height * 0.3048, 1) if metric else max_height

    base_params = f"max_height={max_height}&min_duration={min_duration}&days={days}"
    new_work = "off" if work_filter_on else "on"
    new_units = "metric" if not metric else "imperial"

    context = {
        "windows": windows,
        "metric": metric,
        "units": units_param,
        "work_filter": work_param,
        "height_unit": height_unit,
        "display_height": display_height,
        "min_duration": min_duration,
        "days": days,
        "work_filter_status": "Outside work hours" if work_filter_on else "All daylight tides",
        "units_toggle_url": f"/windows?{base_params}&units={new_units}&work_filter={work_param}",
        "units_toggle_text": "Switch to metric" if not metric else "Switch to imperial",
        "work_toggle_url": f"/windows?{base_params}&units={units_param}&work_filter={new_work}",
        "work_toggle_text": "Show all daylight tides" if work_filter_on else "Show outside work hours only",
    }

    response = templates.TemplateResponse(request=request, name="windows.html", context=context)
    if reset:
        clear_preferences(response)
    else:
        save_preferences(response, new_prefs)
    return response


# =============================================================================
# Test/Debug Routes
# =============================================================================


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
