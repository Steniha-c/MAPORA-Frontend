"""End-to-end Computer Vision and Spatial Reconstruction pipeline tests."""

import os
import tempfile
import cv2
import numpy as np
import pytest

from app.reconstruction.pipeline import SpatialReconstructionPipeline
from app.reconstruction.video_preprocessing import process_video_keyframes
from app.reconstruction.odometry import CameraIntrinsics, OpenCVVisualOdometry
from app.reconstruction.depth import DepthEstimationAdapter
from app.reconstruction.semantics import SemanticSegmentationAdapter
from app.reconstruction.spatial import reconstruct_point_cloud
from app.reconstruction.floor_plan_gen import generate_floor_plan_from_point_cloud
from app.reconstruction.model_3d_gen import generate_3d_model_from_floor_plan


def create_synthetic_indoor_video(filepath: str, num_frames: int = 30):
    """Generate a realistic test video of an indoor room with simulated camera motion."""
    width, height = 640, 480
    fps = 15.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

    for i in range(num_frames):
        # Create indoor wall background with vertical perspective lines and textures
        frame = np.full((height, width, 3), 200, dtype=np.uint8)

        # Floor (lower 35%)
        frame[int(height * 0.65):, :] = [70, 75, 80]
        # Ceiling (top 20%)
        frame[:int(height * 0.20), :] = [230, 230, 235]

        # Shift perspective to simulate camera pan/walk
        offset = int(i * 4)

        # Draw door frame
        door_x = max(20, (180 - offset) % (width - 120))
        cv2.rectangle(frame, (door_x, int(height * 0.30)), (door_x + 90, int(height * 0.65)), (50, 40, 30), 4)

        # Draw wall corners / texture lines
        for x_line in range(50, width + 100, 150):
            shifted_x = (x_line - offset) % width
            cv2.line(frame, (shifted_x, int(height * 0.20)), (shifted_x, int(height * 0.65)), (140, 140, 140), 2)

        out.write(frame)

    out.release()


def test_reconstruction_pipeline_stages():
    """Verify all stages A through G on a generated indoor walkthrough video."""
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, "test_walkthrough.mp4")
        create_synthetic_indoor_video(video_path, num_frames=25)

        assert os.path.exists(video_path)

        # 1. Stage A: Preprocessing
        video_info = process_video_keyframes(video_path, min_interval_seconds=0.2, blur_threshold=10.0)
        assert len(video_info.keyframe_images) >= 3
        assert video_info.width == 640
        assert video_info.height == 480

        # 2. Stage B: Camera Motion / Odometry
        intrinsics = CameraIntrinsics.estimate_from_dimensions(640, 480)
        odometry = OpenCVVisualOdometry()
        poses = odometry.estimate_trajectory(
            video_info.keyframe_images,
            video_info.keyframe_timestamps,
            intrinsics,
        )
        assert len(poses) == len(video_info.keyframe_images)

        # 3. Stage C: Depth Estimation
        depth_adapter = DepthEstimationAdapter()
        depth_results = depth_adapter.estimate_batch(video_info.keyframe_images)
        assert len(depth_results) == len(video_info.keyframe_images)
        assert depth_results[0].depth_map.shape == (480, 640)

        # 4. Stage D: Semantic Segmentation
        sem_adapter = SemanticSegmentationAdapter()
        sem_results = sem_adapter.segment_batch(video_info.keyframe_images)
        assert len(sem_results) == len(video_info.keyframe_images)
        assert sem_results[0].class_mask.shape == (480, 640)

        # 5. Stage E: Spatial Point Cloud
        point_cloud = reconstruct_point_cloud(
            images=video_info.keyframe_images,
            poses=poses,
            depth_results=depth_results,
            semantic_results=sem_results,
            intrinsics=intrinsics,
        )
        assert point_cloud.point_count > 0

        # 6. Stage F: 2D Floor Plan
        floor_plan = generate_floor_plan_from_point_cloud(point_cloud)
        assert len(floor_plan.rooms) >= 1
        assert len(floor_plan.walls) >= 4
        assert floor_plan.rooms[0]["name"] is not None
        assert floor_plan.units == "meters"

        # 7. Stage G: 3D Model Generation
        model_3d = generate_3d_model_from_floor_plan(floor_plan)
        assert len(model_3d.glb_bytes) > 200
        assert model_3d.vertex_count > 0
        assert len(model_3d.room_names) >= 1


def test_full_pipeline_orchestrator():
    """Verify Master Reconstruction Pipeline orchestrator with progress reports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, "test_walkthrough.mp4")
        create_synthetic_indoor_video(video_path, num_frames=20)

        pipeline = SpatialReconstructionPipeline()
        progress_events = []

        def track_progress(stage, progress, message):
            progress_events.append((stage, progress))

        output = pipeline.run(video_path, progress_cb=track_progress)

        assert output.duration_seconds > 0
        assert output.floor_plan is not None
        assert len(output.model_3d.glb_bytes) > 0
        assert len(progress_events) >= 5
        stages_seen = [stage for stage, _ in progress_events]
        assert "validating" in stages_seen
        assert "extracting_keyframes" in stages_seen
        assert "estimating_geometry" in stages_seen
        assert "generating_floor_plan" in stages_seen
        assert "generating_3d_model" in stages_seen
        assert "completed" in stages_seen
