"""
Dataset loader and preprocessor for 28x28 grayscale vision DDPM.

Downloads and prepares MNIST (or Fashion-MNIST) with normalization
from [0, 1] to [-1, 1], matching the zero-centered scale of standard
Gaussian noise N(0, I).
"""

import os
from typing import Tuple
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms


def get_mnist_dataloader(
    dataset_name: str = "mnist",
    data_dir: str = "data",
    batch_size: int = 128,
    train: bool = True,
    max_samples: int = None
) -> DataLoader:
    """Prepares DataLoader for 28x28 grayscale images.
    
    Transforms:
        1. ToTensor(): Scales pixel values from [0, 255] to [0.0, 1.0]
        2. Normalize((0.5,), (0.5,)): Linearly scales from [0.0, 1.0] to [-1.0, 1.0]
        
    Args:
        dataset_name: 'mnist' or 'fashion_mnist'
        data_dir: Local path to cache raw dataset files
        batch_size: Minibatch size for training
        train: If True, loads train split, else test split
        max_samples: Optional limit for fast local iteration
    """
    os.makedirs(data_dir, exist_ok=True)

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    name_lower = dataset_name.lower()
    if name_lower == "mnist":
        dataset = datasets.MNIST(root=data_dir, train=train, download=True, transform=transform)
    elif name_lower == "fashion_mnist":
        dataset = datasets.FashionMNIST(root=data_dir, train=train, download=True, transform=transform)
    else:
        raise ValueError(f"Unknown dataset '{dataset_name}'. Choose 'mnist' or 'fashion_mnist'.")

    if max_samples is not None and max_samples < len(dataset):
        indices = list(range(max_samples))
        dataset = Subset(dataset, indices)

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=train,
        drop_last=train,
        num_workers=0,
        pin_memory=False
    )
