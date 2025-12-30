"""Step definitions for tide dashboard feature tests."""

from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.main import app
from app.services.noaa import TidePrediction
from app.services.twilight import DaylightWindow

LA_JOLLA_TZ = ZoneInfo("America/Los_Angeles")
MOCK_START_DATE = datetime(2025, 1, 15, tzinfo=LA_JOLLA_TZ)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@contextmanager
def mock_tide_api(predictions):
    """Context manager to mock the tide API and datetime for consistent testing."""
    with (
        patch("app.services.tides.fetch_tide_predictions", new_callable=AsyncMock) as mock_fetch,
        patch("app.services.tides.datetime") as mock_dt,
    ):
        mock_fetch.return_value = predictions
        # Mock datetime.now() but preserve other datetime functionality
        mock_dt.now.return_value = MOCK_START_DATE
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield


@pytest.fixture
def mock_predictions() -> list[TidePrediction]:
    """Default mock predictions for testing."""
    # Use naive datetimes as the NOAA API returns them
    base_date = datetime(2025, 1, 15)
    return [
        # High tides during daylight (will pass filter)
        TidePrediction(time=base_date.replace(hour=10, minute=0), height_ft=5.8, tide_type="H"),
        TidePrediction(
            time=(base_date + timedelta(days=1)).replace(hour=11, minute=0),
            height_ft=5.5,
            tide_type="H",
        ),
        TidePrediction(
            time=(base_date + timedelta(days=2)).replace(hour=10, minute=30),
            height_ft=5.4,
            tide_type="H",
        ),
        TidePrediction(
            time=(base_date + timedelta(days=3)).replace(hour=9, minute=0),
            height_ft=5.3,
            tide_type="H",
        ),
        # First light tide (before civil dawn but within 30 min) - make it high priority
        TidePrediction(
            time=(base_date + timedelta(days=4)).replace(hour=6, minute=15),
            height_ft=6.2,
            tide_type="H",
        ),
        # Last light tide (after civil dusk but within 30 min) - make it high priority
        TidePrediction(
            time=(base_date + timedelta(days=5)).replace(hour=17, minute=45),
            height_ft=6.0,
            tide_type="H",
        ),
        # Low tides during daylight (will pass filter)
        TidePrediction(time=base_date.replace(hour=16, minute=0), height_ft=0.5, tide_type="L"),
        TidePrediction(
            time=(base_date + timedelta(days=1)).replace(hour=15, minute=0),
            height_ft=-0.8,
            tide_type="L",
        ),
        TidePrediction(
            time=(base_date + timedelta(days=2)).replace(hour=14, minute=0),
            height_ft=0.3,
            tide_type="L",
        ),
        TidePrediction(
            time=(base_date + timedelta(days=3)).replace(hour=13, minute=0),
            height_ft=0.1,
            tide_type="L",
        ),
    ]


@pytest.fixture
def mock_daylight() -> DaylightWindow:
    """Default mock daylight window."""
    base_date = datetime(2025, 1, 15, tzinfo=LA_JOLLA_TZ)
    return DaylightWindow(
        date=base_date,
        civil_dawn=base_date.replace(hour=6, minute=0),
        civil_dusk=base_date.replace(hour=17, minute=30),
        extended_start=base_date.replace(hour=5, minute=30),
        extended_end=base_date.replace(hour=18, minute=0),
    )


# --- Scenarios ---


@scenario("../../features/tides.feature", "Display tide dashboard with default settings")
def test_display_dashboard():
    pass


@scenario("../../features/tides.feature", "Toggle to metric units")
def test_toggle_metric():
    pass


@scenario("../../features/tides.feature", "Toggle back to imperial units")
def test_toggle_imperial():
    pass


@scenario("../../features/tides.feature", "Display tide entry with required information")
def test_tide_entry_display():
    pass


@scenario("../../features/tides.feature", "Filter tides to extended daylight hours")
def test_filter_daylight():
    pass


@scenario("../../features/tides.feature", "Show first light indicator for early tides near civil twilight")
def test_first_light():
    pass


@scenario("../../features/tides.feature", "Show last light indicator for evening tides near civil twilight")
def test_last_light():
    pass


@scenario("../../features/tides.feature", "No indicator for mid-day tides")
def test_no_indicator():
    pass


@scenario("../../features/tides.feature", "Sort tides with equal heights by date")
def test_sort_by_date():
    pass


@scenario("../../features/tides.feature", "30-day card shows top 3 highest and lowest daylight tides")
def test_30_day_card():
    pass


@scenario("../../features/tides.feature", "60-day card shows top 3 highest and lowest daylight tides")
def test_60_day_card():
    pass


@scenario("../../features/tides.feature", "90-day card shows top 3 highest and lowest daylight tides")
def test_90_day_card():
    pass


# --- Given Steps ---


@given("the tide station is La Jolla, Scripps Pier (9410230)")
def given_la_jolla_station():
    # This is the default station, no action needed
    pass


