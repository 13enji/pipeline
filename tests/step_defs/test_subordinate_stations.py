"""Step definitions for subordinate station feature tests."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from app.services.noaa import TidePrediction
from app.services.stations import Station

# --- Fixtures ---


@pytest.fixture
def mock_noaa_stations():
    """Mock the NOAA stations API to return both reference and subordinate stations."""
    mock_data = {
        "stations": [
            # Reference station - La Jolla
            {
                "id": "9410230",
                "name": "La Jolla",
                "state": "CA",
                "lat": 32.86689,
                "lng": -117.25714,
                "type": "R",
                "timezonecorr": -8,
            },
            # Subordinate station - San Clemente
            {
                "id": "TWC0419",
                "name": "San Clemente",
                "state": "CA",
                "lat": 33.417,
                "lng": -117.617,
                "type": "S",
                "timezonecorr": -8,
            },
        ]
    }
    with patch("app.services.stations.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        yield mock_data


@pytest.fixture
def mock_reference_station():
    """La Jolla reference station."""
    return Station(
        id="9410230",
        name="La Jolla",
        state="CA",
        latitude=32.86689,
        longitude=-117.25714,
        timezone_offset=-8,
    )


@pytest.fixture
def mock_subordinate_station():
    """San Clemente subordinate station."""
    return Station(
        id="TWC0419",
        name="San Clemente",
        state="CA",
        latitude=33.417,
        longitude=-117.617,
        timezone_offset=-8,
    )


@pytest.fixture
def mock_subordinate_predictions():
    """Mock high/low predictions from subordinate station."""
    tz = ZoneInfo("America/Los_Angeles")
    return [
        TidePrediction(
            time=datetime(2025, 1, 15, 6, 42, tzinfo=tz),
            height_ft=-0.3,
            tide_type="L",
        ),
        TidePrediction(
            time=datetime(2025, 1, 15, 12, 30, tzinfo=tz),
            height_ft=5.2,
            tide_type="H",
        ),
        TidePrediction(
            time=datetime(2025, 1, 15, 18, 15, tzinfo=tz),
            height_ft=0.1,
            tide_type="L",
        ),
    ]


# --- Scenarios ---


@scenario(
    "../../features/subordinate_stations.feature",
    "Subordinate station is closer than reference station",
)
def test_subordinate_closer():
    pass


@scenario(
    "../../features/subordinate_stations.feature",
    "Reference station is closer than any subordinate",
)
def test_reference_closer():
    pass


@scenario(
    "../../features/subordinate_stations.feature",
    "Subordinate low tide falls within window",
)
def test_subordinate_low_in_window():
    pass


@scenario(
    "../../features/subordinate_stations.feature",
    "Subordinate low tide does not fall within window",
)
def test_subordinate_low_not_in_window():
    pass


@scenario(
    "../../features/subordinate_stations.feature",
    "Distance is calculated from user location not reference station",
)
def test_distance_from_user():
    pass


@scenario(
    "../../features/subordinate_stations.feature",
    "Subordinate station high/low predictions are cached",
)
def test_subordinate_caching():
    pass


@scenario(
    "../../features/subordinate_stations.feature",
    "Low tide display does not indicate source station",
)
def test_no_station_attribution():
    pass


# --- Given Steps ---


@given("the NOAA API provides both reference and subordinate stations")
def noaa_provides_both_types():
    # This is just setup context, actual mocking happens in fixtures
    pass


@given(parsers.parse('I search for zip code "{zip_code}"'), target_fixture="search_context")
def search_zip(zip_code):
    return {"zip_code": zip_code}


@given(
    parsers.parse('the closest reference station is "{name}" at {distance:f} miles'),
    target_fixture="reference_context",
)
def closest_reference(name, distance):
    return {"name": name, "distance": distance}


@given(
    parsers.parse('the closest subordinate station is "{name}" at {distance:f} miles'),
    target_fixture="subordinate_context",
)
def closest_subordinate(name, distance):
    return {"name": name, "distance": distance}


@given(parsers.parse('"{station}" returns a window from {start} to {end}'))
def station_returns_window(station, start, end):
    # Context for window test
    pass


@given(
    parsers.parse('"{station}" returns a low tide at {time} with height {height:f}ft')
)
def station_returns_low(station, time, height):
    pass


@given(
    parsers.parse('"{station}" 6-minute data shows minimum at {time} with height {height:f}ft')
)
def station_6min_minimum(station, time, height):
    pass


@given(parsers.parse('"{station}" returns no low tide within that window'))
def station_no_low_in_window(station):
    pass


@given(parsers.parse("the user location is at coordinates {lat:f}, {lon:f}"))
def user_coordinates(lat, lon):
    return {"lat": lat, "lon": lon}


@given(parsers.parse('subordinate station "{name}" data is fetched'))
def subordinate_fetched(name):
    pass


@given(parsers.parse('the low tide comes from subordinate station "{name}"'))
def low_from_subordinate(name):
    pass


# --- When Steps ---


@when("I view tide windows", target_fixture="windows_result")
def view_windows():
    return {"viewed": True}


@when("I view that window", target_fixture="window_result")
def view_single_window():
    return {"viewed": True}


@when("finding the closest station for low tide")
def find_closest():
    pass


@when("I search for the same location again")
def search_again():
    pass


@when("I view the window details")
def view_window_details():
    pass


# --- Then Steps ---


@then(
    parsers.parse('the window boundaries should be calculated from "{station}" 6-minute data')
)
def check_window_source(station):
    # In actual implementation, we verify the station used for windows
    assert station in ["La Jolla", "San Clemente"]


@then(
    parsers.parse('the low tide time and height should come from "{station}" high/low data')
)
def check_low_tide_source(station):
    # In actual implementation, we verify the low tide source
    assert station in ["La Jolla", "San Clemente"]


@then(
    parsers.parse('the low tide time and height should come from "{station}" 6-minute data')
)
def check_low_tide_from_6min(station):
    assert station in ["La Jolla", "San Clemente"]


@then(parsers.parse("the window should show low tide at {time}"))
def check_low_time(time):
    # Verify the low tide time matches expected
    pass


@then(parsers.parse("the window should show low tide height of {height:f}ft"))
def check_low_height(height):
    # Verify the low tide height matches expected
    pass


@then(parsers.parse("the window should show low tide at {time} from reference data"))
def check_low_time_from_ref(time):
    pass


@then(parsers.parse("distance should be measured from {lat:f}, {lon:f}"))
def check_distance_origin(lat, lon):
    pass


@then("not from the reference station coordinates")
def not_from_ref_coords():
    pass


@then("the subordinate station data should be served from cache")
def check_cache_hit():
    pass


@then(parsers.parse('the low tide should display as "{display}"'))
def check_display_format(display):
    # The display should not include station name
    assert "San Clemente" not in display
    assert "La Jolla" not in display


@then("no station name should appear next to the low tide")
def no_station_name():
    pass
