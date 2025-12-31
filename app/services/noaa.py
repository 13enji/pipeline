"""NOAA Tides & Currents API service."""

from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

NOAA_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# La Jolla, Scripps Pier station
LA_JOLLA_STATION_ID = "9410230"
LA_JOLLA_LAT = 32.8669
LA_JOLLA_LON = -117.2571


@dataclass
class TidePrediction:
    """A single high/low tide prediction from NOAA."""

    time: datetime
    height_ft: float
    tide_type: str  # "H" for high, "L" for low

    @property
    def height_m(self) -> float:
        """Convert height to meters."""
        return self.height_ft * 0.3048


@dataclass
class TideReading:
    """A single tide height reading at a specific time (6-minute interval data)."""

    time: datetime
    height_ft: float

    @property
    def height_m(self) -> float:
        """Convert height to meters."""
        return self.height_ft * 0.3048


async def fetch_tide_predictions(
    station_id: str = LA_JOLLA_STATION_ID,
    begin_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[TidePrediction]:
    """
    Fetch high/low tide predictions from NOAA API.

    Args:
        station_id: NOAA station ID
        begin_date: Start date for predictions (defaults to today)
        end_date: End date for predictions (defaults to 90 days from begin_date)

    Returns:
        List of TidePrediction objects
    """
    if begin_date is None:
        begin_date = datetime.now()
    if end_date is None:
        end_date = begin_date.replace(day=begin_date.day + 90)

    params = {
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "format": "json",
        "interval": "hilo",
        "begin_date": begin_date.strftime("%Y%m%d"),
        "end_date": end_date.strftime("%Y%m%d"),
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(NOAA_API_BASE, params=params)
        response.raise_for_status()
        data = response.json()

    predictions = []
    for pred in data.get("predictions", []):
        time = datetime.strptime(pred["t"], "%Y-%m-%d %H:%M")
        height = float(pred["v"])
        tide_type = pred["type"]
        predictions.append(TidePrediction(time=time, height_ft=height, tide_type=tide_type))

    return predictions


async def fetch_tide_readings(
    station_id: str = LA_JOLLA_STATION_ID,
    begin_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[TideReading]:
    """
    Fetch 6-minute interval tide predictions from NOAA API.

    Note: NOAA limits 6-minute data to 31 days per request, so this function
    makes multiple requests for longer date ranges.

    Args:
        station_id: NOAA station ID
        begin_date: Start date for predictions (defaults to today)
        end_date: End date for predictions (defaults to 90 days from begin_date)

    Returns:
        List of TideReading objects with 6-minute interval data
    """
    if begin_date is None:
        begin_date = datetime.now()
    if end_date is None:
        end_date = begin_date + timedelta(days=90)

    all_readings: list[TideReading] = []

    # Fetch in monthly chunks (31 days max per request)
    current_start = begin_date
    async with httpx.AsyncClient() as client:
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=30), end_date)

            params = {
                "station": station_id,
                "product": "predictions",
                "datum": "MLLW",
                "time_zone": "lst_ldt",
                "units": "english",
                "format": "json",
                "interval": "6",
                "application": "tide_dashboard",
                "begin_date": current_start.strftime("%Y%m%d"),
                "end_date": current_end.strftime("%Y%m%d"),
            }

            response = await client.get(NOAA_API_BASE, params=params)
            response.raise_for_status()
            data = response.json()

            for reading in data.get("predictions", []):
                time = datetime.strptime(reading["t"], "%Y-%m-%d %H:%M")
                height = float(reading["v"])
                all_readings.append(TideReading(time=time, height_ft=height))

            current_start = current_end + timedelta(days=1)

    return all_readings
