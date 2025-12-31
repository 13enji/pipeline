Feature: NOAA source data links
  As a tidepooler
  I want to see links to NOAA tide prediction pages
  So that I can verify the data and see more details

  # --- Tides Page ---

  Scenario: Tides page has link to NOAA predictions
    Given I am on the tides page
    Then I should see a link to NOAA tide predictions
    And the link should include the La Jolla station ID "9410230"
    And the link should include a 31-day date range starting from today

  # --- Windows Page ---

  Scenario: Each window has a link to NOAA for that day
    Given I am on the windows page
    And there are tide windows displayed
    Then each window should have a NOAA link below it
    And the NOAA link should include the La Jolla station ID "9410230"
    And the NOAA link should include the date of that window

  # --- Location Page ---

  Scenario: Location windows have links to NOAA for that station and day
    Given I have searched for a zip code on the location page
    And there are tide windows displayed
    Then each window should have a NOAA link below it
    And the NOAA link should include the station ID for the found station
    And the NOAA link should include the date of that window

  # --- Link Format ---

  Scenario: NOAA links open in new tab
    Given I am viewing any page with NOAA links
    Then the NOAA links should open in a new tab
