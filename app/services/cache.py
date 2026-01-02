"""Cache service for tide data.

Two separate caches and lists:
- Reference stations: 6-minute interval data (known_reference_stations.json)
- Subordinate stations: high/low data only (known_subordinate_stations.json)
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.noaa import (
    LA_JOLLA_STATION_ID,
    TidePrediction,
    TideReading,
    fetch_tide_predictions,
    fetch_tide_readings,
)

# Default timezone for La Jolla
LA_JOLLA_TZ = ZoneInfo("America/Los_Angeles")

CACHE_TTL_HOURS = 20  # Refresh if cache is older than 20 hours

# Files to persist known stations across restarts
KNOWN_REFERENCE_STATIONS_FILE = (
    Path(__file__).parent.parent.parent / "data" / "known_reference_stations.json"
)
KNOWN_SUBORDINATE_STATIONS_FILE = (
    Path(__file__).parent.parent.parent / "data" / "known_subordinate_stations.json"
)


@dataclass
class ReferenceStationCache:
    """Cache entry for a reference station's 6-minute interval data."""

    readings: list[TideReading]
    fetched_at: datetime
    timezone: ZoneInfo


@dataclass
class SubordinateStationCache:
    """Cache entry for a subordinate station's high/low data."""

    predictions: list[TidePrediction]
    fetched_at: datetime
    timezone: ZoneInfo
    station_name: str = ""
    station_state: str = ""
    station_lat: float = 0.0
    station_lon: float = 0.0


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


# In-memory cache for reference stations (6-minute data)
_reference_cache: dict[str, ReferenceStationCache] = {}

# In-memory cache for subordinate stations (high/low data)
_subordinate_cache: dict[str, SubordinateStationCache] = {}


# --- Reference Station Functions ---


def _load_known_reference_stations() -> list[KnownStation]:
    """Load the list of known reference stations from disk."""
    if not KNOWN_REFERENCE_STATIONS_FILE.exists():
        return []
    try:
        data = json.loads(KNOWN_REFERENCE_STATIONS_FILE.read_text())
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


def _save_known_reference_stations(stations: list[KnownStation]) -> None:
    """Save the list of known reference stations to disk."""
    KNOWN_REFERENCE_STATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
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
    KNOWN_REFERENCE_STATIONS_FILE.write_text(json.dumps(data, indent=2))


