Feature: User Preferences
  As a user
  I want my filter settings to be remembered
  So that I don't have to re-enter them each visit

  # Preferences are stored in cookies and shared across /windows and /location
  # Settings remembered: zip code, work hours, threshold, duration, days, units

  Scenario: First visit uses defaults
    Given I have no saved preferences
    When I visit the location page
    Then I should see the default settings
    And zip code should be "92037"
    And threshold should be "-0.5"
    And min duration should be "60"
    And days should be "90"
    And units should be "imperial"
    And work hours filter should be "on"

  Scenario: Preferences saved on submit
    Given I have no saved preferences
    When I visit the location page
    And I set zip code to "94123"
    And I set threshold to "-1.0"
    And I set min duration to "30"
    And I submit the form
    Then my preferences should be saved

  Scenario: Preferences loaded on return visit
    Given I have saved preferences with zip code "94123"
    And I have saved preferences with threshold "-1.0"
    And I have saved preferences with min duration "30"
    When I visit the location page
    Then zip code should be "94123"
    And threshold should be "-1.0"
    And min duration should be "30"

  Scenario: Preferences shared between pages
    Given I have saved preferences with threshold "-1.0"
    And I have saved preferences with units "metric"
    When I visit the windows page
    Then threshold should be "-1.0"
    And units should be "metric"

  Scenario: Units preference remembered
    Given I have no saved preferences
    When I visit the location page
    And I toggle to metric units
    And I submit the form
    And I visit the windows page
    Then units should be "metric"

  Scenario: Work hours filter remembered
    Given I have no saved preferences
    When I visit the location page
    And I toggle work hours filter off
    And I submit the form
    And I visit the location page again
    Then work hours filter should be "off"

  Scenario: Days preference remembered
    Given I have no saved preferences
    When I visit the windows page
    And I set days to "60"
    And I submit the form
    And I visit the location page
    Then days should be "60"

  Scenario: Reset to defaults
    Given I have saved preferences with zip code "94123"
    And I have saved preferences with threshold "-1.0"
    When I visit the location page
    And I click reset to defaults
    Then zip code should be "92037"
    And threshold should be "-0.5"
    And my preferences should be cleared

  Scenario: Zip code not applied to windows page
    # /windows is La Jolla only, so zip code doesn't apply there
    Given I have saved preferences with zip code "94123"
    When I visit the windows page
    Then the page should load successfully
    # Zip code preference is ignored but other preferences still apply
