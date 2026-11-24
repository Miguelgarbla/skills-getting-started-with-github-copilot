from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    original_activities = deepcopy(activities)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        activities.clear()
        activities.update(original_activities)


def activity_path(activity_name, endpoint):
    return f"/activities/{quote(activity_name, safe='')}/{endpoint}"


def test_root_redirects_to_activity_page(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_data_without_caching(client):
    # Arrange
    activity_name = "Soccer Team"

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json()[activity_name]["participants"] == []
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_participant(client):
    # Arrange
    activity_name = "Soccer Team"
    email = "student@example.edu"

    # Act
    response = client.post(
        activity_path(activity_name, "signup"),
        params={"email": email},
    )
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert email in activities_response.json()[activity_name]["participants"]


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@example.edu"

    # Act
    response = client.post(
        activity_path(activity_name, "signup"),
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_registration(client):
    # Arrange
    activity_name = "Soccer Team"
    email = "student@example.edu"
    signup_url = activity_path(activity_name, "signup")

    # Act
    first_response = client.post(signup_url, params={"email": email})
    duplicate_response = client.post(signup_url, params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert first_response.status_code == 200
    assert duplicate_response.status_code == 400
    assert activities_response.json()[activity_name]["participants"].count(email) == 1


def test_unregister_removes_participant_and_duplicate_entries(client):
    # Arrange
    activity_name = "Soccer Team"
    email = "student@example.edu"
    signup_url = activity_path(activity_name, "signup")
    participants_url = activity_path(activity_name, "participants")

    client.post(signup_url, params={"email": email})
    activities[activity_name]["participants"].append(email)

    # Act
    response = client.delete(participants_url, params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert email not in activities_response.json()[activity_name]["participants"]


def test_unregister_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@example.edu"

    # Act
    response = client.delete(
        activity_path(activity_name, "participants"),
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_unregistered_participant(client):
    # Arrange
    activity_name = "Soccer Team"
    email = "student@example.edu"

    # Act
    response = client.delete(
        activity_path(activity_name, "participants"),
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"
