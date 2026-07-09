# Data Schema

## Objective

Define the minimum source-of-truth schema needed for V0.1 modeling and MVP implementation.

This document describes the canonical logical structure first. Concrete JSON or YAML files can follow this spec.

## Modeling Principle

V0.1 should separate three layers:

1. Stable schema definitions
2. Symbolic registry definitions
3. Instance-level observations and scoring results

## Core Entities

### 1. Feature Schema

Defines the numeric dimensions used across prototype matching.

Recommended V0.1 dimensions:

1. `agency`
2. `visibility`
3. `resource_mobilization`
4. `stability`
5. `risk_exposure`
6. `momentum`
7. `constraint_pressure`
8. `coordination`
9. `timing_maturity`
10. `governance_capacity`

Example logical shape:

```yaml
feature_schema:
  version: "0.1"
  scale: "0_to_1"
  dimensions:
    - key: agency
      label: Agency
      description: Degree of active initiation
    - key: visibility
      label: Visibility
      description: Degree of externalized or observable form
```

### 2. Hexagram Family Registry

Defines the `64` top-level families.

Required fields:

- `id`
- `index`
- `name_cn`
- `name_en`
- `slug`
- `core_pattern`
- `semantic_anchor`
- `status`
- `sources`

Example:

```yaml
hexagram_family:
  id: hex_01_qian
  index: 1
  name_cn: 乾
  name_en: Qian
  slug: qian
  core_pattern: "Initiating force with strong upward drive"
  semantic_anchor: "active emergence, leadership, force, initiation"
  status: draft
  sources:
    - type: classical
      ref: "周易"
```

### 3. Line-State Prototype

Defines each prototype node under a family.

Required fields:

- `id`
- `family_id`
- `line_index`
- `state_name`
- `short_definition`
- `feature_vector`
- `semantic_anchor`
- `transition_hints`
- `example_positive`
- `example_negative`
- `status`

Example:

```yaml
line_state_prototype:
  id: proto_hex_01_line_1
  family_id: hex_01_qian
  line_index: 1
  state_name: "initial emergence"
  short_definition: "Energy is present but still early and fragile"
  feature_vector:
    agency: 0.72
    visibility: 0.20
    resource_mobilization: 0.35
    stability: 0.28
    risk_exposure: 0.44
    momentum: 0.60
    constraint_pressure: 0.52
    coordination: 0.31
    timing_maturity: 0.22
    governance_capacity: 0.18
  semantic_anchor: "early force, hidden activation, not yet fully formed"
  transition_hints:
    - "may rise with support"
    - "may fail if overexposed too early"
  example_positive: []
  example_negative: []
  status: draft
```

### 4. Transition Rule

Defines movement inside or across families.

Required fields:

- `id`
- `from_prototype_id`
- `to_prototype_id`
- `transition_type`
- `conditions`
- `confidence`
- `notes`

Transition types:

- `intra_family_adjacent`
- `intra_family_skip`
- `cross_family_single_line_change`
- `scenario_projection`

### 5. Observation Record

Stores a user-provided or system-captured state observation.

Required fields:

- `id`
- `subject_id`
- `subject_type`
- `mode`
- `timestamp`
- `inputs`
- `consent_state`
- `risk_flags`

Subject types:

- `self`
- `pair`
- `non_human_object`

Modes:

- `questionnaire`
- `free_text`
- `hybrid`

### 6. Score Result

Stores the computed state output for one observation.

Required fields:

- `observation_id`
- `edge_vector`
- `top_families`
- `top_prototypes`
- `uncertainty`
- `explanation_basis`
- `generated_at`

Example:

```yaml
score_result:
  observation_id: obs_001
  edge_vector:
    basis: hexagram_family
    values:
      hex_01_qian: 0.18
      hex_02_kun: 0.06
  top_families:
    - family_id: hex_01_qian
      score: 0.18
  top_prototypes:
    - prototype_id: proto_hex_01_line_1
      score: 0.71
  uncertainty:
    overall: 0.34
    missing_dimensions:
      - timing_maturity
      - governance_capacity
  explanation_basis:
    deterministic_weight: 0.65
    semantic_similarity_weight: 0.35
  generated_at: "2026-07-06T00:00:00Z"
```

### 7. Probe Recommendation

Stores a low-risk next-step information-gathering or action prompt.

Required fields:

- `id`
- `observation_id`
- `probe_type`
- `goal`
- `prompt`
- `risk_level`
- `expected_information_gain`

Probe types:

- `question`
- `reflection`
- `behavioral_test`
- `scenario_check`

## Separation Of Concerns

### Stable Definitions

Should live in versioned source files:

- `feature_schema`
- `hexagram_family_registry`
- `prototype_registry`
- `transition_rules`

### User Or Session Data

Should live in runtime storage:

- `observation_record`
- `score_result`
- `probe_recommendation`

## V0.1 Required Files

Recommended first file set:

```text
docs/02-domain-model/
  data-schema.md
  feature-schema.v0.1.yaml
  hexagram-families.v0.1.yaml
  line-prototypes.v0.1.yaml
  transition-rules.v0.1.yaml
```

## Open Design Decisions

- Should `edge_vector` be normalized across all `64` families at all times?
- Should prototype scoring be mandatory for every result, or optional when only family-level confidence is available?
- How should uncertainty be represented: scalar only, per-dimension, or posterior distribution?
- Which fields are mandatory for deterministic scoring in the first implementation?
