"""
Inspect Forward Diffusion on 28x28 Images (MNIST).

Demonstrates how the forward equation:
    x_t = sqrt(bar{alpha}_t) * x_0 + sqrt(1 - bar{alpha}_t) * epsilon
corrupts recognizable handwritten digits into static Gaussian noise.
"""

import os
import argparse
import torch
import matplotlib.pyplot as plt

from dataset import get_mnist_dataloader
from diffusion import GaussianDiffusionImage


def inspect_forward_mnist(
    dataset_name: str = "mnist",
    num_digits: int = 5,
    timesteps: int = 300,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Visualizing forward image corruption for '{dataset_name}' on {device}...")

    dataloader = get_mnist_dataloader(dataset_name=dataset_name, batch_size=num_digits, train=False)
    images, labels = next(iter(dataloader))
    x_0 = images[:num_digits].to(device)

    diffusion = GaussianDiffusionImage(num_timesteps=timesteps, beta_schedule="linear", device=device)

    eval_steps = [0, int(timesteps * 0.1), int(timesteps * 0.25), int(timesteps * 0.5), int(timesteps * 0.75), timesteps - 1]

    fig, axes = plt.subplots(num_digits, len(eval_steps), figsize=(14, 2.2 * num_digits))
    fig.patch.set_facecolor('#0f172a')

    fixed_noise = torch.randn_like(x_0)

    for col_idx, t_val in enumerate(eval_steps):
        t_tensor = torch.full((num_digits,), t_val, device=device, dtype=torch.long)
        x_t, _ = diffusion.q_sample(x_0=x_0, t=t_tensor, noise=fixed_noise)
        x_t_clamped = torch.clamp(x_t, -1.0, 1.0)
        # Denormalize from [-1, 1] to [0, 1] for visualization
        x_t_vis = (x_t_clamped * 0.5 + 0.5).cpu().numpy()

        alpha_bar = diffusion.alphas_cumprod[t_val].item()

        for row_idx in range(num_digits):
            ax = axes[row_idx, col_idx] if num_digits > 1 else axes[col_idx]
            ax.set_facecolor('#0f172a')
            ax.imshow(x_t_vis[row_idx, 0], cmap='gray', vmin=0, vmax=1)
            ax.axis('off')

            if row_idx == 0:
                ax.set_title(f"t = {t_val}\n$\\bar{{\\alpha}}_t = {alpha_bar:.2f}$", color='#f8fafc', fontsize=11, pad=8)

    plt.suptitle(
        f"Forward Diffusion Process q(x_t | x_0) on {dataset_name.upper()}\nSpatial structure dissolves into pixel static",
        color='#f8fafc',
        fontsize=13,
        y=0.98
    )

    out_path = os.path.join(output_dir, f"forward_diffusion_{dataset_name}.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    print(f"[OK] Saved forward image corruption plot to: {out_path}")
    print("\n[INFO] Forward Observation:")
    print("   - By t=150, the structural identity of the digit is mostly submerged in noise.")
    print("   - By t=299, the image is pure white Gaussian noise.")
    print("   - In training, the U-Net will learn to predict and subtract this noise at each timestep!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect forward diffusion on MNIST images.")
    parser.add_argument("--dataset", type=str, default="mnist", choices=["mnist", "fashion_mnist"])
    parser.add_argument("--digits", type=int, default=5)
    parser.add_argument("--timesteps", type=int, default=300)
    args = parser.parse_args()

    inspect_forward_mnist(dataset_name=args.dataset, num_digits=args.digits, timesteps=args.timesteps)
