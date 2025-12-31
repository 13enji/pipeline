Feature: Weather Integration
  As a user
  I want to see weather forecasts for tide windows
  So that I can plan activities knowing the conditions

  # Weather data from NWS API (Weather.gov)
  # Shows temperature range and precipitation chance for each window
  # Only available for windows within 7 days
  # Uses zip code coordinates (default 92037 for /windows)

  Background:
    Given the weather service is available

  # --- Temperature Display ---

  Scenario: Weather shown for windows within 7 days
    Given I am viewing tide windows
    And there is a window within the next 7 days
    When the page loads
    Then I should see a temperature range for that window
    And I should see a precipitation chance for that window

  Scenario: Temperature range reflects window hours
    Given I am viewing tide windows
    And there is a window from 2pm to 5pm
    When the page loads
    Then the temperature range should be the min and max during those hours
    And not the daily high and low

  Scenario: No weather for windows beyond 7 days
    Given I am viewing tide windows
    And there is a window more than 7 days away
    When the page loads
    Then that window should not display weather information

  # --- Precipitation Display ---

  Scenario: Precipitation chance shown as percentage
    Given I am viewing tide windows
    And there is a window within the next 7 days
    When the page loads
    Then I should see precipitation displayed as a percentage

  # --- Location Behavior ---

  Scenario: Windows page uses default location for weather
    Given I am on the windows page
    When the page loads with windows in the next 7 days
    Then weather should be fetched for La Jolla coordinates

  Scenario: Location page uses zip code for weather
    Given I am on the location page
    And I have entered zip code "94123"
    When the page loads with windows in the next 7 days
    Then weather should be fetched for the zip code coordinates

  # --- Error Handling ---

  Scenario: Weather API failure shows windows without weather
    Given I am viewing tide windows
    And the weather service is unavailable
    When the page loads
    Then I should still see the tide windows
    And weather information should not be displayed
    And no error message should be shown

  # --- Caching ---

  Scenario: Weather data is cached briefly
    Given I am viewing tide windows
    And weather was fetched less than 60 minutes ago for this location
    When the page loads
    Then cached weather data should be used
    And no new API call should be made

  Scenario: Stale weather cache is refreshed
    Given I am viewing tide windows
    And weather was fetched more than 60 minutes ago for this location
    When the page loads
    Then fresh weather data should be fetched

  # --- Display Format ---

  Scenario: Weather displays inline with window
    Given I am viewing tide windows
    And there is a window on Saturday from 2pm to 5pm
    And the temperature during that time ranges from 58 to 64 degrees
    And the precipitation chance is 20%
    When the page loads
    Then I should see "58-64°F" near that window entry
    And I should see "20% rain" near that window entry
