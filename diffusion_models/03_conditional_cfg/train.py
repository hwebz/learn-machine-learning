"""
Training script for Conditional Vision DDPM with Classifier-Free Guidance.

Trains the ConditionalUNet on (image, label) pairs with random label dropout
(p_uncond = 0.15) to enable controllable image generation.
"""

import os
import argparse
import time
import torch
import torch.optim as optim
import matplotlib.pyplot as plt
from tqdm import tqdm

from dataset import get_conditional_dataloader
from conditional_unet import ConditionalUNet
from diffusion import GaussianDiffusionCFG


def train(
    dataset_name: str = "mnist",
    batch_size: int = 128,
    epochs: int = 6,
    lr: float = 2e-4,
    timesteps: int = 300,
    base_channels: int = 32,
    p_uncond: float = 0.15,
    max_samples: int = None,
    checkpoint_dir: str = "checkpoints",
    output_dir: str = "outputs"
):
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Starting Conditional DDPM (CFG) Training ===")
    print(f"Dataset:       {dataset_name.upper()}")
    print(f"Device:        {device}")
    print(f"Epochs:        {epochs}")
    print(f"Batch Size:    {batch_size}")
    print(f"Timesteps:     {timesteps}")
    print(f"Uncond Dropout:{p_uncond:.2f}")
    if max_samples:
        print(f"Max Samples:   {max_samples} (Fast Iteration Mode)")

    dataloader = get_conditional_dataloader(
        dataset_name=dataset_name,
        batch_size=batch_size,
        train=True,
        max_samples=max_samples
    )

    model = ConditionalUNet(
        in_channels=1,
        num_classes=10,
        base_channels=base_channels,
        time_emb_dim=64
    ).to(device)
    
    diffusion = GaussianDiffusionCFG(num_timesteps=timesteps, device=device)

    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    lr_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model Parameters: {num_params:,}\n")

    epoch_losses = []
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        steps = 0

        pbar = tqdm(dataloader, desc=f"Epoch {epoch:02d}/{epochs:02d}", leave=False)
        for images, labels in pbar:
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()

            loss = diffusion.compute_loss(model, images, labels, p_uncond=p_uncond)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            steps += 1
            pbar.set_postfix(loss=f"{loss.item():.4f}")

        lr_scheduler.step()
        avg_loss = total_loss / max(1, steps)
        epoch_losses.append(avg_loss)

        print(f"Epoch [{epoch:02d}/{epochs:02d}] - Loss: {avg_loss:.5f} (LR: {optimizer.param_groups[0]['lr']:.2e})")

    elapsed = time.time() - start_time
    print(f"\n[OK] Training completed in {elapsed:.2f} seconds!")

    # Save Checkpoint
    checkpoint_path = os.path.join(checkpoint_dir, f"mnist_cfg_ddpm_{dataset_name}.pt")
    torch.save({
        "model_state_dict": model.state_dict(),
        "dataset_name": dataset_name,
        "timesteps": timesteps,
        "base_channels": base_channels,
        "num_classes": 10,
        "epoch_losses": epoch_losses
    }, checkpoint_path)
    print(f"[OK] Checkpoint saved to: {checkpoint_path}")

    # Plot Loss Curve
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#1e293b')
    ax.plot(range(1, epochs + 1), epoch_losses, color='#a855f7', lw=2.2, label='Conditional MSE Loss')
    ax.set_title(f"Conditional DDPM (CFG) Training Loss ({dataset_name.upper()})", color='#f8fafc', fontsize=13)
    ax.set_xlabel("Epoch", color='#94a3b8')
    ax.set_ylabel("MSE Loss (True vs Pred Noise)", color='#94a3b8')
    ax.tick_params(colors='#94a3b8')
    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.grid(True, color='#334155', linestyle='--', alpha=0.5)
    ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    loss_plot_path = os.path.join(output_dir, f"loss_curve_cfg_{dataset_name}.png")
    plt.savefig(loss_plot_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Loss curve saved to: {loss_plot_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Conditional Vision DDPM with CFG.")
    parser.add_argument("--dataset", type=str, default="mnist", choices=["mnist", "fashion_mnist"])
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--timesteps", type=int, default=300)
    parser.add_argument("--base_channels", type=int, default=32)
    parser.add_argument("--p_uncond", type=float, default=0.15)
    parser.add_argument("--max_samples", type=int, default=6400)
    args = parser.parse_args()

    train(
        dataset_name=args.dataset,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        timesteps=args.timesteps,
        base_channels=args.base_channels,
        p_uncond=args.p_uncond,
        max_samples=args.max_samples
    )
