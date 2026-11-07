"""Authentication and authorization tests."""

import pytest
from fastapi.testclient import TestClient


def test_user_registration_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new_surveyor@mapora.test", "password": "SecurePassword123!", "role": "surveyor"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "accessToken" in data or "access_token" in data
    user_info = data.get("user")
    assert user_info["email"] == "new_surveyor@mapora.test"
    assert user_info["role"] == "surveyor"


def test_user_registration_duplicate_email(client: TestClient, surveyor_user):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": surveyor_user.email, "password": "AnotherPassword123!"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_login_success(client: TestClient, surveyor_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": surveyor_user.email, "password": "SurveyorPass1!"},
    )
    assert response.status_code == 200
    data = response.json()
    token = data.get("accessToken") or data.get("access_token")
    assert token is not None
    assert data["user"]["email"] == surveyor_user.email
    assert data["user"]["role"] == "surveyor"


def test_login_invalid_password_generic_error(client: TestClient, surveyor_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": surveyor_user.email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_refresh_token_cycle(client: TestClient, surveyor_user):
    # 1. Login to get refresh token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": surveyor_user.email, "password": "SurveyorPass1!"},
    )
    refresh_token = login_res.json().get("refreshToken") or login_res.json().get("refresh_token")
    assert refresh_token is not None

    # 2. Call refresh
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    new_access_token = new_data.get("accessToken") or new_data.get("access_token")
    assert new_access_token is not None

    # 3. Old refresh token should now be revoked (rotation)
    reused_res = client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert reused_res.status_code == 401


def test_auth_me_protected(client: TestClient, surveyor_token):
    # Authorized
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {surveyor_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "surveyor1@mapora.test"

    # Unauthorized without header
    unauth_response = client.get("/api/v1/auth/me")
    assert unauth_response.status_code == 401
