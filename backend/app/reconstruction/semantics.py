"""Stage D: Indoor Semantic Segmentation Adapter (Walls, Floors, Openings)."""

from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.core.logging import logger


class SemanticClass:
    WALL = 1
    FLOOR = 2
    CEILING = 3
    DOOR = 4
    WINDOW = 5
    FURNITURE = 6
    UNKNOWN = 0


CLASS_NAMES = {
    SemanticClass.UNKNOWN: "unknown",
    SemanticClass.WALL: "wall",
    SemanticClass.FLOOR: "floor",
    SemanticClass.CEILING: "ceiling",
    SemanticClass.DOOR: "door",
    SemanticClass.WINDOW: "window",
    SemanticClass.FURNITURE: "furniture",
}


class SemanticSegmentationResult:
    """Class label map and confidence scores for an indoor image."""

    def __init__(
        self,
        class_mask: np.ndarray,
        confidence_mask: np.ndarray,
        is_dl_inferred: bool = False,
        model_name: str = "IndoorGeometricSegmenter",
    ):
        self.class_mask = class_mask.astype(np.uint8)
        self.confidence_mask = confidence_mask.astype(np.float32)
        self.is_dl_inferred = is_dl_inferred
        self.model_name = model_name


class SemanticSegmentationAdapter:
    """
    Adapter for semantic parsing of architectural indoor walkthrough images.
    Identifies walls, floor planes, ceilings, and candidate door/window openings.
    """

    def __init__(self, use_deep_model: bool = False):
        self.use_deep_model = use_deep_model
        self._initialized = False

    def segment_image(self, image: np.ndarray) -> SemanticSegmentationResult:
        """
        Produce a dense semantic class mask and confidence map.
        Uses perspective geometric partition and color-edge analysis when deep segmentation weights are not bundled.
        """
        h, w = image.shape[:2]
        class_mask = np.zeros((h, w), dtype=np.uint8)
        confidence_mask = np.full((h, w), 0.70, dtype=np.float32)

        # Baseline indoor geometric partitioning:
        # Lower 30% is predominantly floor
        floor_y = int(h * 0.70)
        class_mask[floor_y:, :] = SemanticClass.FLOOR
        confidence_mask[floor_y:, :] = 0.85

        # Upper 20% is predominantly ceiling
        ceiling_y = int(h * 0.20)
        class_mask[:ceiling_y, :] = SemanticClass.CEILING
        confidence_mask[:ceiling_y, :] = 0.80

        # Middle zone is primarily wall
        class_mask[ceiling_y:floor_y, :] = SemanticClass.WALL
        confidence_mask[ceiling_y:floor_y, :] = 0.88

        # Edge analysis for door/window rectangular openings
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=50, maxLineGap=10)

        if lines is not None:
            for line in lines:
                coords = line.flatten()
                if len(coords) >= 4:
                    x1, y1, x2, y2 = coords[:4]
                    # Vertical lines in wall region indicate potential door frames or windows
                    if abs(x2 - x1) < 15 and abs(y2 - y1) > 60:
                        mid_y = int((y1 + y2) // 2)
                        if ceiling_y < mid_y < floor_y:
                            # Candidate opening boundary
                            min_x = max(0, int(min(x1, x2)) - 10)
                            max_x = min(w, int(max(x1, x2)) + 10)
                            class_mask[int(min(y1, y2)):int(max(y1, y2)), min_x:max_x] = SemanticClass.DOOR
                            confidence_mask[int(min(y1, y2)):int(max(y1, y2)), min_x:max_x] = 0.75


        return SemanticSegmentationResult(
            class_mask=class_mask,
            confidence_mask=confidence_mask,
            is_dl_inferred=False,
            model_name="IndoorGeometricSegmenter",
        )

    def segment_batch(self, images: List[np.ndarray]) -> List[SemanticSegmentationResult]:
        return [self.segment_image(img) for img in images]
