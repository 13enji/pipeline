import pytest
from fastapi.testclient import TestClient
from pytest_bdd import parsers, scenario, then, when

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def response():
    return {}


@scenario("../../features/hello.feature", "Get greeting from hello endpoint")
def test_hello_endpoint():
    pass


@when("I request the hello endpoint", target_fixture="response")
def request_hello(client):
    return client.get("/hello")


@then("I should receive a greeting message")
def check_response_ok(response):
    assert response.status_code == 200


@then(parsers.parse('the message should say "{expected_message}"'))
def check_message(response, expected_message):
    assert response.json()["message"] == expected_message
