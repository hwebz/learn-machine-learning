"""
Dataset loader for Conditional Vision DDPM.

Loads MNIST with corresponding class labels y in {0, ..., 9}.
Reuses cached data from 02_mnist_ddpm/data if available.
"""

import os
from typing import Optional
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms


def get_conditional_dataloader(
    dataset_name: str = "mnist",
    data_dir: str = "../02_mnist_ddpm/data",
    batch_size: int = 128,
    train: bool = True,
    max_samples: Optional[int] = None
) -> DataLoader:
    """Prepares DataLoader yielding (images, labels) with [-1, 1] normalization."""
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
