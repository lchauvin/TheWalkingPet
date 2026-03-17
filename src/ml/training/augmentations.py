"""Image transforms for training and evaluation.

DINOv2 ViT-L/14 uses 518×518 input (14×37 patches, no padding needed).
"""
from torchvision import transforms

_MEAN = [0.485, 0.456, 0.406]
_STD = [0.229, 0.224, 0.225]

TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
    transforms.RandomGrayscale(p=0.1),
    transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
    transforms.RandomPerspective(distortion_scale=0.3, p=0.3),
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])

EVAL_TRANSFORM = transforms.Compose([
    transforms.Resize((518, 518)),
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])

# Test-Time Augmentation transforms for registration photos.
# 6 views: original, h-flip, rotation ±10°, 90% center crop, mild color jitter.
TTA_TRANSFORMS = [
    # 1. Original
    transforms.Compose([
        transforms.Resize((518, 518)),
        transforms.ToTensor(),
        transforms.Normalize(mean=_MEAN, std=_STD),
    ]),
    # 2. Horizontal flip
    transforms.Compose([
        transforms.Resize((518, 518)),
        transforms.RandomHorizontalFlip(p=1.0),
        transforms.ToTensor(),
        transforms.Normalize(mean=_MEAN, std=_STD),
    ]),
    # 3. Small rotation +10°
    transforms.Compose([
        transforms.Resize((572, 572)),
        transforms.RandomRotation(degrees=(10, 10)),
        transforms.CenterCrop(518),
        transforms.ToTensor(),
        transforms.Normalize(mean=_MEAN, std=_STD),
    ]),
    # 4. Small rotation -10°
    transforms.Compose([
        transforms.Resize((572, 572)),
        transforms.RandomRotation(degrees=(-10, -10)),
        transforms.CenterCrop(518),
        transforms.ToTensor(),
        transforms.Normalize(mean=_MEAN, std=_STD),
    ]),
    # 5. 90% center crop
    transforms.Compose([
        transforms.Resize((576, 576)),
        transforms.CenterCrop(518),
        transforms.ToTensor(),
        transforms.Normalize(mean=_MEAN, std=_STD),
    ]),
    # 6. Mild color jitter
    transforms.Compose([
        transforms.Resize((518, 518)),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=_MEAN, std=_STD),
    ]),
]
