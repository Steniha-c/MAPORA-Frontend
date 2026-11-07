"""Stage E: Spatial Reconstruction - 3D Point Cloud Generation and Coordinate Alignment."""

from typing import List, Optional, Tuple
import numpy as np

from app.core.logging import logger
from app.reconstruction.odometry import CameraIntrinsics, CameraPose
from app.reconstruction.depth import DepthEstimationResult
from app.reconstruction.semantics import SemanticSegmentationResult


class PointCloudResult:
    """Consolidated 3D point cloud with semantic attributes."""

    def __init__(
        self,
        points: np.ndarray,      # (N, 3) float32
        colors: np.ndarray,      # (N, 3) uint8
        semantics: np.ndarray,   # (N,) uint8
        bounds_min: np.ndarray,  # (3,) float32
        bounds_max: np.ndarray,  # (3,) float32
    ):
        self.points = points
        self.colors = colors
        self.semantics = semantics
        self.bounds_min = bounds_min
        self.bounds_max = bounds_max

    @property
    def point_count(self) -> int:
        return len(self.points)


def voxel_downsample(
    points: np.ndarray,
    colors: np.ndarray,
    semantics: np.ndarray,
    voxel_size: float = 0.05,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simple and fast voxel grid filtering."""
    if len(points) == 0:
        return points, colors, semantics

    voxel_indices = np.floor(points / voxel_size).astype(np.int64)
    # Convert 3D indices to unique hash keys
    _, unique_indices = np.unique(voxel_indices, axis=0, return_index=True)

    return points[unique_indices], colors[unique_indices], semantics[unique_indices]


def reconstruct_point_cloud(
    images: List[np.ndarray],
    poses: List[CameraPose],
    depth_results: List[DepthEstimationResult],
    semantic_results: List[SemanticSegmentationResult],
    intrinsics: CameraIntrinsics,
    subsample_step: int = 8,
) -> PointCloudResult:
    """
    Back-project 2D depth maps with camera poses into a shared 3D coordinate system.
    """
    all_points = []
    all_colors = []
    all_semantics = []

    fx, fy = intrinsics.fx, intrinsics.fy
    cx, cy = intrinsics.cx, intrinsics.cy

    num_frames = min(len(images), len(poses), len(depth_results), len(semantic_results))

    for i in range(num_frames):
        img = images[i]
        pose = poses[i]
        depth_map = depth_results[i].depth_map
        sem_mask = semantic_results[i].class_mask

        h, w = depth_map.shape[:2]
        # Subsample grid for computational efficiency
        u = np.arange(0, w, subsample_step)
        v = np.arange(0, h, subsample_step)
        uu, vv = np.meshgrid(u, v)

        z = depth_map[vv, uu]
        # Discard extreme invalid depth
        valid_mask = (z > 0.4) & (z < 10.0)

        uu_valid = uu[valid_mask]
        vv_valid = vv[valid_mask]
        z_valid = z[valid_mask]

        x_cam = (uu_valid - cx) * z_valid / fx
        y_cam = (vv_valid - cy) * z_valid / fy
        points_cam = np.stack([x_cam, y_cam, z_valid], axis=-1)  # (M, 3)

        # Transform to world coordinates: P_world = R @ P_cam + t
        R = pose.rotation
        t = pose.translation.flatten()
        points_world = (points_cam @ R.T) + t

        colors_bgr = img[vv_valid, uu_valid]
        colors_rgb = colors_bgr[:, [2, 1, 0]]  # BGR to RGB
        classes = sem_mask[vv_valid, uu_valid]

        all_points.append(points_world)
        all_colors.append(colors_rgb)
        all_semantics.append(classes)

    if all_points:
        pts = np.vstack(all_points).astype(np.float32)
        cols = np.vstack(all_colors).astype(np.uint8)
        sems = np.concatenate(all_semantics).astype(np.uint8)

        # Statistical outlier removal along gravity axis
        pts, cols, sems = voxel_downsample(pts, cols, sems, voxel_size=0.08)

        # Normalize coordinate system so floor is at Y=0
        y_min = np.percentile(pts[:, 1], 2)
        pts[:, 1] -= y_min

        bounds_min = np.min(pts, axis=0)
        bounds_max = np.max(pts, axis=0)
    else:
        pts = np.empty((0, 3), dtype=np.float32)
        cols = np.empty((0, 3), dtype=np.uint8)
        sems = np.empty((0,), dtype=np.uint8)
        bounds_min = np.zeros(3, dtype=np.float32)
        bounds_max = np.zeros(3, dtype=np.float32)

    logger.info(f"Spatial Reconstruction complete: produced point cloud with {len(pts)} points.")

    return PointCloudResult(
        points=pts,
        colors=cols,
        semantics=sems,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
    )
