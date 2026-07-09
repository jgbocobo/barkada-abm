"""
empirical_cohort.py

Builds the 100-agent empirical cohort for Stage C empirical validation.

Input:  data/survey_responses.csv  (180 real UPLB student survey responses)
Output: data/empirical_cohort.csv  (100 sampled agents with per-agent BDI
                                   parameters and ground-truth adoption state)

Sampling: uniform random, fixed seed (42) for reproducibility.

Each output row is one agent:
  source_id       - index of the source row in survey_responses.csv (0-179)
  persona         - nearest of 5 archetypes (used for adoption_threshold lookup)
  security_belief, social_susceptibility, price_fairness,
  message_quality, involvement
                  - dimension scores normalised to [0, 1] from the respondent's
                    own reverse-coded Likert means (divided by 5)
  adoption_threshold
                  - inherited from the nearest persona archetype
  ground_truth_state
                  - mapped from the respondent's "Frequency of Digital Payment
                    Use" answer: Never->Unaware, Rarely->Aware,
                    'A few times a month'->Trial, 'A few times a week'->Trial,
                    Daily->Regular. (Advocate is not observable in the survey.)
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from generate_synthetic import ITEM_MAP, PERSONAS  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
SURVEY_CSV = REPO_ROOT / "data" / "survey_responses.csv"
OUT_CSV = REPO_ROOT / "data" / "empirical_cohort.csv"

COHORT_SIZE = 100
RANDOM_SEED = 42

DIMS = ["social", "security", "price", "info", "involvement"]
LIKERT_LABEL_TO_INT = {
    "Strongly Disagree": 1,
    "Disagree": 2,
    "Neutral": 3,
    "Agree": 4,
    "Strongly Agree": 5,
}
# Ground-truth state is derived from the respondent's primary payment mode
# (col 6), not frequency. If their primary mode includes any digital option,
# they're considered a Regular (adopter); if cash-only, Unaware (non-adopter).
DIGITAL_MODES = {"Gcash", "GCash", "Maya", "PayMaya", "Bank Transfer"}


def mode_to_state(primary_mode: str) -> str:
    modes = {m.strip() for m in (primary_mode or "").split(";") if m.strip()}
    uses_digital = any(m in DIGITAL_MODES for m in modes)
    return "Regular" if uses_digital else "Unaware"


def parse_likert(cell: str) -> int | None:
    s = (cell or "").strip()
    if s in LIKERT_LABEL_TO_INT:
        return LIKERT_LABEL_TO_INT[s]
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def score_dimensions(likert_50: list[str]) -> dict[str, float | None]:
    """Reverse-code and average the 50 Likert items per BDI dimension."""
    sums = {d: 0.0 for d in DIMS}
    counts = {d: 0 for d in DIMS}
    for i, raw in enumerate(likert_50):
        val = parse_likert(raw)
        if val is None:
            continue
        dim, is_reverse = ITEM_MAP[i]
        if is_reverse:
            val = 6 - val
        sums[dim] += val
        counts[dim] += 1
    return {d: (sums[d] / counts[d] if counts[d] else None) for d in DIMS}


def nearest_persona(dim_means: dict[str, float | None]) -> str:
    best_name, best_dist = None, float("inf")
    for name, profile in PERSONAS.items():
        dist = math.sqrt(
            sum(
                (dim_means[d] - profile[d]) ** 2
                for d in DIMS
                if dim_means[d] is not None
            )
        )
        if dist < best_dist:
            best_name, best_dist = name, dist
    return best_name


# Adoption threshold per persona: inherited from the GAML persona_profiles
# list (6th element of each row). Kept here so this module stays
# self-contained and does not depend on GAML being parsed.
PERSONA_ADOPTION_THRESHOLD = {
    "Tech Enthusiast": 0.15,
    "Social Follower": 0.25,
    "Cautious Adopter": 0.45,
    "Price Sensitive": 0.35,
    "Disengaged": 0.55,
}


def build_cohort():
    with SURVEY_CSV.open() as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]

    # Keep only rows with a complete schema (61 cols).
    usable = []
    for idx, row in enumerate(data):
        if len(row) < 61:
            continue
        usable.append((idx, row))

    if len(usable) < COHORT_SIZE:
        raise RuntimeError(
            f"Only {len(usable)} usable responses, need {COHORT_SIZE}"
        )

    rng = random.Random(RANDOM_SEED)
    sampled = rng.sample(usable, COHORT_SIZE)

    out_rows = []
    for source_id, row in sampled:
        likert_50 = row[11:61]
        dim_means = score_dimensions(likert_50)
        if any(v is None for v in dim_means.values()):
            continue
        persona = nearest_persona(dim_means)
        state = mode_to_state(row[6])

        out_rows.append(
            {
                "source_id": source_id,
                "persona": persona,
                "security_belief": round(dim_means["security"] / 5.0, 4),
                "social_susceptibility": round(dim_means["social"] / 5.0, 4),
                "price_fairness": round(dim_means["price"] / 5.0, 4),
                "message_quality": round(dim_means["info"] / 5.0, 4),
                "involvement": round(dim_means["involvement"] / 5.0, 4),
                "adoption_threshold": PERSONA_ADOPTION_THRESHOLD[persona],
                "ground_truth_state": state,
            }
        )

    fieldnames = [
        "source_id",
        "persona",
        "security_belief",
        "social_susceptibility",
        "price_fairness",
        "message_quality",
        "involvement",
        "adoption_threshold",
        "ground_truth_state",
    ]

    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    return out_rows


def summarise(out_rows):
    from collections import Counter

    persona_counts = Counter(r["persona"] for r in out_rows)
    state_counts = Counter(r["ground_truth_state"] for r in out_rows)

    print(f"Wrote {len(out_rows)} rows to {OUT_CSV.relative_to(REPO_ROOT)}")
    print(f"Seed: {RANDOM_SEED}, source: survey_responses.csv")

    print("\nPersona distribution:")
    for name in PERSONAS:
        n = persona_counts.get(name, 0)
        pct = 100 * n / len(out_rows)
        print(f"  {name:17s} {n:>3d}  ({pct:5.1f}%)")

    print("\nGround-truth state distribution:")
    for s in ["Unaware", "Aware", "Trial", "Regular", "Advocate"]:
        n = state_counts.get(s, 0)
        pct = 100 * n / len(out_rows)
        print(f"  {s:10s} {n:>3d}  ({pct:5.1f}%)")

    adopted = sum(state_counts.get(s, 0) for s in ("Trial", "Regular", "Advocate"))
    nonadopted = sum(state_counts.get(s, 0) for s in ("Unaware", "Aware"))
    total = adopted + nonadopted
    print(
        f"\nOverall: adopted = {adopted}/{total} ({100*adopted/total:.1f}%), "
        f"not adopted = {nonadopted}/{total} ({100*nonadopted/total:.1f}%)"
    )


if __name__ == "__main__":
    summarise(build_cohort())
