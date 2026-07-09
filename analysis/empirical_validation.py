"""
empirical_validation.py

Scores the Stage C empirical-validation run.

Reads:
  data/empirical_cohort.csv                 (100 sampled real respondents,
                                             source_id -> ground_truth_state)
  gama-model/output/empirical_validation_*.csv
                                            (one file per replication, each row
                                             = one empirical agent's final state)

Emits:
  - printed summary (overall, binary, per-persona accuracy; confusion matrix)
  - images/empirical_validation_confusion.png   5x5 confusion-matrix heatmap
  - images/empirical_validation_by_persona.png  per-persona accuracy bar chart

Usage:
    python3 analysis/empirical_validation.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
COHORT_CSV = REPO_ROOT / "data" / "empirical_cohort.csv"
RUN_GLOB = "empirical_validation_*.csv"
OUTPUT_DIR = REPO_ROOT / "gama-model" / "output"
IMG_DIR = REPO_ROOT / "images"

STATES = ["Unaware", "Aware", "Trial", "Regular", "Advocate"]
ADOPTED_STATES = {"Trial", "Regular", "Advocate"}

PERSONA_BY_IDX = {
    1: "Tech Enthusiast",
    2: "Social Follower",
    3: "Cautious Adopter",
    4: "Price Sensitive",
    5: "Disengaged",
}


def load_cohort() -> dict[int, dict]:
    """source_id -> {persona, ground_truth_state}."""
    out: dict[int, dict] = {}
    with COHORT_CSV.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[int(row["source_id"])] = {
                "persona": row["persona"],
                "ground_truth_state": row["ground_truth_state"],
            }
    return out


def load_runs() -> list[list[dict]]:
    """One inner list per replication. Each entry: {source_id, persona_idx, final_state}."""
    files = sorted(OUTPUT_DIR.glob(RUN_GLOB))
    if not files:
        print(
            f"No run files matching {RUN_GLOB} in {OUTPUT_DIR}. "
            f"Run the GAMA exp_empirical_validation experiment first.",
            file=sys.stderr,
        )
        sys.exit(1)

    runs = []
    for p in files:
        with p.open() as f:
            reader = csv.reader(f)
            header = next(reader, None)
            rows = []
            for r in reader:
                if len(r) < 5:
                    continue
                try:
                    rows.append(
                        {
                            "run_id": int(r[0]),
                            "source_id": int(r[1]),
                            "persona_idx": int(r[2]),
                            "final_state": r[3],
                        }
                    )
                except ValueError:
                    continue
            if rows:
                runs.append(rows)
    return runs


def score_run(run: list[dict], cohort: dict[int, dict]) -> dict:
    total = 0
    exact = 0
    binary = 0
    per_persona_total: dict[str, int] = defaultdict(int)
    per_persona_exact: dict[str, int] = defaultdict(int)
    per_persona_binary: dict[str, int] = defaultdict(int)
    conf = np.zeros((len(STATES), len(STATES)), dtype=int)
    state_idx = {s: i for i, s in enumerate(STATES)}

    for a in run:
        truth = cohort.get(a["source_id"])
        if truth is None:
            continue
        total += 1
        gt_state = truth["ground_truth_state"]
        persona = truth["persona"]
        final = a["final_state"]

        per_persona_total[persona] += 1

        if final == gt_state:
            exact += 1
            per_persona_exact[persona] += 1

        if (final in ADOPTED_STATES) == (gt_state in ADOPTED_STATES):
            binary += 1
            per_persona_binary[persona] += 1

        if final in state_idx and gt_state in state_idx:
            conf[state_idx[gt_state], state_idx[final]] += 1

    return {
        "total": total,
        "exact": exact,
        "binary": binary,
        "per_persona_total": dict(per_persona_total),
        "per_persona_exact": dict(per_persona_exact),
        "per_persona_binary": dict(per_persona_binary),
        "confusion": conf,
    }


def aggregate(run_results: list[dict]):
    exact_accs = [r["exact"] / r["total"] for r in run_results if r["total"]]
    binary_accs = [r["binary"] / r["total"] for r in run_results if r["total"]]

    personas = sorted(
        {p for r in run_results for p in r["per_persona_total"]}
    )

    per_persona_exact_accs: dict[str, list[float]] = {p: [] for p in personas}
    per_persona_binary_accs: dict[str, list[float]] = {p: [] for p in personas}
    for r in run_results:
        for p in personas:
            total = r["per_persona_total"].get(p, 0)
            if total == 0:
                continue
            per_persona_exact_accs[p].append(r["per_persona_exact"].get(p, 0) / total)
            per_persona_binary_accs[p].append(r["per_persona_binary"].get(p, 0) / total)

    confusion = sum(r["confusion"] for r in run_results)

    return {
        "n_runs": len(run_results),
        "exact_mean": float(np.mean(exact_accs)) if exact_accs else 0.0,
        "exact_std": float(np.std(exact_accs)) if exact_accs else 0.0,
        "binary_mean": float(np.mean(binary_accs)) if binary_accs else 0.0,
        "binary_std": float(np.std(binary_accs)) if binary_accs else 0.0,
        "personas": personas,
        "per_persona_exact": {
            p: (float(np.mean(v)), float(np.std(v))) if v else (0.0, 0.0)
            for p, v in per_persona_exact_accs.items()
        },
        "per_persona_binary": {
            p: (float(np.mean(v)), float(np.std(v))) if v else (0.0, 0.0)
            for p, v in per_persona_binary_accs.items()
        },
        "confusion": confusion,
    }


def print_summary(agg: dict) -> None:
    print(f"Replications loaded: {agg['n_runs']}\n")
    print("Overall accuracy (mean +/- std across runs):")
    print(f"  Exact state match:    {100*agg['exact_mean']:5.1f}% +/- {100*agg['exact_std']:4.1f}%")
    print(f"  Binary adoption match:{100*agg['binary_mean']:5.1f}% +/- {100*agg['binary_std']:4.1f}%")

    print("\nPer-persona accuracy:")
    print(f"  {'Persona':<18} {'Exact (mean+/-std)':<24} {'Binary (mean+/-std)':<24}")
    for p in agg["personas"]:
        em, es = agg["per_persona_exact"][p]
        bm, bs = agg["per_persona_binary"][p]
        print(f"  {p:<18} {100*em:5.1f}% +/- {100*es:4.1f}%      {100*bm:5.1f}% +/- {100*bs:4.1f}%")

    print("\nConfusion matrix (rows=ground truth, cols=predicted, summed across runs):")
    conf = agg["confusion"]
    hdr = "  " + " " * 12 + "  ".join(f"{s:>10s}" for s in STATES)
    print(hdr)
    for i, s in enumerate(STATES):
        row = "  " + f"{s:<12s}" + "  ".join(f"{int(v):>10d}" for v in conf[i])
        print(row)


def plot_confusion(conf: np.ndarray, n_runs: int) -> Path:
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(conf, cmap="Blues")
    ax.set_xticks(range(len(STATES)))
    ax.set_yticks(range(len(STATES)))
    ax.set_xticklabels(STATES, rotation=30, ha="right")
    ax.set_yticklabels(STATES)
    ax.set_xlabel("Predicted (model final state)")
    ax.set_ylabel("Ground truth (survey-reported)")
    ax.set_title(
        f"Empirical validation confusion matrix\n"
        f"(100 empirical agents x {n_runs} replications)"
    )
    for i in range(len(STATES)):
        for j in range(len(STATES)):
            ax.text(
                j,
                i,
                int(conf[i, j]),
                ha="center",
                va="center",
                color="white" if conf[i, j] > conf.max() / 2 else "black",
                fontsize=10,
            )
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out = IMG_DIR / "empirical_validation_confusion.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_per_persona(agg: dict) -> Path:
    personas = agg["personas"]
    exact_means = [agg["per_persona_exact"][p][0] for p in personas]
    exact_stds = [agg["per_persona_exact"][p][1] for p in personas]
    binary_means = [agg["per_persona_binary"][p][0] for p in personas]
    binary_stds = [agg["per_persona_binary"][p][1] for p in personas]

    x = np.arange(len(personas))
    w = 0.38

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(x - w / 2, np.array(exact_means) * 100, w, yerr=np.array(exact_stds) * 100,
           capsize=3, label="Exact state", color="#4d7cff")
    ax.bar(x + w / 2, np.array(binary_means) * 100, w, yerr=np.array(binary_stds) * 100,
           capsize=3, label="Binary adoption", color="#2ea84e")
    ax.set_xticks(x)
    ax.set_xticklabels(personas, rotation=20, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Empirical validation accuracy by persona")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    out = IMG_DIR / "empirical_validation_by_persona.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def main():
    cohort = load_cohort()
    runs = load_runs()

    run_results = [score_run(r, cohort) for r in runs]
    agg = aggregate(run_results)
    print_summary(agg)

    IMG_DIR.mkdir(exist_ok=True)
    conf_path = plot_confusion(agg["confusion"], agg["n_runs"])
    bar_path = plot_per_persona(agg)
    print(f"\nFigures written:\n  {conf_path.relative_to(REPO_ROOT)}\n  {bar_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
