"""Master Multi-Image Reconstruction Pipeline for MAPORA AI Mapping."""

import os
import time
from typing import Callable, Dict, List, Optional, Tuple, Any
import cv2
import numpy as np

from app.core.logging import logger
from app.reconstruction.odometry import CameraIntrinsics, CameraPose
from app.reconstruction.depth import DepthEstimationAdapter, DepthEstimationResult
from app.reconstruction.semantics import SemanticSegmentationAdapter, SemanticSegmentationResult, SemanticClass
from app.reconstruction.spatial import reconstruct_point_cloud, PointCloudResult
from app.reconstruction.floor_plan_gen import generate_floor_plan_from_point_cloud, GeneratedFloorPlan
from app.reconstruction.model_3d_gen import generate_3d_model_from_floor_plan, GeneratedModel3D


ProgressCallback = Callable[[str, float, str], None]


class InsufficientOverlapError(ValueError):
    """Raised when uploaded photos lack sufficient geometric overlap to correlate 3D poses."""
    pass


class ImagePipelineMetadata:
    """Metadata describing the input photograph batch and capture conditions."""

    def __init__(
        self,
        image_count: int,
        width: int,
        height: int,
        is_single_image: bool = False,
        average_blur_score: float = 0.0,
        total_inliers: int = 0,
    ):
        self.image_count = image_count
        self.width = width
        self.height = height
        self.is_single_image = is_single_image
        self.average_blur_score = average_blur_score
        self.total_inliers = total_inliers


class ImagePipelineOutput:
    """Consolidated output from image reconstruction pipeline."""

    def __init__(
        self,
        metadata: ImagePipelineMetadata,
        point_cloud: PointCloudResult,
        floor_plan: GeneratedFloorPlan,
        model_3d: GeneratedModel3D,
        duration_seconds: float,
    ):
        self.metadata = metadata
        self.point_cloud = point_cloud
        self.floor_plan = floor_plan
        self.model_3d = model_3d
        self.duration_seconds = duration_seconds


