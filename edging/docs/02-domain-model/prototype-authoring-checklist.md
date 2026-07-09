# Prototype Authoring Checklist

## Objective

Define the minimum checklist for authoring one complete family's `6` line-state prototypes in a way that remains scorer-ready.

## One Family = One Atomic Work Unit

A family should be treated as complete only when all of the following are finished:

1. family registry entry exists
2. all `6` prototypes exist
3. all `6` feature vectors are valid
4. all adjacent transitions are present
5. family can be scored by the deterministic pipeline

## Required Fields Per Prototype

Each prototype must include:

- `id`
- `family_id`
- `line_index`
- `state_name`
- `short_definition`
- `feature_vector`
- `semantic_anchor`
- `transition_hints`
- `status`

## Feature Vector Checklist

Every prototype must define all `10` dimensions:

- `agency`
- `visibility`
- `resource_mobilization`
- `stability`
- `risk_exposure`
- `momentum`
- `constraint_pressure`
- `coordination`
- `timing_maturity`
- `governance_capacity`

Validation rules:

- every value must be between `0` and `1`
- no dimension may be omitted
- values should create meaningful stage progression across lines

## Stage Progression Checklist

Across a family's six lines, authoring should preserve stage logic rather than six disconnected labels.

Check for:

- line order feels sequential
- neighboring lines are more related than distant lines
- line `5` is not automatically the strongest on every dimension
- line `6` captures excess, inversion, strain, or terminal condition when appropriate

## Semantic Anchor Checklist

Each anchor should:

- be short enough for embedding and explanation use
- describe pattern rather than narrate a full story
- distinguish the line from neighboring lines
- align with the feature vector

## Short Definition Checklist

Each short definition should:

- be one sentence
- describe the state's structural condition
- avoid mystical certainty
- be interpretable without external commentary

## Family Consistency Checklist

Before marking one family as `draft-complete`, verify:

- the six line names sound like a coherent sequence
- the feature vectors show believable transitions
- the semantic anchors are not redundant
- at least one likely uncertainty contrast exists against a neighboring family

## Priority Family Queue

Recommended first `8` end-to-end families:

1. `hex_01_qian`
2. `hex_02_kun`
3. `hex_03_zhun`
4. `hex_04_meng`
5. `hex_05_xu`
6. `hex_06_song`
7. `hex_07_shi`
8. `hex_08_bi`

## Definition Of Done For One Family

One family is ready for scorer testing when:

- all six prototypes are present
- all feature vectors validate
- all five adjacent transitions exist
- scorer can produce top family and top prototype outputs for example inputs
