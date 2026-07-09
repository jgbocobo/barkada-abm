# ODD+D Protocol: Agent-Based Simulation of Digital Payment Adoption Among UPLB Students

> Following the ODD+D framework (Grimm et al. 2020; Muller et al. 2013) for agent-based
> models with human decision-making.

---

## 1. Purpose and Patterns

### Purpose

This model simulates the diffusion of digital payment applications (GCash/Maya) among
approximately 1,000 UPLB student agents over a 15-week (105-day) semester. The model
serves two goals:

1. **Validation:** Demonstrate that agent-level adoption rules can reproduce the
   macro-level Bass diffusion S-curve when configured with equivalent parameters on a
   well-mixed network (model-to-model comparison).
2. **Experimentation:** Investigate how network topology, seeding strategy, advertising
   intensity, and trust thresholds affect adoption dynamics in a heterogeneous population
   connected by a multilayer campus network.

### Patterns

The model must reproduce the following empirical/theoretical patterns:

| Pattern | Source | Metric |
|---------|--------|--------|
| S-shaped cumulative adoption curve | Bass (1969) | Visual + curve fitting |
| Bell-shaped adoption rate curve | Bass (1969) | Peak timing comparison |
| Baseline RMSE < 5% of M | Validation criterion | RMSE < 50 agents |
| Faster diffusion in clustered networks | Rogers (2003) | Compare topologies |
| Opinion leaders accelerate early adoption | Valente (1996) | Compare seeding strategies |

---

## 2. Entities, State Variables, and Scales

### 2.1 Entities

| Entity | Count | Description |
|--------|-------|-------------|
| Student agent | 1,000 | BDI-driven adopter/non-adopter on a multiplex network |
| Ad agent | 1 | Global advertising broadcaster (external influence) |
| Campus event | 4 | Scheduled events that temporarily boost exposure probability |

### 2.2 Student Agent State Variables

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `state` | enum | {Unaware, Aware, Trial, Regular, Advocate} | Current adoption lifecycle stage |
| `persona` | int | 1-5 | Persona cluster ID from survey K-means |
| `security_belief` | float | 0.0-1.0 | Trust in payment app security |
| `social_susceptibility` | float | 0.0-1.0 | How strongly peers influence this agent |
| `price_fairness` | float | 0.0-1.0 | Perceived fairness of transaction fees |
| `message_quality` | float | 0.0-1.0 | Trust in advertising and app information |
| `involvement` | float | 0.0-1.0 | Personal engagement with fintech topics |
| `adoption_threshold` | float | 0.0-1.0 | Fraction of neighbors who must adopt before agent considers adopting |
| `days_in_state` | int | 0+ | Ticks spent in current state |
| `org_id` | int | 0-N | Student organization membership |
| `college_id` | int | 1-7 | Academic college affiliation |
| `influence_spread_count` | int | 0+ | Number of successful WOM conversions made by this agent |

### 2.3 Global Parameters

| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| Population size | M | 1,000 | Total number of student agents |
| Simulation length | T | 105 | Days (15 weeks) |
| Advertising probability | p_ad | 0.003/day | Probability an Unaware agent is exposed to advertising per tick |
| WOM transmission probability | p_wom | 0.08/day | Base probability of successful word-of-mouth influence per contact |
| Trial period | t_trial | 7 days | Minimum days in Trial before transitioning to Regular |
| Advocate threshold | n_advocate | 3 | Successful WOM conversions needed to become Advocate |
| Advocate credibility bonus | c_advocate | 1.5 | Multiplier on WOM influence strength for Advocates |
| Network overlap | p_overlap | 0.3 | Probability that an org/class edge also appears in the friendship layer |
| Belief threshold | b_threshold | 0.35 | Minimum weighted belief score to allow adoption |
| Risk threshold | r_threshold | 0.3 | Security belief below this blocks adoption |
| Social influence weight | social_weight ($w_s$) | 0.4 | Weight of social norm in the weighted belief score |
| Ad fatigue threshold | ad_fatigue_threshold | 10 | Ad exposures after which an agent becomes fatigued |
| Ad fatigue decay | fatigue_decay | 0.5 | Multiplier on message receptivity once fatigued |
| Disadoption probability | p_disadopt | 0.05/day | Daily probability a peer-unsupported Trial user reverts to Aware |
| Peer support minimum | peer_support_min | 0.25 | Adopter-neighbor fraction below which disadoption can fire |
| Best-friend count | nb_best_friends | 0 (0--5) | Barkada ties per student; 0 disables the layer |
| Best-friend tie weight | w_best | 0.95 | Influence weight of a barkada tie (used when layer is active) |

