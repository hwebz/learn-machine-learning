"""
Conditional Sampling & Guidance Scale (CFG) Ablation.

Demonstrates:
1. Controllable Generation: Sampling specific digits (0 to 9) on command.
2. Guidance Scale Ablation: How varying w in [0.0, 1.0, 2.5, 4.0, 7.0] alters
   fidelity, contrast, and stroke definition from identical starting noise.
"""

import os
import argparse
import torch
import matplotlib.pyplot as plt

from conditional_unet import ConditionalUNet
from diffusion import GaussianDiffusionCFG


def sample_conditional(
    checkpoint_path: str = "checkpoints/mnist_cfg_ddpm_mnist.pt",
    samples_per_class: int = 6,
    guidance_scale: float = 3.0,
    ablation_digit: int = 7,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}. Run train.py first!")

    print(f"[*] Loading conditional model from: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device)
    dataset_name = ckpt.get("dataset_name", "mnist")
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

    diffusion = GaussianDiffusionCFG(num_timesteps=timesteps, device=device)

    # ==========================================
    # 1. Generate Ordered Matrix: Rows 0-9
    # ==========================================
    print(f"[*] Generating {num_classes} classes x {samples_per_class} samples (CFG w={guidance_scale})...")
    all_classes = []
    for c in range(num_classes):
        all_classes.extend([c] * samples_per_class)
    target_classes = torch.tensor(all_classes, dtype=torch.long, device=device)

    gen_images = diffusion.sample_classes(
        model=model,
        classes=target_classes,
        guidance_scale=guidance_scale
    )
    gen_vis = (gen_images * 0.5 + 0.5).cpu().numpy()

    fig, axes = plt.subplots(num_classes, samples_per_class, figsize=(samples_per_class * 1.4, num_classes * 1.4))
    fig.patch.set_facecolor('#0f172a')

    for c in range(num_classes):
        for s in range(samples_per_class):
            idx = c * samples_per_class + s
            ax = axes[c, s]
            ax.set_facecolor('#0f172a')
            ax.imshow(gen_vis[idx, 0], cmap='gray', vmin=0, vmax=1)
            ax.axis('off')

            if s == 0:
                ax.set_ylabel(f"Digit {c}", color='#38bdf8', fontsize=12, rotation=0, labelpad=30, va='center')

    plt.suptitle(
        f"Controllable Synthesis with Classifier-Free Guidance (w = {guidance_scale})\nEvery row conditioned on requested digit label (0 to 9)",
        color='#f8fafc',
        fontsize=13,
        y=0.99
    )

    grid_path = os.path.join(output_dir, f"conditional_digits_{dataset_name}.png")
    plt.savefig(grid_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved conditional 0-9 digits grid to: {grid_path}")

    # ==========================================
    # 2. Guidance Scale (w) Ablation Strip
    # ==========================================
    scales = [0.0, 1.0, 2.5, 4.0, 7.0]
    print(f"[*] Running CFG scale ablation for digit {ablation_digit} across w={scales}...")

    # Fix the same starting Gaussian noise seed
    torch.manual_seed(42)
    fixed_noise = torch.randn((1, 1, 28, 28), device=device)
    target_class_tensor = torch.tensor([ablation_digit], dtype=torch.long, device=device)

    fig, axes = plt.subplots(1, len(scales), figsize=(len(scales) * 2.5, 3.2))
    fig.patch.set_facecolor('#0f172a')

    for i, w_val in enumerate(scales):
        guided_img = diffusion.sample_classes(
            model=model,
            classes=target_class_tensor,
            guidance_scale=w_val,
            fixed_noise=fixed_noise
        )
        img_vis = (guided_img * 0.5 + 0.5).cpu().numpy()[0, 0]

        ax = axes[i]
        ax.set_facecolor('#0f172a')
        ax.imshow(img_vis, cmap='gray', vmin=0, vmax=1)
        ax.axis('off')

        subtitle = f"w = {w_val}\n"
        if w_val == 0.0:
            subtitle += "(Unconditioned)"
        elif w_val == 1.0:
            subtitle += "(Standard Cond)"
        elif w_val == 2.5:
            subtitle += "(Optimal Guidance)"
        elif w_val >= 4.0:
            subtitle += "(High Guidance)"

        ax.set_title(subtitle, color='#f8fafc', fontsize=11, pad=8)

    plt.suptitle(
        f"Classifier-Free Guidance (CFG) Scale Ablation: Target Digit {ablation_digit}\nIdentical starting noise seed showing stroke sharpness scaling with w",
        color='#f8fafc',
        fontsize=13,
        y=1.06
    )

    ablation_path = os.path.join(output_dir, f"cfg_scale_ablation_digit_{ablation_digit}.png")
    plt.savefig(ablation_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved CFG scale ablation strip to: {ablation_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sample from Conditional DDPM with CFG.")
    parser.add_argument("--checkpoint", type=str, default="checkpoints/mnist_cfg_ddpm_mnist.pt")
    parser.add_argument("--samples_per_class", type=int, default=6)
    parser.add_argument("--guidance_scale", type=float, default=3.0)
    parser.add_argument("--ablation_digit", type=int, default=7)
    parser.add_argument("--output_dir", type=str, default="outputs")
    args = parser.parse_args()

    sample_conditional(
        checkpoint_path=args.checkpoint,
        samples_per_class=args.samples_per_class,
        guidance_scale=args.guidance_scale,
        ablation_digit=args.ablation_digit,
        output_dir=args.output_dir
    )
