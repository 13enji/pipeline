"""Tide filtering and processing service."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.noaa import TidePrediction, fetch_tide_predictions
from app.services.twilight import (
    LA_JOLLA_TZ,
    DaylightWindow,
    get_daylight_window,
    is_during_extended_daylight,
)


@dataclass
class ProcessedTide:
    """A processed tide with formatting and twilight info."""

    time: datetime
    height_ft: float
    height_m: float
    tide_type: str
    formatted_date: str  # "DEC 20th 2025"
    formatted_time: str  # "1:00pm"
    twilight_label: str  # "First light" or "Last light"
    twilight_time: str  # formatted time of closest twilight

    def height_display(self, metric: bool = False) -> str:
        """Get formatted height with units."""
        if metric:
            return f"{self.height_m:.2f}m"
        return f"{self.height_ft:.1f}ft"


@dataclass
class TideCard:
    """A tide card for a specific time period."""

    period_days: int
    highest_tides: list[ProcessedTide]
    lowest_tides: list[ProcessedTide]
    highest_count_limited: bool = False  # True if fewer than requested tides found
    lowest_count_limited: bool = False  # True if fewer than requested tides found


def is_outside_work_hours(dt: datetime) -> bool:
    """
    Check if a datetime is outside standard work hours (M-F 9am-5pm).

    Returns True if:
    - It's a weekend (Saturday=5, Sunday=6)
    - It's a weekday but before 9am or at/after 5pm
    """
    # Make timezone-aware if needed
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LA_JOLLA_TZ)

    weekday = dt.weekday()  # Monday=0, Sunday=6
    hour = dt.hour

    # Weekend - always outside work hours
    if weekday >= 5:
        return True

    # Weekday - check if before 9am or at/after 5pm
    return hour < 9 or hour >= 17


def _format_date(dt: datetime) -> str:
    """Format date as 'DEC 20th 2025'."""
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return dt.strftime(f"%b {day}{suffix} %Y").upper()


def _format_time(dt: datetime) -> str:
    """Format time as '1:00pm'."""
    return dt.strftime("%I:%M%p").lstrip("0").lower()


def _get_closest_twilight(tide_time: datetime, daylight: DaylightWindow) -> tuple[str, datetime]:
    """
    Get the closest twilight (first light or last light) to the tide time.

    Returns:
        Tuple of (label, twilight_time)
    """
    # Make tide_time timezone-aware if needed
    if tide_time.tzinfo is None:
        tide_time = tide_time.replace(tzinfo=LA_JOLLA_TZ)

    # Calculate distance to each twilight
    dist_to_dawn = abs((tide_time - daylight.civil_dawn).total_seconds())
    dist_to_dusk = abs((tide_time - daylight.civil_dusk).total_seconds())

    if dist_to_dawn <= dist_to_dusk:
        return ("First light", daylight.civil_dawn)
    else:
        return ("Last light", daylight.civil_dusk)


def _process_tide(prediction: TidePrediction, daylight: DaylightWindow) -> ProcessedTide:
    """Convert a tide prediction to a processed tide."""
    twilight_label, twilight_time = _get_closest_twilight(prediction.time, daylight)

    return ProcessedTide(
        time=prediction.time,
        height_ft=prediction.height_ft,
        height_m=prediction.height_m,
        tide_type=prediction.tide_type,
        formatted_date=_format_date(prediction.time),
        formatted_time=_format_time(prediction.time),
        twilight_label=twilight_label,
        twilight_time=_format_time(twilight_time),
    )


def filter_daylight_tides(
    predictions: list[TidePrediction],
) -> list[tuple[TidePrediction, DaylightWindow]]:
    """
    Filter tides to only those during extended daylight hours.

    Returns list of (prediction, daylight_window) tuples.
    """
    result = []
    daylight_cache: dict[str, DaylightWindow] = {}

    for pred in predictions:
        date_key = pred.time.strftime("%Y-%m-%d")
        if date_key not in daylight_cache:
            daylight_cache[date_key] = get_daylight_window(pred.time)

        daylight = daylight_cache[date_key]
        if is_during_extended_daylight(pred.time, daylight):
            result.append((pred, daylight))

    return result


def get_top_tides(
    predictions: list[tuple[TidePrediction, DaylightWindow]],
    tide_type: str,
    count: int = 3,
    days: int | None = None,
    start_date: datetime | None = None,
    work_filter: bool = False,
) -> list[ProcessedTide]:
    """
    Get top N highest or lowest tides.

    Args:
        predictions: List of (prediction, daylight) tuples
        tide_type: "H" for high tides, "L" for low tides
        count: Number of tides to return
        days: Filter to only tides within this many days
        start_date: Start date for the days filter
        work_filter: If True, only include tides outside M-F 9am-5pm

    Returns:
        List of ProcessedTide objects, sorted by height (desc for high, asc for low)
    """
    if start_date is None:
        start_date = datetime.now(LA_JOLLA_TZ)

    filtered = []
    for pred, daylight in predictions:
        if pred.tide_type != tide_type:
            continue

        if days is not None:
            # Make prediction time timezone-aware for comparison
            pred_time = pred.time
            if pred_time.tzinfo is None:
                pred_time = pred_time.replace(tzinfo=LA_JOLLA_TZ)

            end_date = start_date + timedelta(days=days)
            if not (start_date <= pred_time <= end_date):
                continue

        # Apply work hours filter if enabled
        if work_filter and not is_outside_work_hours(pred.time):
            continue

        filtered.append((pred, daylight))

    # Sort by height (descending for high tides, ascending for low tides)
    # Secondary sort by date (earlier first) for ties
    reverse = tide_type == "H"
    filtered.sort(key=lambda x: (-x[0].height_ft if reverse else x[0].height_ft, x[0].time))

    # Take top N and process
    return [_process_tide(pred, daylight) for pred, daylight in filtered[:count]]


async def get_tide_cards(
    start_date: datetime | None = None,
    work_filter: bool = True,
) -> list[TideCard]:
    """
    Get tide cards for 30, 60, and 90 day periods.

    Args:
        start_date: Start date for predictions (defaults to now)
        work_filter: If True (default), only include tides outside M-F 9am-5pm

    Returns:
        List of TideCard objects for each period
    """
    if start_date is None:
        start_date = datetime.now(LA_JOLLA_TZ)

    # Fetch 90 days of predictions (covers all periods)
    end_date = start_date + timedelta(days=90)
    predictions = await fetch_tide_predictions(
        begin_date=start_date,
        end_date=end_date,
    )

    # Filter to daylight tides
    daylight_tides = filter_daylight_tides(predictions)

    # Create cards for each period
    cards = []
    requested_count = 3
    for days in [30, 60, 90]:
        highest = get_top_tides(
            daylight_tides, "H",
            count=requested_count, days=days, start_date=start_date, work_filter=work_filter,
        )
        lowest = get_top_tides(
            daylight_tides, "L",
            count=requested_count, days=days, start_date=start_date, work_filter=work_filter,
        )
        cards.append(
            TideCard(
                period_days=days,
                highest_tides=highest,
                lowest_tides=lowest,
                highest_count_limited=len(highest) < requested_count,
                lowest_count_limited=len(lowest) < requested_count,
            )
        )

    return cards