### 2.4 Scales

| Dimension | Value | Notes |
|-----------|-------|-------|
| Time | 105 ticks (1 tick = 1 day) | 15-week academic semester |
| Space | Non-spatial | Network-only topology; no geographic coordinates |
| Population | 1,000 agents | Represents UPLB student body sample |

---

## 3. Process Overview and Scheduling

Each tick (day) executes the following processes **in order**:

```
TICK t:
  1. CAMPUS EVENTS
     - Check if current day matches a scheduled event
     - If yes: temporarily boost p_ad by event_boost_factor for this tick

  2. ADVERTISING (external influence)
     - For each agent in state {Unaware, Aware}:
       - With probability p_ad * event_boost:
         - Increment agent.ad_exposure
         - If ad_exposure >= ad_fatigue_threshold: mark agent ad_fatigued
         - If agent is Unaware:
           - Let effective_mq = message_quality * (fatigue_decay if ad_fatigued else 1)
           - If random() < effective_mq: Transition Unaware -> Aware

  3. WORD-OF-MOUTH (internal influence)
     - For each agent in state {Trial, Regular, Advocate}:
       - For each neighbor across all active network layers
         (org, friend, class, and best-friend if nb_best_friends > 0):
         - If neighbor is in state {Unaware, Aware}:
           - tie_weight = max weight across layers connecting the pair
           - credibility = c_advocate if agent is Advocate, else 1.0
           - per_edge_prob = p_wom / avg_degree
           - influence = per_edge_prob * tie_weight * credibility
           - If random() < influence:
             - If neighbor is Unaware: Transition Unaware -> Aware
             - If neighbor is Aware: accumulate influence into social_pressure

  4. ADOPTION DECISION (BDI deliberation)
     - For each agent in state {Aware}:
       - Run BDI deliberation cycle (see Section 5)
       - If intention = adopt: Transition Aware -> Trial

  4b. DISADOPTION
     - For each agent in state {Trial}:
       - Compute peer_support = fraction of all-layer neighbors currently
         in state {Trial, Regular, Advocate}
       - Let barkada_support = (any best-friend neighbor is an adopter)
       - If NOT barkada_support AND peer_support < peer_support_min:
         - With probability p_disadopt:
           - Transition Trial -> Aware
           - Increment nb_disadopted counter

  4c. PROMOTIONS
     - For each agent in state {Trial}:
       - If days_in_state >= t_trial: Transition Trial -> Regular
     - For each agent in state {Regular}:
       - If influence_spread_count >= n_advocate: Transition Regular -> Advocate

  5. STATE UPDATE
     - Increment days_in_state for all agents
     - Reset social_pressure accumulators

  6. DATA COLLECTION
     - Record: day, cumulative_adopters (Trial+Regular+Advocate),
       adoption_rate, count per state, per-layer influence events
```

### Scheduling Notes

- Processes execute **synchronously**: all agents complete step N before any begin step N+1.
- State transitions within a tick take effect at the end of the tick (agents act on
  their state at the start of the tick).
- Social pressure is accumulated across all neighbors before the adoption decision is
  evaluated (not per-contact).

---

## 4. Design Concepts

### 4.1 Theoretical and Empirical Background

The model integrates three theoretical frameworks:

1. **Bass Diffusion Model** (Bass 1969): Macro-level innovation diffusion driven by
   external influence (advertising, coefficient p) and internal influence (word-of-mouth,
   coefficient q). Provides the baseline S-curve for validation.

2. **BDI Agent Architecture** (Bratman 1987; Rao & Georgeff 1995): Agents hold beliefs
   about payment app attributes, form desires based on social pressure and personal
   evaluation, and commit to intentions (adopt or wait). Implemented using GAMA's
   `simple_bdi` architecture.

3. **Multiplex Network Diffusion** (Kivela et al. 2014; Chandrasekhar et al. 2024):
   Adoption spreads through a 3-layer campus network where inter-layer correlation
   (overlapping membership) affects diffusion dynamics.

### 4.2 Emergence

The macro-level S-shaped adoption curve **emerges** from micro-level BDI decisions.
No agent knows the global adoption count; each only observes its direct neighbors.
Clustering of adoption in network communities and tipping-point dynamics are emergent
properties.

### 4.3 Adaptation

