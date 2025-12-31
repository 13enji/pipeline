"""Cache service for tide data."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.noaa import LA_JOLLA_STATION_ID, TideReading, fetch_tide_readings

# Default timezone for La Jolla
LA_JOLLA_TZ = ZoneInfo("America/Los_Angeles")

CACHE_TTL_HOURS = 20  # Refresh if cache is older than 20 hours

# File to persist known stations across restarts
KNOWN_STATIONS_FILE = Path(__file__).parent.parent.parent / "data" / "known_stations.json"


@dataclass
class StationCache:
    """Cache entry for a single station's readings."""

    readings: list[TideReading]
    fetched_at: datetime
    timezone: ZoneInfo


@dataclass
class KnownStation:
    """A station that has been requested and should be refreshed overnight."""

    station_id: str
    timezone_name: str
    name: str = ""
    state: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


# La Jolla coordinates for distance calculations
LA_JOLLA_LAT = 32.8669
LA_JOLLA_LON = -117.2571


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in miles using Haversine formula."""
    import math

    R = 3959  # Earth's radius in miles
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# In-memory cache for 6-minute tide readings, keyed by station ID
_readings_cache: dict[str, StationCache] = {}


def _load_known_stations() -> list[KnownStation]:
    """Load the list of known stations from disk."""
    if not KNOWN_STATIONS_FILE.exists():
        return []
    try:
        data = json.loads(KNOWN_STATIONS_FILE.read_text())
        stations = []
        for s in data:
            stations.append(KnownStation(
                station_id=s["station_id"],
                timezone_name=s["timezone_name"],
                name=s.get("name", ""),
                state=s.get("state", ""),
                latitude=s.get("latitude", 0.0),
                longitude=s.get("longitude", 0.0),
            ))
        return stations
    except (json.JSONDecodeError, KeyError):
        return []


def _save_known_stations(stations: list[KnownStation]) -> None:
    """Save the list of known stations to disk."""
    KNOWN_STATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "station_id": s.station_id,
            "timezone_name": s.timezone_name,
            "name": s.name,
            "state": s.state,
            "latitude": s.latitude,
            "longitude": s.longitude,
        }
        for s in stations
    ]
    KNOWN_STATIONS_FILE.write_text(json.dumps(data, indent=2))


def _add_known_station(
    station_id: str,
    tz: ZoneInfo,
    name: str = "",
    state: str = "",
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> None:
    """Add a station to the known stations list if not already present."""
    stations = _load_known_stations()
    existing = next((s for s in stations if s.station_id == station_id), None)
    if existing is None:
        stations.append(KnownStation(
            station_id=station_id,
            timezone_name=str(tz),
            name=name,
            state=state,
            latitude=latitude,
            longitude=longitude,
        ))
        _save_known_stations(stations)
    elif not existing.name and name:
        # Update existing station with metadata if it was missing
        existing.name = name
        existing.state = state
        existing.latitude = latitude
        existing.longitude = longitude
        _save_known_stations(stations)


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
    station_name: str = "",
    station_state: str = "",
    station_lat: float = 0.0,
    station_lon: float = 0.0,
) -> list[TideReading]:
    """
    Get 6-minute interval tide readings for a station, using cache if available.

    Args:
        station_id: NOAA station ID
        tz: Timezone for the station
        days: Number of days of readings to fetch
        force_refresh: If True, bypass cache and fetch fresh data
        station_name: Station name for display
        station_state: Station state abbreviation
        station_lat: Station latitude
        station_lon: Station longitude

    Returns:
        List of TideReading objects
    """
    # Track this station for overnight refresh
    _add_known_station(
        station_id, tz,
        name=station_name,
        state=station_state,
        latitude=station_lat,
        longitude=station_lon,
    )

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
    Force refresh the tide readings cache for all known stations.

    Returns:
        Dict with refresh status and stats for each station
    """
    stations = _load_known_stations()

    # Always include La Jolla
    if not any(s.station_id == LA_JOLLA_STATION_ID for s in stations):
        stations.append(KnownStation(
            station_id=LA_JOLLA_STATION_ID,
            timezone_name=str(LA_JOLLA_TZ),
        ))
        _save_known_stations(stations)

    results = {}
    for station in stations:
        try:
            readings = await get_tide_readings_cached(
                station_id=station.station_id,
                tz=station.timezone,
                force_refresh=True,
            )
            cache_entry = _readings_cache.get(station.station_id)
            results[station.station_id] = {
                "status": "ok",
                "readings_count": len(readings),
                "fetched_at": cache_entry.fetched_at.isoformat() if cache_entry else None,
            }
        except Exception as e:
            results[station.station_id] = {
                "status": "error",
                "error": str(e),
            }

    return {
        "status": "ok",
        "stations_refreshed": len(results),
        "stations": results,
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
    known = _load_known_stations()
    stations_info = []
    for s in known:
        info: dict[str, object] = {
            "station_id": s.station_id,
            "name": s.name or "(unknown)",
            "state": s.state or "",
            "timezone_name": s.timezone_name,
            "latitude": s.latitude,
            "longitude": s.longitude,
        }
        if s.latitude and s.longitude:
            distance = _haversine_distance(
                LA_JOLLA_LAT, LA_JOLLA_LON, s.latitude, s.longitude
            )
            info["distance_from_la_jolla_miles"] = round(distance, 1)
        # Add cache status if in memory
        if s.station_id in _readings_cache:
            cache_entry = _readings_cache[s.station_id]
            info["cached"] = True
            info["readings_count"] = len(cache_entry.readings)
            info["fetched_at"] = cache_entry.fetched_at.isoformat()
        else:
            info["cached"] = False
        stations_info.append(info)

    return {
        "station_count": len(known),
        "stations": stations_info,
    }
