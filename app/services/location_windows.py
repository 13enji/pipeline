"""Location-based tide window finding service."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.cache import get_tide_predictions_cached, get_tide_readings_cached
from app.services.noaa import TidePrediction, TideReading
from app.services.stations import Station, find_nearest_station_any_type
from app.services.tides import is_outside_work_hours
from app.services.twilight import get_daylight_window_for_location


@dataclass
class TideWindow:
    """A window of time where tide is below a threshold."""

    start_time: datetime
    end_time: datetime
    min_height_ft: float
    min_height_time: datetime
    max_height_ft: float
    avg_height_ft: float
    first_light: datetime | None = None
    last_light: datetime | None = None
    timezone_abbr: str = ""

    @property
    def duration_minutes(self) -> int:
        """Duration of the window in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    @property
    def duration_display(self) -> str:
        """Human-readable duration."""
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours == 0:
            return f"{minutes}min"
        elif minutes == 0:
            return f"{hours}hr"
        else:
            return f"{hours}hr {minutes}min"

    @property
    def formatted_date(self) -> str:
        """Format date as 'SAT DEC 20th 2025'."""
        day = self.start_time.day
        if 11 <= day <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        weekday = self.start_time.strftime("%a").upper()
        return f"{weekday} " + self.start_time.strftime(f"%b {day}{suffix} %Y").upper()

    @property
    def formatted_time_range(self) -> str:
        """Format time range as '6:30am - 9:12am PST'."""
        start = self.start_time.strftime("%I:%M%p").lstrip("0").lower()
        end = self.end_time.strftime("%I:%M%p").lstrip("0").lower()
        if self.timezone_abbr:
            return f"{start} - {end} {self.timezone_abbr}"
        return f"{start} - {end}"

    def min_height_display(self, metric: bool = False) -> str:
        """Get formatted minimum height with units and time."""
        time_str = self.min_height_time.strftime("%I:%M%p").lstrip("0").lower()
        if metric:
            return f"{self.min_height_ft * 0.3048:.2f}m @ {time_str}"
        return f"{self.min_height_ft:.1f}ft @ {time_str}"

    def max_height_display(self, metric: bool = False) -> str:
        """Get formatted maximum height with units."""
        if metric:
            return f"{self.max_height_ft * 0.3048:.2f}m"
        return f"{self.max_height_ft:.1f}ft"

    @property
    def is_morning_window(self) -> bool:
        """Check if this is a morning window (closer to dawn than dusk)."""
        if self.first_light is None or self.last_light is None:
            return True
        middle = self.start_time + (self.end_time - self.start_time) / 2
        if middle.tzinfo is None and self.first_light.tzinfo is not None:
            middle = middle.replace(tzinfo=self.first_light.tzinfo)
        daylight_midpoint = self.first_light + (self.last_light - self.first_light) / 2
        return middle < daylight_midpoint

    @property
    def relevant_light_display(self) -> str:
        """Get the relevant light time display."""
        if self.is_morning_window:
            if self.first_light:
                time_str = self.first_light.strftime("%I:%M%p").lstrip("0").lower()
                return f"First light: {time_str}"
        else:
            if self.last_light:
                time_str = self.last_light.strftime("%I:%M%p").lstrip("0").lower()
                return f"Last light: {time_str}"
        return ""


def _find_min_reading(readings: list[TideReading]) -> TideReading:
    """Find the first reading with the minimum height."""
    min_height = min(r.height_ft for r in readings)
    for r in readings:
        if r.height_ft == min_height:
            return r
    return readings[0]


def _find_low_tide_in_window(
    predictions: list[TidePrediction],
    window_start: datetime,
    window_end: datetime,
) -> TidePrediction | None:
    """Find the low tide prediction that falls within a window's time range.

    Args:
        predictions: List of high/low tide predictions
        window_start: Start of the tide window
        window_end: End of the tide window

    Returns:
        The low tide prediction within the window, or None if not found
    """
    # Make times comparable (strip timezone if needed for comparison)
    for pred in predictions:
        if pred.tide_type != "L":
            continue

        # Compare times - handle both naive and aware datetimes
        pred_time = pred.time
        start = window_start
        end = window_end

        # If prediction is naive but window times have timezone, add timezone
        if pred_time.tzinfo is None and start.tzinfo is not None:
            pred_time = pred_time.replace(tzinfo=start.tzinfo)

        # If window times are naive but prediction has timezone, strip it
        if pred_time.tzinfo is not None and start.tzinfo is None:
            pred_time = pred_time.replace(tzinfo=None)

        if start <= pred_time <= end:
            return pred

    return None


def _find_windows_in_readings(
    readings: list[TideReading],
    max_height_ft: float,
    tz: ZoneInfo,
    tz_abbr: str,
) -> list[TideWindow]:
    """Find continuous windows where tide height is at or below max_height_ft."""
    windows = []
    window_start = None
    window_readings: list[TideReading] = []

    for reading in readings:
        if reading.height_ft <= max_height_ft:
            if window_start is None:
                window_start = reading.time
                window_readings = [reading]
            else:
                window_readings.append(reading)
        else:
            if window_start is not None and len(window_readings) > 0:
                min_reading = _find_min_reading(window_readings)
                heights = [r.height_ft for r in window_readings]
                windows.append(
                    TideWindow(
                        start_time=window_start.replace(tzinfo=tz),
                        end_time=window_readings[-1].time.replace(tzinfo=tz),
                        min_height_ft=min_reading.height_ft,
                        min_height_time=min_reading.time.replace(tzinfo=tz),
                        max_height_ft=max(heights),
                        avg_height_ft=sum(heights) / len(heights),
                        timezone_abbr=tz_abbr,
                    )
                )
                window_start = None
                window_readings = []

    # Handle window at end of readings
    if window_start is not None and len(window_readings) > 0:
        min_reading = _find_min_reading(window_readings)
        heights = [r.height_ft for r in window_readings]
        windows.append(
            TideWindow(
                start_time=window_start.replace(tzinfo=tz),
                end_time=window_readings[-1].time.replace(tzinfo=tz),
                min_height_ft=min_reading.height_ft,
                min_height_time=min_reading.time.replace(tzinfo=tz),
                max_height_ft=max(heights),
                avg_height_ft=sum(heights) / len(heights),
                timezone_abbr=tz_abbr,
            )
        )

    return windows


