"""Stage C: Monocular Depth Estimation Adapter (MiDaS / DPT)."""

import os
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
import torch

from app.core.config import settings
from app.core.logging import logger


class DepthEstimationResult:
    """Estimated metric or relative depth map for a keyframe."""

    def __init__(self, depth_map: np.ndarray, is_model_inferred: bool = True, model_name: str = "MiDaS"):
        # 2D float32 numpy array with depth in meters or normalized relative depth
        self.depth_map = depth_map.astype(np.float32)
        self.is_model_inferred = is_model_inferred
        self.model_name = model_name


class DepthEstimationAdapter:
    """
    Adapter for PyTorch monocular depth estimation.
    Supports MiDaS / DPT models with automatic device selection (CUDA/CPU).
    Gracefully falls back to gradient-structural depth estimation if model weights are not loaded.
    """

    def __init__(self, model_type: Optional[str] = None):
        self.model_type = model_type or settings.MIDAS_MODEL_TYPE
        self.device = torch.device(settings.DEVICE if torch.cuda.is_available() and settings.DEVICE == "cuda" else "cpu")
        self.model: Optional[torch.nn.Module] = None
        self.transform = None
        self._initialized = False

    def initialize_model(self) -> bool:
        """Attempt to load MiDaS PyTorch model from torch hub or local cache."""
        if self._initialized:
            return self.model is not None

        try:
            logger.info(f"Attempting to load {self.model_type} monocular depth model on {self.device}...")
            # Set torch hub cache directory to settings.MODEL_WEIGHTS_DIR
            torch.hub.set_dir(settings.MODEL_WEIGHTS_DIR)

            # Attempt loading MiDaS model
            self.model = torch.hub.load("intel-isl/MiDaS", self.model_type, trust_repo=True)
            self.model.to(self.device)
            self.model.eval()

            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
            if self.model_type in ["DPT_Large", "DPT_Hybrid"]:
                self.transform = midas_transforms.dpt_transform
            else:
                self.transform = midas_transforms.small_transform

            self._initialized = True
            logger.info(f"Successfully loaded {self.model_type} depth model.")
            return True
        except Exception as e:
            logger.warning(
                f"Could not load MiDaS model weights from network/cache: {e}. "
                "Activating geometric depth estimation fallback."
            )
            self.model = None
            self.transform = None
            self._initialized = True
            return False

    def estimate_depth(self, image: np.ndarray) -> DepthEstimationResult:
        """
        Estimate 2D depth map from a single RGB image.
        Returns DepthEstimationResult with depth values scaled to approximate meters (0.5m to 12.0m).
        """
        if not self._initialized:
            self.initialize_model()

        h, w = image.shape[:2]

        if self.model is not None and self.transform is not None:
            try:
                rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                input_batch = self.transform(rgb_img).to(self.device)

                with torch.no_grad():
                    prediction = self.model(input_batch)
                    prediction = torch.nn.functional.interpolate(
                        prediction.unsqueeze(1),
                        size=(h, w),
                        mode="bicubic",
                        align_corners=False,
                    ).squeeze()

                output = prediction.cpu().numpy()
                # Normalize inverse depth to metric range for indoor rooms (0.5m - 8.0m)
                inv_min, inv_max = np.percentile(output, 2), np.percentile(output, 98)
                norm_inv = np.clip((output - inv_min) / max(1e-6, inv_max - inv_min), 0.05, 1.0)
                # Invert: higher disparity = closer distance
                depth_meters = 1.0 / (norm_inv + 0.1) * 2.0
                depth_meters = np.clip(depth_meters, 0.5, 10.0)

                return DepthEstimationResult(depth_meters, is_model_inferred=True, model_name=self.model_type)
            except Exception as e:
                logger.error(f"Inference error with {self.model_type}: {e}. Falling back to structural depth.")

        # Heuristic structural depth estimation fallback:
        # Uses vertical horizon gradient and edge density to approximate indoor room perspective
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        dist_transform = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
        dist_norm = cv2.normalize(dist_transform, None, 0, 1.0, cv2.NORM_MINMAX)

        y_indices, _ = np.indices((h, w))
        horizon_y = h * 0.55
        vertical_gradient = np.abs(y_indices - horizon_y) / (h * 0.5)
        vertical_gradient = np.clip(vertical_gradient, 0.1, 1.0)

        # Indoor rooms: horizon and corners have larger depth; floor near bottom is closer
        depth_map = (1.5 + (1.0 - vertical_gradient) * 3.5 + dist_norm * 1.5).astype(np.float32)
        depth_map = np.clip(depth_map, 0.8, 8.0)

        return DepthEstimationResult(depth_map, is_model_inferred=False, model_name="HeuristicGeometricDepth")

    def estimate_batch(self, images: List[np.ndarray]) -> List[DepthEstimationResult]:
        """Estimate depth for multiple keyframes."""
        return [self.estimate_depth(img) for img in images]