Agents do not learn or change their BDI parameters over time. However, their
`belief_social_norm` (fraction of adopting neighbors) updates each tick as neighbors
adopt, which changes their adoption decision. This represents indirect adaptation
through environmental change rather than internal learning.

### 4.4 Objectives

Each agent has one primary objective: **decide whether to adopt a digital payment app**.
This is modeled through the BDI desire hierarchy (see Section 5). Agents do not
optimize a utility function; they follow threshold-based rules.

### 4.5 Sensing

Agents can observe:
- The adoption state of their **direct neighbors** in all 3 network layers
- Whether advertising has reached them (probabilistic exposure)
- Campus event occurrence (global signal)

Agents **cannot** observe:
- Global adoption count
- Other agents' BDI parameters
- Network structure beyond their immediate neighbors

### 4.6 Interaction

Agents interact through:
- **Word-of-mouth (WOM):** Adopters probabilistically influence non-adopter neighbors.
  Influence strength depends on tie weight (layer) and adopter credibility (state).
- **Social pressure accumulation:** An agent's adoption decision considers the
  aggregate pressure from ALL adopting neighbors, not just individual contacts.

### 4.7 Stochasticity

| Process | Stochastic element |
|---------|--------------------|
| Network generation | Random graph algorithms (Watts-Strogatz, Erdos-Renyi) |
| Network overlap | Bernoulli trials with probability p_overlap |
| Advertising exposure | Bernoulli trial with probability p_ad per agent per tick |
| WOM contact | Bernoulli trial with probability p_wom per neighbor per tick |
| Initial persona assignment | Random assignment proportional to survey-derived cluster sizes |

### 4.8 Collectives

- **Student organizations:** Clusters of agents sharing an org_id, connected by strong
  ties in the Org network layer.
- **Academic colleges:** Groups of agents sharing a college_id, connected by weak ties
  in the Class network layer.
- Collectives are structural (determined at initialization) and do not form or dissolve
  during the simulation.

### 4.9 Observation

Data collected at each tick for analysis:

| Metric | Level | Purpose |
|--------|-------|---------|
| Cumulative adopters | Global | S-curve comparison with Bass ODE |
| Adoption rate | Global | Peak timing analysis |
| Count per state | Global | Lifecycle distribution over time |
| Per-layer influence events | Global | Which network layer drives adoption |
| Adopter degree centrality | Agent | Opinion leader analysis |
| Time to adoption | Agent | Adoption speed distribution |

---

## 5. Individual Decision-Making (+D)

This section describes the BDI deliberation cycle that determines whether an Aware
agent transitions to Trial (adopts).

### 5.1 Beliefs

Each agent maintains beliefs derived from its persona profile and updated by
environmental signals:

| Belief | Source | Update rule |
|--------|--------|-------------|
| `belief_security` | Persona profile (survey Security dimension) | Static; set at initialization |
| `belief_value` | Weighted combination: 0.5 * price_fairness + 0.5 * message_quality | Static; set at initialization |
| `belief_social_norm` | Fraction of direct neighbors in state {Trial, Regular, Advocate} | Updated each tick |

### 5.2 Desires

Desires are evaluated in priority order:

| Priority | Desire | Activation condition |
|----------|--------|---------------------|
| 1 (highest) | `desire_avoid_risk` | belief_security < r_threshold |
| 2 | `desire_adopt` | belief_social_norm >= adoption_threshold * social_susceptibility |

### 5.3 Intentions

The intention selection follows this logic:

```
IF desire_avoid_risk is active:
    intention = WAIT (do not adopt this tick)
ELSE IF desire_adopt is active:
    weighted_belief = w1 * belief_security + w2 * belief_value + w3 * belief_social_norm
    IF weighted_belief > b_threshold:
        intention = ADOPT (transition Aware -> Trial)
    ELSE:
        intention = WAIT
ELSE:
    intention = IGNORE (remain in current state)
```

Where `w1 = 0.3, w2 = 0.3, w3 = 0.4` are belief weights (configurable).

### 5.4 State Transition Diagram

```
                 advertising OR
                 WOM first contact
    [Unaware] ──────────────────────> [Aware] <┐
                                         │     │
                                         │ BDI │ disadoption
                                         │ pass│ (peer_support < 25%
                                         v     │  AND no barkada adopter,
                                      [Trial] ─┘  fires at p_disadopt/day)
                                         │
                                         │ days_in_state >= t_trial (7 days)
                                         v
                                      [Regular]
                                         │
                                         │ influence_spread_count >= n_advocate (3)
                                         v
                                      [Advocate]
```

