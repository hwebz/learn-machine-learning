"""
Training script for the Latent Denoising U-Net.

Uses the frozen, pre-trained VAE encoder to compress images into latent space (4 x 7 x 7),
then trains the LatentUNet with spatial cross-attention to predict latent noise.
"""

import os
import sys
import time
import argparse
import torch
import torch.optim as optim
import matplotlib.pyplot as plt
from tqdm import tqdm

sys.path.append(os.path.abspath("../03_conditional_cfg"))
from dataset import get_conditional_dataloader
from vae import AutoencoderKL
from latent_unet import LatentUNet
from latent_diffusion import LatentDiffusionPipeline


def train_ldm(
    vae_checkpoint: str = "checkpoints/vae.pt",
    batch_size: int = 128,
    epochs: int = 5,
    lr: float = 3e-4,
    timesteps: int = 300,
    base_channels: int = 64,
    p_uncond: float = 0.15,
    max_samples: int = 6400,
    checkpoint_dir: str = "checkpoints",
    output_dir: str = "outputs"
):
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Starting Latent Diffusion Model (LDM) Training ===")
    print(f"Device:        {device}")
    print(f"Epochs:        {epochs}")
    print(f"Batch Size:    {batch_size}")
    print(f"Timesteps:     {timesteps}")
    print(f"Latent Shape:  (4, 7, 7)")
    print(f"Max Samples:   {max_samples}")

    if not os.path.exists(vae_checkpoint):
        raise FileNotFoundError(f"VAE checkpoint not found at: {vae_checkpoint}. Run train_vae.py first!")

    # 1. Load Pre-Trained VAE (Frozen)
    print(f"[*] Loading pre-trained VAE from: {vae_checkpoint}")
    vae_ckpt = torch.load(vae_checkpoint, map_location=device)
    vae = AutoencoderKL(
        latent_channels=vae_ckpt.get("latent_channels", 4),
        base_channels=vae_ckpt.get("base_channels", 32),
        scale_factor=vae_ckpt.get("scale_factor", 0.5)
    ).to(device)
    vae.load_state_dict(vae_ckpt["model_state_dict"])
    vae.eval()
    for param in vae.parameters():
        param.requires_grad = False

    # 2. Setup DataLoader & Latent U-Net
    dataloader = get_conditional_dataloader(
        dataset_name="mnist",
        data_dir="../02_mnist_ddpm/data",
        batch_size=batch_size,
        train=True,
        max_samples=max_samples
    )

    latent_unet = LatentUNet(
        latent_channels=4,
        base_channels=base_channels,
        time_emb_dim=64,
        context_dim=64,
        num_classes=10
    ).to(device)

    pipeline = LatentDiffusionPipeline(num_timesteps=timesteps, device=device)
    optimizer = optim.AdamW(latent_unet.parameters(), lr=lr, weight_decay=1e-4)
    lr_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    num_params = sum(p.numel() for p in latent_unet.parameters() if p.requires_grad)
    print(f"Latent U-Net Parameters: {num_params:,}\n")

    epoch_losses = []
    start_time = time.time()

    # 3. Training Loop in Latent Space
    for epoch in range(1, epochs + 1):
        latent_unet.train()
        total_loss = 0.0
        steps = 0

        pbar = tqdm(dataloader, desc=f"Epoch {epoch:02d}/{epochs:02d}", leave=False)
        for images, labels in pbar:
            images = images.to(device)
            labels = labels.to(device)

            # Encode pixels -> latent space: z_0 in R^(B, 4, 7, 7)
            with torch.no_grad():
                z_0, _, _ = vae.encode(images)

            optimizer.zero_grad()
            loss = pipeline.compute_loss(latent_unet, z_0, labels, p_uncond=p_uncond)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(latent_unet.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            steps += 1
            pbar.set_postfix(loss=f"{loss.item():.4f}")

        lr_scheduler.step()
        avg_loss = total_loss / max(1, steps)
        epoch_losses.append(avg_loss)

        print(f"Epoch [{epoch:02d}/{epochs:02d}] - Latent Loss: {avg_loss:.5f} (LR: {optimizer.param_groups[0]['lr']:.2e})")

    elapsed = time.time() - start_time
    print(f"\n[OK] Latent U-Net training completed in {elapsed:.2f} seconds!")

    # 4. Save Checkpoint
    checkpoint_path = os.path.join(checkpoint_dir, "latent_unet.pt")
    torch.save({
        "model_state_dict": latent_unet.state_dict(),
        "latent_channels": 4,
        "base_channels": base_channels,
        "time_emb_dim": 64,
        "context_dim": 64,
        "num_classes": 10,
        "epoch_losses": epoch_losses
    }, checkpoint_path)
    print(f"[OK] Latent U-Net checkpoint saved to: {checkpoint_path}")

    # 5. Plot Loss Curve
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#1e293b')
    ax.plot(range(1, epochs + 1), epoch_losses, color='#f59e0b', lw=2.2, label='Latent MSE Loss')
    ax.set_title("Latent Diffusion U-Net Training Loss", color='#f8fafc', fontsize=13)
    ax.set_xlabel("Epoch", color='#94a3b8')
    ax.set_ylabel("MSE Loss in Latent Space", color='#94a3b8')
    ax.tick_params(colors='#94a3b8')
    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.grid(True, color='#334155', linestyle='--', alpha=0.5)
    ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    loss_plot_path = os.path.join(output_dir, "loss_curve_ldm.png")
    plt.savefig(loss_plot_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] LDM loss curve saved to: {loss_plot_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Latent U-Net for LDM.")
    parser.add_argument("--vae_ckpt", type=str, default="checkpoints/vae.pt")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--max_samples", type=int, default=6400)
    args = parser.parse_args()

    train_ldm(
        vae_checkpoint=args.vae_ckpt,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_samples=args.max_samples
    )
