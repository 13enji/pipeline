Feature: Hello World
  As a user
  I want to receive a greeting from the API
  So that I can verify the service is running

  Scenario: Get greeting from hello endpoint
    When I request the hello endpoint
    Then I should receive a greeting message
    And the message should say "Hello, World"
