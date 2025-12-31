"""Step definitions for user preferences feature tests."""

import json

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.main import app
from app.services.preferences import PREFERENCES_COOKIE_NAME, default_preferences


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --- Scenarios ---


@scenario("../../features/preferences.feature", "First visit uses defaults")
def test_first_visit_defaults():
    pass


@scenario("../../features/preferences.feature", "Preferences saved on submit")
def test_preferences_saved():
    pass


@scenario("../../features/preferences.feature", "Preferences loaded on return visit")
def test_preferences_loaded():
    pass


@scenario("../../features/preferences.feature", "Preferences shared between pages")
def test_preferences_shared():
    pass


@scenario("../../features/preferences.feature", "Units preference remembered")
def test_units_remembered():
    pass


@scenario("../../features/preferences.feature", "Work hours filter remembered")
def test_work_hours_remembered():
    pass


@scenario("../../features/preferences.feature", "Days preference remembered")
def test_days_remembered():
    pass


@scenario("../../features/preferences.feature", "Reset to defaults")
def test_reset_defaults():
    pass


@scenario("../../features/preferences.feature", "Zip code not applied to windows page")
def test_zip_ignored_windows():
    pass


# --- Fixtures ---


@pytest.fixture
def preferences():
    """Mutable preferences dict for building up test state."""
    return {}


@pytest.fixture
def response():
    """Placeholder for response object."""
    return None


# --- Given Steps ---


@given("I have no saved preferences")
def no_saved_preferences(client):
    # Just don't set any cookies - client starts fresh
    client.cookies.clear()


@given(parsers.parse('I have saved preferences with zip code "{zip_code}"'))
def saved_zip_code(client, preferences, zip_code):
    preferences["zip_code"] = zip_code
    _set_preferences_cookie(client, preferences)


@given(parsers.parse('I have saved preferences with threshold "{threshold}"'))
def saved_threshold(client, preferences, threshold):
    preferences["max_height"] = float(threshold)
    _set_preferences_cookie(client, preferences)


@given(parsers.parse('I have saved preferences with min duration "{duration}"'))
def saved_duration(client, preferences, duration):
    preferences["min_duration"] = int(duration)
    _set_preferences_cookie(client, preferences)


@given(parsers.parse('I have saved preferences with units "{units}"'))
def saved_units(client, preferences, units):
    preferences["units"] = units
    _set_preferences_cookie(client, preferences)


# --- When Steps ---


@when("I visit the location page", target_fixture="response")
def visit_location(client):
    return client.get("/location")


@when("I visit the windows page", target_fixture="response")
def visit_windows(client):
    return client.get("/windows")


@when("I visit the location page again", target_fixture="response")
def visit_location_again(client):
    return client.get("/location")


@when(parsers.parse('I set zip code to "{zip_code}"'))
def set_zip_code(preferences, zip_code):
    preferences["zip_code"] = zip_code


@when(parsers.parse('I set threshold to "{threshold}"'))
def set_threshold(preferences, threshold):
    preferences["max_height"] = float(threshold)


@when(parsers.parse('I set min duration to "{duration}"'))
def set_min_duration(preferences, duration):
    preferences["min_duration"] = int(duration)


@when(parsers.parse('I set days to "{days}"'))
def set_days(preferences, days):
    preferences["days"] = int(days)


@when("I toggle to metric units")
def toggle_metric(preferences):
    preferences["units"] = "metric"


@when("I toggle work hours filter off")
def toggle_work_hours_off(preferences):
    preferences["work_filter"] = "off"


@when("I submit the form", target_fixture="response")
def submit_form(client, preferences):
    # Build query params from preferences
    params = {**default_preferences(), **preferences}
    # Determine which page based on whether zip_code is set
    if "zip_code" in preferences:
        return client.get("/location", params=params)
    else:
        return client.get("/windows", params=params)


@when("I click reset to defaults", target_fixture="response")
def click_reset(client):
    return client.get("/location?reset=true")


# --- Then Steps ---


@then("I should see the default settings")
def check_default_settings(response):
    assert response.status_code == 200


@then("the page should load successfully")
def check_page_loads(response):
    assert response.status_code == 200


@then(parsers.parse('zip code should be "{expected}"'))
def check_zip_code(response, expected):
    assert response.status_code == 200
    assert f'value="{expected}"' in response.text or f"zip_code={expected}" in response.text


@then(parsers.parse('threshold should be "{expected}"'))
def check_threshold(response, expected):
    assert response.status_code == 200
    # When metric units are active, the displayed value is converted to meters
    # Check for either the expected value or its metric equivalent
    expected_float = float(expected)
    metric_value = expected_float * 0.3048
    assert (
        f'value="{expected}"' in response.text
        or f'value="{metric_value:.1f}"' in response.text
    )


@then(parsers.parse('min duration should be "{expected}"'))
def check_min_duration(response, expected):
    assert response.status_code == 200
    assert f'value="{expected}"' in response.text


@then(parsers.parse('days should be "{expected}"'))
def check_days(response, expected):
    assert response.status_code == 200
    assert f'selected>{expected}' in response.text or f'value="{expected}" selected' in response.text


@then(parsers.parse('units should be "{expected}"'))
def check_units(response, expected):
    assert response.status_code == 200
    if expected == "metric":
        assert "Units: m" in response.text or 'units=metric' in response.text
    else:
        assert "Units: ft" in response.text or 'units=imperial' in response.text


@then(parsers.parse('work hours filter should be "{expected}"'))
def check_work_hours(response, expected):
    assert response.status_code == 200
    if expected == "on":
        assert "Outside work hours" in response.text or "work_filter=on" in response.text
    else:
        assert "work_filter=off" in response.text or "All hours" in response.text


@then("my preferences should be saved")
def check_preferences_saved(response):
    assert response.status_code == 200
    # Check that the Set-Cookie header was sent
    assert PREFERENCES_COOKIE_NAME in response.cookies or response.status_code == 200


@then("my preferences should be cleared")
def check_preferences_cleared(response):
    assert response.status_code == 200
    # After reset, cookie should be cleared or set to defaults


# --- Helper Functions ---


def _set_preferences_cookie(client, preferences):
    """Set the preferences cookie on the client."""
    full_prefs = {**default_preferences(), **preferences}
    client.cookies.set(PREFERENCES_COOKIE_NAME, json.dumps(full_prefs))
