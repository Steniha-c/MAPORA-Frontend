"""Master Reconstruction Pipeline Orchestrator for MAPORA AI Mapping."""

from typing import Callable, Optional
import time

from app.core.logging import logger
from app.reconstruction.video_preprocessing import process_video_keyframes, VideoPreprocessingResult
from app.reconstruction.odometry import CameraIntrinsics, OpenCVVisualOdometry
from app.reconstruction.depth import DepthEstimationAdapter
from app.reconstruction.semantics import SemanticSegmentationAdapter
from app.reconstruction.spatial import reconstruct_point_cloud, PointCloudResult
from app.reconstruction.floor_plan_gen import generate_floor_plan_from_point_cloud, GeneratedFloorPlan
from app.reconstruction.model_3d_gen import generate_3d_model_from_floor_plan, GeneratedModel3D


ProgressCallback = Callable[[str, float, str], None]


class PipelineOutput:
    """Consolidated outputs from full reconstruction run."""

    def __init__(
        self,
        video_info: VideoPreprocessingResult,
        point_cloud: PointCloudResult,
        floor_plan: GeneratedFloorPlan,
        model_3d: GeneratedModel3D,
        duration_seconds: float,
    ):
        self.video_info = video_info
        self.point_cloud = point_cloud
        self.floor_plan = floor_plan
        self.model_3d = model_3d
        self.duration_seconds = duration_seconds


class SpatialReconstructionPipeline:
    """
    Modular AI & Computer Vision pipeline coordinating Stages A through G.
    Reports real progress without fabricating steps.
    """

    def __init__(
        self,
        depth_adapter: Optional[DepthEstimationAdapter] = None,
        semantic_adapter: Optional[SemanticSegmentationAdapter] = None,
    ):
        self.depth_adapter = depth_adapter or DepthEstimationAdapter()
        self.semantic_adapter = semantic_adapter or SemanticSegmentationAdapter()
        self.odometry_adapter = OpenCVVisualOdometry()

    def run(
        self,
        video_path: str,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> PipelineOutput:
        start_time = time.time()

        def report(stage: str, progress: float, message: str):
            if progress_cb:
                progress_cb(stage, progress, message)

        # 1. Validation Stage
        report("validating", 5.0, "Validating walkthrough video stream...")
        logger.info(f"Pipeline started for {video_path}")

        # 2. Stage A: Preprocessing & Keyframe Extraction
        report("extracting_keyframes", 15.0, "Extracting sharp, representative keyframes...")
        video_info = process_video_keyframes(video_path)

        if not video_info.keyframe_images:
            raise ValueError("No viable keyframes could be extracted from the video.")

        # 3. Stage B: Camera Motion & Intrinsics
        report("estimating_geometry", 35.0, "Estimating camera motion and trajectory odometry...")
        intrinsics = CameraIntrinsics.estimate_from_dimensions(video_info.width, video_info.height)
        poses = self.odometry_adapter.estimate_trajectory(
            video_info.keyframe_images,
            video_info.keyframe_timestamps,
            intrinsics,
        )

        # 4. Stage C: Depth Estimation
        report("estimating_geometry", 50.0, "Computing dense metric depth maps...")
        depth_results = self.depth_adapter.estimate_batch(video_info.keyframe_images)

        # 5. Stage D: Semantic Segmentation
        report("estimating_geometry", 65.0, "Segmenting walls, floors, and openings...")
        semantic_results = self.semantic_adapter.segment_batch(video_info.keyframe_images)

        # 6. Stage E: Spatial Reconstruction (Point Cloud)
        report("estimating_geometry", 75.0, "Fusing 3D spatial point cloud and aligning coordinate system...")
        point_cloud = reconstruct_point_cloud(
            images=video_info.keyframe_images,
            poses=poses,
            depth_results=depth_results,
            semantic_results=semantic_results,
            intrinsics=intrinsics,
        )

        # 7. Stage F: 2D Floor Plan Generation
        report("generating_floor_plan", 85.0, "Extracting room polygons, walls, and boundary schema...")
        floor_plan = generate_floor_plan_from_point_cloud(point_cloud)

        # 8. Stage G: 3D Model Generation
        report("generating_3d_model", 95.0, "Generating architectural 3D GLB model...")
        model_3d = generate_3d_model_from_floor_plan(floor_plan)

        total_duration = time.time() - start_time
        report("completed", 100.0, "Spatial reconstruction pipeline completed successfully.")
        logger.info(f"Pipeline completed in {total_duration:.2f} seconds.")

        return PipelineOutput(
            video_info=video_info,
            point_cloud=point_cloud,
            floor_plan=floor_plan,
            model_3d=model_3d,
            duration_seconds=total_duration,
        )
