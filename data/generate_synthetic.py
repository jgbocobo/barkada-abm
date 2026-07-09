#!/usr/bin/env python3
"""
Generate synthetic survey responses for Digital Payment Adoption at UPLB.

Calibrated from 10 real pilot responses + 5 persona archetypes from the ABM.
Personas: Tech Enthusiast, Social Follower, Cautious Adopter, Price Sensitive, Disengaged

Output: data/survey_responses.csv (matches Google Forms export format)
"""

import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────
N_TOTAL = 180  # target sample size
ORGS = [
    "YOUNG SOFTWARE ENGINEERS' SOCIETY (YSES)",
    "ALLIANCE OF COMPUTER SCIENCE STUDENTS (ACSS)",
    "UPLB COMPUTER SCIENCE SOCIETY (COSS)",
]
YEAR_LEVELS = ["Freshman", "Sophomore", "Junior", "Senior"]
YEAR_WEIGHTS = [0.20, 0.30, 0.25, 0.25]  # realistic distribution

COLLEGE = "College of Arts and Sciences"
PROGRAM = "BS Computer Science"

LIKERT = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
# Numeric mapping: SD=1, D=2, N=3, A=4, SA=5

PAYMENT_MODES = ["Cash", "Gcash", "Maya", "Bank Transfer"]
FREQUENCY_OPTIONS = ["Daily", "A few times a week", "A few times a month", "Rarely"]

ORG_USES = [
    "Collecting membership fees",
    "Selling merchandise or tickets for events",
    "Fundraising or donation drives",
    "Reimbursing members for expenses",
    "Paying for official organization purchases (e.g., food, supplies)",
]

CONSENT_TEXT = (
    'By ticking the checkbox below, you acknowledge that you have read and '
    'fully understood the information above and that your participation in '
    'this survey is voluntary. You also consent to the collection and use '
    'of your information under this Data Privacy Notice.'
)

# ── 50 Likert items mapped to BDI dimensions ──────────────────────────
# Each item: (dimension, is_reverse_coded)
# Dimensions: social, security, price, info, involvement
ITEM_MAP = [
    # 1 of 5 (items 0-9)
    ("social", False),       # Q1: same apps as friends
    ("security", False),     # Q2: confident in security measures
    ("price", False),        # Q3: transaction fees reasonable
    ("info", False),         # Q4: ads are believable
    ("involvement", False),  # Q5: actively seek info
    ("social", False),       # Q6: org members influence
    ("security", True),      # Q7: worry about data compromise
    ("price", False),        # Q8: costs are fair
    ("info", False),         # Q9: info on features is clear
    ("involvement", True),   # Q10: don't think much, use what's convenient
    # 2 of 5 (items 10-19)
    ("social", False),       # Q11: seeing others makes me use it
    ("security", False),     # Q12: trust companies protect privacy
    ("price", True),         # Q13: exchange rates unjust
    ("info", False),         # Q14: UPLB announcements trustworthy
    ("involvement", False),  # Q15: significant decision
    ("social", False),       # Q16: ask friends for recs
    ("security", False),     # Q17: safer than carrying cash
    ("price", True),         # Q18: convenience fees unfair
    ("info", False),         # Q19: notifications useful
    ("involvement", False),  # Q20: interested in fintech
    # 3 of 5 (items 20-29)
    ("social", False),       # Q21: family opinion matters
    ("security", True),      # Q22: fraud reporting complicated
    ("price", False),        # Q23: value > fees
    ("info", True),          # Q24: skeptical of marketing
    ("involvement", False),  # Q25: knowledgeable about options
    ("social", False),       # Q26: pressured at events
    ("security", False),     # Q27: comfortable linking bank
    ("price", False),        # Q28: GSave/GInvest pricing fair
    ("social", False),       # Q29: rely on friends over official
    ("involvement", True),   # Q30: paying not important in daily life
    # 4 of 5 (items 30-39)
    ("social", False),       # Q31: cashless trend motivates
    ("security", True),      # Q32: fear sending to wrong number
    ("price", True),         # Q33: unfair cross-app charges
    ("info", False),         # Q34: feature info adequate
    ("involvement", False),  # Q35: enjoy trying new features
    ("social", False),       # Q36: prof recommends -> adopt
    ("security", False),     # Q37: companies reputable
    ("price", False),        # Q38: cash-in fees fair
    ("info", False),         # Q39: word-of-mouth reliable
    ("involvement", True),   # Q40: don't notice differences
    # 5 of 5 (items 40-49)
    ("social", False),       # Q41: org app motivates usage
    ("security", False),     # Q42: transaction history private
    ("price", False),        # Q43: promos provide real value
    ("info", True),          # Q44: ignore promo messages
    ("involvement", False),  # Q45: passionate about tech
    ("social", False),       # Q46: prefer widely accepted
    ("security", True),      # Q47: concerned about scams
    ("price", False),        # Q48: fair to charge for expedited
    ("info", True),          # Q49: fee details confusing
    ("involvement", True),   # Q50: don't follow tech trends
]

