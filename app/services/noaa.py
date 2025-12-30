"""NOAA Tides & Currents API service."""

from dataclasses import dataclass
from datetime import datetime

import httpx

NOAA_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# La Jolla, Scripps Pier station
LA_JOLLA_STATION_ID = "9410230"
LA_JOLLA_LAT = 32.8669
LA_JOLLA_LON = -117.2571


@dataclass
class TidePrediction:
    """A single tide prediction from NOAA."""

    time: datetime
    height_ft: float
    tide_type: str  # "H" for high, "L" for low

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
