# Glossary

## Purpose

This glossary freezes the project's working language so product, model, and engineering documents use the same meanings.

Each term is tagged as:

- `Confirmed`: should be treated as the current canonical definition.
- `Working Assumption`: currently useful, but still open to revision.
- `To Validate`: proposed term or interpretation that still needs product, research, or implementation validation.

## Canonical Naming

- Product working name: `Edging`
- System working name: `Edging GPT`
- Core theory name: `Edging: Change Computation Theory`

Status: `Working Assumption`

Note:

- Use `Edging GPT` consistently in internal docs.
- Avoid mixing `Edge GPT` and `Edging GPT`.

## Core Terms

### Edging

Working definition:

`Edging` is a structured method for observing, describing, and probing how an object changes under constraints, relations, and events.

Status: `Confirmed`

### Edge

Working definition:

`Edge` is not an identity label. It is the object's state slice at a given moment inside a changing field.

Status: `Confirmed`

### Edgefield

Working definition:

`Edgefield` is the full change field affecting an object at a given time, including its internal state, relations, environment, memory, uncertainty, and event pressure.

Status: `Confirmed`

### Edge State

Working definition:

`Edge State` is a single-time snapshot of the object's current state inside the Edgefield.

Status: `Confirmed`

### Edge Vector

Working definition:

`Edge Vector` is the numerical representation of the object's current state projected onto the project's change basis.

Current preferred interpretation:

- Primary form: continuous `64D` vector
- Optional linked form: `384` line-state prototype fit scores

Status: `Working Assumption`

### Edge Shift

Working definition:

`Edge Shift` is the state difference between two adjacent observations.

Status: `Confirmed`

### Edge Trajectory

Working definition:

`Edge Trajectory` is the time-ordered sequence of Edge States or Edge Vectors for the same object.

Status: `Confirmed`

### Edge Tension

Working definition:

`Edge Tension` measures internal structural pull between competing tendencies in the current state.

Status: `Working Assumption`

### Edge Potential

Working definition:

`Edge Potential` is the tendency distribution over plausible near-future directions.

Status: `Working Assumption`

### Edge Probe

Working definition:

`Edge Probe` is the smallest safe question, observation, or action designed to reduce uncertainty or validate a hypothesis about the Edgefield.

Status: `Confirmed`

### Edge Engine

Working definition:

`Edge Engine` is the combined reasoning system that samples, updates, scores, simulates, and explains state change.

Status: `Confirmed`

### Information Gap

Working definition:

`Information Gap` is the amount of uncertainty remaining in the current model over the variables that matter for interpretation or next-step guidance.

Status: `Confirmed`

### Edge Projection

Working definition:

`Edge Projection` is a set of candidate future paths with conditions, not a deterministic prediction.

Status: `Confirmed`

### Edge Map

Working definition:

`Edge Map` is the relational view of multiple objects, where each object has its own state representation and each relation has type, strength, direction, and time context.

Status: `Working Assumption`

### Edgescape

Working definition:

`Edgescape` is the visualized landscape of an Edgefield for user-facing interpretation.

Status: `To Validate`

### Edgeverse

Working definition:

`Edgeverse` is the higher-level ecology formed by interacting Edgefields across many objects and systems.

Status: `To Validate`

## Domain Terms

### Hexagram Family

Working definition:

A `Hexagram Family` is one of the `64` top-level change patterns used as part of the project's symbolic and computational basis.

Status: `Confirmed`

### Line-State Prototype

Working definition:

A `Line-State Prototype` is a specific stage-like state node within a hexagram family. In V0.1, the preferred formulation is `64 families x 6 line states = 384 prototypes`.

Status: `Working Assumption`

### Transition Rule

Working definition:

A `Transition Rule` describes how a state may move within a family or across families under specific conditions.

Status: `Confirmed`

### Semantic Anchor

Working definition:

A `Semantic Anchor` is the short explanatory text used to represent a prototype or family in embedding space and user explanation.

Status: `Confirmed`

### Feature Vector

Working definition:

A `Feature Vector` is the structured numeric profile used for deterministic matching before or alongside semantic similarity.

Status: `Confirmed`

## Product Terms

### Self-Assessment

Working definition:

User analyzes their own current state or trajectory.

Status: `Confirmed`

### Co-Reading

Working definition:

Two consenting participants jointly analyze a relationship, interaction, or shared situation.

Status: `Confirmed`

### Non-Human Object Analysis

Working definition:

The system analyzes a role, project, team pattern, brand, or fictional character rather than a real third party.

Status: `Confirmed`

## Safety Terms

### High-Risk Prediction

Working definition:

An output that could materially influence medical, legal, financial, employment, educational, or safety-critical decisions.

Status: `Confirmed`

### Covert Profiling

Working definition:

Inference or judgment about a real person who did not knowingly participate in the analysis flow.

Status: `Confirmed`

### Sensitive Data

Working definition:

Data that creates elevated privacy or harm risk, including identity, biometrics, health, financial, location, private communications, and minor-related information.

Status: `Confirmed`

## Open Terms To Resolve

- Should `Edge Vector` be the primary truth and `384` prototypes only be interpretive scaffolding, or are both first-class?
- Should `Edgescape` and `Edgeverse` remain product vocabulary, or are they too early?
- Should `Edging GPT` remain the external product name given the naming ambiguity already identified in the research reports?
