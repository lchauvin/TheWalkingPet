"""Inference wrapper for the triplet embedding network."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import torch
from PIL import Image

from src.ml.models.triplet_net import TripletNet
from src.ml.training.augmentations import EVAL_TRANSFORM

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 256


class PetEmbedder:
    def __init__(self, checkpoint_path: str | Path | None = None, device: str | None = None):
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model = TripletNet().to(self.device)
        self.model.eval()

        if checkpoint_path and Path(checkpoint_path).exists():
            state = torch.load(checkpoint_path, map_location=self.device)
            # Handle Lightning checkpoints that wrap state_dict
            if "state_dict" in state:
                state = state["state_dict"]
            # Strip "model." prefix if present
            state = {k.replace("model.", ""): v for k, v in state.items()}
            self.model.load_state_dict(state, strict=False)
            logger.info(f"[Embedder] Loaded checkpoint from {checkpoint_path}")
        else:
            logger.warning("[Embedder] No checkpoint loaded — using random weights.")

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
