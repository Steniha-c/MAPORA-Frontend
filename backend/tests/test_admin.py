"""Admin analytics and metrics tests."""

import pytest
from fastapi.testclient import TestClient
from app.models.job import ReconstructionJob
from app.models.project import Project


def test_admin_analytics_query(client: TestClient, db, admin_token, surveyor_user):
    # Seed projects and jobs
    proj = Project(name="Admin Monitored Project", user_id=surveyor_user.id, status="Processing", rooms_count=3)
    db.add(proj)
    db.commit()

    job1 = ReconstructionJob(
        project_id=proj.id,
        user_id=surveyor_user.id,
        stage="completed",
        status="completed",
        progress=100.0,
        duration_seconds=42.5,
    )
    job2 = ReconstructionJob(
        project_id=proj.id,
        user_id=surveyor_user.id,
        stage="validating",
        status="processing",
        progress=20.0,
    )
    db.add_all([job1, job2])
    db.commit()

    res = client.get(
        "/api/v1/admin/analytics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["projectCount"] >= 1
    assert data["userCount"] >= 2
    assert data["jobsRunning"] >= 1
    assert data["jobsCompleted"] >= 1
    assert data["averageProcessingSeconds"] > 0


def test_admin_jobs_pagination(client: TestClient, admin_token):
    res = client.get(
        "/api/v1/admin/jobs?skip=0&limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
