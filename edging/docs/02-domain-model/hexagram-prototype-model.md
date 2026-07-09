# Hexagram Prototype Model

## Objective

Define how `64D` family-level representation and `384` line-state prototypes work together in V0.1.

## Core Decision

V0.1 should use a hybrid model:

- the `64D` edge vector is the primary continuous state representation
- the `384` line-state prototypes are the primary interpretive and transition-aware scaffold

This means:

- the system does not collapse everything into one winning hexagram label
- the system also does not rely on an abstract vector with no stage-like interpretability

## Why Hybrid Wins

### If we use only `64D`

Strengths:

- simpler continuous representation
- easier uncertainty distribution
- easier family-level comparison

Weaknesses:

- weak stage interpretation
- weak transition semantics
- hard to explain "why this exact state"

### If we use only `384 prototypes`

Strengths:

- high interpretability
- strong stage structure
- easy transition reasoning

Weaknesses:

- may become too discrete too early
- harder to represent blended states
- more brittle for ambiguous inputs

### Hybrid Outcome

The hybrid model keeps:

- continuity at family level
- stage semantics at prototype level
- explainability without forcing hard classification

## Representation Layers

### Layer 1: Family Basis

The family basis contains `64` top-level change patterns.

Output form:

```text
e_t in R^64
```

Interpretation:

- each dimension reflects relative activation of one family pattern
- the vector may be normalized for comparability

V0.1 recommendation:

- normalize family weights to sum to `1.0`

### Layer 2: Prototype Basis

The prototype basis contains `384` state prototypes.

Output form:

```text
p_t in R^384
```

Interpretation:

- each score reflects how well the current observation fits a specific line-state prototype
- prototype scores need not be interpreted as exclusive classes

V0.1 recommendation:

- compute prototype scores locally
- expose only top-ranked prototypes in user-facing results

## Canonical Structural Mapping

```text
64 families
  x 6 line states each
  = 384 prototypes
```

Each prototype belongs to exactly one family.

Each family has:

- family-level semantics
- six ordered line-state semantics
- intra-family transition hints
- cross-family change links where needed

## Scoring Flow

Recommended V0.1 flow:

1. collect structured and text input
2. derive a subject feature vector
3. derive a semantic representation
4. score against prototype library
5. aggregate prototype evidence into family-level distribution
6. compute uncertainty
7. return top families, top prototypes, and probes

## Deterministic And Semantic Channels

Prototype scoring should combine two channels.

### Channel 1: Deterministic Feature Match

Compare subject feature vector to prototype feature vectors.

Purpose:

- stability
- inspectability
- repeatable behavior

### Channel 2: Semantic Similarity

Compare subject text or context representation to prototype semantic anchors.

Purpose:

- richer matching
- better handling of natural language descriptions
- more nuanced interpretation

## Recommended Formula Shape

V0.1 does not need a final equation yet, but should follow this shape:

```text
prototype_score
= a * feature_match
+ b * semantic_match
+ c * family_prior
+ d * rule_adjustment
```

With constraints:

- all components should be inspectable
- weights should be versioned
- adjustments should be documented

## Aggregation Logic

Prototype evidence should roll up to family evidence.

Recommended V0.1 family aggregation:

- strongest prototype evidence matters
- local adjacent line coherence matters
- average family support matters

This avoids:

- picking a family from one accidental spike
- forcing six unrelated line scores into one family explanation

## Transition Logic

Transition logic exists at two levels.

### Intra-Family Transition

Movement between nearby line states inside the same family.

Examples:

- early emergence -> visible development
- instability -> stabilization

### Cross-Family Transition

Movement from one family to another under defined conditions.

Examples:

- single-line change mapping
- threshold-triggered projection
- scenario-specific path shift

V0.1 recommendation:

- start with explicit hand-authored transition hints
- delay probabilistic transition learning until schema quality is stable

## Output Contract

Each V0.1 result should provide:

- top `3` family scores
- top `3` prototype scores
- one plain-language explanation of family-level state
- one plain-language explanation of prototype-level stage
- one uncertainty note
- one to three low-risk probes

## Example Interpretation Pattern

Recommended explanation structure:

- family level answers: "what broad change pattern dominates now"
- prototype level answers: "what stage-like position this resembles"
- probe level answers: "what to ask or test next"

## What This Model Avoids

This model avoids:

- single-label reductionism
- mystical certainty
- pure embedding opacity
- over-engineering a full learned transition system before ontology is stable

## V0.1 Build Strategy

The first implementation should:

1. choose `2` to `4` families
2. define all `6` prototypes for each
3. assign feature vectors
4. write semantic anchors
5. write simple transition hints
6. test scoring on example cases

This gives a real validation slice before scaling to all `64` families.

## Open Questions

- Should family aggregation be derived only from prototypes, or also from direct family-level scoring?
- Should prototype scores be normalized within family, across all families, or left as raw fit values?
- What is the best uncertainty signal when top families are close but prototypes are unstable?
