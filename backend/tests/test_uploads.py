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


def test_upload_valid_webm(client: TestClient, surveyor_token):
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "WebM Upload Space"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    project_id = proj_res.json()["id"]

    dummy_webm_content = b"\x1a\x45\xdf\xa3" + b"\x00" * 1024
    files = {"file": ("walkthrough.webm", io.BytesIO(dummy_webm_content), "video/webm")}

    upload_res = client.post(
        f"/api/v1/projects/{project_id}/uploads",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["status"] == "uploaded"


def test_create_project_multipart_upload_flow(client: TestClient, surveyor_token):
    dummy_video = b"\x00\x00\x00 ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 2048
    files = {"video": ("walkthrough_live.mp4", io.BytesIO(dummy_video), "video/mp4")}

    res = client.post(
        "/projects",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["status"] == "Processing"


def test_create_project_multipart_invalid_extension(client: TestClient, surveyor_token):
    files = {"video": ("bad_file.bin", io.BytesIO(b"12345"), "application/octet-stream")}

    res = client.post(
        "/projects",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert res.status_code == 400
    assert "unsupported video file extension" in res.json()["detail"].lower()


def test_create_project_multipart_unauthenticated(client: TestClient):
    dummy_video = b"\x00\x00\x00 ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 1024
    files = {"video": ("walkthrough.mp4", io.BytesIO(dummy_video), "video/mp4")}

    res = client.post("/projects", files=files)
    assert res.status_code == 401


def test_cors_preflight_options(client: TestClient):
    for origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"]:
        res = client.options(
            "/projects",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin

