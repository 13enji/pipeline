"""Cache service for tide data."""

from datetime import datetime, timedelta
from typing import Any

from app.services.noaa import TideReading, fetch_tide_readings
from app.services.twilight import LA_JOLLA_TZ

# In-memory cache for 6-minute tide readings
_readings_cache: dict[str, Any] = {
    "readings": None,
    "fetched_at": None,
}

CACHE_TTL_HOURS = 20  # Refresh if cache is older than 20 hours


def _is_cache_valid() -> bool:
    """Check if the cache is valid (exists and not expired)."""
    if _readings_cache["readings"] is None or _readings_cache["fetched_at"] is None:
        return False
    age = datetime.now(LA_JOLLA_TZ) - _readings_cache["fetched_at"]
    return age < timedelta(hours=CACHE_TTL_HOURS)


async def get_tide_readings(force_refresh: bool = False) -> list[TideReading]:
    """
    Get 6-minute interval tide readings, using cache if available.

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        List of TideReading objects for the next 90 days
    """
    if not force_refresh and _is_cache_valid() and _readings_cache["readings"] is not None:
        return _readings_cache["readings"]

    # Fetch fresh data
    start_date = datetime.now(LA_JOLLA_TZ)
    readings = await fetch_tide_readings(begin_date=start_date)

    # Update cache
    _readings_cache["readings"] = readings
    _readings_cache["fetched_at"] = datetime.now(LA_JOLLA_TZ)

    return readings


async def refresh_cache() -> dict[str, Any]:
    """
    Force refresh the tide readings cache.

    Returns:
        Dict with refresh status and stats
    """
    readings = await get_tide_readings(force_refresh=True)
    return {
        "status": "ok",
        "readings_count": len(readings),
        "fetched_at": _readings_cache["fetched_at"].isoformat() if _readings_cache["fetched_at"] else None,
    }