def calculate_image_blur(image: np.ndarray) -> float:
    """Compute variance of the Laplacian as focus/sharpness metric."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def resize_bounded(image: np.ndarray, max_dim: int = 1024) -> np.ndarray:
    """Resize image preserving aspect ratio if larger than max_dim to bound CPU inference time."""
    h, w = image.shape[:2]
    if max(h, w) <= max_dim:
        return image
    scale = max_dim / float(max(h, w))
    nw = int(round(w * scale))
    nh = int(round(h * scale))
    return cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)


class ImageReconstructionPipeline:
    """
    Modular AI & Computer Vision pipeline coordinating multi-photo spatial reconstruction.
    Supports single-image 2.5D approximation and multi-image SfM camera pose recovery.
    """

    def __init__(
        self,
        depth_adapter: Optional[DepthEstimationAdapter] = None,
        semantic_adapter: Optional[SemanticSegmentationAdapter] = None,
    ):
        self.depth_adapter = depth_adapter or DepthEstimationAdapter()
        self.semantic_adapter = semantic_adapter or SemanticSegmentationAdapter()
        self.sift = cv2.SIFT_create(nfeatures=2500)
        self.matcher = cv2.BFMatcher(cv2.NORM_L2)

    def estimate_camera_poses(
        self,
        images: List[np.ndarray],
        intrinsics: CameraIntrinsics,
    ) -> Tuple[List[CameraPose], int]:
        """
        Estimate 6-DOF camera poses across photographs using pairwise SIFT matching and RANSAC epipolar geometry.
        Returns:
            Tuple of (camera_poses, total_inliers_found)
        """
        num_images = len(images)
        if num_images == 0:
            raise ValueError("No images provided for camera pose estimation.")

        if num_images == 1:
            # Single photo: Camera fixed at world origin looking down +Z axis
            single_pose = CameraPose(rotation=np.eye(3), translation=np.zeros((3, 1)))
            return [single_pose], 0

        # Multi-photo: Extract SIFT features for all images
        keypoints_list = []
        descriptors_list = []

        for idx, img in enumerate(images):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            kps, des = self.sift.detectAndCompute(gray, None)
            keypoints_list.append(kps)
            descriptors_list.append(des)

        K = intrinsics.matrix
        poses: List[CameraPose] = [CameraPose(rotation=np.eye(3), translation=np.zeros((3, 1)))]
        total_inliers = 0

        # Sequential pose chaining with fallback search across earlier reference frames
        for curr_idx in range(1, num_images):
            des_curr = descriptors_list[curr_idx]
            kps_curr = keypoints_list[curr_idx]

            best_prev_idx = -1
            best_inliers = 0
            best_R = np.eye(3)
            best_t = np.zeros((3, 1))

            if des_curr is not None and len(des_curr) >= 10:
                # Compare against immediate predecessor first, then any prior frames
                candidate_indices = [curr_idx - 1] + [j for j in range(curr_idx - 1) if j != curr_idx - 1]
                for prev_idx in candidate_indices:
                    des_prev = descriptors_list[prev_idx]
                    kps_prev = keypoints_list[prev_idx]
                    if des_prev is None or len(des_prev) < 10:
                        continue

                    # k-NN match with Lowe's ratio test
                    raw_matches = self.matcher.knnMatch(des_prev, des_curr, k=2)
                    good_matches = []
                    for match in raw_matches:
                        if len(match) == 2 and match[0].distance < 0.75 * match[1].distance:
                            good_matches.append(match[0])

                    if len(good_matches) >= 8:
                        pts_prev = np.float32([kps_prev[m.queryIdx].pt for m in good_matches])
                        pts_curr = np.float32([kps_curr[m.trainIdx].pt for m in good_matches])

                        E, mask = cv2.findEssentialMat(
                            pts_curr, pts_prev, K, method=cv2.RANSAC, prob=0.999, threshold=1.5
                        )
                        if E is not None and mask is not None:
                            inliers = int(np.sum(mask))
                            if inliers > best_inliers:
                                _, R_rel, t_rel, _ = cv2.recoverPose(E, pts_curr, pts_prev, K, mask=mask)
                                best_inliers = inliers
                                best_prev_idx = prev_idx
                                best_R = R_rel
                                best_t = t_rel

            min_pairwise_inliers = 20
            if best_inliers >= min_pairwise_inliers and best_prev_idx >= 0:
                total_inliers += best_inliers
                prev_pose = poses[best_prev_idx]
                # Global pose composition: R_curr = R_prev @ R_rel, t_curr = t_prev + R_prev @ t_rel
                R_curr = prev_pose.rotation @ best_R
                t_curr = prev_pose.translation + prev_pose.rotation @ best_t
                poses.append(CameraPose(rotation=R_curr, translation=t_curr))
            else:
                # Reject unregistered frame without arbitrary translation fallbacks
                logger.warning(
                    f"Camera pose recovery rejected for photo {curr_idx + 1}: "
                    f"insufficient geometric inliers ({best_inliers} found, {min_pairwise_inliers} required)."
                )
                raise InsufficientOverlapError(
                    f"Insufficient visual overlap between photographs ({best_inliers} verified inlier matches "
                    f"between photo {max(1, best_prev_idx + 1)} and photo {curr_idx + 1}; minimum required is {min_pairwise_inliers}). "
                    f"Please capture 4 to 8 photos with 30%–50% visual overlap across room corners and walls."
                )

        return poses, total_inliers

    def run(
        self,
        image_paths: List[str],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ImagePipelineOutput:
        """
        Execute full end-to-end multi-photo spatial reconstruction.
        """
        start_time = time.time()

        def report(stage: str, progress: float, message: str):
            if progress_cb:
                progress_cb(stage, progress, message)

        if not image_paths:
            raise ValueError("No photograph files provided for reconstruction.")

        # Stage 1: Validation and Image Preprocessing
        report("validating_images", 5.0, f"Validating {len(image_paths)} uploaded photographs...")
        loaded_images: List[np.ndarray] = []
        blur_scores: List[float] = []

        for p in image_paths:
            if not os.path.exists(p):
                raise ValueError(f"Photograph file not found at path: {p}")
            img = cv2.imread(p, cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                raise ValueError(f"Failed to read image at path: {p}")

            # Resize bounded to 1024 to keep CPU memory and ONNX inference bounded
            img_resized = resize_bounded(img, max_dim=1024)
            loaded_images.append(img_resized)
            blur_scores.append(calculate_image_blur(img_resized))

        first_h, first_w = loaded_images[0].shape[:2]
        avg_blur = float(np.mean(blur_scores)) if blur_scores else 0.0
        is_single = len(loaded_images) == 1

        logger.info(
            f"Image pipeline started: {len(loaded_images)} photos, initial resolution {first_w}x{first_h}, "
            f"average blur score: {avg_blur:.1f}"
        )

        # Stage 2: Camera Intrinsics & Pose Estimation
        report("extracting_features", 18.0, "Extracting spatial features and keypoint descriptors...")
        intrinsics = CameraIntrinsics.estimate_from_dimensions(first_w, first_h, fov_deg=65.0)

        report("estimating_cameras", 32.0, "Estimating multi-view camera poses and epipolar geometry...")
        poses, total_inliers = self.estimate_camera_poses(loaded_images, intrinsics)

        # Stage 3: Monocular Depth Estimation
        report("depth_estimation", 50.0, "Computing dense metric depth maps with MiDaS ONNX...")
        depth_results = self.depth_adapter.estimate_batch(loaded_images)

        # Stage 4: Semantic Segmentation
        report("semantic_segmentation", 65.0, "Segmenting walls, floors, ceilings, and architectural openings...")
        semantic_results = self.semantic_adapter.segment_batch(loaded_images)

        # Stage 5: Spatial Point Cloud Fusion
        report("spatial_reconstruction", 75.0, "Fusing 3D spatial point cloud into metric coordinate system...")
        point_cloud = reconstruct_point_cloud(
            images=loaded_images,
            poses=poses,
            depth_results=depth_results,
            semantic_results=semantic_results,
            intrinsics=intrinsics,
            subsample_step=8,
        )

        # Stage 6: 2D Floor Plan Generation
        report("generating_floor_plan", 85.0, "Extracting room polygons, walls, and boundary dimensions...")
        floor_plan = generate_floor_plan_from_point_cloud(point_cloud)

        if is_single:
            # Mark single-photo reconstruction as 2.5D estimated space
            floor_plan.quality_confidence = 0.50
            floor_plan.measurements_available = False
            if floor_plan.rooms:
                floor_plan.rooms[0]["name"] = "Single-Photo Estimated Space"
        else:
            floor_plan.quality_confidence = min(0.92, 0.70 + (total_inliers / 200.0) * 0.22)
            floor_plan.measurements_available = True

        # Stage 7: 3D Architectural Model Generation
        report("generating_3d_model", 95.0, "Extruding interactive 3D GLB model...")
        model_3d = generate_3d_model_from_floor_plan(floor_plan)

        total_duration = time.time() - start_time
        report("completed", 100.0, "Photograph spatial reconstruction completed successfully.")
        logger.info(f"Image pipeline completed in {total_duration:.2f} seconds.")

        metadata = ImagePipelineMetadata(
            image_count=len(loaded_images),
            width=first_w,
            height=first_h,
            is_single_image=is_single,
            average_blur_score=avg_blur,
            total_inliers=total_inliers,
        )

        return ImagePipelineOutput(
            metadata=metadata,
            point_cloud=point_cloud,
            floor_plan=floor_plan,
            model_3d=model_3d,
            duration_seconds=total_duration,
        )