Most transitions are forward-only, but **Trial → Aware is reversible**: a Trial
user whose adopter-neighbor ratio falls below `peer_support_min` and who has no
adopter in their best-friend (barkada) layer faces a `p_disadopt` daily
probability of disadopting. This mechanism is active in the Stage~B experiments
(full model) and disabled in Stage~A (Bass validation). The canonical
illustrations of this lifecycle are Figures~1 and 2 in the paper
(`ICS-template/cs190-ieee.tex` §III-C).

---

## 6. Initialization

### 6.1 Agent Initialization

1. Create 1,000 student agents.
2. Assign each agent a `persona` (1-5) using proportional random assignment based on
   survey-derived cluster sizes. If no survey data is available, use equal proportions
   (200 agents per persona).
3. Set BDI parameters from persona profile lookup table:

| Persona | security_belief | social_susceptibility | price_fairness | message_quality | involvement | adoption_threshold |
|---------|----------------|----------------------|----------------|-----------------|-------------|-------------------|
| 1 - Tech Enthusiast | 0.8 | 0.4 | 0.7 | 0.8 | 0.9 | 0.15 |
| 2 - Social Follower | 0.5 | 0.9 | 0.6 | 0.5 | 0.5 | 0.25 |
| 3 - Cautious Adopter | 0.3 | 0.5 | 0.7 | 0.4 | 0.4 | 0.45 |
| 4 - Price Sensitive | 0.6 | 0.6 | 0.3 | 0.6 | 0.6 | 0.35 |
| 5 - Disengaged | 0.5 | 0.3 | 0.5 | 0.3 | 0.2 | 0.55 |

> **Note:** These are placeholder values derived from synthetic data. They will be
> replaced with survey-derived cluster centroids when survey data is collected and
> analyzed via K-means clustering on the 5 Likert dimensions.

4. Assign `org_id` (random, ~20 orgs of ~50 members each).
5. Assign `college_id` (proportional to UPLB college enrollment).
6. Set all agents to state = Unaware, days_in_state = 0.

### 6.2 Network Initialization

Three network layers are generated sequentially:

**Layer 1 — Org Network (strong ties):**
- For each org: create a dense random subgraph among members (edge probability = 0.6).
- A small number of inter-org edges added (edge probability = 0.02).
- Tie weight: 0.8.
- Expected average degree: ~10.

**Layer 2 — Friend Network (medium ties, small-world):**
- Generate a Watts-Strogatz graph: k = 6 nearest neighbors, p_rewire = 0.1.
- **Overlap correlation:** For each edge in the Org layer, with probability `p_overlap`,
  also add it to the Friend layer (captures the "org mates become friends" phenomenon).
- Tie weight: 0.5.
- Expected average degree: ~6 (plus overlap edges).

**Layer 3 — Class Network (weak ties):**
- For agents sharing the same `college_id`: create edges with probability 0.05.
- For agents in different colleges: create edges with probability 0.005.
- Tie weight: 0.2.
- Expected average degree: ~15.

**Layer 4 — Best-friend Network (barkada, optional):**
- Active only when `nb_best_friends > 0` (default 0; values 1, 3, 5 are
  tested in Experiment 3b).
- Each connected student is assigned `nb_best_friends` random best friends
  drawn uniformly from other connected students.
- Tie weight: 0.95 (`w_best`).
- Best-friend ties contribute three effects: (a) stronger WOM influence via
  the higher tie weight, (b) a +0.2 bonus to `belief_social_norm` during BDI
  when any best friend has adopted, and (c) immunity to disadoption while
  any best friend is an adopter.

### 6.3 Campus Event Schedule

| Event | Day | Duration | p_ad boost factor |
|-------|-----|----------|------------------|
| Registration Week | 1-5 | 5 days | 2.0x |
| University Fair | 30-32 | 3 days | 3.0x |
| Midterm Week | 50-55 | 6 days | 1.5x |
| Finals Week | 95-100 | 6 days | 1.5x |

---

## 7. Input Data

| Data | Source | Status | Used for |
|------|--------|--------|----------|
| Bass ODE baseline | `analysis/bass_ode.py` output | Complete | Validation target S-curve |
| Survey responses | Google Forms (50-item Likert) | Pending (~50 responses) | K-means persona profiles |
| UPLB college enrollment | UPLB registrar data | Placeholder | college_id proportions |
| Org membership distribution | Estimated | Placeholder | org_id assignment |

---

## 8. Submodels

### 8.1 Advertising Submodel

