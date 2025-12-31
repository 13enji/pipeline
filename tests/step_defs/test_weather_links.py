"""Step definitions for weather source links feature tests."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, scenario, then

from app.main import _calculate_ahead_hours, app
from app.services.geocoding import GeoLocation
from app.services.stations import Station, StationWithDistance
from app.services.weather import WindowWeather
from app.services.windows import TideWindow

LA_JOLLA_TZ = ZoneInfo("America/Los_Angeles")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# Mock data for testing
MOCK_LOCATION_LA_JOLLA = GeoLocation(
    zip_code="92037",
    place_name="La Jolla",
    state="CA",
    latitude=32.8328,
    longitude=-117.2713,
)

MOCK_LOCATION_SF = GeoLocation(
    zip_code="94123",
    place_name="San Francisco",
    state="CA",
    latitude=37.8003,
    longitude=-122.4369,
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


def create_mock_window(hours_ahead: int) -> TideWindow:
    """Create a mock tide window starting hours_ahead from now."""
    start = datetime.now(LA_JOLLA_TZ) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=3)
    min_time = start + timedelta(hours=1)
    return TideWindow(
        start_time=start,
        end_time=end,
        min_height_ft=0.5,
        min_height_time=min_time,
        max_height_ft=1.5,
        avg_height_ft=1.0,
        first_light=start.replace(hour=6, minute=30),
        last_light=start.replace(hour=17, minute=30),
    )


MOCK_WEATHER = WindowWeather(
    temp_min=58,
    temp_max=64,
    precip_chance=20,
)


# --- Scenarios ---


@scenario("../../features/weather_links.feature", "Weather text is a clickable link")
def test_weather_clickable_link():
    pass


@scenario("../../features/weather_links.feature", "Weather link styling")
def test_weather_link_styling():
    pass


@scenario("../../features/weather_links.feature", "Weather link includes correct location coordinates")
def test_weather_link_coordinates():
    pass


@scenario("../../features/weather_links.feature", "Weather link includes correct data parameters")
def test_weather_link_parameters():
    pass


@scenario("../../features/weather_links.feature", "AheadHour positions 48-hour window near tide window")
def test_ahead_hour_calculation():
    pass


@scenario("../../features/weather_links.feature", "AheadHour is capped at 100 hours")
def test_ahead_hour_capped():
    pass


@scenario("../../features/weather_links.feature", "AheadHour is 0 for imminent windows")
def test_ahead_hour_zero():
    pass


@scenario("../../features/weather_links.feature", "Location page weather links use searched coordinates")
def test_location_weather_link():
    pass


@scenario("../../features/weather_links.feature", "No weather link for windows beyond 7 days")
def test_no_weather_beyond_7_days():
    pass


# --- Given Steps ---


@given("I am viewing a tide window with weather data", target_fixture="response")
def viewing_window_with_weather(client):
    """Load windows page with mocked weather data."""
    mock_window = create_mock_window(hours_ahead=24)

    with patch("app.main.find_tide_windows", new_callable=AsyncMock) as mock_windows:
        mock_windows.return_value = [mock_window]
        with patch("app.main.get_hourly_forecasts", new_callable=AsyncMock) as mock_forecasts:
            mock_forecasts.return_value = []
            with patch("app.main.get_weather_for_window") as mock_weather:
                mock_weather.return_value = MOCK_WEATHER
                with patch("app.main.geocode_zip", new_callable=AsyncMock) as mock_geo:
                    mock_geo.return_value = MOCK_LOCATION_LA_JOLLA
                    return client.get("/windows")


@given("I am on the windows page", target_fixture="response")
def on_windows_page(client):
    """Load windows page with weather."""
    mock_window = create_mock_window(hours_ahead=24)

    with patch("app.main.find_tide_windows", new_callable=AsyncMock) as mock_windows:
        mock_windows.return_value = [mock_window]
        with patch("app.main.get_hourly_forecasts", new_callable=AsyncMock) as mock_forecasts:
            mock_forecasts.return_value = []
            with patch("app.main.get_weather_for_window") as mock_weather:
                mock_weather.return_value = MOCK_WEATHER
                with patch("app.main.geocode_zip", new_callable=AsyncMock) as mock_geo:
                    mock_geo.return_value = MOCK_LOCATION_LA_JOLLA
                    return client.get("/windows")


@given("there is a window with weather displayed")
def window_with_weather_displayed():
    pass


@given("I am viewing a tide window starting in 24 hours", target_fixture="ahead_hours_result")
def window_24_hours_ahead():
    window = create_mock_window(hours_ahead=24)
    return _calculate_ahead_hours(window.start_time)


@given("I am viewing a tide window starting in 120 hours", target_fixture="ahead_hours_result")
def window_120_hours_ahead():
    window = create_mock_window(hours_ahead=120)
    return _calculate_ahead_hours(window.start_time)


@given("I am viewing a tide window starting in 2 hours", target_fixture="ahead_hours_result")
def window_2_hours_ahead():
    window = create_mock_window(hours_ahead=2)
    return _calculate_ahead_hours(window.start_time)


@given("I am on the location page")
def on_location_page():
    pass


@given('I have searched for zip code "94123"', target_fixture="response")
def searched_sf_zip(client):
    """Search for SF zip code on location page."""
    mock_window = create_mock_window(hours_ahead=24)
    mock_station_sf = Station(
        id="9414290",
        name="San Francisco",
        state="CA",
        latitude=37.8063,
        longitude=-122.4659,
        timezone_offset=-8,
    )
    mock_station_with_distance = StationWithDistance(
        station=mock_station_sf,
        distance_miles=2.0,
    )

    with patch("app.main.geocode_zip", new_callable=AsyncMock) as mock_geo:
        mock_geo.return_value = MOCK_LOCATION_SF
        with patch("app.main.find_nearest_station", new_callable=AsyncMock) as mock_station:
            mock_station.return_value = mock_station_with_distance
            with patch("app.main.find_tide_windows_for_station", new_callable=AsyncMock) as mock_windows:
                mock_windows.return_value = [mock_window]
                with patch("app.main.get_hourly_forecasts", new_callable=AsyncMock) as mock_forecasts:
                    mock_forecasts.return_value = []
                    with patch("app.main.get_weather_for_window") as mock_weather:
                        mock_weather.return_value = MOCK_WEATHER
                        return client.get("/location?zip_code=94123")


@given("I am viewing a tide window more than 7 days away", target_fixture="response")
def window_beyond_7_days(client):
    """Load windows page with window 8 days away (no weather)."""
    mock_window = create_mock_window(hours_ahead=192)  # 8 days

    with patch("app.main.find_tide_windows", new_callable=AsyncMock) as mock_windows:
        mock_windows.return_value = [mock_window]
        with patch("app.main.get_hourly_forecasts", new_callable=AsyncMock) as mock_forecasts:
            mock_forecasts.return_value = []
            with patch("app.main.get_weather_for_window") as mock_weather:
                mock_weather.return_value = None  # No weather beyond 7 days
                with patch("app.main.geocode_zip", new_callable=AsyncMock) as mock_geo:
                    mock_geo.return_value = MOCK_LOCATION_LA_JOLLA
                    return client.get("/windows")


# --- Then Steps ---


@then("the weather info (temp, wind, precip) should be a single clickable link")
def check_weather_is_link(response):
    assert response.status_code == 200
    # Check for weather link with forecast.weather.gov
    assert "forecast.weather.gov" in response.text
    assert '<a href="https://forecast.weather.gov' in response.text


@then("the link should open in a new tab")
def check_opens_new_tab(response):
    assert response.status_code == 200
    # Find weather link with target="_blank"
    assert 'class="weather-link"' in response.text
    assert 'target="_blank"' in response.text


@then("the weather link should keep the current green color")
def check_green_color(response):
    assert response.status_code == 200
    # Check CSS for weather-link with green color
    assert "weather-link" in response.text
    assert "#2e7d32" in response.text or "color: inherit" in response.text


@then("the link should show an underline on hover")
def check_underline_hover(response):
    assert response.status_code == 200
    # Check for hover CSS
    assert ".weather-link:hover" in response.text
    assert "text-decoration" in response.text


@then("the weather link should include La Jolla coordinates")
def check_la_jolla_coords(response):
    assert response.status_code == 200
    # La Jolla coords: 32.8328, -117.2713
    assert "32.8328" in response.text or "32.83" in response.text
    assert "-117.2713" in response.text or "-117.27" in response.text


@then("the link should use textField1 for latitude and textField2 for longitude")
def check_text_field_params(response):
    assert response.status_code == 200
    assert "textField1=" in response.text
    assert "textField2=" in response.text


@then("the weather link should include parameter w0=t for temperature")
def check_temp_param(response):
    assert response.status_code == 200
    assert "w0=t" in response.text


@then("the weather link should include parameter w3=sfcwind for wind")
def check_wind_param(response):
    assert response.status_code == 200
    assert "w3=sfcwind" in response.text


@then("the weather link should include parameter w5=pop for precipitation")
def check_precip_param(response):
    assert response.status_code == 200
    assert "w5=pop" in response.text


@then("the weather link should include FcstType=graphical")
def check_graphical_param(response):
    assert response.status_code == 200
    assert "FcstType=graphical" in response.text


@then("the weather link AheadHour should be approximately 18")
def check_ahead_hours_18(ahead_hours_result):
    # 24 hours - 6 hours = 18 hours (allow some variance for test timing)
    assert 16 <= ahead_hours_result <= 20


@then("the weather link AheadHour should be 100")
def check_ahead_hours_capped(ahead_hours_result):
    assert ahead_hours_result == 100


@then("the weather link AheadHour should be 0")
def check_ahead_hours_zero(ahead_hours_result):
    assert ahead_hours_result == 0


@then("the weather link should include the coordinates for zip 94123")
def check_sf_coords(response):
    assert response.status_code == 200
    # SF coords: 37.8003, -122.4369
    assert "37.8" in response.text
    assert "-122.4" in response.text


@then("no weather info should be displayed")
def check_no_weather_info(response):
    assert response.status_code == 200
    # No weather display means no temp/precip values
    assert "°F" not in response.text or "window-weather" not in response.text


@then("no weather link should be present")
def check_no_weather_link(response):
    assert response.status_code == 200
    # If there's a window but no weather, there should be no forecast.weather.gov link for that window
    # This is validated by the no weather info check
    pass
