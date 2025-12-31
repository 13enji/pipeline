Feature: Location-based tide windows
  As a tidepooler
  I want to find tide windows near any US location
  So that I can plan trips anywhere along the coast

  # --- Location Entry ---

  Scenario: Enter zip code to find nearest station
    Given I am on the location tide finder
    When I enter zip code "92037"
    And I submit the search
    Then I should see the nearest NOAA station name
    And I should see the distance to the station
    And I should see tide windows for that station

  Scenario: Display station distance in miles by default
    Given I have searched for zip code "92037"
    Then I should see "Station is X miles away"

  Scenario: Display station distance in kilometers when metric
    Given I have searched for zip code "92037"
    And units are set to metric
    Then I should see "Station is X km away"

  # --- Time Zone Handling ---

  Scenario: Display times in station's local timezone
    Given I have searched for a location
    When I view tide windows
    Then all times should be in the station's local timezone
    And the timezone should be displayed (e.g., "PST" or "EST")

  # --- Station Information ---

  Scenario: Show station details
    Given I have searched for zip code "92037"
    Then I should see the station name
    And I should see the station ID
    And I should see the distance from my entered location

  # --- Existing Filters Work ---

  Scenario: Threshold filter works with location
    Given I have searched for zip code "92037"
    When I set tides below to -0.5 ft
    Then I should see windows where tide stays below -0.5 ft

  Scenario: Duration filter works with location
    Given I have searched for zip code "92037"
    When I set min duration to 60 minutes
    Then all windows should last at least 60 minutes

  Scenario: Work hours filter works with location
    Given I have searched for zip code "92037"
    When work hours filter is ON
    Then I should only see windows outside M-F 9am-5pm in the station's timezone

  Scenario: Units toggle works with location
    Given I have searched for zip code "92037"
    When I toggle to metric units
    Then heights should display in meters
    And distance should display in kilometers

  # --- Error Handling ---

  Scenario: Invalid zip code
    Given I am on the location tide finder
    When I enter an invalid zip code "00000"
    And I submit the search
    Then I should see an error message
    And I should be able to try again

  Scenario: Zip code with no nearby coastal station
    Given I am on the location tide finder
    When I enter a landlocked zip code "66044"
    And I submit the search
    Then I should see the nearest station (even if far)
    And I should see the distance clearly displayed

  # --- Daylight Handling ---

  Scenario: First and last light are calculated for station location
    Given I have searched for zip code "02101"
    # Boston - different longitude than La Jolla
    When I view tide windows
    Then first and last light times should be for the station's location
    And times should be in the station's timezone
