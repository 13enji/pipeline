Feature: Personalized time-based greeting
  As a user
  I want to enter my name and receive a time-appropriate greeting
  So that I feel welcomed by the application

  Scenario: Display name input form
    When I visit the greeting page
    Then I should see a form prompting for my name

  Scenario: Morning greeting (6am - 12pm)
    Given the server time is 9:00am
    When I submit the name "Ben"
    Then I should see "Good morning Ben"

  Scenario: Afternoon greeting (12pm - 6pm)
    Given the server time is 2:00pm
    When I submit the name "Ben"
    Then I should see "Good afternoon Ben"

  Scenario: Evening greeting (6pm - 10pm)
    Given the server time is 8:00pm
    When I submit the name "Ben"
    Then I should see "Good evening Ben"

  Scenario: Late night greeting (10pm - 6am)
    Given the server time is 11:00pm
    When I submit the name "Ben"
    Then I should see "Go to bed Ben"

  Scenario: Empty name defaults to anonymous
    Given the server time is 9:00am
    When I submit the name ""
    Then I should see "Good morning anonymous"
