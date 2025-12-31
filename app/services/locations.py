"""Service for loading and managing tidepooling locations data."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Coordinates:
    """Geographic coordinates."""

    lat: float
    lon: float


@dataclass
class Location:
    """A tidepooling location."""

    id: str
    name: str
    also_known_as: list[str]
    city: str
    county: str
    region: str
    coordinates: Coordinates | None
    description: str
    best_tide_height_ft: float | None
    best_season: str | None
    tips: list[str]
    marine_life: list[str]
    amenities: list[str]
    access_difficulty: str | None
    sources: list[str]
    possible_duplicate_of: list[str]
    status: str | None = None  # For closed locations

    @property
    def has_coordinates(self) -> bool:
        """Check if location has coordinates."""
        return self.coordinates is not None


# Cache for loaded locations
_locations_cache: dict[str, Location] | None = None
_locations_list_cache: list[Location] | None = None


def _parse_location(data: dict[str, Any]) -> Location:
    """Parse a location dict into a Location object."""
    coords = None
    if data.get("coordinates"):
        coords = Coordinates(
            lat=data["coordinates"]["lat"],
            lon=data["coordinates"]["lon"],
        )

    return Location(
        id=data["id"],
        name=data["name"],
        also_known_as=data.get("also_known_as", []),
        city=data.get("city", ""),
        county=data.get("county", ""),
        region=data.get("region", ""),
        coordinates=coords,
        description=data.get("description", ""),
        best_tide_height_ft=data.get("best_tide_height_ft"),
        best_season=data.get("best_season"),
        tips=data.get("tips", []),
        marine_life=data.get("marine_life", []),
        amenities=data.get("amenities", []),
        access_difficulty=data.get("access_difficulty"),
        sources=data.get("sources", []),
        possible_duplicate_of=data.get("possible_duplicate_of", []),
        status=data.get("status"),
    )


def _load_locations() -> tuple[dict[str, Location], list[Location]]:
    """Load locations from JSON file."""
    global _locations_cache, _locations_list_cache

    if _locations_cache is not None and _locations_list_cache is not None:
        return _locations_cache, _locations_list_cache

    # Find the data file
    data_path = Path(__file__).parent.parent.parent / "data" / "tidepooling_locations_raw.json"

    with open(data_path) as f:
        data = json.load(f)

    locations_by_id: dict[str, Location] = {}
    locations_list: list[Location] = []

    for loc_data in data.get("locations", []):
        location = _parse_location(loc_data)
        locations_by_id[location.id] = location
        locations_list.append(location)

    _locations_cache = locations_by_id
    _locations_list_cache = locations_list

    return locations_by_id, locations_list


def get_all_locations() -> list[Location]:
    """Get all locations as a list."""
    _, locations_list = _load_locations()
    return locations_list


def get_location_by_id(location_id: str) -> Location | None:
    """Get a single location by ID."""
    locations_by_id, _ = _load_locations()
    return locations_by_id.get(location_id)


def get_locations_with_coordinates() -> list[Location]:
    """Get only locations that have coordinates."""
    return [loc for loc in get_all_locations() if loc.has_coordinates]


def get_locations_without_coordinates() -> list[Location]:
    """Get locations without coordinates."""
    return [loc for loc in get_all_locations() if not loc.has_coordinates]


def get_locations_by_county(county: str) -> list[Location]:
    """Get locations filtered by county."""
    return [loc for loc in get_all_locations() if loc.county == county]


def clear_locations_cache() -> None:
    """Clear the locations cache (for testing)."""
    global _locations_cache, _locations_list_cache
    _locations_cache = None
    _locations_list_cache = None
