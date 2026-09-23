"""
Deterministic Latent Space Interpolation with DDIM (eta = 0.0).

Demonstrates continuous latent morphing between two distinct noise vectors z_A and z_B.
Because DDIM with eta=0.0 is an invertible ODE without stochastic noise injection,
spherical linear interpolation (SLERP) in noise space produces a smooth, continuous
morphing trajectory in pixel space.
"""

import os
import sys
import argparse
import numpy as np
import torch
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("../03_conditional_cfg"))

from conditional_unet import ConditionalUNet
from ddim import DDIMSampler, slerp


def interpolate_latents(
    checkpoint_path: str = "../03_conditional_cfg/checkpoints/mnist_cfg_ddpm_mnist.pt",
    digit_a: int = 3,
    digit_b: int = 8,
    num_frames: int = 8,
    num_steps: int = 30,
    guidance_scale: float = 3.0,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

    print(f"[*] Loading conditional model from: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device)
    timesteps = ckpt.get("timesteps", 300)
    base_channels = ckpt.get("base_channels", 32)
    num_classes = ckpt.get("num_classes", 10)

    model = ConditionalUNet(
        in_channels=1,
        num_classes=num_classes,
        base_channels=base_channels,
        time_emb_dim=64
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    sampler = DDIMSampler(num_train_timesteps=timesteps, device=device)

    # 1. Sample two distinct random Gaussian noise vectors
    torch.manual_seed(101)
    z_a = torch.randn((1, 1, 28, 28), device=device)
    torch.manual_seed(202)
    z_b = torch.randn((1, 1, 28, 28), device=device)

    # 2. Compute SLERP interpolated noise vectors across frames
    alphas = np.linspace(0.0, 1.0, num_frames)
    interpolated_noises = []
    interpolated_classes = []

    for alpha in alphas:
        z_interp = slerp(z_a, z_b, float(alpha))
        interpolated_noises.append(z_interp)
        # Class label shifts halfway through interpolation
        chosen_class = digit_a if alpha < 0.5 else digit_b
        interpolated_classes.append(chosen_class)

    batch_noise = torch.cat(interpolated_noises, dim=0)
    batch_classes = torch.tensor(interpolated_classes, dtype=torch.long, device=device)

    print(f"[*] Generating {num_frames} interpolated frames (Digit {digit_a} -> Digit {digit_b}) with {num_steps} DDIM steps...")

    # 3. Deterministic DDIM Sampling (eta = 0.0)
    samples = sampler.sample(
        model=model,
        shape=(num_frames, 1, 28, 28),
        num_steps=num_steps,
        eta=0.0,  # Zero stochasticity
        y=batch_classes,
        guidance_scale=guidance_scale,
        initial_noise=batch_noise
    )
    samples_vis = (samples * 0.5 + 0.5).cpu().numpy()

    # 4. Plot Interpolation Strip
    fig, axes = plt.subplots(1, num_frames, figsize=(num_frames * 2.0, 2.8))
    fig.patch.set_facecolor('#0f172a')

    for i in range(num_frames):
        alpha_val = alphas[i]
        ax = axes[i]
        ax.set_facecolor('#0f172a')
        ax.imshow(samples_vis[i, 0], cmap='gray', vmin=0, vmax=1)
        ax.axis('off')

        title = f"$\\lambda = {alpha_val:.2f}$\n"
        if i == 0:
            title += f"(Digit {digit_a})"
        elif i == num_frames - 1:
            title += f"(Digit {digit_b})"
        else:
            title += f"(Class {interpolated_classes[i]})"

        ax.set_title(title, color='#f8fafc', fontsize=10, pad=6)

    plt.suptitle(
        f"Deterministic Latent Space Interpolation with DDIM (eta = 0.0, {num_steps} steps)\nSmooth SLERP trajectory between two noise latent seeds",
        color='#f8fafc',
        fontsize=13,
        y=1.05
    )

    out_path = os.path.join(output_dir, f"latent_interpolation_{digit_a}_to_{digit_b}.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved latent space interpolation strip to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interpolate between latent noise vectors with DDIM.")
    parser.add_argument("--checkpoint", type=str, default="../03_conditional_cfg/checkpoints/mnist_cfg_ddpm_mnist.pt")
    parser.add_argument("--digit_a", type=int, default=3)
    parser.add_argument("--digit_b", type=int, default=8)
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance_scale", type=float, default=3.0)
    args = parser.parse_args()

    interpolate_latents(
        checkpoint_path=args.checkpoint,
        digit_a=args.digit_a,
        digit_b=args.digit_b,
        num_frames=args.frames,
        num_steps=args.steps,
        guidance_scale=args.guidance_scale
    )
