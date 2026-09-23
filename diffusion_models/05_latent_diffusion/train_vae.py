"""
Training script for the Perceptual VAE Compression Autoencoder.

Trains the AutoencoderKL model on MNIST images to establish
the compressed continuous latent manifold (4 x 7 x 7) for latent diffusion.
"""

import os
import sys
import time
import argparse
import torch
import torch.optim as optim
import matplotlib.pyplot as plt
from tqdm import tqdm

sys.path.append(os.path.abspath("../02_mnist_ddpm"))
from dataset import get_mnist_dataloader
from vae import AutoencoderKL


def train_vae(
    batch_size: int = 128,
    epochs: int = 4,
    lr: float = 1e-3,
    kl_weight: float = 1e-4,
    max_samples: int = 8000,
    checkpoint_dir: str = "checkpoints",
    output_dir: str = "outputs"
):
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Starting VAE Autoencoder Training ===")
    print(f"Device:        {device}")
    print(f"Epochs:        {epochs}")
    print(f"Batch Size:    {batch_size}")
    print(f"KL Weight:     {kl_weight}")
    print(f"Max Samples:   {max_samples}")

    dataloader = get_mnist_dataloader(
        dataset_name="mnist",
        data_dir="../02_mnist_ddpm/data",
        batch_size=batch_size,
        train=True,
        max_samples=max_samples
    )

    model = AutoencoderKL(latent_channels=4, base_channels=32, scale_factor=0.5).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    lr_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"VAE Model Parameters: {num_params:,}\n")

    epoch_losses = []
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_recon = 0.0
        total_kl = 0.0
        steps = 0

        pbar = tqdm(dataloader, desc=f"Epoch {epoch:02d}/{epochs:02d}", leave=False)
        for images, _ in pbar:
            images = images.to(device)
            optimizer.zero_grad()

            x_recon, mu, logvar = model(images)
            loss, recon, kl = AutoencoderKL.compute_loss(images, x_recon, mu, logvar, kl_weight=kl_weight)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            total_recon += recon.item()
            total_kl += kl.item()
            steps += 1
            pbar.set_postfix(recon=f"{recon.item():.4f}", kl=f"{kl.item():.2f}")

        lr_scheduler.step()
        avg_loss = total_loss / max(1, steps)
        avg_recon = total_recon / max(1, steps)
        avg_kl = total_kl / max(1, steps)
        epoch_losses.append(avg_loss)

        print(f"Epoch [{epoch:02d}/{epochs:02d}] - Total: {avg_loss:.5f} (Recon: {avg_recon:.5f}, KL: {avg_kl:.2f})")

    elapsed = time.time() - start_time
    print(f"\n[OK] VAE training completed in {elapsed:.2f} seconds!")

    # Save Checkpoint
    checkpoint_path = os.path.join(checkpoint_dir, "vae.pt")
    torch.save({
        "model_state_dict": model.state_dict(),
        "latent_channels": 4,
        "base_channels": 32,
        "scale_factor": 0.5,
        "epoch_losses": epoch_losses
    }, checkpoint_path)
    print(f"[OK] VAE checkpoint saved to: {checkpoint_path}")

    # Plot Loss Curve
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#1e293b')
    ax.plot(range(1, epochs + 1), epoch_losses, color='#10b981', lw=2.2, label='VAE Total Loss')
    ax.set_title("VAE Autoencoder Training Loss", color='#f8fafc', fontsize=13)
    ax.set_xlabel("Epoch", color='#94a3b8')
    ax.set_ylabel("Loss", color='#94a3b8')
    ax.tick_params(colors='#94a3b8')
    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.grid(True, color='#334155', linestyle='--', alpha=0.5)
    ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    loss_plot_path = os.path.join(output_dir, "loss_curve_vae.png")
    plt.savefig(loss_plot_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] VAE loss curve saved to: {loss_plot_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train VAE for Latent Diffusion.")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--max_samples", type=int, default=8000)
    args = parser.parse_args()

    train_vae(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_samples=args.max_samples
    )
