Feature: Tide window finder for tidepooling
  As a tidepooler
  I want to find windows when the tide is below a threshold
  So that I can plan tidepooling trips

  Background:
    Given the tide station is La Jolla, Scripps Pier (9410230)

  # --- Basic Window Finding ---

  Scenario: Find tidepooling windows with default settings
    When I visit the tide window finder
    Then I should see a search form with tides below, min duration, and days
    And the default tides below should be -0.5 ft
    And the default min duration should be 60 minutes
    And the default search range should be 90 days

  Scenario: Find windows below a negative threshold
    Given the tides below threshold is -1.0 ft
    And the min duration is 60 minutes
    When I search for tide windows
    Then I should see windows where the tide stays below -1.0 ft
    And each window should last at least 60 minutes

  Scenario: Display window information
    When I view a tide window result
    Then I should see the day of week and date
    And I should see the time range (start - end)
    And I should see the duration
    And I should see the lowest tide height during the window
    And I should see the relevant light time (first or last)

  # --- Threshold Behavior ---

  Scenario: Tide at exactly threshold is included
    Given the tides below threshold is -1.0 ft
    And there is a period where the tide is exactly -1.0 ft
    When I search for tide windows
    Then that period should be included in results

  Scenario: Tide above threshold is excluded
    Given the tides below threshold is -1.0 ft
    And there is a period where the tide is -0.5 ft
    When I search for tide windows
    Then that period should not be included in results

  # --- Duration Filtering ---

  Scenario: Short windows are excluded
    Given the min duration is 60 minutes
    And there is a window that lasts only 30 minutes
    When I search for tide windows
    Then that short window should not appear in results

  Scenario: Long windows are included
    Given the min duration is 60 minutes
    And there is a window that lasts 120 minutes
    When I search for tide windows
    Then that window should appear in results

  # --- Daylight Filtering and Light Times ---

  Scenario: Morning window shows first light
    Given a tide window in the morning
    When I view that window in results
    Then I should see first light time (not last light)

  Scenario: Evening window shows last light
    Given a tide window in the evening
    When I view that window in results
    Then I should see last light time (not first light)

  Scenario: Window with sufficient daylight overlap is included
    # Daylight portion (6:00am-9:00am = 180 min) exceeds min duration
    Given a tide window from 5:00am to 9:00am
    And first light is at 6:00am on that day
    And the min duration is 60 minutes
    When I search for tide windows
    Then that window should be included

  Scenario: Window with insufficient daylight overlap is excluded
    # Daylight portion (6:00am-6:30am = 30 min) is less than min duration
    Given a tide window from 4:00am to 6:30am
    And first light is at 6:00am on that day
    And the min duration is 60 minutes
    When I search for tide windows
    Then that window should not be included

  Scenario: Window completely outside daylight is excluded
    Given a tide window from 3:00am to 5:00am
    And first light is at 6:00am on that day
    When I search for tide windows
    Then that window should not be included

  Scenario: Show full window time even when extending past daylight
    Given a tide window from 5:00am to 9:00am
    And first light is at 6:00am on that day
    When I view that window in results
    Then the time range should show "5:00am - 9:00am"
    And it should show "First light: 6:00am"

  # --- Work Hours Filter ---

  Scenario: Work hours filter is on by default
    When I visit the tide window finder
    Then the work hours filter should be ON
    And I should only see windows outside M-F 9am-5pm

  Scenario: Toggle work hours filter off
    Given I am viewing tide windows with work filter ON
    When I toggle off the work hours filter
    Then I should see windows during all daylight hours

  # --- Search Options ---

  Scenario: Search 60 days ahead
    When I set the search range to 60 days
    And I search for tide windows
    Then results may include windows up to 60 days from now

  Scenario: Search 90 days ahead
    When I set the search range to 90 days
    And I search for tide windows
    Then results may include windows up to 90 days from now

  # --- Units Toggle ---

  Scenario: Switch to metric units
    Given I am viewing tide windows in Imperial units
    When I toggle to Metric
    Then heights should display in meters
    And the height input should show meters

  # --- Navigation ---

  Scenario: Navigate to top tides dashboard
    When I am on the tide window finder
    Then I should see a link to the Top Tides dashboard
