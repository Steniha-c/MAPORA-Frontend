"""Video upload API and validation tests."""

import io
import pytest
from fastapi.testclient import TestClient


def test_upload_valid_mp4(client: TestClient, surveyor_token):
    # Create project first
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Upload Target Space"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    project_id = proj_res.json()["id"]

    # Create dummy video bytes
    dummy_video_content = b"\x00\x00\x00 ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 2000
    files = {"file": ("indoor_survey.mp4", io.BytesIO(dummy_video_content), "video/mp4")}

    upload_res = client.post(
        f"/api/v1/projects/{project_id}/uploads",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert data["status"] == "uploaded"
    assert data["projectId"] == project_id

    # Check upload metadata
    upload_id = data["id"]
    meta_res = client.get(
        f"/api/v1/uploads/{upload_id}",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert meta_res.status_code == 200
    assert meta_res.json()["fileSizeBytes"] == len(dummy_video_content)


def test_upload_invalid_extension(client: TestClient, surveyor_token):
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Bad Upload Space"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    project_id = proj_res.json()["id"]

    files = {"file": ("malicious.exe", io.BytesIO(b"binary executable"), "application/octet-stream")}

    upload_res = client.post(
        f"/api/v1/projects/{project_id}/uploads",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert upload_res.status_code == 400
    assert "unsupported video file extension" in upload_res.json()["detail"].lower()


def test_upload_empty_file(client: TestClient, surveyor_token):
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Empty Upload Space"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    project_id = proj_res.json()["id"]

    files = {"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")}

    upload_res = client.post(
        f"/api/v1/projects/{project_id}/uploads",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert upload_res.status_code == 400
