"""DINOv2 ViT-L/14 (with registers) wrapper for pet re-identification.

Meta's self-supervised ViT-L trained on 142M images.
Outputs 1024-dim L2-normalized embeddings.
Cosine similarity of same-animal photos: ~80-85%.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DINOv2Net(nn.Module):
    EMBEDDING_DIM = 1024

    def __init__(self):
        super().__init__()
        self.backbone = torch.hub.load(
            "facebookresearch/dinov2",
            "dinov2_vitl14_reg",
            verbose=False,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)  # (B, 1024)
        return F.normalize(features, p=2, dim=1)
