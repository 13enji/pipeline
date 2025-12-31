"""Tide window finding service."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.cache import get_tide_readings
from app.services.noaa import TideReading
from app.services.tides import is_outside_work_hours
from app.services.twilight import (
    LA_JOLLA_TZ,
    get_daylight_window,
)


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
        """Format time range as '6:30am - 9:12am'."""
        start = self.start_time.strftime("%I:%M%p").lstrip("0").lower()
        end = self.end_time.strftime("%I:%M%p").lstrip("0").lower()
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
            return True  # Default to morning if no light data
        middle = self.start_time + (self.end_time - self.start_time) / 2
        if middle.tzinfo is None:
            middle = middle.replace(tzinfo=LA_JOLLA_TZ)
        # Compare middle of window to midpoint of daylight
        daylight_midpoint = self.first_light + (self.last_light - self.first_light) / 2
        return middle < daylight_midpoint

    @property
    def relevant_light_display(self) -> str:
        """Get the relevant light time display (first light for morning, last light for evening)."""
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
    return readings[0]  # Fallback, should never reach here


def _find_windows_in_readings(
    readings: list[TideReading],
    max_height_ft: float,
) -> list[TideWindow]:
    """
    Find continuous windows where tide height is at or below max_height_ft.

    Args:
        readings: List of TideReading objects (sorted by time)
        max_height_ft: Maximum tide height to consider

    Returns:
        List of TideWindow objects
    """
    windows = []
    window_start = None
    window_readings: list[TideReading] = []

    for reading in readings:
        if reading.height_ft <= max_height_ft:
            # In a valid window
            if window_start is None:
                window_start = reading.time
                window_readings = [reading]
            else:
                window_readings.append(reading)
        else:
            # Window ended
            if window_start is not None and len(window_readings) > 0:
                min_reading = _find_min_reading(window_readings)
                heights = [r.height_ft for r in window_readings]
                windows.append(
                    TideWindow(
                        start_time=window_start,
                        end_time=window_readings[-1].time,
                        min_height_ft=min_reading.height_ft,
                        min_height_time=min_reading.time,
                        max_height_ft=max(heights),
                        avg_height_ft=sum(heights) / len(heights),
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
                start_time=window_start,
                end_time=window_readings[-1].time,
                min_height_ft=min_reading.height_ft,
                min_height_time=min_reading.time,
                max_height_ft=max(heights),
                avg_height_ft=sum(heights) / len(heights),
            )
        )

    return windows


def _get_daylight_overlap_minutes(window: TideWindow) -> int:
    """
    Calculate the overlap between a window and daylight hours (civil dawn to dusk).

    Returns:
        Number of minutes the window overlaps with daylight
    """
    start = window.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=LA_JOLLA_TZ)

    daylight = get_daylight_window(start)

    # Calculate overlap between window and daylight
    overlap_start = max(start, daylight.civil_dawn)
    overlap_end = min(window.end_time.replace(tzinfo=LA_JOLLA_TZ), daylight.civil_dusk)

    if overlap_start >= overlap_end:
        return 0  # No overlap

    return int((overlap_end - overlap_start).total_seconds() / 60)


def _add_light_times_to_window(window: TideWindow) -> TideWindow:
    """Add first_light and last_light times to a window."""
    start = window.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=LA_JOLLA_TZ)

    daylight = get_daylight_window(start)

    window.first_light = daylight.civil_dawn
    window.last_light = daylight.civil_dusk
    return window


def _is_window_outside_work_hours(window: TideWindow) -> bool:
    """Check if window is entirely outside work hours."""
    # Check both start and end of window
    return is_outside_work_hours(window.start_time) and is_outside_work_hours(window.end_time)


async def find_tide_windows(
    max_height_ft: float = 1.0,
    min_duration_minutes: int = 60,
    daylight_only: bool = True,
    work_filter: bool = True,
    days: int = 90,
) -> list[TideWindow]:
    """
    Find tide windows matching the criteria.

    Args:
        max_height_ft: Maximum tide height for the window
        min_duration_minutes: Minimum window duration in minutes
        daylight_only: Only include windows during daylight hours
        work_filter: Only include windows outside work hours (M-F 9-5)
        days: Number of days to search

    Returns:
        List of TideWindow objects matching criteria, sorted by date
    """
    readings = await get_tide_readings()

    # Filter readings to requested day range
    now = datetime.now(LA_JOLLA_TZ)
    end_date = now + timedelta(days=days)
    filtered_readings = [
        r for r in readings
        if r.time.replace(tzinfo=LA_JOLLA_TZ) <= end_date
    ]

    # Find all windows below threshold
    windows = _find_windows_in_readings(filtered_readings, max_height_ft)

    # Filter by daylight overlap (must have min_duration minutes of daylight)
    if daylight_only:
        windows = [
            w for w in windows
            if _get_daylight_overlap_minutes(w) >= min_duration_minutes
        ]

    # Add light times to each window
    windows = [_add_light_times_to_window(w) for w in windows]

    # Filter by work hours
    if work_filter:
        windows = [w for w in windows if _is_window_outside_work_hours(w)]

    # Sort by date
    windows.sort(key=lambda w: w.start_time)

    return windows
