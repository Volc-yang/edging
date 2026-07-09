# Deterministic Scorer

## Objective

Define the first inspectable scoring layer for V0.1 so the project can produce repeatable results before adding more adaptive reasoning.

## Role In The System

The deterministic scorer is the baseline computational engine.

It should:

- consume structured observation inputs
- compare them to prototype definitions
- produce prototype and family scores
- expose uncertainty signals
- support explanation generation

It should not:

- generate final prose on its own
- make high-stakes judgments
- hide scoring logic behind opaque heuristics

## Inputs

### Required Inputs

- `subject_type`
- `mode`
- `timestamp`
- `feature_vector`

### Optional Inputs

- `free_text`
- `context_tags`
- `relation_context`
- `previous_score_result`

## Input Contract

Minimal structured input shape:

```yaml
observation_input:
  subject_type: self
  mode: hybrid
  timestamp: "2026-07-06T00:00:00Z"
  feature_vector:
    agency: 0.74
    visibility: 0.46
    resource_mobilization: 0.41
    stability: 0.39
    risk_exposure: 0.44
    momentum: 0.63
    constraint_pressure: 0.48
    coordination: 0.40
    timing_maturity: 0.36
    governance_capacity: 0.29
  free_text: "I feel like things are moving, but not fully settled."
  context_tags:
    - early_stage
    - work_transition
```

## Scoring Stages

The deterministic scorer should run in five stages:

1. input validation
2. prototype feature matching
3. rule adjustment
4. family aggregation
5. uncertainty estimation

## Stage 1: Input Validation

Checks:

- required dimensions exist
- each feature value is within `0..1`
- unsupported subject types are rejected
- blocked safety modes are rejected before scoring

Validation outcomes:

- `valid`
- `partially_valid`
- `rejected`

## Stage 2: Prototype Feature Matching

Each prototype receives a feature-match score based on distance from the input feature vector.

Recommended V0.1 method:

- weighted absolute distance
- converted into similarity

Example shape:

```text
distance(i) = sum over m of w_m * abs(x_m - p_i,m)
feature_match(i) = max(0, 1 - distance(i))
```

Where:

- `x_m` is the subject value on dimension `m`
- `p_i,m` is prototype `i`'s value on dimension `m`
- `w_m` is dimension weight

V0.1 recommendation:

- default all `w_m = 0.10`
- allow future question-dependent weight overrides

## Stage 3: Rule Adjustment

The scorer may adjust prototype scores with explicit rule-based modifiers.

Purpose:

- encode domain constraints
- reduce implausible matches
- preserve interpretive consistency

Examples:

- reduce advanced leadership-like prototypes if `timing_maturity` is very low
- reduce stable carrying prototypes if `stability` and `governance_capacity` are both very low

Recommended rule output:

```text
adjusted_score(i) = clip(feature_match(i) + adjustment(i), 0, 1)
```

V0.1 constraints:

- adjustments must be small
- adjustments must be documented
- adjustments must never silently replace the base score

## Stage 4: Family Aggregation

Prototype scores should be aggregated into family-level scores.

Recommended V0.1 family score shape:

```text
family_score(f)
= 0.60 * max_prototype_score(f)
+ 0.25 * mean_prototype_score(f)
+ 0.15 * local_coherence(f)
```

Where:

- `max_prototype_score(f)` is the strongest prototype score in family `f`
- `mean_prototype_score(f)` is the average prototype score in family `f`
- `local_coherence(f)` rewards adjacent strong line-state support

### Local Coherence

Recommended approximation:

- compute the best adjacent-pair average inside a family
- use that as coherence signal

Reason:

- avoids isolated spikes
- rewards stage continuity

### Family Normalization

After aggregation, convert family scores into a normalized distribution.

Recommended V0.1 behavior:

- divide each family score by the total positive family score sum
- if total is zero, return low-confidence empty-state fallback

## Stage 5: Uncertainty Estimation

The scorer should explicitly estimate uncertainty.

Recommended V0.1 signals:

- `overall_uncertainty`
- `missing_dimensions`
- `top_family_gap`
- `top_prototype_gap`

### Suggested Heuristics

Increase uncertainty when:

- required dimensions are missing
- top two family scores are very close
- top prototypes point to conflicting stages
- many prototypes have similar low-to-mid scores with no clear center

Decrease uncertainty when:

- one family clearly dominates
- adjacent prototypes reinforce each other
- inputs are complete and internally consistent

## Output Contract

The scorer should return:

```yaml
score_result:
  validation_status: valid
  top_families:
    - family_id: hex_01_qian
      score: 0.31
  top_prototypes:
    - prototype_id: proto_hex_01_line_2
      score: 0.76
  family_distribution: {}
  prototype_distribution: {}
  uncertainty:
    overall: 0.28
    top_family_gap: 0.11
    top_prototype_gap: 0.09
    missing_dimensions: []
  explanation_basis:
    scoring_version: "0.1"
    dimension_weights: default_equal
    rule_adjustments_applied: []
```

## Fallback Behaviors

### Low Information

If too many dimensions are missing:

- do not force a strong state conclusion
- return a low-confidence result
- recommend one or two clarifying probes

### Ambiguous Match

If the top families are too close:

- return multiple candidate families
- surface the ambiguity explicitly
- recommend a probe targeted at separating them

### Rejected Input

If the request violates MVP boundaries:

- do not score
- return policy rejection metadata

## Probe Selection Hook

The deterministic scorer should expose which dimensions are most uncertain or most discriminative.

This enables the next layer to ask questions such as:

- "Is this situation already visible to others, or mostly still internal?"
- "Is the main issue lack of timing, or lack of carrying capacity?"

## Versioning

The scorer spec must version:

- feature schema version
- prototype registry version
- rule set version
- aggregation formula version

## V0.1 Non-Goals

- learned end-to-end model training
- dynamic graph reasoning
- probabilistic transition learning
- direct free-text-only scoring without structured features

## Immediate Next Steps

1. define initial dimension weights
2. define first adjustment rules for `乾` and `坤`
3. define top-gap thresholds for uncertainty bands
4. create `10` manual example inputs and expected scoring behavior
