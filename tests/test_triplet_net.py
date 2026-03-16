"""Tests for the TripletNet model."""
import pytest
import torch

from src.ml.models.triplet_net import TripletNet


@pytest.fixture
def model():
    return TripletNet()


def test_output_shape(model):
    x = torch.randn(4, 3, 224, 224)
    out = model(x)
    assert out.shape == (4, TripletNet.EMBEDDING_DIM)


def test_l2_normalized(model):
    model.eval()
    x = torch.randn(8, 3, 224, 224)
    with torch.no_grad():
        out = model(x)
    norms = torch.norm(out, dim=1)
    assert torch.allclose(norms, torch.ones(8), atol=1e-5)


def test_frozen_layers(model):
    # Layers up to and including layer2 should be frozen
    for name, param in model.backbone.named_parameters():
        # layer3, layer4, avgpool are NOT frozen
        if "layer3" in name or "layer4" in name or "avgpool" in name:
            assert param.requires_grad, f"{name} should require grad"
