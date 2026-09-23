"""
Inspect Forward Diffusion Process.

Run this script BEFORE training any neural network!
It demonstrates how the closed-form forward formula:
    x_t = sqrt(bar{alpha}_t) * x_0 + sqrt(1 - bar{alpha}_t) * epsilon
systematically dissolves structured 2D shapes into isotropic Gaussian noise.
"""

import os
import argparse
import torch
import matplotlib.pyplot as plt

from dataset import generate_2d_data
from diffusion import GaussianDiffusion2D


def inspect_forward_diffusion(
    dataset_name: str = "swiss_roll",
    n_samples: int = 2500,
    timesteps: int = 100,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Visualizing forward diffusion for '{dataset_name}' on {device}...")

    # 1. Sample clean data x_0
    raw_data = generate_2d_data(dataset_name=dataset_name, n_samples=n_samples)
    x_0 = torch.from_numpy(raw_data).to(device)

    # 2. Initialize diffusion scheduler
    diffusion = GaussianDiffusion2D(num_timesteps=timesteps, beta_schedule="linear", device=device)

    # 3. Select key timesteps to inspect
    eval_steps = [0, int(timesteps * 0.1), int(timesteps * 0.25), int(timesteps * 0.5), int(timesteps * 0.75), timesteps - 1]

    fig, axes = plt.subplots(1, len(eval_steps), figsize=(20, 3.6), sharex=True, sharey=True)
    fig.patch.set_facecolor('#0f172a')  # Dark slate background

    fixed_noise = torch.randn_like(x_0)

    for i, t_val in enumerate(eval_steps):
        t_tensor = torch.full((n_samples,), t_val, device=device, dtype=torch.long)
        x_t, _ = diffusion.q_sample(x_0=x_0, t=t_tensor, noise=fixed_noise)
        pts = x_t.cpu().numpy()

        ax = axes[i]
        ax.set_facecolor('#1e293b')
        ax.scatter(pts[:, 0], pts[:, 1], s=5, alpha=0.6, c=pts[:, 0], cmap='plasma', edgecolors='none')
        
        alpha_bar = diffusion.alphas_cumprod[t_val].item()
        ax.set_title(f"Step t = {t_val}\n$\\bar{{\\alpha}}_t = {alpha_bar:.3f}$", color='#f8fafc', fontsize=12, pad=10)
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 4)
        ax.tick_params(colors='#94a3b8')
        for spine in ax.spines.values():
            spine.set_color('#334155')

    plt.suptitle(
        f"Forward Diffusion Process q(x_t | x_0) - Dataset: {dataset_name.upper()}\nStructure gradually dissolves into isotropic Gaussian noise",
        color='#f8fafc',
        fontsize=14,
        y=1.12
    )

    out_path = os.path.join(output_dir, f"forward_diffusion_{dataset_name}.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    print(f"[OK] Saved forward diffusion inspection plot to: {out_path}")
    print("\n[INFO] Key Observation:")
    print("   - At t=0, points retain 100% of their geometric manifold (alpha_bar ~ 1.0).")
    print("   - At t=T, points are indistinguishable from standard normal noise N(0, I) (alpha_bar ~ 0.0).")
    print("   - The job of our neural network will simply be learning how to STEP BACKWARDS along this sequence!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect forward diffusion process on 2D data.")
    parser.add_argument("--dataset", type=str, default="swiss_roll", choices=["swiss_roll", "eight_gaussians", "two_moons", "s_curve"])
    parser.add_argument("--samples", type=int, default=2500)
    parser.add_argument("--timesteps", type=int, default=100)
    args = parser.parse_args()

    inspect_forward_diffusion(dataset_name=args.dataset, n_samples=args.samples, timesteps=args.timesteps)
