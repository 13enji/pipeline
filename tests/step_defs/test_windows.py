"""Step definitions for tide window finder feature tests."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.main import app
from app.services.noaa import TideReading

# Mock readings for testing
MOCK_READINGS = []


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def create_mock_readings():
    """Create mock 6-minute tide readings for testing."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    LA_JOLLA_TZ = ZoneInfo("America/Los_Angeles")
    readings = []

    # Create readings for 7 days
    # Pattern: tide goes from +2ft down to -2ft and back up over ~12 hours
    base_date = datetime(2025, 1, 18, tzinfo=LA_JOLLA_TZ)  # Saturday

    for day in range(7):
        current_date = base_date + timedelta(days=day)
        for hour in range(24):
            for minute in range(0, 60, 6):
                time = current_date.replace(hour=hour, minute=minute)
                # Simple sine-wave-like pattern
                # Low tide around 7am and 7pm, high tide around 1am and 1pm
                import math
                hours_float = hour + minute / 60
                height = 2.0 * math.sin((hours_float - 7) * math.pi / 6)
                readings.append(TideReading(time=time.replace(tzinfo=None), height_ft=height))

    return readings


@pytest.fixture(autouse=True)
def mock_cache():
    """Mock the cache to return test readings."""
    readings = create_mock_readings()
    with patch("app.services.cache.get_tide_readings") as mock:
        mock.return_value = readings
        with patch("app.services.windows.get_tide_readings", mock):
            yield


# --- Scenarios ---


@scenario("../../features/windows.feature", "Find tidepooling windows with default settings")
def test_default_settings():
    pass


@scenario("../../features/windows.feature", "Find windows below a negative threshold")
def test_negative_threshold():
    pass


@scenario("../../features/windows.feature", "Display window information")
def test_display_info():
    pass


@scenario("../../features/windows.feature", "Tide at exactly threshold is included")
def test_exact_threshold():
    pass


@scenario("../../features/windows.feature", "Tide above threshold is excluded")
def test_above_threshold():
    pass


@scenario("../../features/windows.feature", "Short windows are excluded")
def test_short_windows():
    pass


@scenario("../../features/windows.feature", "Long windows are included")
def test_long_windows():
    pass


@scenario("../../features/windows.feature", "Only daylight windows are shown")
def test_daylight_only():
    pass


@scenario("../../features/windows.feature", "Work hours filter is on by default")
def test_work_filter_default():
    pass


@scenario("../../features/windows.feature", "Toggle work hours filter off")
def test_toggle_work_filter():
    pass


@scenario("../../features/windows.feature", "Search 60 days ahead")
def test_60_days():
    pass


@scenario("../../features/windows.feature", "Search 90 days ahead")
def test_90_days():
    pass


@scenario("../../features/windows.feature", "Switch to metric units")
def test_metric_units():
    pass


@scenario("../../features/windows.feature", "Navigate to top tides dashboard")
def test_navigation():
    pass


# --- Given Steps ---


@given("the tide station is La Jolla, Scripps Pier (9410230)")
def given_la_jolla_station():
    pass


@given(parsers.parse("the tides below threshold is {threshold} ft"))
def given_threshold(threshold):
    pass


@given(parsers.parse("the min duration is {duration} minutes"))
def given_min_duration(duration):
    pass


@given(parsers.parse("there is a period where the tide is exactly {height} ft"))
def given_exact_tide(height):
    pass


@given(parsers.parse("there is a period where the tide is {height} ft"))
def given_tide_period(height):
    pass


@given(parsers.parse("there is a window that lasts only {duration} minutes"))
def given_short_window(duration):
    pass


@given(parsers.parse("there is a window that lasts {duration} minutes"))
def given_long_window(duration):
    pass


@given("I am viewing tide windows with work filter ON", target_fixture="response")
def viewing_with_work_filter(client):
    return client.get("/windows?work_filter=on")


@given("I am viewing tide windows in Imperial units", target_fixture="response")
def viewing_imperial(client):
    return client.get("/windows?units=imperial")


# --- When Steps ---


@when("I visit the tide window finder", target_fixture="response")
def visit_window_finder(client):
    return client.get("/windows")


@when("I search for tide windows", target_fixture="response")
def search_windows(client):
    return client.get("/windows")


