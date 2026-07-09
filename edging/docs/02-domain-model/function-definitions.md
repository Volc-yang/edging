# Function Definitions

## Objective

Define the canonical V0.1 computational functions behind the `64D` family representation and `384` line-state prototype system.

This document answers:

- what functions the system must implement
- what each function consumes
- what each function returns
- how the `64D` and `384` layers connect

## Scope

These are V0.1 engineering functions, not final learned-model equations.

They are designed to be:

- inspectable
- deterministic-first
- versionable
- compatible with later probabilistic or learned upgrades

## Canonical State Objects

### Subject Feature Vector

```text
x in [0,1]^10
```

Where `x` is the observed subject feature vector under the V0.1 feature schema.

### Prototype Feature Vector

```text
p_i in [0,1]^10
```

Where `p_i` is the feature vector of prototype `i`.

### Prototype Score Vector

```text
P(x) in R^384
```

Where each entry is the fit score for one line-state prototype.

### Family Score Vector

```text
E(x) in R^64
```

Where each entry is the aggregated activation of one hexagram family.

## Function Set Overview

V0.1 requires at least these functions:

1. `validate_input`
2. `feature_match`
3. `rule_adjustment`
4. `prototype_score`
5. `local_coherence`
6. `family_aggregation`
7. `family_normalization`
8. `uncertainty_estimation`
9. `probe_target_selection`

## 1. validate_input

### Purpose

Check whether an observation can enter the scorer.

### Input

- `observation_input`
- `feature_schema`
- `policy_mode`

### Output

```yaml
validation_result:
  status: valid | partially_valid | rejected
  missing_dimensions: []
  out_of_range_dimensions: []
  policy_flags: []
```

### Rules

- required dimensions must exist unless partial scoring is explicitly allowed
- all feature values must be between `0` and `1`
- blocked product modes must reject before scoring

## 2. feature_match

### Purpose

Compute similarity between the subject feature vector and a single prototype feature vector.

### Input

- subject vector `x`
- prototype vector `p_i`
- dimension weights `w`

### Definition

```text
d_i = sum_m (w_m * |x_m - p_i,m|)
f_i = max(0, 1 - d_i)
```

Where:

- `d_i` is weighted distance
- `f_i` is feature match score

### Output

```text
f_i in [0,1]
```

### V0.1 Default

- equal weights across all 10 dimensions
- weights sum to `1.0`

## 3. rule_adjustment

### Purpose

Apply small interpretable score modifiers based on explicit domain rules.

### Input

- prototype id `i`
- base feature score `f_i`
- subject vector `x`
- optional context tags

### Definition

```text
r_i = sum_k adjustment_k(i, x, context)
```

Each rule returns a bounded value, for example:

```text
adjustment_k in [-0.10, +0.10]
```

### Output

```text
r_i
```

### V0.1 Constraints

- no hidden rules
- no large score overrides
- every rule must be documented and versioned

## 4. prototype_score

### Purpose

Produce the final deterministic score for a prototype.

### Input

- feature match `f_i`
- rule adjustment `r_i`

### Definition

```text
s_i = clip(f_i + r_i, 0, 1)
```

### Output

```text
s_i in [0,1]
```

### Full Vector Form

```text
P(x) = [s_1, s_2, ..., s_384]
```

## 5. local_coherence

### Purpose

Reward adjacent line-state support within the same family so family-level results are not driven by isolated spikes.

### Input

- family `h`
- prototype scores for the 6 line states in that family

Let:

```text
S_h = [s_h,1, s_h,2, ..., s_h,6]
```

### Definition

Recommended V0.1:

```text
c_h = max_j ((s_h,j + s_h,j+1) / 2)
```

For `j = 1..5`.

### Output

```text
c_h in [0,1]
```

## 6. family_aggregation

### Purpose

Aggregate prototype evidence from 6 line states into one family activation score.

### Input

- the 6 prototype scores for family `h`
- coherence score `c_h`

### Definition

Let:

```text
m_h = max_j s_h,j
a_h = mean_j s_h,j
```

Then:

```text
g_h = 0.60 * m_h + 0.25 * a_h + 0.15 * c_h
```

### Output

```text
g_h in [0,1]
```

### Full Vector Form

```text
G(x) = [g_1, g_2, ..., g_64]
```

## 7. family_normalization

### Purpose

Convert raw family activations into the canonical `64D` edge vector.

### Input

- raw family scores `G(x)`

### Definition

If:

```text
Z = sum_h g_h
```

Then:

```text
e_h = g_h / Z
```

If `Z = 0`, return low-confidence fallback with empty dominance.

### Output

```text
E(x) = [e_1, e_2, ..., e_64]
```

With:

```text
sum_h e_h = 1
```

### Meaning

This is the canonical `64D` state representation for V0.1.

## 8. uncertainty_estimation

### Purpose

Estimate how much confidence the system should place in the result.

### Input

- validation result
- prototype score vector `P(x)`
- family score vector `E(x)`

### Suggested Signals

- `missing_dimensions_count`
- `top_family_gap`
- `top_prototype_gap`
- `family_entropy_proxy`
- `prototype_conflict_flag`

### Definitions

#### Top Family Gap

If the top two normalized family scores are `e_(1)` and `e_(2)`:

```text
gap_family = e_(1) - e_(2)
```

#### Top Prototype Gap

If the top two prototype scores are `s_(1)` and `s_(2)`:

```text
gap_proto = s_(1) - s_(2)
```

#### Family Entropy Proxy

V0.1 approximation:

```text
h_proxy = 1 - max_h e_h
```

### Output

```yaml
uncertainty:
  overall: 0.0_to_1.0
  top_family_gap: number
  top_prototype_gap: number
  missing_dimensions: []
  prototype_conflict_flag: true_or_false
```

### V0.1 Guidance

- higher `gap_family` lowers uncertainty
- higher `gap_proto` lowers uncertainty
- more missing dimensions increases uncertainty
- stage conflicts inside top families increase uncertainty

## 9. probe_target_selection

### Purpose

Choose which unknown or weakly separated dimension to probe next.

### Input

- uncertainty object
- top competing families
- top competing prototypes
- feature completeness status

### Suggested Logic

Prioritize:

1. missing dimensions
2. dimensions that best separate top competing families
3. dimensions that best separate top competing prototypes

### Output

```yaml
probe_target:
  dimension: timing_maturity
  reason: "top candidates differ mainly on timing and governance"
```

## End-To-End Contract

The canonical V0.1 deterministic pipeline is:

```text
observation_input
 -> validate_input
 -> feature_match for each prototype
 -> rule_adjustment for each prototype
 -> prototype_score vector P(x)
 -> family_aggregation for each family
 -> family_normalization to E(x)
 -> uncertainty_estimation
 -> probe_target_selection
```

## Definition Of Done For Function Layer

The function layer is complete when:

- every prototype has a valid `10D` feature vector
- every family can aggregate from exactly 6 line states
- the scorer can return `P(x)` and `E(x)` for one valid input
- uncertainty is returned as structured data
- all formulas are versioned and documented

## Open Upgrade Path

Future versions may add:

- semantic similarity terms
- question-conditioned weights
- learned priors
- transition probability functions
- full posterior state estimation

But V0.1 should keep the deterministic definitions above as the audit-friendly baseline.
