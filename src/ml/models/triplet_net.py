"""Triplet embedding network based on ResNet50.

Architecture:
- ResNet50 backbone, frozen up to layer2
- Custom head: Linear(2048→512) → BatchNorm → ReLU → Dropout(0.3) → Linear(512→256) → L2Normalize
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models


class L2Normalize(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(x, p=2, dim=1)


class TripletNet(nn.Module):
    EMBEDDING_DIM = 256

    def __init__(self):
        super().__init__()
        backbone = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)

        # Freeze everything up to and including layer2
        freeze_until = {"layer2"}
        freeze = True
        for name, module in backbone.named_children():
            if name in freeze_until:
                freeze = False
            if freeze or name in freeze_until:
                for param in module.parameters():
                    param.requires_grad = False

        # Remove the original classifier
        self.backbone = nn.Sequential(*list(backbone.children())[:-1])  # output: (B, 2048, 1, 1)

        self.head = nn.Sequential(
            nn.Linear(2048, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, self.EMBEDDING_DIM),
            L2Normalize(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)          # (B, 2048, 1, 1)
        features = features.flatten(1)       # (B, 2048)
        embeddings = self.head(features)     # (B, 256)
        return embeddings
