"""YOLOv8 pet detection and segmentation.

Uses yolov8m-seg pretrained on COCO.
COCO class 15 = cat, class 16 = dog.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

PET_CLASSES = {15: "CAT", 16: "DOG"}


class PetDetector:
    def __init__(self, model_name: str = "yolov8m-seg.pt", conf: float = 0.25):
        from ultralytics import YOLO
        self.model = YOLO(model_name)
        self.conf = conf

    def best_detection(self, image: Image.Image) -> Optional[dict]:
        """
        Run YOLOv8 on the image and return the highest-confidence pet detection.

        Returns a dict with:
          - class_id: int
          - species: str ("CAT" or "DOG")
          - confidence: float
          - bbox: (x1, y1, x2, y2)
          - masked: PIL.Image (background removed, cropped to bbox)

        Returns None if no pet is detected.
        """
        results = self.model(image, conf=self.conf, verbose=False)

        best = None
        best_conf = -1.0

        for result in results:
            if result.boxes is None:
                continue
            for i, box in enumerate(result.boxes):
                cls_id = int(box.cls[0].item())
                if cls_id not in PET_CLASSES:
                    continue
                conf = float(box.conf[0].item())
                if conf <= best_conf:
                    continue

                best_conf = conf
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                # Build masked crop
                masked_img = self._apply_mask(image, result, i, x1, y1, x2, y2)

                best = {
                    "class_id": cls_id,
                    "species": PET_CLASSES[cls_id],
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                    "masked": masked_img,
                }

        return best

    def _apply_mask(
        self,
        image: Image.Image,
        result,
        index: int,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> Image.Image:
        """Apply segmentation mask and return cropped image."""
        img_np = np.array(image)

        if result.masks is not None and index < len(result.masks):
            mask_data = result.masks[index].data[0].cpu().numpy()
            # Resize mask to original image size
            mask_pil = Image.fromarray((mask_data * 255).astype(np.uint8)).resize(
                image.size, Image.NEAREST
            )
            mask_np = np.array(mask_pil)

            # Apply mask: zero out background
            masked = img_np.copy()
            masked[mask_np == 0] = 0
        else:
            masked = img_np

        # Crop to bounding box
        cropped = masked[y1:y2, x1:x2]
        return Image.fromarray(cropped)
