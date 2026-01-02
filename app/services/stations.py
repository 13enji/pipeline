"""NOAA station lookup service."""

import math
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import httpx

NOAA_STATIONS_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"

# Cache for station list (fetched once per app lifetime)
_stations_cache: list["Station"] | None = None
_all_stations_cache: list["Station"] | None = None  # Includes subordinate stations


@dataclass
class Station:
    """A NOAA tide prediction station."""

    id: str
    name: str
    state: str
    latitude: float
    longitude: float
    timezone_offset: int  # Hours from UTC
    station_type: str = "R"  # "R" for reference, "S" for subordinate

    @property
    def is_reference(self) -> bool:
        """Check if this is a reference (harmonic) station."""
        return self.station_type == "R"

    @property
    def is_subordinate(self) -> bool:
        """Check if this is a subordinate station."""
        return self.station_type == "S"

    @property
    def timezone(self) -> ZoneInfo:
        """Get the timezone for this station based on offset."""
        # Map common US timezone offsets to zone names
        offset_to_tz = {
            -10: "Pacific/Honolulu",  # Hawaii
            -9: "America/Anchorage",  # Alaska
            -8: "America/Los_Angeles",  # Pacific
            -7: "America/Denver",  # Mountain
            -6: "America/Chicago",  # Central
            -5: "America/New_York",  # Eastern
            -4: "America/Puerto_Rico",  # Atlantic
            10: "Pacific/Guam",  # Guam
            12: "Pacific/Majuro",  # Marshall Islands
        }
        tz_name = offset_to_tz.get(self.timezone_offset, "America/New_York")
        return ZoneInfo(tz_name)

    @property
    def timezone_abbr(self) -> str:
        """Get timezone abbreviation (e.g., PST, EST)."""
        from datetime import datetime

        now = datetime.now(self.timezone)
        return now.strftime("%Z")


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in miles using Haversine formula.

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in miles
    """
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


async def _fetch_stations() -> list[Station]:
    """Fetch reference tide prediction stations from NOAA.

    Only returns reference stations (type="R") which have full datum data
    and can return 6-minute interval tide predictions.
    """
    global _stations_cache

    if _stations_cache is not None:
        return _stations_cache

    params = {"type": "tidepredictions"}

    async with httpx.AsyncClient() as client:
        response = await client.get(NOAA_STATIONS_URL, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()

    stations = []
    for s in data.get("stations", []):
        # Skip stations without coordinates
        if s.get("lat") is None or s.get("lng") is None:
            continue

        # Only include reference stations (type="R") which have full datum data
        if s.get("type") != "R":
            continue

        stations.append(
            Station(
                id=s["id"],
                name=s["name"],
                state=s.get("state", ""),
                latitude=float(s["lat"]),
                longitude=float(s["lng"]),
                timezone_offset=int(s.get("timezonecorr", -8)),
                station_type="R",
            )
        )

    _stations_cache = stations
    return stations


async def _fetch_all_stations() -> list[Station]:
    """Fetch all tide prediction stations from NOAA (reference AND subordinate).

    Returns both reference stations (type="R") and subordinate stations (type="S").
    Reference stations support 6-minute interval data.
    Subordinate stations only support high/low predictions.
    """
    global _all_stations_cache

    if _all_stations_cache is not None:
        return _all_stations_cache

    params = {"type": "tidepredictions"}

    async with httpx.AsyncClient() as client:
        response = await client.get(NOAA_STATIONS_URL, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()

    stations = []
    for s in data.get("stations", []):
        # Skip stations without coordinates
        if s.get("lat") is None or s.get("lng") is None:
            continue

        # Include both reference (R) and subordinate (S) stations
        station_type = s.get("type", "R")
        if station_type not in ("R", "S"):
            continue

        stations.append(
            Station(
                id=s["id"],
                name=s["name"],
                state=s.get("state", ""),
                latitude=float(s["lat"]),
                longitude=float(s["lng"]),
                timezone_offset=int(s.get("timezonecorr", -8)),
                station_type=station_type,
            )
        )

    _all_stations_cache = stations
    return stations


@dataclass
class StationWithDistance:
    """A station with calculated distance from a reference point."""

    station: Station
    distance_miles: float

    @property
    def distance_km(self) -> float:
        """Distance in kilometers."""
        return self.distance_miles * 1.60934

    def distance_display(self, metric: bool = False) -> str:
        """Format distance for display."""
        if metric:
            return f"{self.distance_km:.1f} km"
        return f"{self.distance_miles:.1f} miles"


async def find_nearest_station(latitude: float, longitude: float) -> StationWithDistance:
    """
    Find the nearest reference NOAA tide prediction station to given coordinates.

    Only searches reference stations (type="R") which support 6-minute data.

    Args:
        latitude: Reference latitude
        longitude: Reference longitude

    Returns:
        StationWithDistance with nearest reference station and distance
    """
    stations = await _fetch_stations()

    nearest: StationWithDistance | None = None

    for station in stations:
        distance = _haversine_distance(
            latitude, longitude, station.latitude, station.longitude
        )

        if nearest is None or distance < nearest.distance_miles:
            nearest = StationWithDistance(station=station, distance_miles=distance)

    if nearest is None:
        raise ValueError("No stations found")

    return nearest


async def find_nearest_station_any_type(
    latitude: float, longitude: float
) -> StationWithDistance:
    """
    Find the nearest NOAA tide prediction station (reference OR subordinate).

    Searches all stations regardless of type. Use this when you only need
    high/low predictions, not 6-minute interval data.

    Args:
        latitude: Reference latitude
        longitude: Reference longitude

    Returns:
        StationWithDistance with nearest station (any type) and distance
    """
    stations = await _fetch_all_stations()

    nearest: StationWithDistance | None = None

    for station in stations:
        distance = _haversine_distance(
            latitude, longitude, station.latitude, station.longitude
        )

        if nearest is None or distance < nearest.distance_miles:
            nearest = StationWithDistance(station=station, distance_miles=distance)

    if nearest is None:
        raise ValueError("No stations found")

    return nearest


def clear_station_cache() -> None:
    """Clear the cached station list (for testing)."""
    global _stations_cache, _all_stations_cache
    _stations_cache = None
    _all_stations_cache = None
