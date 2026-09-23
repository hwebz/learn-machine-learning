"""
Training Script for 2D Toy DDPM.

Trains the ToyMLPDiffusion network to predict noise epsilon_theta(x_t, t)
using MSE loss under the GaussianDiffusion2D schedule.
"""

import os
import argparse
import time
import torch
import torch.optim as optim
import matplotlib.pyplot as plt
from tqdm import tqdm

from dataset import get_dataloader
from model import ToyMLPDiffusion
from diffusion import GaussianDiffusion2D


def train(
    dataset_name: str = "swiss_roll",
    n_samples: int = 15000,
    batch_size: int = 256,
    epochs: int = 40,
    lr: float = 1e-3,
    timesteps: int = 100,
    hidden_dim: int = 128,
    num_layers: int = 3,
    checkpoint_dir: str = "checkpoints",
    output_dir: str = "outputs"
):
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Starting 2D DDPM Training ===")
    print(f"Dataset:       {dataset_name}")
    print(f"Device:        {device}")
    print(f"Epochs:        {epochs}")
    print(f"Batch Size:    {batch_size}")
    print(f"Timesteps:     {timesteps}")
    print(f"Model Dim:     Hidden={hidden_dim}, Layers={num_layers}")

    # 1. DataLoader & Components
    dataloader = get_dataloader(dataset_name=dataset_name, n_samples=n_samples, batch_size=batch_size)
    model = ToyMLPDiffusion(input_dim=2, hidden_dim=hidden_dim, time_emb_dim=64, num_layers=num_layers).to(device)
    diffusion = GaussianDiffusion2D(num_timesteps=timesteps, beta_schedule="linear", device=device)

    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    lr_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model Parameters: {num_params:,}\n")

    # 2. Training Loop
    epoch_losses = []
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        steps = 0

        pbar = tqdm(dataloader, desc=f"Epoch {epoch:02d}/{epochs:02d}", leave=False)
        for x_0 in pbar:
            x_0 = x_0.to(device)
            optimizer.zero_grad()
            loss = diffusion.compute_loss(model, x_0)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            steps += 1
            pbar.set_postfix(loss=f"{loss.item():.4f}")

        lr_scheduler.step()
        avg_loss = total_loss / max(1, steps)
        epoch_losses.append(avg_loss)

        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs:02d}] - Loss: {avg_loss:.5f} (LR: {optimizer.param_groups[0]['lr']:.2e})")

    elapsed = time.time() - start_time
    print(f"\n[OK] Training completed in {elapsed:.2f} seconds!")

    # 3. Save Checkpoint
    checkpoint_path = os.path.join(checkpoint_dir, f"toy_ddpm_{dataset_name}.pt")
    torch.save({
        "model_state_dict": model.state_dict(),
        "dataset_name": dataset_name,
        "timesteps": timesteps,
        "hidden_dim": hidden_dim,
        "num_layers": num_layers,
        "epoch_losses": epoch_losses
    }, checkpoint_path)
    print(f"[OK] Checkpoint saved to: {checkpoint_path}")

    # 4. Plot Loss Curve
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#1e293b')
    ax.plot(range(1, epochs + 1), epoch_losses, color='#38bdf8', lw=2.2, label='MSE Loss')
    ax.set_title(f"DDPM Training Loss Curve ({dataset_name.upper()})", color='#f8fafc', fontsize=13)
    ax.set_xlabel("Epoch", color='#94a3b8')
    ax.set_ylabel("MSE Loss (True vs Pred Noise)", color='#94a3b8')
    ax.tick_params(colors='#94a3b8')
    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.grid(True, color='#334155', linestyle='--', alpha=0.5)
    ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    loss_plot_path = os.path.join(output_dir, f"loss_curve_{dataset_name}.png")
    plt.savefig(loss_plot_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] Loss curve saved to: {loss_plot_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train 2D DDPM model.")
    parser.add_argument("--dataset", type=str, default="swiss_roll", choices=["swiss_roll", "eight_gaussians", "two_moons", "s_curve"])
    parser.add_argument("--samples", type=int, default=15000)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--timesteps", type=int, default=100)
    parser.add_argument("--hidden_dim", type=int, default=128)
    parser.add_argument("--layers", type=int, default=3)
    args = parser.parse_args()

    train(
        dataset_name=args.dataset,
        n_samples=args.samples,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        timesteps=args.timesteps,
        hidden_dim=args.hidden_dim,
        num_layers=args.layers
    )
