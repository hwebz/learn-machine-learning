"""
End-to-End Latent Diffusion Generation & Visualization.

Generates novel digits by:
1. Sampling pure Gaussian noise in latent space: z_T ~ N(0, I) in R^(N x 4 x 7 x 7).
2. Denoising latents using DDIM (20 steps) with cross-attention conditioning.
3. Decoding the final latent z_0 through the VAE decoder D(z_0) to reconstruct pixels (28 x 28).
"""

import os
import argparse
import torch
import matplotlib.pyplot as plt

from vae import AutoencoderKL
from latent_unet import LatentUNet
from latent_diffusion import LatentDiffusionPipeline


def sample_ldm(
    vae_ckpt_path: str = "checkpoints/vae.pt",
    unet_ckpt_path: str = "checkpoints/latent_unet.pt",
    samples_per_class: int = 4,
    num_steps: int = 20,
    guidance_scale: float = 3.0,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(vae_ckpt_path):
        raise FileNotFoundError(f"VAE checkpoint not found at: {vae_ckpt_path}. Run train_vae.py first!")
    if not os.path.exists(unet_ckpt_path):
        raise FileNotFoundError(f"Latent U-Net checkpoint not found at: {unet_ckpt_path}. Run train_ldm.py first!")

    print(f"[*] Loading VAE model from: {vae_ckpt_path}")
    vae_ckpt = torch.load(vae_ckpt_path, map_location=device)
    vae = AutoencoderKL(
        latent_channels=vae_ckpt.get("latent_channels", 4),
        base_channels=vae_ckpt.get("base_channels", 32),
        scale_factor=vae_ckpt.get("scale_factor", 0.5)
    ).to(device)
    vae.load_state_dict(vae_ckpt["model_state_dict"])
    vae.eval()

    print(f"[*] Loading Latent U-Net from: {unet_ckpt_path}")
    unet_ckpt = torch.load(unet_ckpt_path, map_location=device)
    latent_unet = LatentUNet(
        latent_channels=unet_ckpt.get("latent_channels", 4),
        base_channels=unet_ckpt.get("base_channels", 64),
        time_emb_dim=unet_ckpt.get("time_emb_dim", 64),
        context_dim=unet_ckpt.get("context_dim", 64),
        num_classes=unet_ckpt.get("num_classes", 10)
    ).to(device)
    latent_unet.load_state_dict(unet_ckpt["model_state_dict"])
    latent_unet.eval()

    pipeline = LatentDiffusionPipeline(num_timesteps=300, device=device)

    # Prepare classes: 0 through 9
    num_classes = 10
    all_classes = []
    for c in range(num_classes):
        all_classes.extend([c] * samples_per_class)
    target_classes = torch.tensor(all_classes, dtype=torch.long, device=device)

    print(f"[*] Running End-to-End Latent Diffusion ({num_steps} DDIM steps, CFG w={guidance_scale})...")

    # Generate end-to-end: Latent Denoising -> VAE Decoding
    decoded_imgs, denoised_latents = pipeline.generate_end_to_end(
        latent_model=latent_unet,
        vae=vae,
        classes=target_classes,
        num_steps=num_steps,
        guidance_scale=guidance_scale
    )

    decoded_vis = (decoded_imgs * 0.5 + 0.5).cpu().numpy()
    latents_vis = denoised_latents.cpu().numpy()

    # ==========================================
    # 1. Output 1: 10x4 Decoded Image Grid
    # ==========================================
    fig, axes = plt.subplots(num_classes, samples_per_class, figsize=(samples_per_class * 1.6, num_classes * 1.5))
    fig.patch.set_facecolor('#0f172a')

    for c in range(num_classes):
        for s in range(samples_per_class):
            idx = c * samples_per_class + s
            ax = axes[c, s]
            ax.set_facecolor('#0f172a')
            ax.imshow(decoded_vis[idx, 0], cmap='gray', vmin=0, vmax=1)
            ax.axis('off')

            if s == 0:
                ax.set_ylabel(f"Digit {c}", color='#38bdf8', fontsize=11, rotation=0, labelpad=28, va='center')

    plt.suptitle(
        f"Latent Diffusion Models (LDM) Synthesized Digits\nLatent DDIM ({num_steps} steps, CFG w={guidance_scale}) -> Decoded by VAE",
        color='#f8fafc',
        fontsize=13,
        y=0.99
    )

    grid_path = os.path.join(output_dir, "ldm_generated_digits.png")
    plt.savefig(grid_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved LDM generated digits grid to: {grid_path}")

    # ==========================================
    # 2. Output 2: Latent Channels vs Decoded Pixels
    # ==========================================
    num_inspect = 5
    fig, axes = plt.subplots(num_inspect, 5, figsize=(11, num_inspect * 2.1))
    fig.patch.set_facecolor('#0f172a')

    for r in range(num_inspect):
        # 4 Latent Channels (7x7)
        for ch in range(4):
            ax = axes[r, ch]
            ax.set_facecolor('#0f172a')
            ax.imshow(latents_vis[r * samples_per_class, ch], cmap='viridis')
            ax.axis('off')
            if r == 0:
                ax.set_title(f"Latent Ch {ch}\n(7x7)", color='#a855f7', fontsize=10, pad=6)

        # Decoded Pixel Image (28x28)
        ax_dec = axes[r, 4]
        ax_dec.set_facecolor('#0f172a')
        ax_dec.imshow(decoded_vis[r * samples_per_class, 0], cmap='gray', vmin=0, vmax=1)
        ax_dec.axis('off')
        if r == 0:
            ax_dec.set_title("VAE Decoded Image\n(28x28)", color='#10b981', fontsize=10, pad=6)

    plt.suptitle(
        "Inside the LDM: Denoised Latent Space Channels -> Decoded Final Image\nCompact representations contain high-level conceptual geometry",
        color='#f8fafc',
        fontsize=12,
        y=0.99
    )

    latent_to_pixel_path = os.path.join(output_dir, "ldm_latent_to_pixel.png")
    plt.savefig(latent_to_pixel_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved latent-to-pixel visualization to: {latent_to_pixel_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-End Latent Diffusion Sampling.")
    parser.add_argument("--vae_ckpt", type=str, default="checkpoints/vae.pt")
    parser.add_argument("--unet_ckpt", type=str, default="checkpoints/latent_unet.pt")
    parser.add_argument("--samples_per_class", type=int, default=4)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--guidance_scale", type=float, default=3.0)
    args = parser.parse_args()

    sample_ldm(
        vae_ckpt_path=args.vae_ckpt,
        unet_ckpt_path=args.unet_ckpt,
        samples_per_class=args.samples_per_class,
        num_steps=args.steps,
        guidance_scale=args.guidance_scale
    )