# ── Persona definitions ────────────────────────────────────────────────
# Mean Likert score (1-5) per dimension for each persona
# Calibrated from ABM profiles + real pilot data
PERSONAS = {
    # Proportions calibrated from pilot: Cautious Adopter dominant (~50%),
    # no Disengaged observed, remaining personas split roughly evenly.
    "Tech Enthusiast": {
        "social": 3.2,      # moderate social influence
        "security": 4.2,    # high trust in security
        "price": 3.8,       # generally find prices fair
        "info": 4.0,        # find info quality good
        "involvement": 4.5, # very high engagement
        "proportion": 0.167,
        "payment_modes": {"Cash": 0.5, "Gcash": 0.9, "Maya": 0.4, "Bank Transfer": 0.5},
        "frequency_weights": [0.45, 0.40, 0.10, 0.05],
        "org_prob": 0.6,
    },
    "Social Follower": {
        "social": 4.3,      # very high social susceptibility
        "security": 3.4,    # moderate trust
        "price": 3.3,       # moderate price perception
        "info": 3.2,        # moderate info quality
        "involvement": 3.2, # moderate engagement
        "proportion": 0.167,
        "payment_modes": {"Cash": 0.7, "Gcash": 0.85, "Maya": 0.15, "Bank Transfer": 0.2},
        "frequency_weights": [0.25, 0.50, 0.15, 0.10],
        "org_prob": 0.55,
    },
    "Cautious Adopter": {
        "social": 3.0,      # moderate
        "security": 2.5,    # low trust, high worry
        "price": 3.5,       # fair on price
        "info": 2.8,        # skeptical of info
        "involvement": 2.8, # low-moderate engagement
        "proportion": 0.500,
        "payment_modes": {"Cash": 0.9, "Gcash": 0.5, "Maya": 0.05, "Bank Transfer": 0.1},
        "frequency_weights": [0.05, 0.30, 0.35, 0.30],
        "org_prob": 0.35,
    },
    "Price Sensitive": {
        "social": 3.5,      # moderate-high
        "security": 3.5,    # moderate
        "price": 2.3,       # find prices unfair
        "info": 3.3,        # moderate info quality
        "involvement": 3.4, # moderate
        "proportion": 0.166,
        "payment_modes": {"Cash": 0.85, "Gcash": 0.65, "Maya": 0.1, "Bank Transfer": 0.15},
        "frequency_weights": [0.10, 0.35, 0.35, 0.20],
        "org_prob": 0.45,
    },
    "Disengaged": {
        "social": 2.5,      # low social influence
        "security": 3.0,    # neutral
        "price": 3.0,       # neutral
        "info": 2.5,        # low info engagement
        "involvement": 1.8, # very low
        "proportion": 0.000,
        "payment_modes": {"Cash": 0.95, "Gcash": 0.3, "Maya": 0.02, "Bank Transfer": 0.05},
        "frequency_weights": [0.02, 0.15, 0.28, 0.55],
        "org_prob": 0.20,
    },
}


