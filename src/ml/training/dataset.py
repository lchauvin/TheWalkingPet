"""Pet identity dataset for metric learning.

Loads images as flat (image, label_int) pairs — compatible with
pytorch-metric-learning's MPerClassSampler which needs a `labels` property.

Expected directory structure:
  root/
    <identity_id>/
      image1.jpg
      image2.jpg
      ...
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from torch.utils.data import Dataset

from src.ml.training.augmentations import EVAL_TRANSFORM, TRAIN_TRANSFORM

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class PetIdentityDataset(Dataset):
    def __init__(self, root: str | Path, train: bool = True):
        self.root = Path(root)
        self.transform = TRAIN_TRANSFORM if train else EVAL_TRANSFORM

        self._samples: list[tuple[Path, int]] = []
        self._class_to_idx: dict[str, int] = {}

        identity_dirs = sorted([d for d in self.root.iterdir() if d.is_dir()])
        for idx, identity_dir in enumerate(identity_dirs):
            class_name = identity_dir.name
            self._class_to_idx[class_name] = idx
            for img_path in identity_dir.iterdir():
                if img_path.suffix.lower() in IMAGE_EXTENSIONS:
                    self._samples.append((img_path, idx))

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, index: int):
        img_path, label = self._samples[index]
        image = Image.open(img_path).convert("RGB")
        return self.transform(image), label

    @property
    def labels(self) -> np.ndarray:
        """Required by MPerClassSampler."""
        return np.array([label for _, label in self._samples])

    @property
    def num_classes(self) -> int:
        return len(self._class_to_idx)
