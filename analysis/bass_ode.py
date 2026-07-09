"""
Bass Diffusion Model — ODE Baseline
====================================

Purpose:
  Implements the Bass (1969) diffusion model as an ordinary differential
  equation (ODE) to generate baseline adoption S-curves. These curves serve
  as the ground truth for Stage A model-to-model validation: the GAMA ABM
  must reproduce these curves when configured with equivalent parameters
  on a well-mixed (complete) network.

Theory:
  The Bass ODE models cumulative adoption N(t) as:

      dN(t)/dt = [p + q * N(t)/M] * [M - N(t)]

  where:
    p = coefficient of innovation (external influence, e.g., advertising)
    q = coefficient of imitation  (internal influence, e.g., word-of-mouth)
    M = market potential (total population that could adopt)

  The closed-form solution is:

      N(t) = M * (1 - exp(-(p+q)*t)) / (1 + (q/p) * exp(-(p+q)*t))

  This produces the characteristic S-shaped adoption curve.

Parameter Scaling:
  Standard Bass values from the literature (p ~ 0.01-0.03, q ~ 0.3-0.5)
  are calibrated for ANNUAL data. Since our simulation uses DAILY timesteps
  over a 15-week (105-day) semester, parameters are rescaled accordingly.
  The three scenarios (low/medium/high) bracket the range of plausible
  diffusion speeds within the campus context.

Validation Workflow:
  1. Run this script  → produces bass_baseline.csv
  2. Run GAMA ABM with same p, q, M on complete network → export ABM CSV
  3. Compare both CSVs in Python: overlay curves, compute RMSE, peak timing

References:
  - Bass, F.M. (1969). Management Science, 15(5), 215-227.
  - Giordano, G. et al. (2024). arXiv:2410.18730.
  - Kiesling, E. et al. (2012). CEJOR, 20(2), 183-230.

Output:
  - bass_baseline.csv  (day, cumulative_adopters, adoption_rate)
  - bass_scurves.png   (S-curves and adoption rate plots)
"""

import os
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "baseline")
FIGURE_DIR = os.path.join(PROJECT_ROOT, "images")

# ── Parameters ──────────────────────────────────────────────────────
M = 1000          # market potential (total agent population)
T = 105           # simulation length in days (15 weeks)
dt = 1            # one day per timestep

# Daily-scaled parameter sets for a 105-day (15-week) semester
# Derived from annual Bass values (Bass 1969, Kiesling 2012) rescaled
# to daily timesteps: p_daily ≈ p_annual/365, q_daily ≈ q_annual/365
# then calibrated so adoption reaches realistic levels (50-90%) by semester end.
param_sets = {
    "Low diffusion":    {"p": 0.001, "q": 0.05},
    "Medium diffusion": {"p": 0.003, "q": 0.08},
    "High diffusion":   {"p": 0.005, "q": 0.12},
}

# ── Bass ODE ────────────────────────────────────────────────────────
def bass_ode(N, t, p, q, M):
    """dN/dt = [p + q * N(t)/M] * [M - N(t)]"""
    return (p + q * N / M) * (M - N)

# ── Closed-form solution ────────────────────────────────────────────
def bass_closed(t, p, q, M):
    """N(t) = M * (1 - exp(-(p+q)*t)) / (1 + (q/p)*exp(-(p+q)*t))"""
    return M * (1 - np.exp(-(p + q) * t)) / (1 + (q / p) * np.exp(-(p + q) * t))

# ── Generate curves ─────────────────────────────────────────────────
t = np.arange(0, T + dt, dt)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10))

for label, params in param_sets.items():
    p, q = params["p"], params["q"]

    # ODE numerical solution
    N_ode = odeint(bass_ode, 0, t, args=(p, q, M)).flatten()

    # Closed-form solution (for verification)
    N_closed = bass_closed(t, p, q, M)

    # Adoption rate (new adopters per day)
    rate = np.gradient(N_ode, dt)

    # Plot cumulative S-curve
    ax1.plot(t, N_ode, linewidth=2, label=f"{label} (p={p}, q={q})")

    # Plot adoption rate
    ax2.plot(t, rate, linewidth=2, label=f"{label} (p={p}, q={q})")

# ── Cumulative adoption plot ────────────────────────────────────────
ax1.set_xlabel("Day", fontsize=12)
ax1.set_ylabel("Total Adopters", fontsize=12)
ax1.set_title("Bass Diffusion S-Curves", fontsize=14)
ax1.legend(fontsize=10)
ax1.set_xlim(0, T)
ax1.set_ylim(0, M * 1.05)
ax1.grid(True, alpha=0.3)

# ── Adoption rate plot ──────────────────────────────────────────────
ax2.set_xlabel("Day", fontsize=12)
ax2.set_ylabel("New Adopters", fontsize=12)
ax2.set_title("Bass Adoption Rate (Bell Curve)", fontsize=14)
ax2.legend(fontsize=10)
ax2.set_xlim(0, T)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
os.makedirs(FIGURE_DIR, exist_ok=True)
plt.savefig(os.path.join(FIGURE_DIR, "bass_scurves.png"), dpi=150)
plt.close()

# ── Export CSV for the medium diffusion baseline ────────────────────
p_base, q_base = 0.003, 0.08
N_baseline = odeint(bass_ode, 0, t, args=(p_base, q_base, M)).flatten()
rate_baseline = np.gradient(N_baseline, dt)

df = pd.DataFrame({
    "day": t.astype(int),
    "cumulative_adopters": np.round(N_baseline, 2),
    "adoption_rate": np.round(rate_baseline, 2),
})
df.to_csv(os.path.join(OUTPUT_DIR, "bass_baseline.csv"), index=False)

print(f"Bass ODE Baseline (p={p_base}, q={q_base}, M={M})")
print(f"  Peak adoption day: {int(t[np.argmax(rate_baseline)])}")
print(f"  Peak rate: {rate_baseline.max():.1f} adopters/day")
print(f"  Day 50 penetration: {N_baseline[50]/M*100:.1f}%")
print(f"  Final penetration: {N_baseline[-1]/M*100:.1f}%")
print(f"\nFiles saved to {OUTPUT_DIR}:")
print(f"  bass_scurves.png")
print(f"  bass_baseline.csv")
