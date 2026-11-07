"""Stage A: Video Preprocessing and Keyframe Extraction using OpenCV."""

import os
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger


class VideoPreprocessingResult:
    """Container for video properties and extracted keyframe data."""

    def __init__(
        self,
        duration_seconds: float,
        fps: float,
        width: int,
        height: int,
        total_frames: int,
        keyframe_indices: List[int],
        keyframe_images: List[np.ndarray],
        keyframe_timestamps: List[float],
    ):
        self.duration_seconds = duration_seconds
        self.fps = fps
        self.width = width
        self.height = height
        self.total_frames = total_frames
        self.keyframe_indices = keyframe_indices
        self.keyframe_images = keyframe_images
        self.keyframe_timestamps = keyframe_timestamps


def calculate_blur_score(image: np.ndarray) -> float:
    """Compute variance of the Laplacian as a focus/blur measure."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def calculate_frame_difference(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate normalized histogram difference between two frames."""
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2

    hist1 = cv2.calcHist([gray1], [0], None, [64], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [64], [0, 256])
    cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    # Correlation comparison (1.0 = identical, < 0.8 = significant visual change)
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return max(0.0, 1.0 - similarity)


def process_video_keyframes(
    video_path: str,
    min_interval_seconds: Optional[float] = None,
    blur_threshold: Optional[float] = None,
    max_keyframes: int = 40,
) -> VideoPreprocessingResult:
    """
    OpenCV-based video decoder and keyframe extractor.
    Filters out blurry frames and selects keyframes with significant motion.
    """
    min_interval = min_interval_seconds or settings.KEYFRAME_MIN_INTERVAL_SECONDS
    min_blur = blur_threshold or settings.KEYFRAME_BLUR_THRESHOLD

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to decode video file: {video_path}. Unsupported or corrupt format.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0.0

    if total_frames <= 0 or width <= 0 or height <= 0:
        cap.release()
        raise ValueError("Invalid video stream dimensions or frame count.")

    min_frame_step = max(1, int(fps * min_interval))
    keyframe_indices: List[int] = []
    keyframe_images: List[np.ndarray] = []
    keyframe_timestamps: List[float] = []

    last_selected_frame: Optional[np.ndarray] = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps

        # Check candidate frame step
        if not keyframe_indices or (frame_idx - keyframe_indices[-1] >= min_frame_step):
            blur_score = calculate_blur_score(frame)

            # Only accept frames above sharpness threshold (or relax if list is empty)
            if blur_score >= min_blur or not keyframe_images:
                if last_selected_frame is None:
                    # Always include initial clear frame
                    keyframe_indices.append(frame_idx)
                    keyframe_images.append(frame.copy())
                    keyframe_timestamps.append(timestamp)
                    last_selected_frame = frame
                else:
                    diff = calculate_frame_difference(last_selected_frame, frame)
                    if diff >= settings.KEYFRAME_FEATURE_DIFF_RATIO or (frame_idx - keyframe_indices[-1] > fps * 3.0):
                        keyframe_indices.append(frame_idx)
                        keyframe_images.append(frame.copy())
                        keyframe_timestamps.append(timestamp)
                        last_selected_frame = frame

                if len(keyframe_images) >= max_keyframes:
                    break

        frame_idx += 1

    cap.release()

    # Fallback: If fewer than 3 keyframes extracted and video has frames, sample evenly spaced frames
    if len(keyframe_images) < 3 and total_frames > 0:
        cap = cv2.VideoCapture(video_path)
        target_count = min(total_frames, 5)
        step = max(1, total_frames // target_count)
        for i in range(0, total_frames, step):
            if i not in keyframe_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    keyframe_indices.append(i)
                    keyframe_images.append(frame.copy())
                    keyframe_timestamps.append(i / fps)
            if len(keyframe_images) >= target_count:
                break
        cap.release()


    logger.info(
        f"Video Preprocessing Complete: {duration:.1f}s, {width}x{height} @ {fps:.1f}fps, "
        f"{len(keyframe_images)} keyframes extracted."
    )

    return VideoPreprocessingResult(
        duration_seconds=duration,
        fps=fps,
        width=width,
        height=height,
        total_frames=total_frames,
        keyframe_indices=keyframe_indices,
        keyframe_images=keyframe_images,
        keyframe_timestamps=keyframe_timestamps,
    )
