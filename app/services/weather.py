"""Weather service using NWS (Weather.gov) API."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

# Cache TTL in minutes
WEATHER_CACHE_TTL = 60

# In-memory cache: {(lat_rounded, lon_rounded): {data, fetched_at}}
_weather_cache: dict[tuple[float, float], dict[str, Any]] = {}


@dataclass
class WindowWeather:
    """Weather data for a tide window."""

    temp_min: int
    temp_max: int
    precip_chance: int  # Max precipitation chance during window

    def temp_display(self, metric: bool = False) -> str:
        """Format temperature range for display."""
        if metric:
            # Convert F to C
            min_c = round((self.temp_min - 32) * 5 / 9)
            max_c = round((self.temp_max - 32) * 5 / 9)
            return f"{min_c}-{max_c}°C"
        return f"{self.temp_min}-{self.temp_max}°F"

    def precip_display(self) -> str:
        """Format precipitation chance for display."""
        return f"{self.precip_chance}% rain"


@dataclass
class HourlyForecast:
    """Single hour forecast data."""

    start_time: datetime
    end_time: datetime
    temperature: int  # Fahrenheit
    precip_chance: int  # Percentage


def _round_coords(lat: float, lon: float) -> tuple[float, float]:
    """Round coordinates to ~1km precision for cache keys."""
    return (round(lat, 2), round(lon, 2))


def _is_cache_valid(cache_entry: dict[str, Any]) -> bool:
    """Check if cache entry is still valid."""
    if not cache_entry:
        return False
    fetched_at = cache_entry.get("fetched_at")
    if not fetched_at:
        return False
    age = datetime.now() - fetched_at
    return age < timedelta(minutes=WEATHER_CACHE_TTL)


async def _get_grid_point(lat: float, lon: float) -> str | None:
    """Get the hourly forecast URL for coordinates."""
    # Round to 4 decimal places (~10m precision) to avoid NWS 301 redirects
    lat = round(lat, 4)
    lon = round(lon, 4)
    url = f"https://api.weather.gov/points/{lat},{lon}"
    headers = {"User-Agent": "TideWindowFinder/1.0 (contact@example.com)"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get("properties", {}).get("forecastHourly")
    except (httpx.RequestError, ValueError):
        return None


async def _fetch_hourly_forecast(forecast_url: str) -> list[HourlyForecast]:
    """Fetch hourly forecast data from NWS."""
    headers = {"User-Agent": "TideWindowFinder/1.0 (contact@example.com)"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(forecast_url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                return []
            data = response.json()

            forecasts = []
            for period in data.get("properties", {}).get("periods", []):
                start_time = datetime.fromisoformat(
                    period["startTime"].replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(
                    period["endTime"].replace("Z", "+00:00")
                )
                temperature = period.get("temperature", 0)
                precip = period.get("probabilityOfPrecipitation", {})
                precip_chance = precip.get("value") if precip.get("value") else 0

                forecasts.append(
                    HourlyForecast(
                        start_time=start_time,
                        end_time=end_time,
                        temperature=temperature,
                        precip_chance=precip_chance,
                    )
                )
            return forecasts
    except (httpx.RequestError, ValueError, KeyError):
        return []


async def get_hourly_forecasts(lat: float, lon: float) -> list[HourlyForecast]:
    """Get hourly forecasts for coordinates, using cache if available."""
    cache_key = _round_coords(lat, lon)

    # Check cache
    if cache_key in _weather_cache and _is_cache_valid(_weather_cache[cache_key]):
        return _weather_cache[cache_key]["forecasts"]

    # Fetch fresh data
    forecast_url = await _get_grid_point(lat, lon)
    if not forecast_url:
        return []

    forecasts = await _fetch_hourly_forecast(forecast_url)

    # Cache the results
    if forecasts:
        _weather_cache[cache_key] = {
            "forecasts": forecasts,
            "fetched_at": datetime.now(),
        }

    return forecasts


def get_weather_for_window(
    forecasts: list[HourlyForecast],
    window_start: datetime,
    window_end: datetime,
) -> WindowWeather | None:
    """Extract weather data for a specific time window.

    Returns None if window is beyond forecast range or no data available.
    """
    if not forecasts:
        return None

    # Make window times timezone-aware if needed (assume same timezone as forecasts)
    if window_start.tzinfo is None and forecasts:
        # Use the forecast timezone
        tz = forecasts[0].start_time.tzinfo
        window_start = window_start.replace(tzinfo=tz)
        window_end = window_end.replace(tzinfo=tz)

    # Find forecasts that overlap with the window
    matching = []
    for f in forecasts:
        # Check if forecast period overlaps with window
        # Forecast overlaps if it starts before window ends AND ends after window starts
        if f.start_time < window_end and f.end_time > window_start:
            matching.append(f)

    if not matching:
        return None

    temps = [f.temperature for f in matching]
    precips = [f.precip_chance for f in matching]

    return WindowWeather(
        temp_min=min(temps),
        temp_max=max(temps),
        precip_chance=max(precips),
    )


def clear_weather_cache() -> None:
    """Clear the weather cache (for testing)."""
    _weather_cache.clear()
