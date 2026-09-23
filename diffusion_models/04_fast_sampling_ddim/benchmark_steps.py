"""
Benchmark DDIM Sampling Steps vs Generation Speed and Visual Quality.

Samples identical noise seeds across S in [5, 10, 20, 50, 100, 300] steps,
measuring inference latency and visual fidelity trade-offs.
"""

import os
import sys
import time
import argparse
import torch
import matplotlib.pyplot as plt

# Add sibling directories to path for imports
sys.path.append(os.path.abspath("../03_conditional_cfg"))
sys.path.append(os.path.abspath("../02_mnist_ddpm"))

from conditional_unet import ConditionalUNet
from ddim import DDIMSampler


def benchmark_steps(
    checkpoint_path: str = "../03_conditional_cfg/checkpoints/mnist_cfg_ddpm_mnist.pt",
    steps_list = [5, 10, 20, 50, 100, 300],
    sample_classes = [0, 3, 7, 8],
    guidance_scale: float = 3.0,
    eta: float = 0.0,
    output_dir: str = "outputs"
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}. Run Stage 3 train.py first!")

    print(f"[*] Loading model from: {checkpoint_path}")
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

    # Fix identical starting noise for all step counts
    torch.manual_seed(42)
    num_digits = len(sample_classes)
    fixed_noise = torch.randn((num_digits, 1, 28, 28), device=device)
    target_labels = torch.tensor(sample_classes, dtype=torch.long, device=device)

    results = {}
    timings = {}

    print(f"[*] Benchmarking step counts across {steps_list} on {device} (eta={eta})...\n")
    print(f"{'Steps':<10} | {'Time (s)':<10} | {'Speedup':<10}")
    print("-" * 36)

    baseline_time = None

    for steps in steps_list:
        start_t = time.time()
        samples = sampler.sample(
            model=model,
            shape=(num_digits, 1, 28, 28),
            num_steps=steps,
            eta=eta,
            y=target_labels,
            guidance_scale=guidance_scale,
            initial_noise=fixed_noise
        )
        elapsed = time.time() - start_t
        timings[steps] = elapsed
        results[steps] = (samples * 0.5 + 0.5).cpu().numpy()

        if baseline_time is None and steps == max(steps_list):
            baseline_time = elapsed
        
    baseline_time = timings[max(steps_list)]
    for steps in steps_list:
        speedup = baseline_time / timings[steps]
        print(f"{steps:<10} | {timings[steps]:<10.2f} | {speedup:<10.1f}x")

    # Plot Comparison Grid
    cols = len(steps_list)
    rows = num_digits
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.2, rows * 2.0))
    fig.patch.set_facecolor('#0f172a')

    for col_idx, steps in enumerate(steps_list):
        data = results[steps]
        sec = timings[steps]
        speedup = baseline_time / sec

        for row_idx in range(rows):
            ax = axes[row_idx, col_idx] if rows > 1 else axes[col_idx]
            ax.set_facecolor('#0f172a')
            ax.imshow(data[row_idx, 0], cmap='gray', vmin=0, vmax=1)
            ax.axis('off')

            if row_idx == 0:
                header = f"{steps} Steps\n{sec:.2f}s ({speedup:.1f}x)"
                ax.set_title(header, color='#f8fafc', fontsize=10, pad=6)

            if col_idx == 0:
                digit_label = sample_classes[row_idx]
                ax.set_ylabel(f"Digit {digit_label}", color='#38bdf8', fontsize=11, rotation=0, labelpad=28, va='center')

    plt.suptitle(
        f"DDIM Accelerated Sampling vs Standard DDPM (eta = {eta})\nIdentical initial noise seeds across step counts",
        color='#f8fafc',
        fontsize=13,
        y=0.99
    )

    out_path = os.path.join(output_dir, "ddim_steps_comparison.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"\n[OK] Saved DDIM step benchmark comparison to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark DDIM sampling steps.")
    parser.add_argument("--checkpoint", type=str, default="../03_conditional_cfg/checkpoints/mnist_cfg_ddpm_mnist.pt")
    parser.add_argument("--steps", nargs="+", type=int, default=[5, 10, 20, 50, 100, 300])
    parser.add_argument("--classes", nargs="+", type=int, default=[0, 3, 7, 8])
    parser.add_argument("--guidance_scale", type=float, default=3.0)
    parser.add_argument("--eta", type=float, default=0.0)
    args = parser.parse_args()

    benchmark_steps(
        checkpoint_path=args.checkpoint,
        steps_list=args.steps,
        sample_classes=args.classes,
        guidance_scale=args.guidance_scale,
        eta=args.eta
    )