def clamp_likert(val):
    """Clamp to 1-5 integer range."""
    return max(1, min(5, round(val)))


def generate_likert(persona_profile, std_dev=0.9):
    """Generate 50 Likert responses for a persona."""
    responses = []
    for dim, is_reverse in ITEM_MAP:
        mean = persona_profile[dim]
        if is_reverse:
            mean = 6.0 - mean  # reverse: high dim score -> low Likert
        score = clamp_likert(random.gauss(mean, std_dev))
        responses.append(LIKERT[score - 1])
    return responses


def generate_payment_modes(persona_probs):
    """Generate semi-colon separated payment modes."""
    modes = []
    for mode in PAYMENT_MODES:
        if random.random() < persona_probs[mode]:
            modes.append(mode)
    if not modes:
        modes = ["Cash"]  # everyone has at least cash
    return ";".join(modes)


def generate_org_uses():
    """Generate random subset of org payment uses."""
    n = random.randint(1, len(ORG_USES))
    return ";".join(random.sample(ORG_USES, n))


def generate_email(index):
    """Anonymized UP email — prefix stripped, domain only."""
    return "@up.edu.ph"


def generate_timestamp(base_date, index):
    """Generate a plausible timestamp spread over collection period."""
    offset = timedelta(
        days=random.randint(0, 14),
        hours=random.randint(6, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    ts = base_date + offset
    return ts.strftime("%Y/%m/%d %-I:%M:%S %p AST")


def main():
    base_date = datetime(2026, 3, 10)  # survey collection start
    rows = []

    for persona_name, profile in PERSONAS.items():
        n = round(N_TOTAL * profile["proportion"])
        for i in range(n):
            year = random.choices(YEAR_LEVELS, weights=YEAR_WEIGHTS, k=1)[0]
            frequency = random.choices(
                FREQUENCY_OPTIONS, weights=profile["frequency_weights"], k=1
            )[0]
            payment = generate_payment_modes(profile["payment_modes"])

            in_org = random.random() < profile["org_prob"]
            org_name = random.choice(ORGS) if in_org else ""
            org_uses = generate_org_uses() if in_org else ""

            likert = generate_likert(profile)

            row = [
                "",  # timestamp placeholder
                generate_email(len(rows)),
                CONSENT_TEXT,
                year,
                COLLEGE,
                PROGRAM,
                payment,
                frequency,
                "Yes" if in_org else "No",
                org_name,
                org_uses,
            ] + likert

            rows.append(row)

    # Shuffle so personas aren't grouped
    random.shuffle(rows)

    # Assign timestamps in order
    for i, row in enumerate(rows):
        row[0] = generate_timestamp(base_date, i)

    # Sort by timestamp
    rows.sort(key=lambda r: r[0])

    # ── Write CSV matching original format ──
    # Read header from real CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(script_dir, "survey_responses_raw.csv")

    with open(raw_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    out_path = os.path.join(script_dir, "survey_responses.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    # ── Print summary ──
    print(f"Generated {len(rows)} synthetic responses → {out_path}")
    print(f"\nPersona breakdown:")
    persona_names = list(PERSONAS.keys())
    counts = {p: round(N_TOTAL * PERSONAS[p]["proportion"]) for p in persona_names}
    for p, c in counts.items():
        print(f"  {p}: {c}")

    # Count demographics
    orgs_count = sum(1 for r in rows if r[8] == "Yes")
    print(f"\nOrg members: {orgs_count}/{len(rows)}")
    for yr in YEAR_LEVELS:
        c = sum(1 for r in rows if r[3] == yr)
        print(f"  {yr}: {c}")


if __name__ == "__main__":
    main()
