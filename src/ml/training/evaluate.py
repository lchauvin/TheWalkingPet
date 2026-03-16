"""Evaluation metrics: CMC (Rank-1/5/10) and mAP.

Usage:
    python -m src.ml.training.evaluate --data data/cats --checkpoint models/best.pt
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.ml.embedder import PetEmbedder
from src.ml.training.dataset import PetIdentityDataset

logger = logging.getLogger(__name__)


def extract_embeddings(
    embedder: PetEmbedder,
    dataset: PetIdentityDataset,
    batch_size: int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    all_embs, all_labels = [], []
    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(embedder.device)
            embs = embedder.model(imgs)
            all_embs.append(embs.cpu().numpy())
            all_labels.append(labels.numpy())
    return np.vstack(all_embs), np.concatenate(all_labels)


def compute_cmc_map(
    embeddings: np.ndarray,
    labels: np.ndarray,
    ranks: list[int] = [1, 5, 10],
) -> dict:
    """Compute CMC and mAP using cosine similarity."""
    # Normalize (should already be normalized, but just in case)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embs = embeddings / (norms + 1e-8)

    sim_matrix = embs @ embs.T  # (N, N)
    np.fill_diagonal(sim_matrix, -1.0)  # exclude self

    n = len(labels)
    cmc_counts = {r: 0 for r in ranks}
    ap_list = []

    for i in range(n):
        sorted_idx = np.argsort(-sim_matrix[i])
        sorted_labels = labels[sorted_idx]
        gt_mask = sorted_labels == labels[i]

        # CMC
        for r in ranks:
            if gt_mask[:r].any():
                cmc_counts[r] += 1

        # AP
        hits = 0
        precision_sum = 0.0
        for j, is_match in enumerate(gt_mask):
            if is_match:
                hits += 1
                precision_sum += hits / (j + 1)
        total_relevant = gt_mask.sum()
        ap_list.append(precision_sum / total_relevant if total_relevant > 0 else 0.0)

    results = {f"rank_{r}": cmc_counts[r] / n for r in ranks}
    results["mAP"] = float(np.mean(ap_list))
    return results


def evaluate(data_dir: str, checkpoint: str | None = None) -> dict:
    from src.ml.training.augmentations import EVAL_TRANSFORM
    dataset = PetIdentityDataset(data_dir, train=False)
    embedder = PetEmbedder(checkpoint_path=checkpoint)

    embeddings, labels = extract_embeddings(embedder, dataset)
    metrics = compute_cmc_map(embeddings, labels)

    print(f"Rank-1:  {metrics['rank_1']:.1%}")
    print(f"Rank-5:  {metrics['rank_5']:.1%}")
    print(f"Rank-10: {metrics['rank_10']:.1%}")
    print(f"mAP:     {metrics['mAP']:.1%}")
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to identity dataset root")
    parser.add_argument("--checkpoint", default=None, help="Path to model checkpoint")
    args = parser.parse_args()
    evaluate(args.data, args.checkpoint)
