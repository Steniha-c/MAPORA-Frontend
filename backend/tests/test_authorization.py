"""Cross-user authorization and role enforcement tests."""

import pytest
from fastapi.testclient import TestClient


def test_surveyor_cannot_access_other_surveyor_project(
    client: TestClient, surveyor_token, other_surveyor_token
):
    # Surveyor 1 creates project
    res1 = client.post(
        "/api/v1/projects",
        json={"name": "Surveyor 1 Confidential Project"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert res1.status_code == 201
    project_id = res1.json()["id"]

    # Surveyor 2 attempts to get Surveyor 1's project -> should fail (404/403)
    res2 = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {other_surveyor_token}"},
    )
    assert res2.status_code in [403, 404]

    # Surveyor 2 attempts to delete Surveyor 1's project -> should fail
    del_res = client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {other_surveyor_token}"},
    )
    assert del_res.status_code in [403, 404]


def test_admin_can_access_any_surveyor_project(
    client: TestClient, surveyor_token, admin_token
):
    # Surveyor creates project
    res = client.post(
        "/api/v1/projects",
        json={"name": "Surveyor Field Map"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert res.status_code == 201
    project_id = res.json()["id"]

    # Admin accesses Surveyor's project -> should succeed
    admin_get = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_get.status_code == 200
    assert admin_get.json()["id"] == project_id


def test_surveyor_forbidden_from_admin_endpoints(
    client: TestClient, surveyor_token, admin_token
):
    # Surveyor attempts to fetch admin analytics -> 403 Forbidden
    surveyor_res = client.get(
        "/api/v1/admin/analytics",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert surveyor_res.status_code == 403

    # Admin accesses admin analytics -> 200 OK
    admin_res = client.get(
        "/api/v1/admin/analytics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    assert "projectCount" in admin_res.json()
