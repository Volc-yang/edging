# Edgefield Model

## Objective

Define what `Edgefield` is in computational terms so the project has a stable bridge from theory to product and implementation.

## Core Thesis

`Edgefield` is the system's primary world model.

The project should not treat the user as a static type. It should treat the subject as a changing state inside a field shaped by:

- internal tendencies
- relations
- environment
- time
- events
- uncertainty

In implementation terms, the system does not compute "what are you once and for all". It computes "what is the current state, what is uncertain, and what may change next".

## Modeling Unit

The basic modeling unit is a `subject at time t`.

A subject may be:

- a self-assessing person
- a consensual pair context
- a non-human object such as a role, brand, team pattern, or project

The model should avoid assuming that all subjects are humans.

## Canonical Representation

Recommended V0.1 representation:

```text
F_t = <S_t, R_t, E_t, M_t, U_t>
```

Where:

- `S_t`: state representation of the subject at time `t`
- `R_t`: relation context at time `t`
- `E_t`: environment and event context at time `t`
- `M_t`: memory or historical trace up to time `t`
- `U_t`: uncertainty representation at time `t`

Status:

- `Confirmed` as the working structural frame

## Component Definitions

### 1. State `S_t`

`S_t` is the current state slice of the subject.

Recommended V0.1 form:

- family-level continuous `64D` edge vector
- optional prototype-level `384` fit score layer

Interpretation:

- `64D` captures global pattern distribution
- `384` captures stage-like local interpretability

### 2. Relation Context `R_t`

`R_t` stores relevant relationship structure around the subject.

V0.1 recommendation:

- keep this lightweight
- allow zero, one, or multiple relation entries
- do not require a full graph in MVP

Possible fields:

- relation type
- direction
- intensity
- consent state
- conflict tag

Examples:

- self mode may have empty `R_t`
- co-reading mode may include a pair relation
- project analysis may include role-to-role or team-to-goal relations

### 3. Environment And Events `E_t`

`E_t` captures external conditions influencing interpretation.

Examples:

- current phase or timing
- known stressors
- opportunity window
- organization or family context
- major recent event

V0.1 recommendation:

- use explicit user-entered contextual tags
- do not ingest external surveillance or scraped personal data

### 4. Memory `M_t`

`M_t` is the retained history relevant to the current interpretation.

V0.1 recommendation:

- treat memory as optional but structurally supported
- start with simple previous observations rather than long-lived agent memory

Possible contents:

- previous observations
- previous scores
- previous probes
- previous state deltas

### 5. Uncertainty `U_t`

`U_t` records what the system does not know well enough.

This is essential because the system's next best action is often to reduce uncertainty, not to over-answer.

V0.1 recommendation:

- include one overall uncertainty score
- include a list of missing or weak dimensions
- include confidence notes for explanation

## Observation Cycle

The basic cycle should be:

1. collect minimal input
2. build initial `F_t`
3. estimate `S_t`
4. estimate uncertainty `U_t`
5. if needed, ask an `Edge Probe`
6. update `F_t`
7. produce explanation and low-risk next steps

This makes the system a field-reconstruction loop rather than a one-shot labeler.

## Time Model

The project should support time explicitly, even if MVP uses only simple snapshots.

Recommended time levels:

- `snapshot`: one isolated observation
- `revisit`: repeated observations across sessions
- `trajectory`: ordered sequence with interpretable shifts

V0.1 requirement:

- every observation must have a timestamp
- the system should be able to compare current and previous state when prior data exists

## What Edgefield Is Not

`Edgefield` is not:

- a synonym for chat context
- a hidden personality essence
- a justification for collecting unlimited data
- a fully simulated world model in MVP

It is a bounded representation of the factors that matter for structured interpretation.

## Minimal Computational Contract

Any V0.1 implementation claiming to use `Edgefield` should support:

- one subject
- one timestamped observation
- one state representation
- one uncertainty representation
- optional relation context
- optional historical reference
- at least one probe recommendation path

If these pieces are missing, the system is not yet an Edgefield system in the intended sense.

## Relation To Other Concepts

### Edge

`Edge` is the state slice.

### Edgefield

`Edgefield` is the full state-bearing context that makes the slice meaningful.

### Edge Vector

`Edge Vector` is the numeric representation inside `S_t`.

### Edge Probe

`Edge Probe` is the mechanism used to reduce `U_t`.

### Edge Projection

`Edge Projection` is the scenario output generated after the field is sufficiently reconstructed.

## V0.1 Design Decisions

Recommended decisions for now:

- keep `Edgefield` as the top-level conceptual model
- treat `64D` family vector as the primary state layer
- allow `384` prototypes as an interpretive and transition-aware secondary layer
- represent uncertainty explicitly
- keep relation modeling lightweight in MVP

## Open Questions

- How much of `R_t` should be exposed in user-facing outputs?
- Should `E_t` be normalized as tags, free text, or both?
- What is the minimum memory window needed before trajectory outputs become meaningful?
- At what point should lightweight relation context become a true graph model?
