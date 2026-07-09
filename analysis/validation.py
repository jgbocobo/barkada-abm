"""
Validation Script — ABM vs Bass ODE Comparison
===============================================

Purpose:
    Compares the GAMA ABM output against the Bass ODE baseline to validate
    that the agent-based diffusion engine reproduces the analytical S-curve
    under equivalent conditions (homogeneous agents, well-mixed network).

Usage:
    1. Run the baseline ABM configuration in GAMA (30 Monte Carlo runs).
    2. Export each run as a CSV to gama-model/output/ with columns:
       day, cumulative_adopters
    3. Run this script:
       python analysis/validation.py

Metrics:
    - RMSE between mean ABM curve and Bass ODE curve
    - Peak adoption day difference
    - Final penetration difference
    - Visual overlay of all 30 runs + mean + ODE baseline

References:
    - Bass, F.M. (1969). Management Science, 15(5), 215-227.
    - Giordano, G. et al. (2024). arXiv:2410.18730.
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASELINE_CSV = os.path.join(PROJECT_ROOT, "data", "baseline", "bass_baseline.csv")
ABM_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "gama-model", "output")
FIGURE_DIR = os.path.join(PROJECT_ROOT, "images")

M = 1000  # Population size (must match ABM and Bass ODE)


def load_baseline():
    """Load the Bass ODE baseline CSV."""
    df = pd.read_csv(BASELINE_CSV)
    return df["day"].values, df["cumulative_adopters"].values, df["adoption_rate"].values


def load_abm_runs():
    """Load ABM run data from the GAMA output directory.

    Supports two formats:
    1. Single file: baseline_all_runs.csv with columns: run_id, cycle, nb_adopters
    2. Multiple files: baseline_run_*.csv with columns: run_id, cycle, nb_adopters

    Returns a list of DataFrames (one per run), each with columns: day, cumulative_adopters.
    """
    single_file = os.path.join(ABM_OUTPUT_DIR, "baseline_all_runs.csv")
    if os.path.exists(single_file):
        df = pd.read_csv(single_file, header=None, names=["run_id", "day", "cumulative_adopters"])
        runs = []
        for run_id in sorted(df["run_id"].unique()):
            run_df = df[df["run_id"] == run_id][["day", "cumulative_adopters"]].reset_index(drop=True)
            runs.append(run_df)
        print(f"Loaded {len(runs)} ABM runs from {single_file}")
        return runs

    pattern = os.path.join(ABM_OUTPUT_DIR, "baseline_run_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"No ABM output files found.\n"
            f"Expected: {single_file} or files matching {pattern}\n"
            f"Run the baseline ABM in GAMA and export CSVs first."
        )
    runs = [pd.read_csv(f) for f in files]
    print(f"Loaded {len(runs)} ABM runs from {ABM_OUTPUT_DIR}")
    return runs


def compute_metrics(bass_curve, abm_mean_curve):
    """Compute validation metrics between Bass ODE and mean ABM curve.

    Args:
        bass_curve: numpy array of Bass ODE cumulative adopters (length T+1).
        abm_mean_curve: numpy array of mean ABM cumulative adopters (length T+1).

    Returns:
        dict with RMSE, peak_day_diff, and final_penetration_diff.
    """
    # RMSE
    rmse = np.sqrt(np.mean((bass_curve - abm_mean_curve) ** 2))

    # Peak adoption day (day of maximum adoption rate)
    bass_rate = np.gradient(bass_curve)
    abm_rate = np.gradient(abm_mean_curve)
    peak_diff = int(np.argmax(abm_rate) - np.argmax(bass_rate))

    # Final penetration
    final_diff = abm_mean_curve[-1] - bass_curve[-1]

    return {
        "rmse": rmse,
        "rmse_pct": rmse / M * 100,
        "peak_day_diff": peak_diff,
        "final_penetration_diff": final_diff,
        "final_penetration_diff_pct": final_diff / M * 100,
    }


def plot_validation(days, bass_curve, abm_runs, abm_mean, metrics):
    """Generate the validation overlay plot.

    Shows all individual ABM runs (light gray), the mean ABM curve (blue),
    and the Bass ODE baseline (red dashed).
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10))

    # Cumulative adoption
    for run in abm_runs:
        ax1.plot(run["day"], run["cumulative_adopters"],
                 color="gray", alpha=0.15, linewidth=0.5)
    ax1.plot(days, abm_mean, color="blue", linewidth=2, label="ABM Mean")
    ax1.plot(days, bass_curve, color="red", linewidth=2,
             linestyle="--", label="Bass ODE")
    ax1.set_xlabel("Day")
    ax1.set_ylabel("Total Adopters")
    ax1.set_title("Validation: ABM vs Bass ODE (Total Adopters)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Adoption rate
    bass_rate = np.gradient(bass_curve)
    abm_rate = np.gradient(abm_mean)
    ax2.plot(days, abm_rate, color="blue", linewidth=2, label="ABM Mean Rate")
    ax2.plot(days, bass_rate, color="red", linewidth=2,
             linestyle="--", label="Bass ODE Rate")
    ax2.set_xlabel("Day")
    ax2.set_ylabel("New Adopters")
    ax2.set_title("Validation: New Adopters per Day")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Metrics annotation
    text = (
        f"RMSE: {metrics['rmse']:.1f} ({metrics['rmse_pct']:.1f}%)\n"
        f"Peak day diff: {metrics['peak_day_diff']:+d} days\n"
        f"Final diff: {metrics['final_penetration_diff']:+.1f} "
        f"({metrics['final_penetration_diff_pct']:+.1f}%)"
    )
    ax1.text(0.02, 0.98, text, transform=ax1.transAxes,
             verticalalignment="top", fontsize=9,
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

    plt.tight_layout()
    os.makedirs(FIGURE_DIR, exist_ok=True)
    out_path = os.path.join(FIGURE_DIR, "validation_overlay.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Validation plot saved to {out_path}")


def main():
    """Run the full validation pipeline."""
    print("=" * 60)
    print("ABM vs Bass ODE Validation")
    print("=" * 60)

    # Load data
    days, bass_curve, bass_rate = load_baseline()
    abm_runs = load_abm_runs()

    # Compute mean ABM curve across all runs (handle varying run lengths)
    min_run_len = min(len(run) for run in abm_runs)
    min_len = min(len(bass_curve), min_run_len)
    days = days[:min_len]
    bass_curve = bass_curve[:min_len]
    bass_rate = bass_rate[:min_len]
    for i, run in enumerate(abm_runs):
        abm_runs[i] = run.iloc[:min_len]
    all_adopters = np.array([run["cumulative_adopters"].values for run in abm_runs])
    abm_mean = np.mean(all_adopters, axis=0)

    # Compute metrics
    metrics = compute_metrics(bass_curve, abm_mean)

    print(f"\nResults ({len(abm_runs)} runs):")
    print(f"  RMSE:              {metrics['rmse']:.1f} agents ({metrics['rmse_pct']:.1f}% of M)")
    print(f"  Peak day diff:     {metrics['peak_day_diff']:+d} days")
    print(f"  Final penetration: {metrics['final_penetration_diff']:+.1f} agents "
          f"({metrics['final_penetration_diff_pct']:+.1f}%)")

    # Validation pass/fail
    passed = metrics["rmse_pct"] < 5.0
    print(f"\n  VALIDATION: {'PASSED' if passed else 'FAILED'} "
          f"(threshold: RMSE < 5% of M = {M * 0.05:.0f} agents)")

    # Plot
    plot_validation(days, bass_curve, abm_runs, abm_mean, metrics)

    return metrics


if __name__ == "__main__":
    main()
