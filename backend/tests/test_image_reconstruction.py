"""Multi-Image Indoor Photograph Upload & 2D/3D Reconstruction Tests."""

import io
import os
import tempfile
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.reconstruction.image_pipeline import (
    ImageReconstructionPipeline,
    InsufficientOverlapError,
)
from app.models.geometry import FloorPlan, Model3D


def create_synthetic_room_photo(offset_x: int = 0) -> bytes:
    """Generate a synthetic realistic indoor room photograph with structural lines."""
    width, height = 512, 384
    img = np.full((height, width, 3), 215, dtype=np.uint8)

    # Floor (lower 35%)
    img[int(height * 0.65):, :] = [65, 70, 75]
    # Ceiling (top 20%)
    img[:int(height * 0.20), :] = [235, 235, 240]

    # Doorway with frame
    door_x = (160 - offset_x) % (width - 120)
    cv2.rectangle(img, (door_x, int(height * 0.30)), (door_x + 80, int(height * 0.65)), (40, 35, 30), -1)
    cv2.rectangle(img, (door_x - 4, int(height * 0.28)), (door_x + 84, int(height * 0.65)), (80, 60, 40), 3)

    # Vertical wall corners with distinct texture features for SIFT matching
    for i, x in enumerate(range(40, width + 100, 100)):
        sx = (x - offset_x) % width
        cv2.line(img, (sx, int(height * 0.20)), (sx, int(height * 0.65)), (110, 110, 115), 3)
        # Texture patterns to generate strong keypoints
        for y in range(int(height * 0.25), int(height * 0.60), 35):
            cv2.circle(img, (sx, y), 5 + (i % 3), (90, 80, 70), -1)

    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def create_noise_photo() -> bytes:
    """Generate an unrelated random image with no architectural geometry."""
    img = np.random.randint(0, 256, (384, 512, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def test_batch_image_upload_endpoint(client: TestClient, surveyor_token):
    """Test uploading multiple photographs to an existing project."""
    # 1. Create project
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Photo Test Site", "location": "Living Space", "color": "blue"},
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 2. Upload 2 photos
    photo1 = create_synthetic_room_photo(offset_x=0)
    photo2 = create_synthetic_room_photo(offset_x=20)

    files = [
        ("files", ("angle1.jpg", photo1, "image/jpeg")),
        ("files", ("angle2.jpg", photo2, "image/jpeg")),
    ]

    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/images",
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert data["uploaded"] == 2
    assert len(data["images"]) == 2
    assert data["projectId"] == proj_id

    # 3. List photos
    list_res = client.get(
        f"/api/v1/projects/{proj_id}/images",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert list_res.status_code == 200
    images = list_res.json()
    assert len(images) == 2
    assert images[0]["originalFilename"] in ["angle1.jpg", "angle2.jpg"]


def test_create_project_multipart_photo_flow(client: TestClient, surveyor_token):
    """Test creating a new project directly with photos via multipart form."""
    photo1 = create_synthetic_room_photo(offset_x=0)
    photo2 = create_synthetic_room_photo(offset_x=15)

    files = [
        ("images", ("room_corner1.jpg", photo1, "image/jpeg")),
        ("images", ("room_corner2.jpg", photo2, "image/jpeg")),
    ]
    data = {
        "name": "Suite 4B Photos",
        "location": "North Wing",
        "color": "sand",
    }

    res = client.post(
        "/api/v1/projects",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert res.status_code == 201
    result = res.json()
    assert "id" in result
    assert result["status"] == "Processing"

    # Verify project status endpoint returns queued or processing
    status_res = client.get(
        f"/api/v1/projects/{result['id']}/status",
        headers={"Authorization": f"Bearer {surveyor_token}"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] in ["queued", "processing", "completed"]


def test_single_photo_reconstruction_pipeline():
    """Verify single-photo mode generates a 2.5D spatial estimation with appropriate flags."""
    with tempfile.TemporaryDirectory() as temp_dir:
        p1 = os.path.join(temp_dir, "single.jpg")
        with open(p1, "wb") as f:
            f.write(create_synthetic_room_photo(0))

        pipeline = ImageReconstructionPipeline()
        output = pipeline.run([p1])

        assert output.metadata.is_single_image is True
        assert output.metadata.image_count == 1
        assert output.floor_plan.quality_confidence == 0.50
        assert output.floor_plan.measurements_available is False
        assert len(output.floor_plan.rooms) >= 1
        assert "Estimated Space" in output.floor_plan.rooms[0]["name"]
        assert len(output.model_3d.glb_bytes) > 0


def test_multi_photo_reconstruction_pipeline():
    """Verify multi-photo mode extracts camera motion, matches features, and produces 2D/3D geometry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = []
        for i in range(3):
            p = os.path.join(temp_dir, f"frame_{i}.jpg")
            with open(p, "wb") as f:
                f.write(create_synthetic_room_photo(offset_x=i * 12))
            paths.append(p)

        pipeline = ImageReconstructionPipeline()
        output = pipeline.run(paths)

        assert output.metadata.is_single_image is False
        assert output.metadata.image_count == 3
        assert output.metadata.total_inliers >= 15
        assert output.floor_plan.measurements_available is True
        assert output.floor_plan.quality_confidence > 0.60
        assert len(output.floor_plan.rooms) >= 1
        assert len(output.floor_plan.walls) >= 4
        assert len(output.model_3d.glb_bytes) > 0
        assert output.model_3d.vertex_count > 0


def test_insufficient_overlap_detection():
    """Verify that unrelated photos with insufficient visual overlap raise InsufficientOverlapError."""
    with tempfile.TemporaryDirectory() as temp_dir:
        p1 = os.path.join(temp_dir, "real_room.jpg")
        with open(p1, "wb") as f:
            f.write(create_synthetic_room_photo(0))

        p2 = os.path.join(temp_dir, "noise.jpg")
        with open(p2, "wb") as f:
            f.write(create_noise_photo())

        pipeline = ImageReconstructionPipeline()
        with pytest.raises(InsufficientOverlapError) as exc_info:
            pipeline.run([p1, p2])

        assert "Insufficient visual overlap" in str(exc_info.value)

