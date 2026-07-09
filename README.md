# Barkada-ABM: Agent-Based Model of Digital Payment Adoption

Simulation code and analysis for the paper:

> **Simulating the Barkada Effect: An Agent-Based Model of Digital Payment
> Adoption Among University Students**
> Jorge G. Bocobo and Zenith O. Arnejo
> Institute of Computer Science, University of the Philippines Los Baños
> *24th International Conference on Practical Applications of Agents and
> Multi-Agent Systems (PAAMS 2026), Naples, Italy.* Springer LNAI.

This repository provides the GAMA agent-based model, the Python analysis
scripts, and the (anonymized) survey-derived data needed to reproduce the
study's three-stage evaluation.

## Overview

The model simulates how digital payment adoption spreads among university
students through peer word-of-mouth, advertising, and close-friend
("*barkada*") ties. Student agents use a Belief–Desire–Intention (BDI)
decision rule, are embedded in a multiplex campus network (organization,
friendship, classroom layers), and can adopt, sustain, or *disadopt* the
platform over a 15-week semester. The model is evaluated in three stages:

- **Stage A — Model-to-model validation:** the ABM reproduces the analytical
  Bass diffusion ODE on a well-mixed network (RMSE 2.7%).
- **Stage B — Empirical validation:** 100 agents are parameterized from real
  UPLB survey respondents and scored against their self-reported payment mode
  (72.3% per-agent exact-state accuracy).
- **Stage C — Scenario analysis:** experiments on network topology, layer
  removal, advertising intensity, trust thresholds, and *barkada* ties.

The model follows the ODD (Overview–Design concepts–Details) protocol; see
[`docs/odd-protocol.md`](docs/odd-protocol.md) for the full specification.

## Repository structure

```
gama-model/
  models/digital_payment_adoption.gaml   GAMA model (baseline + all experiments)
analysis/
  bass_ode.py                            Analytical Bass ODE baseline (Stage A)
  validation.py                          ABM-vs-ODE comparison (Stage A)
  empirical_cohort.py                    Builds the 100-agent empirical cohort (Stage B)
  empirical_validation.py                Scores agents vs. self-reported behavior (Stage B)
  experiment_plots.py                    Figures for the scenario experiments (Stage C)
data/
  survey_responses_anonymized.csv        180 UPLB responses, de-identified (see Data & privacy)
  empirical_cohort.csv                   Derived 100-agent cohort used in Stage B
  baseline/bass_baseline.csv             Analytical Bass baseline series
  generate_synthetic.py                  Item map, archetype definitions, synthetic-data utility
docs/
  odd-protocol.md                        Full ODD-protocol description of the model
```

## Requirements

- **GAMA Platform** 1.9+ (https://gama-platform.org) to run the `.gaml` model.
- **Python** 3.10+ with `numpy`, `pandas`, `scipy`, and `matplotlib`:

```bash
pip install numpy pandas scipy matplotlib
```

## Running the model

**Simulation (GAMA).** Open `gama-model/models/digital_payment_adoption.gaml`
in GAMA. The file defines a `baseline` GUI experiment, a `baseline_batch`
experiment (30 replications), a `full_model` experiment, and the RQ1–RQ3
scenario experiments. Run an experiment to export per-tick adoption/disadoption
CSVs.

**Analysis (Python).** From the repository root:

```bash
python analysis/bass_ode.py           # generate the analytical Bass baseline
python analysis/validation.py         # Stage A: ABM vs. ODE
python analysis/empirical_validation.py  # Stage B: score agents vs. survey
python analysis/experiment_plots.py   # Stage C: scenario figures
```

## Data & privacy

The **raw** survey export is **not** published. It contained respondent
usernames/emails and submission timestamps collected via Google Forms under
informed consent (Philippine Data Privacy Act of 2012, RA 10173); that consent
covered the study, not public redistribution of identifiable data.

To keep the pipeline reproducible while protecting respondents, this repository
instead provides:

- `data/survey_responses_anonymized.csv` — the 180 responses with all direct
  identifiers removed (Timestamp, Username/email, and the consent-notice field
  dropped; a surrogate `respondent_id` added). Only demographics, organization
  context, and the 50 Likert items remain.
- `data/empirical_cohort.csv` — the de-identified 100-agent cohort actually
  used in Stage B, so downstream validation and simulation reproduce exactly.

`analysis/empirical_cohort.py` documents how the cohort is derived from the
survey responses.

## Citation

If you use this code, please cite:

```bibtex
@inproceedings{Bocobo2026Barkada,
  author    = {Bocobo, Jorge G. and Arnejo, Zenith O.},
  title     = {Simulating the Barkada Effect: An Agent-Based Model of Digital
               Payment Adoption Among University Students},
  booktitle = {Advances in Practical Applications of Agentic AI and Multi-Agent
               Systems (PAAMS 2026)},
  series    = {Lecture Notes in Artificial Intelligence},
  publisher = {Springer},
  year      = {2026}
}
```

## License

Released under the MIT License. See [`LICENSE`](LICENSE).
