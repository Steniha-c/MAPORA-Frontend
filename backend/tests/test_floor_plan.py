"""Floor plan and geometry editing tests."""

import pytest
from fastapi.testclient import TestClient
from app.models.geometry import FloorPlan, Room, Wall
from app.models.project import Project


def test_get_and_update_floor_plan(client: TestClient, db, surveyor_user, surveyor_token):
    # Setup project and floor plan manually in DB
    proj = Project(name="Interactive Space", user_id=surveyor_user.id, status="Ready")
    db.add(proj)
    db.commit()

    plan = FloorPlan(project_id=proj.id, coordinate_system="normalized-cartesian-2d", units="meters", is_active=True)
    db.add(plan)
    db.commit()

    room = Room(floor_plan_id=plan.id, name="Initial Room", bounds_x=0.0, bounds_y=0.0, bounds_width=4.0, bounds_height=3.0, area_sqm=12.0)
    wall = Wall(floor_plan_id=plan.id, start_x=0.0, start_y=0.0, end_x=4.0, end_y=0.0, kind="wall")
    db.add(room)
    db.add(wall)
    db.commit()

    # 1. Fetch floor plan
    get_res = client.get(
        f"/api/v1/projects/{proj.id}/floor-plan",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["coordinateSystem"] == "normalized-cartesian-2d"
    assert len(data["rooms"]) == 1
    assert data["rooms"][0]["name"] == "Initial Room"

    # 2. Update floor plan: rename room and adjust bounds
    patch_res = client.patch(
        f"/api/v1/projects/{proj.id}/floor-plan",
        json={
            "rooms": [
                {
                    "id": room.id,
                    "name": "Renamed Master Bedroom",
                    "bounds": {"x": 0.5, "y": 0.5, "width": 5.0, "height": 4.0},
                }
            ]
        },
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["rooms"][0]["name"] == "Renamed Master Bedroom"
    assert updated_data["rooms"][0]["bounds"]["width"] == 5.0


def test_reject_invalid_room_bounds(client: TestClient, db, surveyor_user, surveyor_token):
    proj = Project(name="Validation Space", user_id=surveyor_user.id, status="Ready")
    db.add(proj)
    db.commit()

    plan = FloorPlan(project_id=proj.id, is_active=True)
    db.add(plan)
    db.commit()

    room = Room(floor_plan_id=plan.id, name="Test Room", bounds_x=0.0, bounds_y=0.0, bounds_width=2.0, bounds_height=2.0)
    db.add(room)
    db.commit()

    # Reject non-positive bounding width
    bad_res = client.patch(
        f"/api/v1/projects/{proj.id}/floor-plan",
        json={
            "rooms": [
                {
                    "id": room.id,
                    "bounds": {"x": 0.0, "y": 0.0, "width": -5.0, "height": 3.0},
                }
            ]
        },
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert bad_res.status_code == 400
