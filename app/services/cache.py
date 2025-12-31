"""Cache service for tide data."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.noaa import LA_JOLLA_STATION_ID, TideReading, fetch_tide_readings

# Default timezone for La Jolla
LA_JOLLA_TZ = ZoneInfo("America/Los_Angeles")

CACHE_TTL_HOURS = 20  # Refresh if cache is older than 20 hours


@dataclass
class StationCache:
    """Cache entry for a single station's readings."""

    readings: list[TideReading]
    fetched_at: datetime
    timezone: ZoneInfo


# In-memory cache for 6-minute tide readings, keyed by station ID
_readings_cache: dict[str, StationCache] = {}


def _is_cache_valid(station_id: str, tz: ZoneInfo) -> bool:
    """Check if the cache for a station is valid (exists and not expired)."""
    if station_id not in _readings_cache:
        return False
    cache_entry = _readings_cache[station_id]
    age = datetime.now(tz) - cache_entry.fetched_at
    return age < timedelta(hours=CACHE_TTL_HOURS)


async def get_tide_readings_cached(
    station_id: str = LA_JOLLA_STATION_ID,
    tz: ZoneInfo = LA_JOLLA_TZ,
    days: int = 90,
    force_refresh: bool = False,
) -> list[TideReading]:
    """
    Get 6-minute interval tide readings for a station, using cache if available.

    Args:
        station_id: NOAA station ID
        tz: Timezone for the station
        days: Number of days of readings to fetch
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        List of TideReading objects
    """
    if not force_refresh and _is_cache_valid(station_id, tz):
        return _readings_cache[station_id].readings

    # Fetch fresh data
    start_date = datetime.now(tz)
    readings = await fetch_tide_readings(
        station_id=station_id,
        begin_date=start_date,
        end_date=start_date + timedelta(days=days),
    )

    # Update cache
    _readings_cache[station_id] = StationCache(
        readings=readings,
        fetched_at=datetime.now(tz),
        timezone=tz,
    )

    return readings


async def get_tide_readings(force_refresh: bool = False) -> list[TideReading]:
    """
    Get 6-minute interval tide readings for La Jolla (backwards compatibility).

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        List of TideReading objects for the next 90 days
    """
    return await get_tide_readings_cached(
        station_id=LA_JOLLA_STATION_ID,
        tz=LA_JOLLA_TZ,
        force_refresh=force_refresh,
    )


async def refresh_cache() -> dict[str, object]:
    """
    Force refresh the tide readings cache for La Jolla.

    Returns:
        Dict with refresh status and stats
    """
    readings = await get_tide_readings(force_refresh=True)
    cache_entry = _readings_cache.get(LA_JOLLA_STATION_ID)
    return {
        "status": "ok",
        "readings_count": len(readings),
        "fetched_at": cache_entry.fetched_at.isoformat() if cache_entry else None,
    }


async def refresh_station_cache(station_id: str, tz: ZoneInfo) -> dict[str, object]:
    """
    Force refresh the tide readings cache for a specific station.

    Args:
        station_id: NOAA station ID
        tz: Station timezone

    Returns:
        Dict with refresh status and stats
    """
    readings = await get_tide_readings_cached(
        station_id=station_id,
        tz=tz,
        force_refresh=True,
    )
    cache_entry = _readings_cache.get(station_id)
    return {
        "status": "ok",
        "station_id": station_id,
        "readings_count": len(readings),
        "fetched_at": cache_entry.fetched_at.isoformat() if cache_entry else None,
    }


def get_cache_stats() -> dict[str, object]:
    """Get statistics about cached stations."""
    stats = {}
    for station_id, cache_entry in _readings_cache.items():
        stats[station_id] = {
            "readings_count": len(cache_entry.readings),
            "fetched_at": cache_entry.fetched_at.isoformat(),
            "timezone": str(cache_entry.timezone),
        }
    return stats