Maps Bass coefficient of innovation (p) to per-agent daily exposure probability.

```
For each Unaware agent i at tick t:
    exposed = random() < p_ad * event_boost(t)
    if exposed:
        if agent.message_quality > random():
            agent.state = Aware
```

The `message_quality` filter ensures that not all exposures lead to awareness — agents
with low trust in advertising are harder to reach.

### 8.2 Word-of-Mouth Submodel

Maps Bass coefficient of imitation (q) to network-mediated peer influence.

```
For each adopter agent j (state in {Trial, Regular, Advocate}):
    credibility = c_advocate if j.state == Advocate else 1.0
    for each neighbor i of j across all 3 layers:
        if i.state in {Unaware, Aware}:
            tie_weight = max(weights across all layers connecting i and j)
            influence = tie_weight * p_wom * credibility
            if random() < influence:
                if i.state == Unaware:
                    i.state = Aware  # First contact
                else:
                    i.social_pressure += influence  # Accumulate for BDI
```

### 8.3 Influence Aggregation Submodel

For agents appearing in multiple network layers, the **maximum** tie weight is used
(not the sum). This reflects that your org mate who is also your friend influences
you at the strength of the stronger relationship, not double.

```
w_effective(i, j) = max(w_org(i,j), w_friend(i,j), w_class(i,j))
```

Where `w_layer(i,j) = 0` if no edge exists between i and j in that layer.

### 8.4 BDI Deliberation Submodel

See Section 5 for the full decision-making specification.

### 8.5 Disadoption Submodel

Models the abandonment of platforms that lack peer support during the Trial
period. Active only in Stage~B (the full model); disabled for Stage~A
Bass validation.

```
For each Trial agent i at tick t:
    neighbors = union of all-layer neighbors of i (deduplicated)
    adopters  = neighbors in state {Trial, Regular, Advocate}
    peer_support = |adopters| / |neighbors|   (0 if |neighbors| = 0)

    barkada_support = (any best-friend neighbor of i is an adopter)

    if (not barkada_support) and (peer_support < peer_support_min):
        if random() < p_disadopt:
            i.state = Aware
            i.days_in_state = 0
            nb_disadopted += 1
```

`p_disadopt` defaults to 0.05 (5% daily) and `peer_support_min` defaults to
0.25 (25%). Experiment 3b (best-friend / barkada) shows that giving each
student even one best-friend connection reduces cumulative disadoptions by
45.6%; five best friends reduces them by 92.8%.

### 8.6 Ad Fatigue Submodel

After repeated advertising exposures, an agent's receptivity to further ads
decays. Active only in Stage~B.

```
For each Unaware/Aware agent i exposed to an ad at tick t:
    i.ad_exposure += 1
    if i.ad_exposure >= ad_fatigue_threshold:
        i.ad_fatigued = true

When processing the ad's effect on an Unaware agent:
    effective_mq = i.message_quality
    if i.ad_fatigued:
        effective_mq *= fatigue_decay
    if random() < effective_mq:
        i.state = Aware
```

`ad_fatigue_threshold` defaults to 10 exposures and `fatigue_decay` defaults
to 0.5 (50% receptivity retained once fatigued).

---

## References

- Bass, F.M. (1969). A new product growth for model consumer durables. *Management Science*, 15(5), 215-227.
- Bratman, M.E. (1987). *Intention, Plans, and Practical Reason*. Harvard University Press.
- Chandrasekhar, A., Chaudhary, S., Golub, B., & Jackson, M.O. (2024). Multiplexing in networks and diffusion. *arXiv:2412.11957*.
- Grimm, V., et al. (2020). The ODD protocol for describing agent-based and other simulation models: A second update. *JASSS*, 23(2), 7.
- Kiesling, E., Gunther, M., Stummer, C., & Wakolbinger, L.M. (2012). Agent-based simulation of innovation diffusion. *CEJOR*, 20(2), 183-230.
- Kivela, M., et al. (2014). Multilayer networks. *Journal of Complex Networks*, 2(3), 203-271.
- Muller, B., et al. (2013). Describing human decisions in agent-based models - ODD+D. *Environmental Modelling & Software*, 48, 37-48.
- Rao, A.S. & Georgeff, M.P. (1995). BDI agents: From theory to practice. *ICMAS*, 95, 312-319.
- Rogers, E.M. (2003). *Diffusion of Innovations* (5th ed.). Free Press.
- Valente, T.W. (1996). Social network thresholds in the diffusion of innovations. *Social Networks*, 18(1), 69-89.
