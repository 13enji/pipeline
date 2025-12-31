"""NOAA station lookup service."""

import math
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import httpx

NOAA_STATIONS_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"

# Cache for station list (fetched once per app lifetime)
_stations_cache: list["Station"] | None = None


@dataclass
class Station:
    """A NOAA tide prediction station."""

    id: str
    name: str
    state: str
    latitude: float
    longitude: float
    timezone_offset: int  # Hours from UTC

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
    """Fetch all tide prediction stations from NOAA."""
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

        stations.append(
            Station(
                id=s["id"],
                name=s["name"],
                state=s.get("state", ""),
                latitude=float(s["lat"]),
                longitude=float(s["lng"]),
                timezone_offset=int(s.get("timezonecorr", -8)),
            )
        )

    _stations_cache = stations
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
    Find the nearest NOAA tide prediction station to given coordinates.

    Args:
        latitude: Reference latitude
        longitude: Reference longitude

    Returns:
        StationWithDistance with nearest station and distance
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


def clear_station_cache() -> None:
    """Clear the cached station list (for testing)."""
    global _stations_cache
    _stations_cache = None
