"""Training script for the triplet embedding network.

Uses pytorch-metric-learning with BatchHardMiner and online hard mining.

Usage:
    python -m src.ml.training.train --data data/cats --epochs 100 --output models/
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from src.ml.models.triplet_net import TripletNet
from src.ml.training.dataset import PetIdentityDataset

logger = logging.getLogger(__name__)


def train(
    data_dir: str,
    output_dir: str = "models",
    epochs: int = 100,
    batch_size: int = 128,
    lr: float = 1e-4,
    patience: int = 15,
    m_per_class: int = 4,
):
    from pytorch_metric_learning import distances, losses, miners, samplers

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    dataset = PetIdentityDataset(data_dir, train=True)
    logger.info(f"Dataset: {len(dataset)} images, {dataset.num_classes} identities")

    sampler = samplers.MPerClassSampler(
        labels=dataset.labels,
        m=m_per_class,
        batch_size=batch_size,
        length_before_new_iter=len(dataset),
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        sampler=sampler,
        num_workers=4,
        pin_memory=True,
        drop_last=True,
    )

    model = TripletNet().to(device)
    optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

    distance_fn = distances.CosineSimilarity()
    miner = miners.BatchHardMiner(distance=distance_fn)
    criterion = losses.TripletMarginLoss(margin=0.2, distance=distance_fn)

    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))
    writer = SummaryWriter(log_dir=str(output_path / "runs"))

    best_loss = float("inf")
    patience_counter = 0
    best_checkpoint = output_path / "best.pt"

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_pairs = 0

        for imgs, labels in loader:
            imgs = imgs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            with torch.autocast(device.type, enabled=(device.type == "cuda")):
                embeddings = model(imgs)
                hard_pairs = miner(embeddings, labels)
                loss = criterion(embeddings, labels, hard_pairs)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()
            total_pairs += 1

        scheduler.step()
        avg_loss = total_loss / max(total_pairs, 1)
        writer.add_scalar("Loss/train", avg_loss, epoch)
        writer.add_scalar("LR", scheduler.get_last_lr()[0], epoch)
        logger.info(f"Epoch {epoch:3d}/{epochs} | loss={avg_loss:.4f}")

        # Early stopping
        if avg_loss < best_loss:
            best_loss = avg_loss
            patience_counter = 0
            torch.save(model.state_dict(), best_checkpoint)
            logger.info(f"  -> Saved best checkpoint (loss={best_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch} (patience={patience})")
                break

    writer.close()
    logger.info(f"Training complete. Best checkpoint: {best_checkpoint}")
    return str(best_checkpoint)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to identity dataset root")
    parser.add_argument("--output", default="models", help="Output directory for checkpoints")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=15)
    args = parser.parse_args()

    train(
        data_dir=args.data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )
