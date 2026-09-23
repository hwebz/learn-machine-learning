"""
2D Toy Datasets for Diffusion Models.

Generates continuous 2D manifolds (Swiss Roll, Two Moons, 8-Gaussians, S-Curve)
normalized to roughly [-2, 2] so standard Gaussian noise (N(0, I)) can dominate
the data space during forward diffusion.
"""

import math
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.datasets import make_swiss_roll, make_moons, make_s_curve


def generate_2d_data(dataset_name: str = "swiss_roll", n_samples: int = 10000, noise: float = 0.5) -> np.ndarray:
    """Generate 2D point cloud data.
    
    Args:
        dataset_name: Name of the distribution ('swiss_roll', 'eight_gaussians', 'two_moons', 's_curve')
        n_samples: Number of coordinate pairs (x1, x2) to sample
        noise: Internal dataset jitter/noise
        
    Returns:
        np.ndarray of shape (n_samples, 2), centered and scaled with mean ~0, std ~1
    """
    dataset_name = dataset_name.lower()
    
    if dataset_name == "swiss_roll":
        # make_swiss_roll generates 3D coordinates (x, y, z); we project onto (x, z)
        data, _ = make_swiss_roll(n_samples=n_samples, noise=noise)
        data = data[:, [0, 2]]
        data = (data - data.mean(axis=0)) / (data.std(axis=0) + 1e-6) * 1.5

    elif dataset_name == "eight_gaussians":
        # 8 isotropic Gaussian clusters arranged in a circle of radius 2.0
        scale = 2.0
        centers = [
            (scale * math.cos(2 * math.pi * i / 8), scale * math.sin(2 * math.pi * i / 8))
            for i in range(8)
        ]
        centers = np.array(centers, dtype=np.float32)
        indices = np.random.choice(len(centers), size=n_samples)
        chosen_centers = centers[indices]
        cluster_noise = np.random.randn(n_samples, 2) * 0.15
        data = chosen_centers + cluster_noise

    elif dataset_name == "two_moons":
        data, _ = make_moons(n_samples=n_samples, noise=noise * 0.1)
        data = (data - data.mean(axis=0)) / (data.std(axis=0) + 1e-6) * 1.5

    elif dataset_name == "s_curve":
        data, _ = make_s_curve(n_samples=n_samples, noise=noise * 0.1)
        data = data[:, [0, 2]]
        data = (data - data.mean(axis=0)) / (data.std(axis=0) + 1e-6) * 1.5

    else:
        raise ValueError(f"Unknown dataset '{dataset_name}'. Available: 'swiss_roll', 'eight_gaussians', 'two_moons', 's_curve'")

    return data.astype(np.float32)


class Toy2DDataset(Dataset):
    """PyTorch Dataset wrapper for 2D coordinate distributions."""

    def __init__(self, dataset_name: str = "swiss_roll", n_samples: int = 10000, noise: float = 0.5):
        raw_data = generate_2d_data(dataset_name=dataset_name, n_samples=n_samples, noise=noise)
        self.data = torch.from_numpy(raw_data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return self.data[idx]


def get_dataloader(
    dataset_name: str = "swiss_roll",
    n_samples: int = 10000,
    batch_size: int = 256,
    shuffle: bool = True
) -> DataLoader:
    """Create a DataLoader for 2D toy coordinates."""
    dataset = Toy2DDataset(dataset_name=dataset_name, n_samples=n_samples)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, drop_last=True)
