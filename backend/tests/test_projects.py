"""Project management and CRUD tests."""

import pytest
from fastapi.testclient import TestClient


def test_create_and_get_project(client: TestClient, surveyor_token):
    # Create project
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "Downtown Loft", "location": "Floor 3, Unit 302", "color": "plum"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert create_res.status_code == 201
    project_data = create_res.json()
    project_id = project_data["id"]
    assert project_data["name"] == "Downtown Loft"
    assert project_data["color"] == "plum"

    # Get project by ID
    get_res = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == project_id


def test_list_projects(client: TestClient, surveyor_token):
    client.post(
        "/api/v1/projects",
        json={"name": "Studio Alpha", "location": "Site A", "color": "blue"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    client.post(
        "/api/v1/projects",
        json={"name": "Studio Beta", "location": "Site B", "color": "sand"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )

    list_res = client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 2
    names = [p["name"] for p in items]
    assert "Studio Alpha" in names
    assert "Studio Beta" in names


def test_update_project_name(client: TestClient, surveyor_token):
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "Original Name", "location": "Location 1"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    project_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Renamed Project"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Renamed Project"


def test_delete_project(client: TestClient, surveyor_token):
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "To Be Deleted", "location": "Temporary"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    project_id = create_res.json()["id"]

    del_res = client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert del_res.status_code == 204

    # Confirm it cannot be retrieved
    get_res = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert get_res.status_code == 404


def test_project_versions_and_restore(client: TestClient, surveyor_token):
    # Create project
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "Versioning Suite", "location": "Lab 1"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    project_id = create_res.json()["id"]

    # Initial versions check
    versions_res = client.get(
        f"/api/v1/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert versions_res.status_code == 200
    versions = versions_res.json()
    assert len(versions) >= 1

    # Create new snapshot version
    snap_res = client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"description": "Pre-edit snapshot"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert snap_res.status_code == 201
    new_version_id = snap_res.json()["id"]

    # Restore version
    restore_res = client.post(
        f"/api/v1/projects/{project_id}/versions/{new_version_id}/restore",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    # Restore returns 204 or 400 if snapshot was empty
    assert restore_res.status_code in [204, 400]
