"""
Experiment Visualization — All RQs
====================================

Generates publication-quality figures from GAMA experiment outputs.

Experiments:
    RQ1: exp1_topology, exp1b_layers
    RQ2: exp2_advertising
    RQ3: exp3_trust, exp3c_best_friends

Usage:
    python analysis/experiment_plots.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "gama-model" / "output"
IMAGE_DIR = PROJECT_ROOT / "images"
IMAGE_DIR.mkdir(exist_ok=True)

M = 1000
T = 105

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "figure.dpi": 150,
})


def load_experiment(prefix):
    """Load all CSV files matching prefix. Returns DataFrame or None."""
    files = sorted(OUTPUT_DIR.glob(f"{prefix}*.csv"))
    if not files:
        print(f"  No files for {prefix}*")
        return None

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, header=None, names=["sim_id", "cycle", "adopters", "disadopted", "param"])
            df["adopters"] = pd.to_numeric(df["adopters"], errors="coerce")
            df["cycle"] = pd.to_numeric(df["cycle"], errors="coerce")
            df["disadopted"] = pd.to_numeric(df["disadopted"], errors="coerce")
            frames.append(df)
        except Exception as e:
            print(f"  Warning: {f.name}: {e}")

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["cycle", "adopters"])
    combined = combined[combined["cycle"] <= T]
    combined["param"] = combined["param"].astype(str).str.strip()
    return combined


def plot_curves(df, title, filename, label_map=None, colors=None, show_disadopt=False):
    """Plot adoption S-curves with 95% CI shading."""
    if df is None or df.empty:
        print(f"  Skipping {filename} — no data")
        return

    ncols = 3 if show_disadopt else 2
    fig, axes = plt.subplots(1, ncols, figsize=(6 * ncols, 5.5))
    ax1, ax2 = axes[0], axes[1]
    ax3 = axes[2] if show_disadopt else None

    conditions = sorted(df["param"].unique(), key=str)
    lmap = label_map or {}
    default_colors = plt.cm.tab10(np.linspace(0, 1, min(10, len(conditions))))
    cmap = colors or {}

    for idx, cond in enumerate(conditions):
        subset = df[df["param"] == cond]
        grouped = subset.groupby("cycle")["adopters"]
        mean = grouped.mean()
        count = grouped.count()
        ci = 1.96 * grouped.std().fillna(0) / np.sqrt(count.clip(lower=1))

        label = lmap.get(cond, cond.replace("_", " ").title())
        color = cmap.get(cond, default_colors[idx % len(default_colors)])

        # S-curve
        ax1.plot(mean.index, mean.values, label=label, color=color, lw=2)
        ax1.fill_between(mean.index, (mean - ci).values, (mean + ci).values, alpha=0.15, color=color)

        # Daily rate
        rate = mean.diff().fillna(0)
        ax2.plot(rate.index, rate.values, label=label, color=color, lw=2)

        # Disadoption curve
        if show_disadopt and ax3 is not None:
            dis_mean = subset.groupby("cycle")["disadopted"].mean()
            ax3.plot(dis_mean.index, dis_mean.values, label=label, color=color, lw=2)

    ax1.set_xlabel("Day")
    ax1.set_ylabel("Total Adopters")
    ax1.set_title("Adoption Curve")
    ax1.legend(loc="lower right", fontsize=9)
    ax1.set_xlim(0, T)
    ax1.set_ylim(0, M * 1.05)
    ax1.axhline(y=M / 2, color="gray", ls="--", alpha=0.3)
    ax1.grid(True, alpha=0.2)

    ax2.set_xlabel("Day")
    ax2.set_ylabel("New Adopters")
    ax2.set_title("New Adopters per Day")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.set_xlim(0, T)
    ax2.grid(True, alpha=0.2)

    if show_disadopt and ax3 is not None:
        ax3.set_xlabel("Day")
        ax3.set_ylabel("Total Disadoptions")
        ax3.set_title("Disadoption Over Time")
        ax3.legend(loc="lower right", fontsize=9)
        ax3.set_xlim(0, T)
        ax3.grid(True, alpha=0.2)

    plt.suptitle(title, fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = IMAGE_DIR / filename
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved {out.name}")


def plot_bar(df, title, filename, label_map=None, colors=None):
    """Bar chart of final adoption % and disadoptions per condition."""
    if df is None or df.empty:
        return

    final = df[df["cycle"] == df["cycle"].max()]
    summary = final.groupby("param").agg(
        adopt_mean=("adopters", "mean"),
        adopt_std=("adopters", "std"),
        dis_mean=("disadopted", "mean"),
        dis_std=("disadopted", "std"),
    ).reset_index().sort_values("param", key=lambda s: s.astype(str))

    lmap = label_map or {}
    default_colors = plt.cm.tab10(np.linspace(0, 1, min(10, len(summary))))
    cmap = colors or {}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    labels = [lmap.get(p, p.replace("_", " ").title()) for p in summary["param"]]
    bar_colors = [cmap.get(p, default_colors[i % len(default_colors)]) for i, p in enumerate(summary["param"])]

    # Adoption bar
    pct = summary["adopt_mean"] / M * 100
    err = summary["adopt_std"] / M * 100
    bars1 = ax1.bar(range(len(summary)), pct, yerr=err, capsize=5,
                    color=bar_colors, edgecolor="white", lw=0.5)
    ax1.set_xticks(range(len(summary)))
    ax1.set_xticklabels(labels, rotation=15, ha="right")
    ax1.set_ylabel("Final Adoption Rate (%)")
    ax1.set_title("Final Adoption")
    ax1.set_ylim(0, 105)
    for bar, p in zip(bars1, pct):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f"{p:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9)

    # Disadoption bar
    bars2 = ax2.bar(range(len(summary)), summary["dis_mean"], yerr=summary["dis_std"],
                    capsize=5, color=bar_colors, edgecolor="white", lw=0.5)
    ax2.set_xticks(range(len(summary)))
    ax2.set_xticklabels(labels, rotation=15, ha="right")
    ax2.set_ylabel("Total Disadoptions")
    ax2.set_title("Disadoptions")
    for bar, d in zip(bars2, summary["dis_mean"]):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{d:.0f}", ha="center", va="bottom", fontweight="bold", fontsize=9)

    plt.suptitle(title, fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = IMAGE_DIR / filename
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved {out.name}")


def print_summary(df, name):
    """Print summary stats per condition."""
    if df is None or df.empty:
        return
    final = df[df["cycle"] == df["cycle"].max()]
    print(f"\n  {'Condition':<20} {'Final%':>8} {'StdDev':>8} {'t(50%)':>8} {'Disadopt':>10}")
    print(f"  {'-'*58}")
    for cond in sorted(final["param"].unique(), key=str):
        fa = final[final["param"] == cond].groupby("sim_id")["adopters"].first()
        fd = final[final["param"] == cond].groupby("sim_id")["disadopted"].first()
        # time to 50%
        cond_df = df[df["param"] == cond]
        ht = []
        for s in cond_df["sim_id"].unique():
            r = cond_df[(cond_df["sim_id"] == s) & (cond_df["adopters"] >= 500)]
            ht.append(int(r["cycle"].min()) if len(r) > 0 else None)
        ht_s = pd.Series(ht).dropna()
        ht_str = f"{ht_s.mean():.1f}d" if len(ht_s) > 0 else "never"
        print(f"  {cond:<20} {fa.mean()/10:>7.1f}% {fa.std():>7.1f} {ht_str:>8} {fd.mean():>9.1f}")


def main():
    print("=" * 60)
    print("EXPERIMENT VISUALIZATION — ALL RQs")
    print("=" * 60)

    # ── RQ1: Network Topology ──────────────────────────────────
    print("\n\nRQ1a: Network Topology")
    topo_colors = {"random": "#E53935", "small_world": "#1E88E5",
                   "scale_free": "#43A047", "multiplex": "#8E24AA"}
    topo_labels = {"random": "Random", "small_world": "Small-World",
                   "scale_free": "Scale-Free", "multiplex": "Multiplex"}
    df_topo = load_experiment("exp1_topology_")
    print_summary(df_topo, "topology")
    plot_curves(df_topo, "RQ1: Network Topology Comparison", "rq1a_topology_curves.png",
                label_map=topo_labels, colors=topo_colors, show_disadopt=True)
    plot_bar(df_topo, "RQ1: Network Topology — Final Results", "rq1a_topology_bar.png",
             label_map=topo_labels, colors=topo_colors)

    # ── RQ1: Layer Removal ─────────────────────────────────────
    print("\n\nRQ1b: Layer Removal")
    layer_colors = {"all": "#1E88E5", "org_only": "#E53935",
                    "friend_only": "#43A047", "class_only": "#FB8C00"}
    layer_labels = {"all": "All Layers", "org_only": "Org Only (Strong)",
                    "friend_only": "Friend Only (Medium)", "class_only": "Class Only (Weak)"}
    df_layers = load_experiment("exp1b_layers_")
    print_summary(df_layers, "layers")
    plot_curves(df_layers, "RQ1: Which Network Layer Matters Most?", "rq1b_layers_curves.png",
                label_map=layer_labels, colors=layer_colors, show_disadopt=True)
    plot_bar(df_layers, "RQ1: Layer Configuration — Final Results", "rq1b_layers_bar.png",
             label_map=layer_labels, colors=layer_colors)

    # ── RQ2: Advertising Intensity ─────────────────────────────
    print("\n\nRQ2: Advertising Intensity")
    ad_colors = {"0.001": "#1E88E5", "0.003": "#43A047", "0.005": "#FB8C00", "0.01": "#E53935"}
    ad_labels = {"0.001": "p=0.001 (Light)", "0.003": "p=0.003 (Default)",
                 "0.005": "p=0.005 (Heavy)", "0.01": "p=0.01 (Aggressive)"}
    df_ad = load_experiment("exp2_advertising_")
    print_summary(df_ad, "advertising")
    plot_curves(df_ad, "RQ2: Advertising Intensity (with Ad Fatigue)", "rq2_advertising_curves.png",
                label_map=ad_labels, colors=ad_colors, show_disadopt=True)
    plot_bar(df_ad, "RQ2: Advertising Intensity — Final Results", "rq2_advertising_bar.png",
             label_map=ad_labels, colors=ad_colors)

    # ── RQ3: Trust Threshold ───────────────────────────────────
    print("\n\nRQ3a: Trust Threshold")
    trust_colors = {"0.1": "#43A047", "0.3": "#1E88E5", "0.35": "#8E24AA",
                    "0.5": "#FB8C00", "0.7": "#E53935"}
    trust_labels = {"0.1": "b=0.1 (Easy)", "0.3": "b=0.3", "0.35": "b=0.35 (Default)",
                    "0.5": "b=0.5", "0.7": "b=0.7 (Hard)"}
    df_trust = load_experiment("exp3_trust_")
    print_summary(df_trust, "trust")
    plot_curves(df_trust, "RQ3: Trust Threshold — Where Does Adoption Collapse?",
                "rq3a_trust_curves.png", label_map=trust_labels, colors=trust_colors, show_disadopt=True)
    plot_bar(df_trust, "RQ3: Trust Threshold — Final Results", "rq3a_trust_bar.png",
             label_map=trust_labels, colors=trust_colors)

    # ── RQ3: Best Friends ──────────────────────────────────────
    print("\n\nRQ3b: Best Friends (Barkada Effect)")
    bf_colors = {"0": "#E53935", "1": "#FB8C00", "3": "#1E88E5", "5": "#43A047"}
    bf_labels = {"0": "0 (None)", "1": "1 Best Friend", "3": "3 Best Friends", "5": "5 Best Friends"}
    df_bf = load_experiment("exp3c_best_friends_")
    print_summary(df_bf, "best_friends")
    plot_curves(df_bf, "RQ3: Can Your Barkada Override Distrust?", "rq3b_bestfriends_curves.png",
                label_map=bf_labels, colors=bf_colors, show_disadopt=True)
    plot_bar(df_bf, "RQ3: Best Friends — Final Results", "rq3b_bestfriends_bar.png",
             label_map=bf_labels, colors=bf_colors)

    print("\n" + "=" * 60)
    print(f"Done. {len(list(IMAGE_DIR.glob('rq*.png')))} figures saved to images/")


if __name__ == "__main__":
    main()
