Feature: Use closest station for low tide time
  As a tidepooler
  I want low tide times from the nearest station (including subordinates)
  So that I get more accurate low tide predictions for my location

  Background:
    Given the NOAA API provides both reference and subordinate stations

  # --- Core Behavior ---

  Scenario: Subordinate station is closer than reference station
    Given I search for zip code "92054"
    And the closest reference station is "La Jolla" at 23.78 miles
    And the closest subordinate station is "San Clemente" at 21.10 miles
    When I view tide windows
    Then the window boundaries should be calculated from "La Jolla" 6-minute data
    And the low tide time and height should come from "San Clemente" high/low data

  Scenario: Reference station is closer than any subordinate
    Given I search for zip code "92037"
    And the closest reference station is "La Jolla" at 1.5 miles
    And the closest subordinate station is "San Clemente" at 25.0 miles
    When I view tide windows
    Then the window boundaries should be calculated from "La Jolla" 6-minute data
    And the low tide time and height should come from "La Jolla" 6-minute data

  Scenario: Subordinate low tide falls within window
    Given I search for zip code "92054"
    And "La Jolla" returns a window from 5:00am to 8:30am
    And "San Clemente" returns a low tide at 6:42am with height -0.3ft
    When I view that window
    Then the window should show low tide at 6:42am
    And the window should show low tide height of -0.3ft

  Scenario: Subordinate low tide does not fall within window
    Given I search for zip code "92054"
    And "La Jolla" returns a window from 5:00am to 8:30am
    And "La Jolla" 6-minute data shows minimum at 6:30am with height -0.2ft
    And "San Clemente" returns no low tide within that window
    When I view that window
    Then the window should show low tide at 6:30am from reference data
    And the window should show low tide height of -0.2ft

  # --- Distance Calculation ---

  Scenario: Distance is calculated from user location not reference station
    Given I search for zip code "92054"
    And the user location is at coordinates 33.20, -117.36
    When finding the closest station for low tide
    Then distance should be measured from 33.20, -117.36
    And not from the reference station coordinates

  # --- Caching ---

  Scenario: Subordinate station high/low predictions are cached
    Given I search for zip code "92054"
    And subordinate station "San Clemente" data is fetched
    When I search for the same location again
    Then the subordinate station data should be served from cache

  # --- No UI Change ---

  Scenario: Low tide display does not indicate source station
    Given I search for zip code "92054"
    And the low tide comes from subordinate station "San Clemente"
    When I view the window details
    Then the low tide should display as "Low: -0.3ft @ 6:42am"
    And no station name should appear next to the low tide