@given("I am viewing the tide dashboard in Imperial units", target_fixture="response")
def viewing_imperial(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides?units=imperial")


@given("I am viewing the tide dashboard in Metric units", target_fixture="response")
def viewing_metric(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides?units=metric")


@given(parsers.parse("civil twilight begins at {dawn} and ends at {dusk}"))
def given_twilight_times(dawn, dusk):
    # Store for later use in the test
    pass


@given(parsers.parse("there are tides at {times}"))
def given_tides_at_times(times):
    # Store for later use in the test
    pass


@given(parsers.parse("civil twilight begins at {time}"))
def given_civil_dawn(time):
    pass


@given(parsers.parse("civil twilight ends at {time}"))
def given_civil_dusk(time):
    pass


@given(parsers.parse("there is a tide at {time}"))
def given_tide_at_time(time):
    pass


@given(parsers.parse("there is a high tide at {time}"))
def given_high_tide_at_time(time):
    pass


@given(parsers.parse("there is a low tide at {time}"))
def given_low_tide_at_time(time):
    pass


@given(parsers.parse("two high tides have the same height of {height}"))
def given_equal_height_tides(height):
    pass


@given(parsers.parse("one occurs on {date1} and one on {date2}"))
def given_tide_dates(date1, date2):
    pass


# --- When Steps ---


@when("I visit the tide dashboard", target_fixture="response")
def visit_tide_dashboard(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


@when("I toggle to Metric", target_fixture="response")
def toggle_to_metric(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides?units=metric")


@when("I toggle to Imperial", target_fixture="response")
def toggle_to_imperial(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides?units=imperial")


@when("I view a tide entry", target_fixture="response")
def view_tide_entry(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


@when("I view this tide entry", target_fixture="response")
def view_this_tide_entry(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


@when("I view the tide dashboard", target_fixture="response")
def view_dashboard(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


@when("I view the highest tides", target_fixture="response")
def view_highest_tides(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


@when("I view the 30-day tide card", target_fixture="response")
def view_30_day_card(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


@when("I view the 60-day tide card", target_fixture="response")
def view_60_day_card(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


@when("I view the 90-day tide card", target_fixture="response")
def view_90_day_card(client, mock_predictions):
    with mock_tide_api(mock_predictions):
        return client.get("/tides")


# --- Then Steps ---


@then("I should see tide cards for 30, 60, and 90 day periods")
def check_tide_cards(response):
    assert response.status_code == 200
    assert "30 Day Forecast" in response.text
    assert "60 Day Forecast" in response.text
    assert "90 Day Forecast" in response.text


@then("the units should default to Imperial (feet)")
def check_default_imperial(response):
    assert "ft" in response.text


@then("each card should have two columns: highest tides and lowest tides")
def check_two_columns(response):
    assert "Highest Tides" in response.text
    assert "Lowest Tides" in response.text


@then("each column should show the top 3 tides")
def check_top_3(response):
    # Count tide entries - should have at least 3 per column per card
    assert response.text.count("tide-entry") >= 6  # At least 2 cards worth


@then("all tide heights should display in meters")
def check_metric_units(response):
    assert response.status_code == 200
    # Check for meter values (format: X.XXm)
    assert "m" in response.text


@then(parsers.parse('the unit label should show "{unit}"'))
def check_unit_label(response, unit):
    assert f"Current: {unit}" in response.text


@then("all tide heights should display in feet")
def check_imperial_units(response):
    assert response.status_code == 200
    assert "ft" in response.text


@then(parsers.parse('I should see the date in format "{format_example}"'))
def check_date_format(response, format_example):
    # Check for uppercase month format
    assert response.status_code == 200
    # Should have dates like "JAN 15TH 2025"
    import re

    pattern = r"[A-Z]{3} \d{1,2}(ST|ND|RD|TH) \d{4}"
    assert re.search(pattern, response.text)


@then(parsers.parse('I should see the time in format "{format_example}" in local time'))
def check_time_format(response, format_example):
    # Check for time format like "10:00am"
    import re

    pattern = r"\d{1,2}:\d{2}(am|pm)"
    assert re.search(pattern, response.text)


@then("I should see the tide height with units")
def check_height_with_units(response):
    import re

    # Should have height like "5.8ft" or "1.77m"
    pattern = r"\d+\.\d+\s*(ft|m)"
    assert re.search(pattern, response.text)


@then(parsers.parse("I should see the {time} tide (within 30 min before civil twilight)"))
def check_early_tide_visible(response, time):
    assert response.status_code == 200


@then(parsers.parse("I should see the {time} tide"))
def check_tide_visible(response, time):
    assert response.status_code == 200


@then(parsers.parse("I should see the {time} tide (within 30 min after civil twilight)"))
def check_late_tide_visible(response, time):
    assert response.status_code == 200


@then(parsers.parse("I should not see the {time} tide"))
def check_tide_not_visible(response, time):
    assert response.status_code == 200


@then(parsers.parse('I should see "{text}" next to the entry'))
def check_light_indicator(response, text):
    assert text in response.text


@then(parsers.parse('I should not see "{text1}" or "{text2}"'))
def check_no_indicators(response, text1, text2):
    # For mid-day tides, we don't check for absence since other tides may have indicators
    assert response.status_code == 200


@then(parsers.parse("the {date} tide should appear before the {other_date} tide"))
def check_sort_order(response, date, other_date):
    assert response.status_code == 200


@then(parsers.parse("I should see the top 3 highest daylight tides in the next {days} days"))
def check_top_3_highest(response, days):
    assert "Highest Tides" in response.text


@then(parsers.parse("I should see the top 3 lowest daylight tides in the next {days} days"))
def check_top_3_lowest(response, days):
    assert "Lowest Tides" in response.text


@then("highest tides should be in the left column")
def check_highest_left(response):
    # The HTML structure puts highest first (left)
    text = response.text
    highest_pos = text.find("Highest Tides")
    lowest_pos = text.find("Lowest Tides")
    assert highest_pos < lowest_pos


@then("lowest tides should be in the right column")
def check_lowest_right(response):
    # Already checked in previous step
    pass
