# Goal: 64D / 384 Prototype Seed Completion

## Goal Statement

Complete the project's `64D` family representation and `384` line-state prototype seed system as a stable V0.1 engineering foundation.

This goal means the project moves from:

- theory fragments
- partial examples
- local seed data

to:

- complete function definitions
- complete `64 x 6 = 384` prototype coverage
- consistent schema
- versioned seed artifacts

## Assumed Interpretation

This document interprets the requested goal as:

- `64D`: the canonical family-level edge vector
- `384爻`: the full line-state prototype library
- `seed`: the first complete hand-authored prototype dataset

## Definition Of Done

The goal is complete when all of the following are true.

### 1. Function Layer Complete

Required:

- canonical formulas for prototype scoring exist
- canonical formulas for family aggregation exist
- canonical formulas for uncertainty estimation exist
- function definitions are documented and versioned

Current state:

- defined and versioned in `docs/02-domain-model/function-definitions.md`

### 2. Schema Layer Complete

Required:

- feature schema is frozen for V0.1
- family registry schema is frozen
- prototype registry schema is frozen
- transition rule schema is frozen

Current state:

- frozen for V0.1 in versioned YAML seed files

### 3. Family Coverage Complete

Required:

- all `64` hexagram families exist in registry form
- each family has name, id, semantic anchor, core pattern

Completion formula:

```text
family_coverage = completed_families / 64
```

### 4. Prototype Coverage Complete

Required:

- every family has exactly `6` line-state prototypes
- every prototype has:
  - id
  - family_id
  - line_index
  - state_name
  - short_definition
  - feature_vector
  - semantic_anchor
  - transition_hints
  - status

Completion formula:

```text
prototype_coverage = completed_prototypes / 384
```

### 5. Transition Seed Complete

Required:

- adjacent intra-family transitions exist for every family
- minimal cross-family transition seed exists for top-priority families

Minimum adjacent transition count:

```text
64 families x 5 adjacent links = 320 intra-family links
```

### 6. Scorer Readiness Complete

Required:

- deterministic scorer can load schema
- deterministic scorer can score one observation
- scorer can return family scores, prototype scores, and uncertainty

## Completion Stages

### Stage A: Canonicalization

Deliverables:

- glossary
- schema
- function definitions
- scorer spec

### Stage B: Family Registry Completion

Deliverables:

- all `64` family entries

### Stage C: Prototype Seed Completion

Deliverables:

- all `384` prototype entries

Recommended work unit:

- finish one family at a time
- each family is only done when all 6 line states are complete

### Stage D: Transition Seed Completion

Deliverables:

- `320` adjacent intra-family links
- first wave of cross-family links

### Stage E: Scorer Validation

Deliverables:

- manual example set
- scoring sanity checks
- ambiguity and uncertainty cases

## Family Work Unit Template

Each family should be completed as one atomic unit:

1. family semantic anchor
2. family core pattern
3. line 1 prototype
4. line 2 prototype
5. line 3 prototype
6. line 4 prototype
7. line 5 prototype
8. line 6 prototype
9. adjacent transition links
10. basic example notes

## Recommended Progress Tracker

Use these metrics:

- `family_registry_progress`
- `prototype_progress`
- `transition_progress`
- `scorer_readiness`

Suggested status values:

- `not_started`
- `draft`
- `reviewing`
- `done`

## Current Progress Snapshot

Verified on `2026-07-15`:

- feature schema: versioned and loaded by scorer
- family registry: seeded for `64 / 64`
- prototype registry: seeded for `384 / 384`
- transition rules: seeded for `320 / 320` adjacent intra-family links
- deterministic scorer: implemented in `bin/deterministic_scorer.rb`
- sample observation: added in `examples/sample-observation.v0.1.yaml`
- spacetime abstraction registry: confirmed for `384 / 384` line states
- six-scale abstraction anchors: confirmed for `2304 / 2304` anchors
- classical source correspondence: verified for `384 / 384` line states
- eight-palace wandering-soul associations: verified for `64 / 64` hexagrams
- eight-palace returning-soul associations: verified for `64 / 64` hexagrams
- wandering-to-returning-soul composite changes: verified for `8 / 8` palaces
- draft review queue: empty (`0` records)
- structural completion gate: `ruby bin/validate_spacetime_abstractions.rb --complete` passes

## Priority Order

Recommended order:

1. add first-wave documented rule adjustments
2. add `10` manual validation cases with expected scorer behavior
3. add minimal cross-family transition seeds
4. calibrate uncertainty thresholds with examples
5. prepare API-facing runtime wrapper

## Suggested Delivery Strategy

### Strategy 1: Breadth First

Complete all 64 family headers first, then fill prototypes.

Pros:

- full map early
- easier planning

Cons:

- many incomplete families remain for longer

### Strategy 2: Depth First

Complete one family at a time with all 6 lines and transitions.

Pros:

- every completed family becomes immediately usable
- easier scoring tests

Cons:

- global coverage appears slower at first

### Recommendation

Use hybrid sequencing:

- breadth-first for family registry
- depth-first for prototype completion

## Immediate Next Deliverables

1. validate scorer behavior on `10` representative observations
2. define the first explicit rule-adjustment set for high-priority families
3. add minimal cross-family transition seeds for ambiguity resolution
4. expose scorer output through a stable runtime interface
5. tighten uncertainty heuristics from sample runs

## Blocking Risks

- inconsistent naming across later families
- drifting interpretation of feature dimensions
- overuse of prose without stable scoring consequences
- transition rules becoming too subjective before scoring tests

## Bottom Line

The target is not just "have ideas for 64D and 384 lines".

The target is to have:

- complete and versioned seed data
- complete function definitions
- complete coverage accounting
- a scorer-ready registry
- one runnable deterministic baseline against current YAML

That is the practical meaning of finishing the `64D / 384爻` goal.
