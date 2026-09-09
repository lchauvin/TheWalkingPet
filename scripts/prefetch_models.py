"""Download the ML weights into the image at build time.

Without this the first request after every container start pulls ~1.2 GB of
DINOv2 weights from GitHub and the YOLO checkpoint from Ultralytics, so a cold
start depends on both being reachable.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    import torch

    # torch.hub reads from $TORCH_HOME/hub at runtime, so the cache must be
    # written there -- not to $TORCH_HOME itself, or the weights are re-fetched.
    torch_home = os.environ.get("TORCH_HOME", "/opt/ml-cache/torch")
    torch.hub.set_dir(os.path.join(torch_home, "hub"))

    print("[prefetch] DINOv2 ViT-L/14 (reg)...", flush=True)
    from src.ml.models.dinov2 import DINOv2Net

    DINOv2Net()

    model_name = os.environ.get("YOLO_MODEL", "yolov8m-seg.pt")
    print(f"[prefetch] {model_name}...", flush=True)
    from ultralytics import YOLO

    YOLO(model_name)

    print("[prefetch] done", flush=True)


if __name__ == "__main__":
    main()
