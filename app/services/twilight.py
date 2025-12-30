"""Twilight calculation service using astral library."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun

# La Jolla location for twilight calculations
LA_JOLLA_LOCATION = LocationInfo(
    name="La Jolla",
    region="California",
    timezone="America/Los_Angeles",
    latitude=32.8669,
    longitude=-117.2571,
)

LA_JOLLA_TZ = ZoneInfo("America/Los_Angeles")

# Extended daylight window: 30 minutes before/after civil twilight
TWILIGHT_EXTENSION_MINUTES = 30


@dataclass
class DaylightWindow:
    """Daylight window for a specific date."""

    date: datetime
    civil_dawn: datetime  # Civil twilight begins (sun 6° below horizon)
    civil_dusk: datetime  # Civil twilight ends
    extended_start: datetime  # 30 min before civil dawn
    extended_end: datetime  # 30 min after civil dusk


def get_daylight_window(date: datetime) -> DaylightWindow:
    """
    Get the daylight window for a specific date at La Jolla.

    Args:
        date: The date to calculate daylight for

    Returns:
        DaylightWindow with civil twilight times and extended window
    """
    s = sun(LA_JOLLA_LOCATION.observer, date=date.date(), tzinfo=LA_JOLLA_TZ)

    civil_dawn = s["dawn"]
    civil_dusk = s["dusk"]

    extension = timedelta(minutes=TWILIGHT_EXTENSION_MINUTES)

    return DaylightWindow(
        date=date,
        civil_dawn=civil_dawn,
        civil_dusk=civil_dusk,
        extended_start=civil_dawn - extension,
        extended_end=civil_dusk + extension,
    )


def is_during_extended_daylight(time: datetime, daylight: DaylightWindow) -> bool:
    """Check if a time falls within the extended daylight window."""
    # Make time timezone-aware if it isn't
    if time.tzinfo is None:
        time = time.replace(tzinfo=LA_JOLLA_TZ)
    return daylight.extended_start <= time <= daylight.extended_end


def get_light_indicator(time: datetime, daylight: DaylightWindow) -> str | None:
    """
    Get the light indicator for a tide time.

    Returns:
        "First light" if before civil dawn
        "Last light" if after civil dusk
        None if during full daylight
    """
    # Make time timezone-aware if it isn't
    if time.tzinfo is None:
        time = time.replace(tzinfo=LA_JOLLA_TZ)

    if daylight.extended_start <= time < daylight.civil_dawn:
        return "First light"
    elif daylight.civil_dusk < time <= daylight.extended_end:
        return "Last light"
    return None
