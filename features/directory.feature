Feature: Tidepooling Locations Directory
  As a user looking for tidepooling spots
  I want to browse a directory of locations on a map
  So that I can find and learn about places to visit

  Background:
    Given the tidepooling locations data is loaded

  # Directory Page - Map
  Scenario: Directory page shows a map with location markers
    When I visit the directory page
    Then I should see a full-width map at the top
    And the map should show markers for locations with coordinates
    And locations without coordinates should not appear on the map

  Scenario: Clicking a map marker shows a popup
    When I visit the directory page
    And I click on a location marker
    Then I should see a popup with the location name
    And the popup should have a link to the location detail page

  # Directory Page - List
  Scenario: Directory page shows a list of all locations
    When I visit the directory page
    Then I should see a list of all locations below the map
    And each location in the list should show its name and city
    And each location should link to its detail page

  Scenario: Locations without coordinates appear in the list
    When I visit the directory page
    Then locations without coordinates should appear in the list
    And they should be visually distinguished from mapped locations

  # Location Detail Page
  Scenario: Location detail page shows all location information
    When I visit the location page for "shell-beach-la-jolla"
    Then I should see the location name "Shell Beach"
    And I should see the description
    And I should see the city and county
    And I should see the best tide height if available
    And I should see the best season if available
    And I should see the list of tips if available
    And I should see the marine life if available
    And I should see the amenities if available
    And I should see the access difficulty if available
    And I should see the data sources

  Scenario: Location detail page shows a small map
    Given the location "shell-beach-la-jolla" has coordinates
    When I visit the location page for "shell-beach-la-jolla"
    Then I should see a small map showing the location
    And the map should be centered on the location coordinates

  Scenario: Location without coordinates shows no map
    Given the location "la-jolla-tide-pools" has no coordinates
    When I visit the location page for "la-jolla-tide-pools"
    Then I should not see a map on the detail page

  Scenario: Location detail page has navigation back to directory
    When I visit the location page for "shell-beach-la-jolla"
    Then I should see a link back to the directory

  # Mobile-First Design
  Scenario: Directory page is mobile responsive
    When I visit the directory page on a mobile device
    Then the map should be full width
    And the location list should stack vertically
    And touch interactions should work on the map

  Scenario: Location detail page is mobile responsive
    When I visit the location page for "shell-beach-la-jolla" on a mobile device
    Then the content should be readable without horizontal scrolling
    And the map should be appropriately sized for mobile

  # Error Handling
  Scenario: Invalid location ID returns 404
    When I visit the location page for "nonexistent-location"
    Then I should see a 404 error page
    And I should see a link back to the directory
