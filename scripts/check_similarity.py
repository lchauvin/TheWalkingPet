"""Diagnostic: compare MegaDescriptor vs DINOv2 similarity between two images.

Usage:
    python -m scripts.check_similarity path/to/image1.jpg path/to/image2.jpg
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

from src.ml.detector import PetDetector
from src.ml.embedder import PetEmbedder
from src.config import settings

_MEAN = [0.485, 0.456, 0.406]
_STD  = [0.229, 0.224, 0.225]

_T384 = transforms.Compose([
    transforms.Resize((384, 384)),
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])
_T224 = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])
_T518 = transforms.Compose([
    transforms.Resize((518, 518)),
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])


def cosine_sim(a, b) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0


def embed_tensor(model, t: torch.Tensor, device) -> list[float]:
    with torch.no_grad():
        out = model(t.unsqueeze(0).to(device))
        if isinstance(out, (tuple, list)):
            out = out[0]
        out = F.normalize(out.squeeze(0), p=2, dim=0)
    return out.cpu().tolist()


def bbox_crop(img: Image.Image, bbox: tuple) -> Image.Image:
    x1, y1, x2, y2 = bbox
    return img.crop((x1, y1, x2, y2))


def load_dinov2(device):
    print("  Loading DINOv2 ViT-L/14 (reg)...")
    model = torch.hub.load("facebookresearch/dinov2", "dinov2_vitl14_reg", verbose=False)
    model.eval().to(device)
    return model


def main():
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.check_similarity image1.jpg image2.jpg")
        sys.exit(1)

    p1, p2 = sys.argv[1], sys.argv[2]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ── MegaDescriptor ──────────────────────────────────────────────
    print("Loading MegaDescriptor...")
    embedder = PetEmbedder()
    mega_model = embedder.model.backbone
    detector = PetDetector(model_name=settings.yolo_model)

    img1 = Image.open(p1).convert("RGB")
    img2 = Image.open(p2).convert("RGB")
    det1 = detector.best_detection(img1)
    det2 = detector.best_detection(img2)

    print(f"\n{'Mode':<42} {'Sim':>6}")
    print("-" * 50)

    # MegaDescriptor — masked crop (current pipeline)
    e1_m = embedder.embed_image(det1["masked"] if det1 else img1)
    e2_m = embedder.embed_image(det2["masked"] if det2 else img2)
    print(f"  {'MegaDescriptor — masked crop':<40} {cosine_sim(e1_m, e2_m):>6.1%}")

    # MegaDescriptor — plain bbox crop
    if det1 and det2:
        c1 = bbox_crop(img1, det1["bbox"])
        c2 = bbox_crop(img2, det2["bbox"])
        e1_b = embed_tensor(mega_model, _T384(c1), device)
        e2_b = embed_tensor(mega_model, _T384(c2), device)
        print(f"  {'MegaDescriptor — bbox crop':<40} {cosine_sim(e1_b, e2_b):>6.1%}")

    # MegaDescriptor — full image
    e1_f = embed_tensor(mega_model, _T384(img1), device)
    e2_f = embed_tensor(mega_model, _T384(img2), device)
    print(f"  {'MegaDescriptor — full image':<40} {cosine_sim(e1_f, e2_f):>6.1%}")

    # ── DINOv2 ──────────────────────────────────────────────────────
    print()
    dino = load_dinov2(device)

    # DINOv2 — masked crop
    e1_dm = embed_tensor(dino, _T518(det1["masked"] if det1 else img1), device)
    e2_dm = embed_tensor(dino, _T518(det2["masked"] if det2 else img2), device)
    print(f"  {'DINOv2 ViT-L/14 — masked crop':<40} {cosine_sim(e1_dm, e2_dm):>6.1%}")

    # DINOv2 — bbox crop
    if det1 and det2:
        e1_db = embed_tensor(dino, _T518(c1), device)
        e2_db = embed_tensor(dino, _T518(c2), device)
        print(f"  {'DINOv2 ViT-L/14 — bbox crop':<40} {cosine_sim(e1_db, e2_db):>6.1%}")

    # DINOv2 — full image
    e1_df = embed_tensor(dino, _T518(img1), device)
    e2_df = embed_tensor(dino, _T518(img2), device)
    print(f"  {'DINOv2 ViT-L/14 — full image':<40} {cosine_sim(e1_df, e2_df):>6.1%}")

    if det1 and det2:
        print(f"\nDetections:")
        print(f"  Image 1: {det1['species']} conf={det1['confidence']:.2f} bbox={det1['bbox']}")
        print(f"  Image 2: {det2['species']} conf={det2['confidence']:.2f} bbox={det2['bbox']}")


if __name__ == "__main__":
    main()
