"""File export generation tests (SVG, PDF, DXF, GLB)."""

import pytest
from fastapi.testclient import TestClient
from app.models.geometry import FloorPlan, Room, Wall
from app.models.project import Project


def test_export_svg_pdf_dxf(client: TestClient, db, surveyor_user, surveyor_token):
    # Setup project with active floor plan
    proj = Project(name="Architectural Pavilion", user_id=surveyor_user.id, status="Ready")
    db.add(proj)
    db.commit()

    plan = FloorPlan(project_id=proj.id, coordinate_system="normalized-cartesian-2d", units="meters", is_active=True)
    db.add(plan)
    db.commit()

    room = Room(floor_plan_id=plan.id, name="Exhibition Hall", bounds_x=0.0, bounds_y=0.0, bounds_width=8.0, bounds_height=6.0, area_sqm=48.0)
    wall1 = Wall(floor_plan_id=plan.id, start_x=0.0, start_y=0.0, end_x=8.0, end_y=0.0, kind="wall")
    wall2 = Wall(floor_plan_id=plan.id, start_x=3.0, start_y=0.0, end_x=4.0, end_y=0.0, kind="door")
    db.add_all([room, wall1, wall2])
    db.commit()

    # 1. Test SVG export
    svg_res = client.get(
        f"/api/v1/projects/{proj.id}/export?format=svg",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert svg_res.status_code == 200
    assert "svg" in svg_res.headers.get("content-type", "")
    assert b"<svg" in svg_res.content
    assert b"Exhibition Hall" in svg_res.content

    # 2. Test PDF export
    pdf_res = client.get(
        f"/api/v1/projects/{proj.id}/export?format=pdf",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert pdf_res.status_code == 200
    assert "pdf" in pdf_res.headers.get("content-type", "")
    assert svg_res.content.startswith(b"<?xml") or b"<svg" in svg_res.content
    assert pdf_res.content.startswith(b"%PDF-")

    # 3. Test DXF export
    dxf_res = client.get(
        f"/api/v1/projects/{proj.id}/export?format=dxf",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert dxf_res.status_code == 200
    assert b"SECTION" in dxf_res.content
    assert b"WALLS" in dxf_res.content


def test_export_empty_project_error(client: TestClient, db, surveyor_user, surveyor_token):
    # Empty project without any floor plan
    proj = Project(name="Empty Unprocessed Project", user_id=surveyor_user.id, status="Needs attention")
    db.add(proj)
    db.commit()

    res = client.get(
        f"/api/v1/projects/{proj.id}/export?format=svg",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert res.status_code == 400
    assert "no active floor plan available" in res.json()["detail"].lower()


def test_export_glb_and_obj(client: TestClient, db, surveyor_user, surveyor_token):
    import io, trimesh
    from app.models.geometry import Model3D
    from app.storage.provider import get_storage

    proj = Project(name="3D Pavilion", user_id=surveyor_user.id, status="Ready")
    db.add(proj)
    db.commit()

    plan = FloorPlan(project_id=proj.id, coordinate_system="normalized-cartesian-2d", units="meters", is_active=True)
    db.add(plan)
    db.commit()

    box = trimesh.creation.box()
    glb_bytes = trimesh.exchange.gltf.export_glb(box)
    storage = get_storage()
    storage_key = f"models/{proj.id}/scene.glb"
    storage.save(io.BytesIO(glb_bytes), storage_key, content_type="model/gltf-binary")

    model = Model3D(
        project_id=proj.id,
        storage_key=storage_key,
        vertex_count=len(box.vertices),
        face_count=len(box.faces),
        format="glb",
    )
    db.add(model)
    db.commit()

    # Test GLB export
    glb_res = client.get(
        f"/api/v1/projects/{proj.id}/export?format=glb",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert glb_res.status_code == 200
    assert len(glb_res.content) > 100

    # Test OBJ export
    obj_res = client.get(
        f"/api/v1/projects/{proj.id}/export?format=obj",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert obj_res.status_code == 200
    assert b"v " in obj_res.content or b"vn " in obj_res.content

