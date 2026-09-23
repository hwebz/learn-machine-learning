"""
Reverse Sampling & Visualization for 2D DDPM.

Loads a trained model checkpoint, generates samples starting from pure
Gaussian noise x_T ~ N(0, I), and visualizes the reverse denoising trajectory.
"""

import os
import argparse
import torch
import numpy as np
import matplotlib.pyplot as plt

from dataset import generate_2d_data
from model import ToyMLPDiffusion
from diffusion import GaussianDiffusion2D


def sample_and_visualize(
    checkpoint_path: str = "checkpoints/toy_ddpm_swiss_roll.pt",
    n_samples: int = 2500,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}. Run train.py first!")

    print(f"[*] Loading checkpoint from: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device)
    dataset_name = ckpt.get("dataset_name", "swiss_roll")
    timesteps = ckpt.get("timesteps", 100)
    hidden_dim = ckpt.get("hidden_dim", 128)
    num_layers = ckpt.get("num_layers", 3)

    # 1. Instantiate model and diffusion scheduler
    model = ToyMLPDiffusion(input_dim=2, hidden_dim=hidden_dim, time_emb_dim=64, num_layers=num_layers).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    diffusion = GaussianDiffusion2D(num_timesteps=timesteps, beta_schedule="linear", device=device)

    print(f"[*] Generating {n_samples} samples via reverse diffusion on {device}...")

    # 2. Run sampling with full trajectory recording
    final_samples, trajectory = diffusion.sample(
        model=model,
        shape=(n_samples, 2),
        return_trajectory=True
    )
    # trajectory has length num_timesteps + 1 (from t=T down to t=0)

    # 3. Create Multi-Step Trajectory Plot
    eval_indices = [0, int(timesteps * 0.25), int(timesteps * 0.5), int(timesteps * 0.75), int(timesteps * 0.9), timesteps]
    # In trajectory: index 0 is pure noise (t=T), index timesteps is final x_0
    step_labels = ["t = T (Noise)", f"t = {int(timesteps*0.75)}", f"t = {int(timesteps*0.5)}", f"t = {int(timesteps*0.25)}", f"t = {int(timesteps*0.1)}", "t = 0 (Generated)"]

    fig, axes = plt.subplots(1, len(eval_indices) + 1, figsize=(24, 3.8), sharex=True, sharey=True)
    fig.patch.set_facecolor('#0f172a')

    for i, idx in enumerate(eval_indices):
        pts = trajectory[idx].cpu().numpy()
        ax = axes[i]
        ax.set_facecolor('#1e293b')
        ax.scatter(pts[:, 0], pts[:, 1], s=4, alpha=0.6, c=pts[:, 0], cmap='viridis', edgecolors='none')
        ax.set_title(step_labels[i], color='#f8fafc', fontsize=12, pad=10)
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 4)
        ax.tick_params(colors='#94a3b8')
        for spine in ax.spines.values():
            spine.set_color('#334155')

    # Add ground truth in final column for direct comparison
    gt_pts = generate_2d_data(dataset_name=dataset_name, n_samples=n_samples)
    ax_gt = axes[-1]
    ax_gt.set_facecolor('#1e293b')
    ax_gt.scatter(gt_pts[:, 0], gt_pts[:, 1], s=4, alpha=0.6, c=gt_pts[:, 0], cmap='viridis', edgecolors='none')
    ax_gt.set_title("Ground Truth Data", color='#38bdf8', fontsize=12, pad=10)
    ax_gt.set_xlim(-4, 4)
    ax_gt.set_ylim(-4, 4)
    ax_gt.tick_params(colors='#94a3b8')
    for spine in ax_gt.spines.values():
        spine.set_color('#38bdf8')

    plt.suptitle(
        f"DDPM Reverse Denoising Process p_theta(x_{{t-1}} | x_t) - Dataset: {dataset_name.upper()}\nStarting from pure Gaussian noise and condensing into structured manifold",
        color='#f8fafc',
        fontsize=14,
        y=1.12
    )

    traj_path = os.path.join(output_dir, f"reverse_denoising_{dataset_name}.png")
    plt.savefig(traj_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved reverse trajectory progression to: {traj_path}")

    # 4. Side-by-Side Comparison Plot (Ground Truth vs Generated)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), sharex=True, sharey=True)
    fig.patch.set_facecolor('#0f172a')

    gen_pts = final_samples.cpu().numpy()

    for ax, data_pts, title, color_theme in [
        (ax1, gt_pts, f"Ground Truth ({dataset_name})", '#38bdf8'),
        (ax2, gen_pts, f"DDPM Generated Samples (t=0)", '#a855f7')
    ]:
        ax.set_facecolor('#1e293b')
        ax.scatter(data_pts[:, 0], data_pts[:, 1], s=6, alpha=0.7, c=data_pts[:, 0], cmap='plasma', edgecolors='none')
        ax.set_title(title, color=color_theme, fontsize=13, pad=10)
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 4)
        ax.tick_params(colors='#94a3b8')
        for spine in ax.spines.values():
            spine.set_color('#334155')

    comp_path = os.path.join(output_dir, f"comparison_{dataset_name}.png")
    plt.savefig(comp_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved high-resolution comparison to: {comp_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sample and visualize from 2D DDPM.")
    parser.add_argument("--checkpoint", type=str, default="checkpoints/toy_ddpm_swiss_roll.pt")
    parser.add_argument("--samples", type=int, default=2500)
    parser.add_argument("--output_dir", type=str, default="outputs")
    args = parser.parse_args()

    sample_and_visualize(
        checkpoint_path=args.checkpoint,
        n_samples=args.samples,
        output_dir=args.output_dir
    )
