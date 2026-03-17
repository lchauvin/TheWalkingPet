"""Inference wrapper for DINOv2 embedding network."""
from __future__ import annotations

import logging
from typing import List

import torch
import torch.nn.functional as F
from PIL import Image

from src.ml.models.dinov2 import DINOv2Net
from src.ml.training.augmentations import EVAL_TRANSFORM, TTA_TRANSFORMS

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024


class PetEmbedder:
    def __init__(self, checkpoint_path: str | None = None, device: str | None = None):
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        logger.info(f"[Embedder] Loading DINOv2 ViT-L/14 on {self.device}...")
        self.model = DINOv2Net().to(self.device)
        self.model.eval()
        logger.info("[Embedder] DINOv2 ready.")

    @torch.no_grad()
    def embed_image(self, image: Image.Image) -> List[float]:
        """Embed a single PIL image, return as a Python list of floats."""
        tensor = EVAL_TRANSFORM(image).unsqueeze(0).to(self.device)
        embedding = self.model(tensor)
        return embedding.squeeze(0).cpu().tolist()

    @torch.no_grad()
    def embed_batch(self, images: list[Image.Image]) -> list[list[float]]:
        """Embed a batch of PIL images."""
        tensors = torch.stack([EVAL_TRANSFORM(img) for img in images]).to(self.device)
        embeddings = self.model(tensors)
        return embeddings.cpu().tolist()

    @torch.no_grad()
    def embed_image_tta(self, image: Image.Image) -> List[float]:
        """Embed with test-time augmentation: average over multiple augmented views.

        Used for registration photos only (sightings use single-pass for speed).
        """
        tensors = torch.stack([t(image) for t in TTA_TRANSFORMS]).to(self.device)
        embeddings = self.model(tensors)  # (N, 1024), already L2-normalized per forward()
        avg = embeddings.mean(dim=0)
        avg = F.normalize(avg, p=2, dim=0)
        return avg.cpu().tolist()
