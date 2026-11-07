"""Frontend contract integration tests strictly verifying compatibility with MAPORA-Frontend."""

import io
import pytest
from fastapi.testclient import TestClient
from app.models.geometry import FloorPlan, Room, Wall, Model3D
from app.models.project import Project


def test_frontend_auth_contract(client: TestClient, surveyor_user):
    # Frontend calls POST /auth/login with {email, password}
    res = client.post(
        "/auth/login",
        json={"email": surveyor_user.email, "password": "SurveyorPass1!"},
    )
    assert res.status_code == 200
    data = res.json()
    # Frontend AuthSession expects { accessToken: string, user: { id: string, email: string, role: string } }
    assert "accessToken" in data or "access_token" in data
    assert "user" in data
    assert "id" in data["user"]
    assert "email" in data["user"]
    assert "role" in data["user"]


def test_frontend_create_mapping_and_polling(client: TestClient, surveyor_token):
    # Frontend calls POST /projects with FormData: body.append('video', file)
    dummy_video = b"\x00\x00\x00 ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 1000
    files = {"video": ("walkthrough.mp4", io.BytesIO(dummy_video), "video/mp4")}

    res = client.post(
        "/projects",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    # Frontend expects { id: string, status: string }
    assert "id" in data
    assert "status" in data
    project_id = data["id"]

    # Frontend polls GET /projects/:id/status
    status_res = client.get(
        f"/projects/{project_id}/status",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    # ProcessingStatus expects { projectId, stage, status, progress, message, updatedAt }
    assert status_data["projectId"] == project_id
    assert "stage" in status_data
    assert "status" in status_data
    assert "progress" in status_data


def test_frontend_floor_plan_and_scene_contract(client: TestClient, db, surveyor_user, surveyor_token):
    proj = Project(name="Northlight Apartment", user_id=surveyor_user.id, status="Ready")
    db.add(proj)
    db.commit()

    plan = FloorPlan(project_id=proj.id, coordinate_system="normalized-cartesian-2d", units="meters", is_active=True)
    db.add(plan)
    db.commit()

    room = Room(floor_plan_id=plan.id, name="Living Room", bounds_x=0.0, bounds_y=0.0, bounds_width=5.0, bounds_height=4.0, area_sqm=20.0)
    wall = Wall(floor_plan_id=plan.id, start_x=0.0, start_y=0.0, end_x=5.0, end_y=0.0, kind="wall")
    door = Wall(floor_plan_id=plan.id, start_x=2.0, start_y=0.0, end_x=2.9, end_y=0.0, kind="door")
    model = Model3D(project_id=proj.id, format="glb", storage_key="models/test/scene.glb", file_size_bytes=1024)
    db.add_all([room, wall, door, model])
    db.commit()

    # 1. Frontend calls maporaApi.getFloorPlan
    fp_res = client.get(
        f"/projects/{proj.id}/floor-plan",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert fp_res.status_code == 200
    fp_data = fp_res.json()
    # FloorPlanModel { coordinateSystem, units, measurementsAvailable, rooms, walls }
    assert "coordinateSystem" in fp_data
    assert "units" in fp_data
    assert "measurementsAvailable" in fp_data
    assert len(fp_data["rooms"]) == 1
    assert fp_data["rooms"][0]["name"] == "Living Room"
    assert "bounds" in fp_data["rooms"][0]
    assert "areaSquareMeters" in fp_data["rooms"][0]
    assert len(fp_data["walls"]) == 2
    assert fp_data["walls"][0]["kind"] in ["wall", "door"]

    # 2. Frontend calls maporaApi.getScene
    scene_res = client.get(
        f"/projects/{proj.id}/scene",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert scene_res.status_code == 200
    scene_data = scene_res.json()
    # Frontend expects { geometryUrl: string }
    assert "geometryUrl" in scene_data
    assert len(scene_data["geometryUrl"]) > 0


def test_frontend_admin_analytics_contract(client: TestClient, admin_token):
    # Frontend calls maporaApi.getAdminAnalytics
    res = client.get(
        "/admin/analytics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    # AdminAnalytics schema
    assert "projectCount" in data
    assert "userCount" in data
    assert "jobsRunning" in data
    assert "jobsFailed" in data
    assert "updatedAt" in data
