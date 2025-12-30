from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_time():
    return {}


# Scenarios


@scenario("../../features/greeting.feature", "Display name input form")
def test_display_form():
    pass


@scenario("../../features/greeting.feature", "Morning greeting (6am - 12pm)")
def test_morning_greeting():
    pass


@scenario("../../features/greeting.feature", "Afternoon greeting (12pm - 6pm)")
def test_afternoon_greeting():
    pass


@scenario("../../features/greeting.feature", "Evening greeting (6pm - 10pm)")
def test_evening_greeting():
    pass


@scenario("../../features/greeting.feature", "Late night greeting (10pm - 6am)")
def test_late_night_greeting():
    pass


@scenario("../../features/greeting.feature", "Empty name defaults to anonymous")
def test_empty_name():
    pass


# Steps


@when("I visit the greeting page", target_fixture="response")
def visit_greeting_page(client):
    return client.get("/greet")


@then("I should see a form prompting for my name")
def check_form_exists(response):
    assert response.status_code == 200
    assert "<form" in response.text
    assert "name" in response.text.lower()


@given(parsers.parse("the server time is {time}"), target_fixture="mock_time")
def set_server_time(time):
    # Parse time like "9:00am" or "2:00pm"
    time_str = time.lower().replace(" ", "")
    if "am" in time_str:
        hour = int(time_str.replace("am", "").split(":")[0])
        if hour == 12:
            hour = 0
    else:
        hour = int(time_str.replace("pm", "").split(":")[0])
        if hour != 12:
            hour += 12
    return datetime(2024, 1, 1, hour, 0, 0)


@when(parsers.parse('I submit the name "{name}"'), target_fixture="response")
def submit_name(client, name, mock_time):
    with patch("app.main.get_current_time", return_value=mock_time):
        return client.post("/greet", data={"name": name})


@when('I submit the name ""', target_fixture="response")
def submit_empty_name(client, mock_time):
    with patch("app.main.get_current_time", return_value=mock_time):
        return client.post("/greet", data={"name": ""})


@then(parsers.parse('I should see "{expected_text}"'))
def check_greeting_text(response, expected_text):
    assert response.status_code == 200
    assert expected_text in response.text
