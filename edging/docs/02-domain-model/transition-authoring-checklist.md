# Transition Authoring Checklist

## Objective

Define the minimum checklist for authoring transition seeds between line-state prototypes.

## Transition Types In V0.1

Required:

- `intra_family_adjacent`

Optional early seed:

- `cross_family_single_line_change`
- `scenario_projection`

## Minimum Requirement Per Family

Each family must have `5` adjacent transitions:

1. line `1 -> 2`
2. line `2 -> 3`
3. line `3 -> 4`
4. line `4 -> 5`
5. line `5 -> 6`

This creates the minimum full-library target:

```text
64 families x 5 transitions = 320 adjacent transition seeds
```

## Required Fields Per Transition

Each transition must include:

- `id`
- `from_prototype_id`
- `to_prototype_id`
- `transition_type`
- `conditions`
- `confidence`
- `notes`

## Condition Checklist

Each transition should describe:

- what tends to increase
- what tends to decrease
- what must stabilize
- what may break the transition

Conditions should be written in feature-language where possible.

## Adjacent Transition Design Rules

Good adjacent transitions:

- reflect line order progression
- are consistent with feature vectors
- explain how one state becomes the next
- include risk of failure or distortion

Avoid:

- purely narrative transitions with no scoring consequence
- transitions that contradict the family's core pattern
- transitions that require data the MVP does not collect

## Cross-Family Transition Seed Rules

Early cross-family links should be used sparingly.

Only add them when:

- a family boundary shift is conceptually strong
- the shift matters for explanation or projection
- the transition can be stated without ambiguity inflation

## Definition Of Done For One Family's Transition Layer

One family's transition layer is ready when:

- all `5` adjacent links exist
- each link names at least `2` to `3` concrete conditions
- notes explain the logic in plain language
- no transition conflicts with the family's prototype ordering
