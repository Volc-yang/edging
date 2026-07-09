# Roadmap

## Objective

Turn the current research base into a buildable V0.1 program with clear milestones.

## Guiding Strategy

The program should move in this order:

1. Canonicalize language
2. Freeze MVP boundaries
3. Freeze domain model
4. Validate a tiny prototype set
5. Only then scale product and system complexity

## Phase 0: Documentation Canonicalization

Goal:

Convert PDF research into a maintainable Markdown-first source of truth.

Deliverables:

- `glossary.md`
- `mvp-scope.md`
- `data-schema.md`
- `risk-boundaries.md`
- this `roadmap.md`

Exit criteria:

- one naming convention is chosen
- one glossary is canonical
- MVP and non-MVP boundaries are explicit
- first schema assumptions are documented

## Phase 1: Domain Model Freeze

Goal:

Decide what the system computes before building broad product behavior.

Deliverables:

- `edgefield-model.md`
- `hexagram-prototype-model.md`
- `feature-schema.v0.1.yaml`
- `hexagram-families.v0.1.yaml`
- `line-prototypes.seed.yaml`
- `transition-rules.seed.yaml`

Exit criteria:

- at least `2` to `4` hexagram families are fully defined
- each selected family has all `6` line-state prototypes
- scoring inputs and outputs are unambiguous
- uncertainty representation is chosen

## Phase 2: Deterministic Prototype Engine

Goal:

Build the smallest inspectable reasoning layer.

Deliverables:

- feature scoring function
- family aggregation logic
- prototype matching logic
- uncertainty calculator
- probe recommendation rules

Exit criteria:

- one observation can produce repeatable structured output
- explanations can point back to explicit schema elements
- at least `10` example cases can be manually reviewed end to end

## Phase 3: MVP Interaction Layer

Goal:

Wrap the prototype engine in a constrained product flow.

Deliverables:

- self-assessment flow
- consensual co-reading flow
- non-human object flow
- blocked-request handling
- explanation templates

Exit criteria:

- all supported flows work without unsafe fallthrough
- rejection behavior is consistent
- output tone stays reflective rather than absolute

## Phase 4: Early Evaluation

Goal:

Test whether the system is understandable, stable, and safe enough to continue.

Deliverables:

- evaluation rubric
- example-set review process
- consistency checks across similar inputs
- unsafe prompt red-team set

Exit criteria:

- core outputs are understandable to reviewers
- similarity cases behave consistently enough
- blocked scenarios are rejected reliably

## Suggested 2-Week Plan

### Week 1

- finalize glossary
- finalize MVP scope
- finalize risk boundaries
- define feature schema
- choose first `2` to `4` hexagram families

### Week 2

- write first seed prototype registry
- define first transition rules
- draft deterministic scorer behavior
- create first example cases
- review gaps and contradictions

## Suggested 6-Week Plan

### Weeks 1-2

- documentation canonicalization
- scope freeze
- first seed schema

### Weeks 3-4

- prototype registry drafting
- deterministic engine sketch
- first example evaluations

### Weeks 5-6

- constrained product flow
- safety handling
- internal evaluation and revision

## Current Blockers

- no canonical external naming decision
- no final answer on `64D vector` versus `384 prototypes` versus hybrid primacy
- no machine-readable registry yet
- no chosen first family set for implementation

## Recommended Next Actions

1. Create `edgefield-model.md`
2. Create `hexagram-prototype-model.md`
3. Draft the first YAML schema files
4. Pick the first `2` to `4` families for seed implementation
5. Build a deterministic scorer before any open-ended agent layer