def _add_known_reference_station(
    station_id: str,
    tz: ZoneInfo,
    name: str = "",
    state: str = "",
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> None:
    """Add a reference station to the known list if not already present."""
    stations = _load_known_reference_stations()
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
        _save_known_reference_stations(stations)
    elif not existing.name and name:
        existing.name = name
        existing.state = state
        existing.latitude = latitude
        existing.longitude = longitude
        _save_known_reference_stations(stations)


def _is_reference_cache_valid(station_id: str, tz: ZoneInfo) -> bool:
    """Check if the reference cache for a station is valid."""
    if station_id not in _reference_cache:
        return False
    cache_entry = _reference_cache[station_id]
    age = datetime.now(tz) - cache_entry.fetched_at
    return age < timedelta(hours=CACHE_TTL_HOURS)


async def get_reference_station_data(
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
    Get 6-minute interval tide data for a reference station.

    Args:
        station_id: NOAA station ID
        tz: Timezone for the station
        days: Number of days of data to fetch
        force_refresh: If True, bypass cache and fetch fresh data
        station_name: Station name for display
        station_state: Station state abbreviation
        station_lat: Station latitude
        station_lon: Station longitude

    Returns:
        List of TideReading objects (6-minute intervals)
    """
    # Track this station for overnight refresh
    _add_known_reference_station(
        station_id, tz,
        name=station_name,
        state=station_state,
        latitude=station_lat,
        longitude=station_lon,
    )

    if not force_refresh and _is_reference_cache_valid(station_id, tz):
        return _reference_cache[station_id].readings

    # Fetch fresh data
    start_date = datetime.now(tz)
    readings = await fetch_tide_readings(
        station_id=station_id,
        begin_date=start_date,
        end_date=start_date + timedelta(days=days),
    )

    # Update cache
    _reference_cache[station_id] = ReferenceStationCache(
        readings=readings,
        fetched_at=datetime.now(tz),
        timezone=tz,
    )

    return readings


# Backwards compatibility alias
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
    """Backwards compatibility wrapper for get_reference_station_data."""
    return await get_reference_station_data(
        station_id=station_id,
        tz=tz,
        days=days,
        force_refresh=force_refresh,
        station_name=station_name,
        station_state=station_state,
        station_lat=station_lat,
        station_lon=station_lon,
    )


async def get_tide_readings(force_refresh: bool = False) -> list[TideReading]:
    """Get 6-minute interval tide data for La Jolla (backwards compatibility)."""
    return await get_reference_station_data(
        station_id=LA_JOLLA_STATION_ID,
        tz=LA_JOLLA_TZ,
        force_refresh=force_refresh,
    )


# --- Subordinate Station Functions ---


def _load_known_subordinate_stations() -> list[KnownStation]:
    """Load the list of known subordinate stations from disk."""
    if not KNOWN_SUBORDINATE_STATIONS_FILE.exists():
        return []
    try:
        data = json.loads(KNOWN_SUBORDINATE_STATIONS_FILE.read_text())
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


def _save_known_subordinate_stations(stations: list[KnownStation]) -> None:
    """Save the list of known subordinate stations to disk."""
    KNOWN_SUBORDINATE_STATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
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
    KNOWN_SUBORDINATE_STATIONS_FILE.write_text(json.dumps(data, indent=2))


def _add_known_subordinate_station(
    station_id: str,
    tz: ZoneInfo,
    name: str = "",
    state: str = "",
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> None:
    """Add a subordinate station to the known list if not already present."""
    stations = _load_known_subordinate_stations()
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
        _save_known_subordinate_stations(stations)
    elif not existing.name and name:
        existing.name = name
        existing.state = state
        existing.latitude = latitude
        existing.longitude = longitude
        _save_known_subordinate_stations(stations)


def _is_subordinate_cache_valid(station_id: str, tz: ZoneInfo) -> bool:
    """Check if the subordinate cache for a station is valid."""
    if station_id not in _subordinate_cache:
        return False
    cache_entry = _subordinate_cache[station_id]
    age = datetime.now(tz) - cache_entry.fetched_at
    return age < timedelta(hours=CACHE_TTL_HOURS)


async def get_subordinate_station_data(
    station_id: str,
    tz: ZoneInfo,
    days: int = 90,
    force_refresh: bool = False,
    station_name: str = "",
    station_state: str = "",
    station_lat: float = 0.0,
    station_lon: float = 0.0,
) -> list[TidePrediction]:
    """
    Get high/low tide data for a subordinate station.

    Args:
        station_id: NOAA station ID
        tz: Timezone for the station
        days: Number of days of data to fetch
        force_refresh: If True, bypass cache and fetch fresh data
        station_name: Station name for display
        station_state: Station state abbreviation
        station_lat: Station latitude
        station_lon: Station longitude

    Returns:
        List of TidePrediction objects (high/low only)
    """
    # Track this station for overnight refresh
    _add_known_subordinate_station(
        station_id, tz,
        name=station_name,
        state=station_state,
        latitude=station_lat,
        longitude=station_lon,
    )

    if not force_refresh and _is_subordinate_cache_valid(station_id, tz):
        return _subordinate_cache[station_id].predictions

    # Fetch fresh data
    start_date = datetime.now(tz)
    predictions = await fetch_tide_predictions(
        station_id=station_id,
        begin_date=start_date,
        end_date=start_date + timedelta(days=days),
    )

    # Update cache
    _subordinate_cache[station_id] = SubordinateStationCache(
        predictions=predictions,
        fetched_at=datetime.now(tz),
        timezone=tz,
        station_name=station_name,
        station_state=station_state,
        station_lat=station_lat,
        station_lon=station_lon,
    )

    return predictions


# Backwards compatibility alias
async def get_tide_predictions_cached(
    station_id: str,
    tz: ZoneInfo,
    days: int = 90,
    force_refresh: bool = False,
    station_name: str = "",
    station_state: str = "",
    station_lat: float = 0.0,
    station_lon: float = 0.0,
    station_type: str = "",  # Ignored - kept for backwards compatibility
) -> list[TidePrediction]:
    """Backwards compatibility wrapper for get_subordinate_station_data."""
    return await get_subordinate_station_data(
        station_id=station_id,
        tz=tz,
        days=days,
        force_refresh=force_refresh,
        station_name=station_name,
        station_state=station_state,
        station_lat=station_lat,
        station_lon=station_lon,
    )


# --- Refresh Functions ---


async def refresh_cache() -> dict[str, object]:
    """
    Force refresh both reference and subordinate station caches.

    Returns:
        Dict with refresh status and stats for each station
    """
    results: dict[str, dict[str, object]] = {
        "reference_stations": {},
        "subordinate_stations": {},
    }

    # Refresh reference stations
    ref_stations = _load_known_reference_stations()

    # Always include La Jolla
    if not any(s.station_id == LA_JOLLA_STATION_ID for s in ref_stations):
        ref_stations.append(KnownStation(
            station_id=LA_JOLLA_STATION_ID,
            timezone_name=str(LA_JOLLA_TZ),
        ))
        _save_known_reference_stations(ref_stations)

    for station in ref_stations:
        try:
            readings = await get_reference_station_data(
                station_id=station.station_id,
                tz=station.timezone,
                force_refresh=True,
            )
            cache_entry = _reference_cache.get(station.station_id)
            results["reference_stations"][station.station_id] = {
                "status": "ok",
                "name": station.name,
                "count": len(readings),
                "fetched_at": cache_entry.fetched_at.isoformat() if cache_entry else None,
            }
        except Exception as e:
            results["reference_stations"][station.station_id] = {
                "status": "error",
                "name": station.name,
                "error": str(e),
            }

    # Refresh subordinate stations
    sub_stations = _load_known_subordinate_stations()

    for station in sub_stations:
        try:
            predictions = await get_subordinate_station_data(
                station_id=station.station_id,
                tz=station.timezone,
                force_refresh=True,
                station_name=station.name,
                station_state=station.state,
                station_lat=station.latitude,
                station_lon=station.longitude,
            )
            cache_entry = _subordinate_cache.get(station.station_id)
            results["subordinate_stations"][station.station_id] = {
                "status": "ok",
                "name": station.name,
                "count": len(predictions),
                "fetched_at": cache_entry.fetched_at.isoformat() if cache_entry else None,
            }
        except Exception as e:
            results["subordinate_stations"][station.station_id] = {
                "status": "error",
                "name": station.name,
                "error": str(e),
            }

    return {
        "status": "ok",
        "reference_stations_refreshed": len(results["reference_stations"]),
        "subordinate_stations_refreshed": len(results["subordinate_stations"]),
        "stations": results,
    }


async def refresh_station_cache(station_id: str, tz: ZoneInfo) -> dict[str, object]:
    """Force refresh the cache for a specific reference station."""
    readings = await get_reference_station_data(
        station_id=station_id,
        tz=tz,
        force_refresh=True,
    )
    cache_entry = _reference_cache.get(station_id)
    return {
        "status": "ok",
        "station_id": station_id,
        "count": len(readings),
        "fetched_at": cache_entry.fetched_at.isoformat() if cache_entry else None,
    }


# --- Stats Functions ---


def get_cache_stats() -> dict[str, object]:
    """Get statistics about all cached stations."""
    # Reference stations
    ref_stations = _load_known_reference_stations()
    ref_info = []
    for s in ref_stations:
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
        if s.station_id in _reference_cache:
            cache_entry = _reference_cache[s.station_id]
            info["cached"] = True
            info["count"] = len(cache_entry.readings)
            info["fetched_at"] = cache_entry.fetched_at.isoformat()
        else:
            info["cached"] = False
        ref_info.append(info)

    # Subordinate stations
    sub_stations = _load_known_subordinate_stations()
    sub_info = []
    for s in sub_stations:
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
        if s.station_id in _subordinate_cache:
            cache_entry = _subordinate_cache[s.station_id]
            info["cached"] = True
            info["count"] = len(cache_entry.predictions)
            info["fetched_at"] = cache_entry.fetched_at.isoformat()
        else:
            info["cached"] = False
        sub_info.append(info)

    return {
        "reference_station_count": len(ref_stations),
        "reference_stations": ref_info,
        "subordinate_station_count": len(sub_stations),
        "subordinate_stations": sub_info,
    }