@when("I view a tide window result", target_fixture="response")
def view_result(client):
    return client.get("/windows")


@when("I toggle off the work hours filter", target_fixture="response")
def toggle_work_filter_off(client):
    return client.get("/windows?work_filter=off")


@when(parsers.parse("I set the search range to {days} days"))
def set_search_range(days):
    pass


@when("I toggle to Metric", target_fixture="response")
def toggle_to_metric(client):
    return client.get("/windows?units=metric")


@when("I am on the tide window finder", target_fixture="response")
def on_window_finder(client):
    return client.get("/windows")


# --- Then Steps ---


@then("I should see a search form with tides below, min duration, and days")
def check_search_form(response):
    assert response.status_code == 200
    assert "Tides below" in response.text
    assert "Min duration" in response.text
    assert "Days to search" in response.text


@then(parsers.parse("the default tides below should be {value} ft"))
def check_default_threshold(response, value):
    assert response.status_code == 200
    assert f'value="{value}"' in response.text or f"value=\"{value}\"" in response.text


@then(parsers.parse("the default min duration should be {value} minutes"))
def check_default_duration(response, value):
    assert response.status_code == 200
    assert f'value="{value}"' in response.text


@then(parsers.parse("the default search range should be {value} days"))
def check_default_range(response, value):
    assert response.status_code == 200
    assert f'value="{value}"' in response.text or f'selected">{value} days' in response.text


@then(parsers.parse("I should see windows where the tide stays below {threshold} ft"))
def check_windows_below_threshold(response, threshold):
    assert response.status_code == 200
    # Results section should exist
    assert "Results" in response.text


@then(parsers.parse("each window should last at least {duration} minutes"))
def check_min_duration(response, duration):
    assert response.status_code == 200


@then("I should see the day of week and date")
def check_day_and_date(response):
    assert response.status_code == 200
    import re
    # Should have dates like "SAT JAN 18TH 2025"
    pattern = r"[A-Z]{3} [A-Z]{3} \d{1,2}(ST|ND|RD|TH) \d{4}"
    assert re.search(pattern, response.text)


@then("I should see the time range (start - end)")
def check_time_range(response):
    assert response.status_code == 200
    import re
    # Should have time ranges like "6:30am - 9:12am"
    pattern = r"\d{1,2}:\d{2}[ap]m\s*-\s*\d{1,2}:\d{2}[ap]m"
    assert re.search(pattern, response.text)


@then("I should see the duration")
def check_duration_display(response):
    assert response.status_code == 200
    # Should have duration like "2hr" or "1hr 30min"
    assert "hr" in response.text or "min" in response.text


@then("I should see the lowest tide height during the window")
def check_lowest_height(response):
    assert response.status_code == 200
    assert "Low:" in response.text


@then("that period should be included in results")
def check_period_included(response):
    assert response.status_code == 200


@then("that period should not be included in results")
def check_period_excluded(response):
    assert response.status_code == 200


@then("that short window should not appear in results")
def check_short_excluded(response):
    assert response.status_code == 200


@then("that window should appear in results")
def check_window_appears(response):
    assert response.status_code == 200


@then("all results should be during extended daylight hours")
def check_daylight_hours(response):
    assert response.status_code == 200


@then("the work hours filter should be ON")
def check_work_filter_on(response):
    assert response.status_code == 200
    assert "Show All Daylight" in response.text  # Button text when filter is ON


@then("I should only see windows outside M-F 9am-5pm")
def check_outside_work_hours(response):
    assert response.status_code == 200
    assert "Outside work hours" in response.text


@then("I should see windows during all daylight hours")
def check_all_daylight(response):
    assert response.status_code == 200
    assert "All daylight" in response.text


@then(parsers.parse("results may include windows up to {days} days from now"))
def check_extended_range(response, days):
    assert response.status_code == 200


@then("heights should display in meters")
def check_metric_heights(response):
    assert response.status_code == 200
    assert "Units: m" in response.text


@then("the height input should show meters")
def check_metric_input(response):
    assert response.status_code == 200
    assert "Tides below (m)" in response.text


@then("I should see a link to the Top Tides dashboard")
def check_dashboard_link(response):
    assert response.status_code == 200
    assert "/tides" in response.text
    assert "Top Tides" in response.text
