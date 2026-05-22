"""
Integration tests for FastAPI Activity Management System.

Tests all endpoints using the AAA (Arrange-Act-Assert) pattern:
- Arrange: Set up test conditions
- Act: Execute the action being tested
- Assert: Verify the results

Coverage includes:
- GET /activities: retrieve all activities
- GET /: redirect to static index
- POST /activities/{activity_name}/signup: register students with validation
- DELETE /activities/{activity_name}/participants/{email}: remove students
"""

import pytest


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """
        Test: GET /activities returns all 9 activities with correct data structure.
        
        AAA Pattern:
        - Arrange: Activities already set up via reset_activities fixture
        - Act: Make GET request to /activities
        - Assert: Verify response contains all activities with required fields
        """
        # Act
        response = client.get("/activities")
        
        # Assert
        assert response.status_code == 200
        activities_data = response.json()
        assert len(activities_data) == 9
        
        # Verify Chess Club exists and has correct structure
        assert "Chess Club" in activities_data
        chess_club = activities_data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        
    def test_get_activities_contains_participants_list(self, client, reset_activities):
        """
        Test: Participants list is populated correctly for activities.
        
        AAA Pattern:
        - Arrange: Activities with pre-existing participants via fixture
        - Act: Make GET request to /activities
        - Assert: Verify participants are correctly returned
        """
        # Act
        response = client.get("/activities")
        activities_data = response.json()
        
        # Assert
        chess_club = activities_data["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestRootRedirect:
    """Tests for GET / endpoint."""

    def test_root_redirects_to_static_index(self, client, reset_activities):
        """
        Test: Root path redirects to /static/index.html.
        
        AAA Pattern:
        - Arrange: TestClient ready
        - Act: Make GET request to /
        - Assert: Verify redirect response
        """
        # Act
        response = client.get("/", follow_redirects=False)
        
        # Assert
        assert response.status_code in [301, 307]
        assert response.headers["location"] == "/static/index.html"


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint - Success cases."""

    def test_signup_successful(self, client, reset_activities):
        """
        Test: Student successfully signs up for an activity.
        
        AAA Pattern:
        - Arrange: Setup test data with known activity
        - Act: POST signup request for new student
        - Assert: Verify response and participant list updated
        """
        # Arrange
        activity_name = "Chess Club"
        email = "new_student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]

    def test_signup_updates_availability_count(self, client, reset_activities):
        """
        Test: Availability count decreases after successful signup.
        
        AAA Pattern:
        - Arrange: Get initial availability, sign up student
        - Act: Retrieve activities after signup
        - Assert: Verify availability decreased by 1
        """
        # Arrange
        activity_name = "Basketball Team"
        email = "new_player@mergington.edu"
        
        initial_response = client.get("/activities")
        initial_participants = len(
            initial_response.json()[activity_name]["participants"]
        )
        initial_availability = (
            initial_response.json()[activity_name]["max_participants"]
            - initial_participants
        )
        
        # Act
        client.post(f"/activities/{activity_name}/signup", params={"email": email})
        
        # Assert
        updated_response = client.get("/activities")
        updated_participants = len(
            updated_response.json()[activity_name]["participants"]
        )
        updated_availability = (
            updated_response.json()[activity_name]["max_participants"]
            - updated_participants
        )
        
        assert updated_availability == initial_availability - 1
        assert updated_participants == initial_participants + 1


class TestSignupValidation:
    """Tests for POST /activities/{activity_name}/signup endpoint - Error cases."""

    def test_signup_activity_not_found(self, client, reset_activities):
        """
        Test: 404 error when activity doesn't exist.
        
        AAA Pattern:
        - Arrange: Setup request with non-existent activity
        - Act: POST signup request to non-existent activity
        - Assert: Verify 404 response with correct detail
        """
        # Arrange
        activity_name = "NonExistent Club"
        email = "student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_email_rejected(self, client, reset_activities):
        """
        Test: 400 error when student already registered for activity.
        
        AAA Pattern:
        - Arrange: Identify student already in activity
        - Act: POST signup request with duplicate email
        - Assert: Verify 400 response with duplicate error
        """
        # Arrange
        activity_name = "Chess Club"
        duplicate_email = "michael@mergington.edu"  # Already in Chess Club
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": duplicate_email}
        )
        
        # Assert
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_signup_activity_at_capacity(self, client, reset_activities):
        """
        Test: 400 error when activity is at maximum capacity.
        
        AAA Pattern:
        - Arrange: Create activity at capacity by filling participant slots
        - Act: POST signup request when activity is full
        - Assert: Verify 400 response with capacity error
        """
        # Arrange
        activity_name = "Tennis Club"
        max_participants = 16
        current_participants = len(
            client.get("/activities").json()[activity_name]["participants"]
        )
        
        # Fill remaining spots
        for i in range(max_participants - current_participants):
            client.post(
                f"/activities/{activity_name}/signup",
                params={"email": f"student{i}@test.edu"}
            )
        
        # Verify activity is full
        assert len(client.get("/activities").json()[activity_name]["participants"]) == max_participants
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "overfull@test.edu"}
        )
        
        # Assert
        assert response.status_code == 400
        assert "full" in response.json()["detail"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint - Success cases."""

    def test_remove_participant_successful(self, client, reset_activities):
        """
        Test: Successfully remove a participant from an activity.
        
        AAA Pattern:
        - Arrange: Identify participant to remove
        - Act: DELETE request to remove participant
        - Assert: Verify response and participant list updated
        """
        # Arrange
        activity_name = "Chess Club"
        email_to_remove = "michael@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email_to_remove}"
        )
        
        # Assert
        assert response.status_code == 200
        assert "Removed" in response.json()["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email_to_remove not in activities_data[activity_name]["participants"]

    def test_remove_participant_increases_availability(self, client, reset_activities):
        """
        Test: Availability count increases after removing a participant.
        
        AAA Pattern:
        - Arrange: Get initial availability, identify participant to remove
        - Act: DELETE request to remove participant
        - Assert: Verify availability increased by 1
        """
        # Arrange
        activity_name = "Programming Class"
        email_to_remove = "emma@mergington.edu"
        
        initial_response = client.get("/activities")
        initial_participants = len(
            initial_response.json()[activity_name]["participants"]
        )
        initial_availability = (
            initial_response.json()[activity_name]["max_participants"]
            - initial_participants
        )
        
        # Act
        client.delete(
            f"/activities/{activity_name}/participants/{email_to_remove}"
        )
        
        # Assert
        updated_response = client.get("/activities")
        updated_participants = len(
            updated_response.json()[activity_name]["participants"]
        )
        updated_availability = (
            updated_response.json()[activity_name]["max_participants"]
            - updated_participants
        )
        
        assert updated_availability == initial_availability + 1
        assert updated_participants == initial_participants - 1


class TestRemoveParticipantValidation:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint - Error cases."""

    def test_remove_from_nonexistent_activity(self, client, reset_activities):
        """
        Test: 404 error when removing from non-existent activity.
        
        AAA Pattern:
        - Arrange: Setup request with non-existent activity
        - Act: DELETE request to non-existent activity
        - Assert: Verify 404 response
        """
        # Arrange
        activity_name = "Fake Club"
        email = "student@test.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_remove_nonexistent_participant(self, client, reset_activities):
        """
        Test: 404 error when removing participant not in activity.
        
        AAA Pattern:
        - Arrange: Identify valid activity but non-existent participant
        - Act: DELETE request for non-existent participant
        - Assert: Verify 404 response with participant not found error
        """
        # Arrange
        activity_name = "Chess Club"
        non_existent_email = "notinactivity@test.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{non_existent_email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestIntegrationScenarios:
    """Integration tests combining multiple operations."""

    def test_signup_then_remove_participant(self, client, reset_activities):
        """
        Test: Complete flow of signing up and then removing a participant.
        
        AAA Pattern:
        - Arrange: Setup activity and new student email
        - Act: Sign up student, then remove student
        - Assert: Verify participant added then removed correctly
        """
        # Arrange
        activity_name = "Debate Team"
        email = "debate_student@mergington.edu"
        
        initial_response = client.get("/activities")
        initial_count = len(
            initial_response.json()[activity_name]["participants"]
        )
        
        # Act: Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Assert: Verify signup
        after_signup = client.get("/activities")
        assert email in after_signup.json()[activity_name]["participants"]
        
        # Act: Remove
        remove_response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        assert remove_response.status_code == 200
        
        # Assert: Verify removal
        after_removal = client.get("/activities")
        assert email not in after_removal.json()[activity_name]["participants"]
        assert len(after_removal.json()[activity_name]["participants"]) == initial_count

    def test_multiple_signups_capacity_limit(self, client, reset_activities):
        """
        Test: Multiple signups respect capacity limit.
        
        AAA Pattern:
        - Arrange: Identify activity with limited capacity
        - Act: Sign up multiple students to near capacity, then exceed
        - Assert: Verify all signups succeed until capacity, then rejected
        """
        # Arrange
        activity_name = "Art Workshop"
        max_capacity = 18
        
        initial_response = client.get("/activities")
        initial_participants = len(
            initial_response.json()[activity_name]["participants"]
        )
        remaining_slots = max_capacity - initial_participants
        
        # Act & Assert: Fill remaining slots
        for i in range(remaining_slots):
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": f"artist{i}@test.edu"}
            )
            assert response.status_code == 200
        
        # Act & Assert: Try to exceed capacity
        final_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "toomany@test.edu"}
        )
        assert final_response.status_code == 400
        assert "full" in final_response.json()["detail"]
