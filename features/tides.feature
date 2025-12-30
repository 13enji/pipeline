Feature: Tide dashboard for Solana Beach
  As a user
  I want to see the highest and lowest daylight tides
  So that I can plan beach activities

  Background:
    Given the tide station is La Jolla, Scripps Pier (9410230)

  # --- Dashboard Display ---

  Scenario: Display tide dashboard with default settings
    When I visit the tide dashboard
    Then I should see tide cards for 30, 60, and 90 day periods
    And the units should default to Imperial (feet)
    And each card should have two columns: highest tides and lowest tides
    And each column should show the top 3 tides

  # --- Unit Toggle ---

  Scenario: Toggle to metric units
    Given I am viewing the tide dashboard in Imperial units
    When I toggle to Metric
    Then all tide heights should display in meters
    And the unit label should show "m"

  Scenario: Toggle back to imperial units
    Given I am viewing the tide dashboard in Metric units
    When I toggle to Imperial
    Then all tide heights should display in feet
    And the unit label should show "ft"

  # --- Tide Entry Display ---

  Scenario: Display tide entry with required information
    When I view a tide entry
    Then I should see the day of week and date in format "SAT DEC 20th 2025"
    And I should see the tide time in format "1:00pm" in local time
    And I should see the closest twilight time with label
    And I should see the tide height with units

  # --- Daylight Filtering ---

  Scenario: Filter tides to extended daylight hours
    Given civil twilight begins at 6:00am and ends at 8:00pm
    And there are tides at 3:00am, 5:35am, 10:00am, and 8:25pm
    When I view the tide dashboard
    Then I should see the 5:35am tide (within 30 min before civil twilight)
    And I should see the 10:00am tide
    And I should see the 8:25pm tide (within 30 min after civil twilight)
    And I should not see the 3:00am tide

  # --- First Light / Last Light Indicators ---

  Scenario: Show first light indicator for early tides near civil twilight
    Given civil twilight begins at 6:00am
    And there is a tide at 5:45am
    When I view this tide entry
    Then I should see "First light" next to the entry

  Scenario: Show last light indicator for evening tides near civil twilight
    Given civil twilight ends at 8:00pm
    And there is a tide at 8:20pm
    When I view this tide entry
    Then I should see "Last light" next to the entry

  Scenario: No indicator for mid-day tides
    Given civil twilight begins at 6:00am and ends at 8:00pm
    And there is a tide at 12:00pm
    When I view this tide entry
    Then I should not see "First light" or "Last light"

  # --- Work Hours Filter ---

  Scenario: Default to showing only tides outside work hours
    When I visit the tide dashboard
    Then the work hours filter should be ON by default
    And I should only see tides outside M-F 9am-5pm

  Scenario: Toggle to show all daylight tides
    Given I am viewing the tide dashboard with work filter ON
    When I toggle off the work hours filter
    Then I should see all daylight tides including those during work hours

  Scenario: Weekend tides always shown when filter is ON
    Given the work hours filter is ON
    And there is a daylight tide at 2pm on Saturday
    When I view the tide dashboard
    Then the Saturday 2pm tide should be visible

  Scenario: Weekday morning tide before 9am shown when filter is ON
    Given the work hours filter is ON
    And there is a daylight tide at 7am on Monday
    When I view the tide dashboard
    Then the Monday 7am tide should be visible

  Scenario: Weekday tide during work hours hidden when filter is ON
    Given the work hours filter is ON
    And there is a daylight tide at 11am on Tuesday
    When I view the tide dashboard
    Then the Tuesday 11am tide should not be visible

  Scenario: Show message when fewer than 3 tides match filter
    Given the work hours filter is ON
    And only 2 high tides match the filter in the 30-day period
    When I view the 30-day tide card
    Then I should see a message indicating fewer tides are available

  # --- Sorting ---

  Scenario: Sort tides with equal heights by date
    Given two high tides have the same height of 5.8ft
    And one occurs on January 15th and one on January 20th
    When I view the highest tides
    Then the January 15th tide should appear before the January 20th tide

  # --- Time Period Cards ---

  Scenario: 30-day card shows top 3 highest and lowest daylight tides
    When I view the 30-day tide card
    Then I should see the top 3 highest daylight tides in the next 30 days
    And I should see the top 3 lowest daylight tides in the next 30 days
    And highest tides should be in the left column
    And lowest tides should be in the right column

  Scenario: 60-day card shows top 3 highest and lowest daylight tides
    When I view the 60-day tide card
    Then I should see the top 3 highest daylight tides in the next 60 days
    And I should see the top 3 lowest daylight tides in the next 60 days

  Scenario: 90-day card shows top 3 highest and lowest daylight tides
    When I view the 90-day tide card
    Then I should see the top 3 highest daylight tides in the next 90 days
    And I should see the top 3 lowest daylight tides in the next 90 days