def _get_daylight_overlap_minutes(
    window: TideWindow,
    latitude: float,
    longitude: float,
    tz: ZoneInfo,
) -> int:
    """Calculate the overlap between a window and daylight hours."""
    daylight = get_daylight_window_for_location(
        window.start_time, latitude, longitude, tz
    )

    overlap_start = max(window.start_time, daylight.civil_dawn)
    overlap_end = min(window.end_time, daylight.civil_dusk)

    if overlap_start >= overlap_end:
        return 0

    return int((overlap_end - overlap_start).total_seconds() / 60)


def _add_light_times_to_window(
    window: TideWindow,
    latitude: float,
    longitude: float,
    tz: ZoneInfo,
) -> TideWindow:
    """Add first_light and last_light times to a window."""
    daylight = get_daylight_window_for_location(
        window.start_time, latitude, longitude, tz
    )

    window.first_light = daylight.civil_dawn
    window.last_light = daylight.civil_dusk
    return window


async def find_tide_windows_for_station(
    station: Station,
    max_height_ft: float = 0.5,
    min_duration_minutes: int = 60,
    daylight_only: bool = True,
    work_filter: bool = True,
    days: int = 90,
    user_latitude: float | None = None,
    user_longitude: float | None = None,
) -> list[TideWindow]:
    """
    Find tide windows for a specific station.

    Args:
        station: The NOAA reference station to get 6-minute tide data for
        max_height_ft: Maximum tide height for the window
        min_duration_minutes: Minimum window duration in minutes
        daylight_only: Only include windows during daylight hours
        work_filter: Only include windows outside work hours (M-F 9-5)
        days: Number of days to search
        user_latitude: User's latitude for finding closest station for low tide
        user_longitude: User's longitude for finding closest station for low tide

    Returns:
        List of TideWindow objects matching criteria, sorted by date
    """
    tz = station.timezone
    tz_abbr = station.timezone_abbr

    # Get 6-minute readings from reference station (for window calculations)
    readings = await get_tide_readings_cached(
        station_id=station.id,
        tz=tz,
        days=days,
        station_name=station.name,
        station_state=station.state,
        station_lat=station.latitude,
        station_lon=station.longitude,
    )

    # Find all windows below threshold
    windows = _find_windows_in_readings(readings, max_height_ft, tz, tz_abbr)

    # Get low tide predictions from closest station (may be subordinate)
    low_tide_predictions: list[TidePrediction] = []
    if user_latitude is not None and user_longitude is not None:
        try:
            closest_station = await find_nearest_station_any_type(
                user_latitude, user_longitude
            )
            low_tide_predictions = await get_tide_predictions_cached(
                station_id=closest_station.station.id,
                tz=closest_station.station.timezone,
                days=days,
                station_name=closest_station.station.name,
                station_state=closest_station.station.state,
                station_lat=closest_station.station.latitude,
                station_lon=closest_station.station.longitude,
                station_type=closest_station.station.station_type,
            )
        except (ValueError, Exception):
            # Fall back to reference station predictions if lookup fails
            pass

    # If no subordinate predictions, use reference station predictions
    if not low_tide_predictions:
        try:
            low_tide_predictions = await get_tide_predictions_cached(
                station_id=station.id,
                tz=tz,
                days=days,
                station_name=station.name,
                station_state=station.state,
                station_lat=station.latitude,
                station_lon=station.longitude,
                station_type=station.station_type,
            )
        except Exception:
            pass  # Will use 6-minute data fallback

    # Enhance windows with low tide data from closest station
    for window in windows:
        low_tide = _find_low_tide_in_window(
            low_tide_predictions, window.start_time, window.end_time
        )
        if low_tide is not None:
            # Use the closest station's low tide time and height
            low_time = low_tide.time
            if low_time.tzinfo is None:
                low_time = low_time.replace(tzinfo=tz)
            window.min_height_ft = low_tide.height_ft
            window.min_height_time = low_time
        # If no low tide found in predictions, keep the 6-minute data fallback
        # (already set by _find_windows_in_readings)

    # Filter by daylight overlap
    if daylight_only:
        windows = [
            w for w in windows
            if _get_daylight_overlap_minutes(
                w, station.latitude, station.longitude, tz
            ) >= min_duration_minutes
        ]

    # Add light times to each window
    windows = [
        _add_light_times_to_window(w, station.latitude, station.longitude, tz)
        for w in windows
    ]

    # Filter by work hours
    if work_filter:
        windows = [
            w for w in windows
            if is_outside_work_hours(w.start_time) and is_outside_work_hours(w.end_time)
        ]

    # Sort by date
    windows.sort(key=lambda w: w.start_time)

    return windows
