"""
Inspect VAE Perceptual Compression (Pixel Space -> Latent Space -> Reconstruction).

Visualizes how high-dimensional images (28 x 28) are encoded into 4 continuous
latent feature channels (7 x 7) and reconstructed back into clean pixels.
"""

import os
import sys
import argparse
import torch
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("../02_mnist_ddpm"))
from dataset import get_mnist_dataloader
from vae import AutoencoderKL


def inspect_compression(
    checkpoint_path: str = "checkpoints/vae.pt",
    num_samples: int = 4,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}. Run train_vae.py first!")

    print(f"[*] Loading VAE model from: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device)
    model = AutoencoderKL(
        latent_channels=ckpt.get("latent_channels", 4),
        base_channels=ckpt.get("base_channels", 32),
        scale_factor=ckpt.get("scale_factor", 0.5)
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    dataloader = get_mnist_dataloader(
        dataset_name="mnist",
        data_dir="../02_mnist_ddpm/data",
        batch_size=num_samples,
        train=False
    )
    images, _ = next(iter(dataloader))
    x_orig = images[:num_samples].to(device)

    with torch.no_grad():
        scaled_z, mu, logvar = model.encode(x_orig)
        x_recon = model.decode(scaled_z)

    # Denormalize to [0, 1]
    orig_vis = (x_orig * 0.5 + 0.5).cpu().numpy()
    recon_vis = (x_recon * 0.5 + 0.5).cpu().numpy()
    latent_vis = scaled_z.cpu().numpy()  # (num_samples, 4, 7, 7)

    # Plot: Original | Latent Ch 0 | Latent Ch 1 | Latent Ch 2 | Latent Ch 3 | Reconstruction
    fig, axes = plt.subplots(num_samples, 6, figsize=(14, num_samples * 2.2))
    fig.patch.set_facecolor('#0f172a')

    for r in range(num_samples):
        # 1. Original
        ax_orig = axes[r, 0]
        ax_orig.set_facecolor('#0f172a')
        ax_orig.imshow(orig_vis[r, 0], cmap='gray', vmin=0, vmax=1)
        ax_orig.axis('off')
        if r == 0:
            ax_orig.set_title("Original\n(1x28x28)", color='#38bdf8', fontsize=11, pad=8)

        # 2. 4 Latent Channels
        for ch in range(4):
            ax_lat = axes[r, ch + 1]
            ax_lat.set_facecolor('#0f172a')
            ax_lat.imshow(latent_vis[r, ch], cmap='viridis')
            ax_lat.axis('off')
            if r == 0:
                ax_lat.set_title(f"Latent Ch {ch}\n(7x7)", color='#a855f7', fontsize=11, pad=8)

        # 3. Decoded Reconstruction
        ax_rec = axes[r, 5]
        ax_rec.set_facecolor('#0f172a')
        ax_rec.imshow(recon_vis[r, 0], cmap='gray', vmin=0, vmax=1)
        ax_rec.axis('off')
        if r == 0:
            ax_rec.set_title("Reconstruction\n(1x28x28)", color='#10b981', fontsize=11, pad=8)

    plt.suptitle(
        "VAE Perceptual Compression: Pixels -> Compact Latent Manifold -> Reconstruction\nDiffusion operates entirely on the middle 4x7x7 latent channels!",
        color='#f8fafc',
        fontsize=13,
        y=0.99
    )

    out_path = os.path.join(output_dir, "vae_compression_inspection.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Saved VAE compression inspection plot to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect VAE compression.")
    parser.add_argument("--checkpoint", type=str, default="checkpoints/vae.pt")
    parser.add_argument("--samples", type=int, default=4)
    args = parser.parse_args()

    inspect_compression(checkpoint_path=args.checkpoint, num_samples=args.samples)
