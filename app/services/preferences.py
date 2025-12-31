"""User preferences service using cookies."""

import json
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response

PREFERENCES_COOKIE_NAME = "tide_preferences"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


@dataclass
class UserPreferences:
    """User's saved preferences."""

    zip_code: str = "92037"
    max_height: float = -0.5
    min_duration: int = 60
    days: int = 90
    units: str = "imperial"
    work_filter: str = "on"

    def to_dict(self) -> dict[str, Any]:
        return {
            "zip_code": self.zip_code,
            "max_height": self.max_height,
            "min_duration": self.min_duration,
            "days": self.days,
            "units": self.units,
            "work_filter": self.work_filter,
        }


def default_preferences() -> dict[str, Any]:
    """Get default preferences as a dict."""
    return UserPreferences().to_dict()


def load_preferences(request: Request) -> UserPreferences:
    """Load preferences from cookie, falling back to defaults."""
    cookie_value = request.cookies.get(PREFERENCES_COOKIE_NAME)
    if not cookie_value:
        return UserPreferences()

    try:
        data = json.loads(cookie_value)
        return UserPreferences(
            zip_code=data.get("zip_code", "92037"),
            max_height=float(data.get("max_height", -0.5)),
            min_duration=int(data.get("min_duration", 60)),
            days=int(data.get("days", 90)),
            units=data.get("units", "imperial"),
            work_filter=data.get("work_filter", "on"),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return UserPreferences()


def save_preferences(response: Response, prefs: UserPreferences) -> None:
    """Save preferences to cookie."""
    response.set_cookie(
        key=PREFERENCES_COOKIE_NAME,
        value=json.dumps(prefs.to_dict()),
        max_age=COOKIE_MAX_AGE,
        httponly=False,  # Allow JavaScript access if needed
        samesite="lax",
    )


def clear_preferences(response: Response) -> None:
    """Clear the preferences cookie."""
    response.delete_cookie(key=PREFERENCES_COOKIE_NAME)
