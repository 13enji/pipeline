Feature: Landing page
  As a visitor
  I want to see a landing page at the root URL
  So that I can navigate to the main features of the app

  # --- Page Content ---

  Scenario: Landing page displays at root URL
    Given I visit the root URL
    Then I should see a landing page
    And I should see a page title "Tidepooling.org"

  Scenario: Landing page has navigation buttons
    Given I am on the landing page
    Then I should see a "Location Window" button
    And I should see a "La Jolla Window" button
    And I should see a "Tides" button
    And I should see a "Cache Stats" button

  # --- Navigation ---

  Scenario: Location Window button navigates to location page
    Given I am on the landing page
    When I click the "Location Window" button
    Then I should be on the "/location" page

  Scenario: La Jolla Window button navigates to windows page
    Given I am on the landing page
    When I click the "La Jolla Window" button
    Then I should be on the "/windows" page

  Scenario: Tides button navigates to tides page
    Given I am on the landing page
    When I click the "Tides" button
    Then I should be on the "/tides" page

  Scenario: Cache Stats button navigates to cache stats page
    Given I am on the landing page
    When I click the "Cache Stats" button
    Then I should be on the "/cache-stats" page

  # --- Styling ---

  Scenario: Landing page matches app styling
    Given I am on the landing page
    Then the page should use the same styling as other pages

  Scenario: Landing page is mobile responsive
    Given I am on the landing page on a mobile device
    Then the buttons should be stacked vertically
