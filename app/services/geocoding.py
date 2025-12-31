"""Geocoding service for converting zip codes to coordinates."""

from dataclasses import dataclass

import httpx


@dataclass
class GeoLocation:
    """A geographic location with coordinates."""

    zip_code: str
    place_name: str
    state: str
    latitude: float
    longitude: float


class GeocodingError(Exception):
    """Error during geocoding."""

    pass


async def geocode_zip(zip_code: str) -> GeoLocation:
    """
    Convert a US zip code to geographic coordinates.

    Uses the Zippopotam.us API (free, no API key required).

    Args:
        zip_code: US zip code (5 digits)

    Returns:
        GeoLocation with coordinates and place info

    Raises:
        GeocodingError: If zip code is invalid or API fails
    """
    # Validate zip code format
    zip_code = zip_code.strip()
    if not zip_code.isdigit() or len(zip_code) != 5:
        raise GeocodingError(f"Invalid zip code format: {zip_code}")

    url = f"https://api.zippopotam.us/us/{zip_code}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)

            if response.status_code == 404:
                raise GeocodingError(f"Zip code not found: {zip_code}")

            response.raise_for_status()
            data = response.json()

    except httpx.HTTPStatusError as e:
        raise GeocodingError(f"Geocoding API error: {e}") from e
    except httpx.RequestError as e:
        raise GeocodingError(f"Network error during geocoding: {e}") from e

    if not data.get("places"):
        raise GeocodingError(f"No location found for zip code: {zip_code}")

    place = data["places"][0]

    return GeoLocation(
        zip_code=zip_code,
        place_name=place["place name"],
        state=place["state abbreviation"],
        latitude=float(place["latitude"]),
        longitude=float(place["longitude"]),
    )
