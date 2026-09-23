# Stage 4: Accelerated Sampling with DDIM (Denoising Diffusion Implicit Models)

Welcome to Stage 4! Here we break the **sampling speed barrier** of diffusion models using **DDIM** (Song et al., 2020).

---

## ⚡ The Breakthrough: Non-Markovian Forward Processes

In standard DDPM (Stages 1–3), sampling is notoriously slow because it requires simulating a Markov chain step-by-step through hundreds of timesteps (e.g., $T=300$ or $1000$).

Song et al. made a critical mathematical realization:
> The DDPM training loss $\mathcal{L}_{\text{simple}}$ only depends on the **marginal** distributions $q(x_t | x_0)$, **never on the joint transition** $q(x_t | x_{t-1})$!

We can design a family of non-Markovian forward processes that share the **exact same marginals**:
$$q_\sigma(x_t | x_0) = \mathcal{N}(x_t; \sqrt{\bar{\alpha}_t} x_0, (1 - \bar{\alpha}_t)\mathbf{I})$$

### The Practical Implication:
**Zero retraining!** Any DDPM model trained in Stage 2 or Stage 3 can immediately be sampled using DDIM in **20 to 50 steps** instead of 300!

---

## 📐 Mathematical Formulation

Given a sub-sequence of timesteps $\tau = [\tau_1, \tau_2, \dots, \tau_S]$ (where $S \ll T$):

1. **Estimate clean $x_0$**:
   $$\hat{x}_0 = \frac{x_t - \sqrt{1 - \bar{\alpha}_t} \epsilon_\theta(x_t, t)}{\sqrt{\bar{\alpha}_t}}$$

2. **Compute variance scaling $\sigma_t(\eta)$**:
   $$\sigma_t(\eta) = \eta \sqrt{\frac{1 - \bar{\alpha}_{t-\Delta t}}{1 - \bar{\alpha}_t}} \sqrt{1 - \frac{\bar{\alpha}_t}{\bar{\alpha}_{t-\Delta t}}}$$

3. **Step backwards**:
   $$x_{t-\Delta t} = \sqrt{\bar{\alpha}_{t-\Delta t}} \hat{x}_0 + \sqrt{1 - \bar{\alpha}_{t-\Delta t} - \sigma_t^2} \epsilon_\theta(x_t, t) + \sigma_t z$$

### The Stochasticity Parameter $\eta$:
- **$\eta = 1.0$ (Stochastic SDE)**: Adds random noise $z \sim \mathcal{N}(0, \mathbf{I})$ at each step (recovers standard DDPM).
- **$\eta = 0.0$ (Deterministic ODE)**: The noise term $\sigma_t z$ becomes $0$. The sampling trajectory is an exact, deterministic Ordinary Differential Equation!

---

## 🏃 Hands-On Execution Guide

### Step 1: Speed & Step Count Benchmark
Benchmark image quality vs sampling time across $S \in [5, 10, 20, 50, 100, 300]$:
```powershell
cd diffusion_models/04_fast_sampling_ddim

..\.venv\Scripts\python.exe benchmark_steps.py --steps 5 10 20 50 100 300 --classes 0 3 7 8
```
*Output image:* `outputs/ddim_steps_comparison.png`

### Step 2: Deterministic Latent Space Interpolation ($\eta = 0.0$)
Because $\eta=0.0$ creates a deterministic 1-to-1 bijection between noise space $\mathcal{N}(0, \mathbf{I})$ and image space, we can interpolate between two random noise vectors using Spherical Linear Interpolation (SLERP) to watch one digit smoothly morph into another:
```powershell
..\.venv\Scripts\python.exe interpolate.py --digit_a 3 --digit_b 8 --frames 8 --steps 30
```
*Output image:* `outputs/latent_interpolation_3_to_8.png`
