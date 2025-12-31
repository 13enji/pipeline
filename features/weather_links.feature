Feature: Weather source links
  As a tidepooler
  I want to see links to NWS forecast pages
  So that I can verify the weather data and see more details

  # Weather data links to forecast.weather.gov
  # Link is embedded in the weather display text (temp, wind, precip)
  # AheadHour parameter positions the 48-hour window near the tide window time

  # --- Link Appearance ---

  Scenario: Weather text is a clickable link
    Given I am viewing a tide window with weather data
    Then the weather info (temp, wind, precip) should be a single clickable link
    And the link should open in a new tab

  Scenario: Weather link styling
    Given I am viewing a tide window with weather data
    Then the weather link should keep the current green color
    And the link should show an underline on hover

  # --- Link URL Structure ---

  Scenario: Weather link includes correct location coordinates
    Given I am on the windows page
    And there is a window with weather displayed
    Then the weather link should include La Jolla coordinates
    And the link should use textField1 for latitude and textField2 for longitude

  Scenario: Weather link includes correct data parameters
    Given I am viewing a tide window with weather data
    Then the weather link should include parameter w0=t for temperature
    And the weather link should include parameter w3=sfcwind for wind
    And the weather link should include parameter w5=pop for precipitation
    And the weather link should include FcstType=graphical

  # --- AheadHour Calculation ---

  Scenario: AheadHour positions 48-hour window near tide window
    Given I am viewing a tide window starting in 24 hours
    Then the weather link AheadHour should be approximately 18
    # (24 hours - 6 hours = 18 hours ahead)

  Scenario: AheadHour is capped at 100 hours
    Given I am viewing a tide window starting in 120 hours
    Then the weather link AheadHour should be 100
    # Window is beyond 100h, so we cap at max available

  Scenario: AheadHour is 0 for imminent windows
    Given I am viewing a tide window starting in 2 hours
    Then the weather link AheadHour should be 0
    # (2 hours - 6 hours = negative, so use 0)

  # --- Location Page ---

  Scenario: Location page weather links use station coordinates
    Given I am on the location page
    And I have searched for zip code "94123"
    And there is a window with weather displayed
    Then the weather link should include the station coordinates
    And the link should use textField1 for latitude and textField2 for longitude
    # Weather is for where user will BE (station), not where they searched from

  # --- No Link When No Weather ---

  Scenario: No weather link for windows beyond 7 days
    Given I am viewing a tide window more than 7 days away
    Then no weather info should be displayed
    And no weather link should be present
