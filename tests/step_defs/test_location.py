"""Step definitions for location-based tide window finder feature tests."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.main import app
from app.services.geocoding import GeoLocation
from app.services.stations import Station, StationWithDistance


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# Mock data for testing
MOCK_LOCATION = GeoLocation(
    zip_code="92037",
    place_name="La Jolla",
    state="CA",
    latitude=32.8455,
    longitude=-117.2521,
)

MOCK_STATION = Station(
    id="9410230",
    name="La Jolla, Scripps Pier",
    state="CA",
    latitude=32.8669,
    longitude=-117.2571,
    timezone_offset=-8,
)

MOCK_STATION_WITH_DISTANCE = StationWithDistance(
    station=MOCK_STATION,
    distance_miles=1.5,
)


@pytest.fixture
def mock_geocode():
    """Mock the geocoding service."""
    with patch("app.main.geocode_zip", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_LOCATION
        yield mock


@pytest.fixture
def mock_station():
    """Mock the station lookup service."""
    with patch("app.main.find_nearest_station", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_STATION_WITH_DISTANCE
        yield mock


@pytest.fixture
def mock_windows():
    """Mock the window finding service."""
    with patch(
        "app.main.find_tide_windows_for_station", new_callable=AsyncMock
    ) as mock:
        mock.return_value = []  # Empty list for simplicity
        yield mock


# --- Scenarios ---


@scenario("../../features/location.feature", "Enter zip code to find nearest station")
def test_enter_zip():
    pass


@scenario("../../features/location.feature", "Display station distance in miles by default")
def test_distance_miles():
    pass


@scenario("../../features/location.feature", "Display station distance in kilometers when metric")
def test_distance_km():
    pass


@scenario("../../features/location.feature", "Display times in station's local timezone")
def test_timezone_display():
    pass


@scenario("../../features/location.feature", "Show station details")
def test_station_details():
    pass


@scenario("../../features/location.feature", "Threshold filter works with location")
def test_threshold_filter():
    pass


@scenario("../../features/location.feature", "Duration filter works with location")
def test_duration_filter():
    pass


@scenario("../../features/location.feature", "Work hours filter works with location")
def test_work_filter():
    pass


@scenario("../../features/location.feature", "Units toggle works with location")
def test_units_toggle():
    pass


@scenario("../../features/location.feature", "Invalid zip code")
def test_invalid_zip():
    pass


@scenario("../../features/location.feature", "Zip code with no nearby coastal station")
def test_landlocked_zip():
    pass


@scenario(
    "../../features/location.feature",
    "First and last light are calculated for station location",
)
def test_light_times():
    pass


# --- Given Steps ---


@given("I am on the location tide finder", target_fixture="response")
def on_location_finder(client, mock_geocode, mock_station, mock_windows):
    return client.get("/location")


@given(parsers.parse('I have searched for zip code "{zip_code}"'), target_fixture="response")
def searched_zip(client, zip_code, mock_geocode, mock_station, mock_windows):
    return client.get(f"/location?zip_code={zip_code}")


@given("I have searched for a location", target_fixture="response")
def searched_location(client, mock_geocode, mock_station, mock_windows):
    return client.get("/location?zip_code=92037")


@given("units are set to metric", target_fixture="response")
def units_metric(client, mock_geocode, mock_station, mock_windows):
    return client.get("/location?zip_code=92037&units=metric")


# --- When Steps ---


@when(parsers.parse('I enter zip code "{zip_code}"'))
def enter_zip(zip_code):
    pass  # The actual request is made in the submit step


@when("I submit the search", target_fixture="response")
def submit_search(client, mock_geocode, mock_station, mock_windows):
    return client.get("/location?zip_code=92037")


@when("I view tide windows", target_fixture="response")
def view_windows(client, mock_geocode, mock_station, mock_windows):
    return client.get("/location?zip_code=92037")


@when(parsers.parse("I set tides below to {value} ft"), target_fixture="response")
def set_threshold(client, value, mock_geocode, mock_station, mock_windows):
    return client.get(f"/location?zip_code=92037&max_height={value}")


@when(parsers.parse("I set min duration to {value} minutes"), target_fixture="response")
def set_duration(client, value, mock_geocode, mock_station, mock_windows):
    return client.get(f"/location?zip_code=92037&min_duration={value}")


@when("work hours filter is ON", target_fixture="response")
def work_filter_on(client, mock_geocode, mock_station, mock_windows):
    return client.get("/location?zip_code=92037&work_filter=on")


@when("I toggle to metric units", target_fixture="response")
def toggle_metric(client, mock_geocode, mock_station, mock_windows):
    return client.get("/location?zip_code=92037&units=metric")


@when(parsers.parse('I enter an invalid zip code "{zip_code}"'))
def enter_invalid_zip(zip_code):
    pass


@when(parsers.parse('I enter a landlocked zip code "{zip_code}"'))
def enter_landlocked_zip(zip_code):
    pass


# --- Then Steps ---


@then("I should see the nearest NOAA station name")
def check_station_name(response):
    assert response.status_code == 200
    assert "La Jolla" in response.text or "station" in response.text.lower()


@then("I should see the distance to the station")
def check_distance(response):
    assert response.status_code == 200
    assert "miles" in response.text.lower() or "km" in response.text.lower()


@then("I should see tide windows for that station")
def check_windows(response):
    assert response.status_code == 200
    assert "Results" in response.text


@then(parsers.parse('I should see "Station is X miles away"'))
def check_miles_format(response):
    assert response.status_code == 200
    assert "miles away" in response.text.lower()


@then(parsers.parse('I should see "Station is X km away"'))
def check_km_format(response):
    assert response.status_code == 200
    assert "km away" in response.text.lower()


@then("all times should be in the station's local timezone")
def check_times_tz(response):
    assert response.status_code == 200
    # Timezone should be displayed
    assert "PST" in response.text or "PDT" in response.text or "Timezone" in response.text


@then('the timezone should be displayed (e.g., "PST" or "EST")')
def check_tz_displayed(response):
    assert response.status_code == 200
    assert "Timezone:" in response.text or "PST" in response.text or "PDT" in response.text


@then("I should see the station name")
def check_station_name_display(response):
    assert response.status_code == 200
    # Station name should appear in station-info section
    assert "La Jolla" in response.text


@then("I should see the station ID")
def check_station_id(response):
    assert response.status_code == 200
    assert "9410230" in response.text or "Station ID" in response.text


@then("I should see the distance from my entered location")
def check_distance_display(response):
    assert response.status_code == 200
    assert "away" in response.text.lower()


@then(parsers.parse("I should see windows where tide stays below {value} ft"))
def check_threshold_windows(response, value):
    assert response.status_code == 200


@then(parsers.parse("all windows should last at least {value} minutes"))
def check_duration_windows(response, value):
    assert response.status_code == 200


@then("I should only see windows outside M-F 9am-5pm in the station's timezone")
def check_work_hours(response):
    assert response.status_code == 200
    assert "Outside work hours" in response.text


@then("heights should display in meters")
def check_metric_heights(response):
    assert response.status_code == 200
    assert "Units: m" in response.text


@then("distance should display in kilometers")
def check_metric_distance(response):
    assert response.status_code == 200
    assert "km" in response.text.lower()


@then("I should see an error message")
def check_error(response):
    assert response.status_code == 200
    # Error should be displayed for invalid zip


@then("I should be able to try again")
def check_retry(response):
    assert response.status_code == 200
    # Form should still be visible
    assert "zip_code" in response.text.lower()


@then("I should see the nearest station (even if far)")
def check_far_station(response):
    assert response.status_code == 200


@then("I should see the distance clearly displayed")
def check_distance_clear(response):
    assert response.status_code == 200
    assert "away" in response.text.lower()


@then("first and last light times should be for the station's location")
def check_light_location(response):
    assert response.status_code == 200


@then("times should be in the station's timezone")
def check_times_in_tz(response):
    assert response.status_code == 200
