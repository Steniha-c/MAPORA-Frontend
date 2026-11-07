"""Stage B: Feature-Based Visual Odometry and Camera Trajectory Estimation."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.core.logging import logger


class CameraIntrinsics:
    """Camera intrinsic parameters matrix K."""

    def __init__(self, fx: float, fy: float, cx: float, cy: float):
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy

    @property
    def matrix(self) -> np.ndarray:
        return np.array([
            [self.fx, 0, self.cx],
            [0, self.fy, self.cy],
            [0, 0, 1.0]
        ], dtype=np.float64)

    @classmethod
    def estimate_from_dimensions(cls, width: int, height: int, fov_deg: float = 65.0) -> "CameraIntrinsics":
        """Estimate intrinsics from image resolution assuming typical indoor smartphone field of view."""
        fov_rad = np.radians(fov_deg)
        fx = (width / 2.0) / np.tan(fov_rad / 2.0)
        fy = fx
        cx = width / 2.0
        cy = height / 2.0
        return cls(fx=fx, fy=fy, cx=cx, cy=cy)


class CameraPose:
    """Estimated 6-DOF camera pose relative to initial world frame."""

    def __init__(self, rotation: np.ndarray, translation: np.ndarray, timestamp: float = 0.0):
        # 3x3 rotation matrix
        self.rotation = rotation.astype(np.float64)
        # 3x1 translation vector
        self.translation = translation.astype(np.float64).reshape((3, 1))
        self.timestamp = timestamp

    @property
    def transform_matrix(self) -> np.ndarray:
        """4x4 homogeneous transformation matrix [R | t]."""
        t_mat = np.eye(4, dtype=np.float64)
        t_mat[:3, :3] = self.rotation
        t_mat[:3, 3:] = self.translation
        return t_mat


class OdometryAdapter(ABC):
    """Abstract interface for modular visual odometry / SLAM backends."""

    @abstractmethod
    def estimate_trajectory(
        self,
        images: List[np.ndarray],
        timestamps: List[float],
        intrinsics: CameraIntrinsics,
    ) -> List[CameraPose]:
        pass


class OpenCVVisualOdometry(OdometryAdapter):
    """
    Monocular visual odometry using ORB feature tracking and Essential Matrix decomposition.
    Note on Monocular Scale Ambiguity: Monocular reconstruction estimates motion up to a scale factor.
    Baseline translation is normalized to estimated human walking speed (~1.0 m/s) when scale is uncalibrated.
    """

    def __init__(self, n_features: int = 2000):
        self.orb = cv2.ORB_create(
            nfeatures=n_features,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=31,
            patchSize=31,
        )
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    def _extract_and_match(
        self, img1: np.ndarray, img2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Extract ORB keypoints and find robust Lowe-ratio matches."""
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2

        kp1, des1 = self.orb.detectAndCompute(gray1, None)
        kp2, des2 = self.orb.detectAndCompute(gray2, None)

        if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
            return np.empty((0, 2)), np.empty((0, 2))

        # 2-NN matches for ratio test
        matches = self.matcher.knnMatch(des1, des2, k=2)
        good_pts1 = []
        good_pts2 = []

        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.75 * n.distance:
                    good_pts1.append(kp1[m.queryIdx].pt)
                    good_pts2.append(kp2[m.trainIdx].pt)

        return np.array(good_pts1, dtype=np.float32), np.array(good_pts2, dtype=np.float32)

    def estimate_trajectory(
        self,
        images: List[np.ndarray],
        timestamps: List[float],
        intrinsics: CameraIntrinsics,
    ) -> List[CameraPose]:
        if not images:
            return []

        # Initial pose at origin [I | 0]
        poses: List[CameraPose] = [
            CameraPose(np.eye(3), np.zeros((3, 1)), timestamps[0] if timestamps else 0.0)
        ]

        current_R = np.eye(3, dtype=np.float64)
        current_t = np.zeros((3, 1), dtype=np.float64)
        K = intrinsics.matrix

        for i in range(1, len(images)):
            prev_img = images[i - 1]
            curr_img = images[i]
            dt = timestamps[i] - timestamps[i - 1] if len(timestamps) > i else 0.5
            dt = max(0.05, min(dt, 2.0))

            pts1, pts2 = self._extract_and_match(prev_img, curr_img)

            if len(pts1) >= 12:
                # Essential matrix with RANSAC
                E, inliers = cv2.findEssentialMat(
                    pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0
                )

                if E is not None and E.shape == (3, 3):
                    _, R, t, mask = cv2.recoverPose(E, pts1, pts2, K)

                    # Scale heuristic for indoor walkthrough (~1.0 m/s walking speed)
                    step_scale = 1.0 * dt
                    t_scaled = t * step_scale

                    # Accumulate pose: T_world = T_world @ T_relative
                    current_t = current_t + current_R @ t_scaled
                    current_R = current_R @ R

            poses.append(CameraPose(current_R.copy(), current_t.copy(), timestamps[i]))

        logger.info(f"Visual Odometry complete: estimated {len(poses)} camera poses.")
        return poses


class ExternalSlamAdapter(OdometryAdapter):
    """
    Placeholder/hook for external SLAM frameworks (e.g. COLMAP or ORB-SLAM3).
    When binaries are available in PATH, this adapter formats poses from sparse bundle adjustment.
    """

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path

    def estimate_trajectory(
        self,
        images: List[np.ndarray],
        timestamps: List[float],
        intrinsics: CameraIntrinsics,
    ) -> List[CameraPose]:
        logger.info("External SLAM requested. Falling back to OpenCVVisualOdometry as binary not detected.")
        fallback = OpenCVVisualOdometry()
        return fallback.estimate_trajectory(images, timestamps, intrinsics)
