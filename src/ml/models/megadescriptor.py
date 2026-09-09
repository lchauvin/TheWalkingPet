"""MegaDescriptor-L-384 wrapper for zero-shot animal re-identification.

WACV 2024 Best Paper — Swin Transformer trained on 29 animal re-ID datasets with ArcFace loss.
HuggingFace: BVRA/MegaDescriptor-L-384
Output: 1536-dim L2-normalized embedding.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class MegaDescriptorNet(nn.Module):
    EMBEDDING_DIM = 1536

    def __init__(self):
        super().__init__()
        import timm
        self.backbone = timm.create_model(
            "hf-hub:BVRA/MegaDescriptor-L-384",
            pretrained=True,
            num_classes=0,  # remove classification head, return features
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)  # (B, 1536)
        return F.normalize(features, p=2, dim=1)
