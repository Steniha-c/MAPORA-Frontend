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
    Loads local offline MiDaS checkpoints deterministically without PyTorch Hub network requests.
    """

    def __init__(self, model_type: Optional[str] = None):
        self.model_type = model_type or settings.MIDAS_MODEL_TYPE
        self.device = torch.device(settings.DEVICE if torch.cuda.is_available() and settings.DEVICE == "cuda" else "cpu")
        self.model: Optional[torch.nn.Module] = None
        self.transform = None
        self._initialized = False

    def _load_offline_midas_small(self) -> bool:
        """Load MiDaS v2.1 Small model and transforms from local disk without any network requests."""
        possible_weight_paths = [
            Path("backend/models_cache/weights/midas_v21_small_256.pt"),
            Path("backend/models_cache/intel-isl_MiDaS_master/weights/midas_v21_small_256.pt"),
            Path(settings.MODEL_WEIGHTS_DIR) / "weights" / "midas_v21_small_256.pt",
            Path(settings.MODEL_WEIGHTS_DIR) / "midas_v21_small_256.pt",
        ]

        weights_file = None
        for p in possible_weight_paths:
            if p.exists() and p.stat().st_size > 10_000_000:
                weights_file = p
                break

        if not weights_file:
            return False

        repo_dir = Path("backend/models_cache/intel-isl_MiDaS_master")
        if not repo_dir.exists():
            repo_dir = Path(settings.MODEL_WEIGHTS_DIR) / "intel-isl_MiDaS_master"

        if not repo_dir.exists():
            return False

        try:
            import sys
            import timm
            import torch.nn as nn

            repo_str = str(repo_dir.resolve())
            if repo_str not in sys.path:
                sys.path.insert(0, repo_str)

            import midas.blocks as B

            def custom_effnet(use_pretrained, exportable=False):
                effnet = timm.create_model("tf_efficientnet_lite3", pretrained=False)
                pretrained = nn.Module()
                act1 = getattr(effnet, "act1", nn.ReLU6(inplace=True))
                pretrained.layer1 = nn.Sequential(effnet.conv_stem, effnet.bn1, act1, *effnet.blocks[0:2])
                pretrained.layer2 = nn.Sequential(*effnet.blocks[2:3])
                pretrained.layer3 = nn.Sequential(*effnet.blocks[3:5])
                pretrained.layer4 = nn.Sequential(*effnet.blocks[5:9])
                return pretrained

            B._make_pretrained_efficientnet_lite3 = custom_effnet

            from midas.model_loader import load_model

            model, transform, net_w, net_h = load_model(
                str(self.device),
                str(weights_file),
                "midas_v21_small_256",
                optimize=False,
            )
            self.model = model
            self.transform = transform
            self._initialized = True
            logger.info(f"Loaded genuine MiDaS Small model offline from {weights_file} (device={self.device})")
            return True
        except Exception as e:
            logger.error(f"Failed to load offline MiDaS model: {e}")
            return False

    def initialize_model(self) -> bool:
        """Attempt to load MiDaS PyTorch model from local cache first, then torch hub."""
        if self._initialized and self.model is not None:
            return True

        logger.info(f"Initializing {self.model_type} monocular depth model on {self.device}...")

        # 1. Attempt offline local loading first (guaranteed zero-network, immune to HTTP 403)
        if self._load_offline_midas_small():
            return True

        # 2. Secondary fallback: Attempt torch.hub if network is available
        try:
            torch.hub.set_dir(settings.MODEL_WEIGHTS_DIR)
            self.model = torch.hub.load("intel-isl/MiDaS", self.model_type, trust_repo=True)
            self.model.to(self.device)
            self.model.eval()

            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
            if self.model_type in ["DPT_Large", "DPT_Hybrid"]:
                self.transform = midas_transforms.dpt_transform
            else:
                self.transform = midas_transforms.small_transform

            self._initialized = True
            logger.info(f"Successfully loaded {self.model_type} depth model via torch.hub.")
            return True
        except Exception as e:
            logger.error(
                f"Could not load MiDaS model weights from network/cache: {e}. "
                "Local weights midas_v21_small_256.pt must be present in backend/models_cache/weights/."
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

        if self.model is None or self.transform is None:
            raise RuntimeError(
                "Monocular depth estimation failed: Genuine MiDaS neural model weights are unavailable. "
                "Silent synthetic depth substitution has been disabled. "
                "Ensure midas_v21_small_256.pt is located in backend/models_cache/weights/."
            )

        h, w = image.shape[:2]
        rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Handle transform whether it's Compose from model_loader or torchvision transform
        if callable(self.transform):
            try:
                # midas.model_loader transforms take dict: {"image": rgb_img}
                transformed = self.transform({"image": rgb_img})
                if isinstance(transformed, dict):
                    input_batch = torch.from_numpy(transformed["image"]).to(self.device).unsqueeze(0)
                else:
                    input_batch = transformed.to(self.device)
                    if input_batch.dim() == 3:
                        input_batch = input_batch.unsqueeze(0)
            except Exception:
                input_batch = self.transform(rgb_img).to(self.device)
                if input_batch.dim() == 3:
                    input_batch = input_batch.unsqueeze(0)
        else:
            raise RuntimeError("Invalid transform object in DepthEstimationAdapter.")

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

        return DepthEstimationResult(depth_meters, is_model_inferred=True, model_name="MiDaS_small_v21")

    def estimate_batch(self, images: List[np.ndarray]) -> List[DepthEstimationResult]:
        """Estimate depth for multiple keyframes."""
        return [self.estimate_depth(img) for img in images]
