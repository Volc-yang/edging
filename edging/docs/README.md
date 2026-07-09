# Edging Docs Analysis And Next-Step Plan

## Current Status

The current `docs/` directory is a research drop, not yet a maintainable documentation system.

Observed characteristics:

- All core materials are PDF reports.
- There are duplicate or near-duplicate files for the V3 report.
- Naming is inconsistent: `Edge GPT` and `Edging GPT` are both used.
- There is no index, no version history, no canonical source-of-truth doc, and no machine-editable spec.
- The directory currently contains product thinking, theory evolution, engineering modeling, and project initiation content mixed together.

## What The Existing PDFs Already Cover

### 1. Product feasibility and compliance baseline

`edging GPT 产品研究报告.pdf` establishes:

- The product should not be framed as mystical prediction.
- The safer positioning is a cultural-symbolic self-reflection / relationship insight tool.
- MVP should stay in low-risk use cases.
- Mainland China compliance is a first-class product constraint.

### 2. Theory upgrade direction

`Edging GPT 现阶段研究报告.pdf` establishes:

- The project should evolve from static classification to dynamic field reconstruction.
- The center of gravity should move from "which hexagram are you" to "how does the object evolve in a field".
- Core internal concepts such as `Edgefield`, `Edge Vector`, `Edge Probe`, and `Edge Engine` already exist.

### 3. V3 architecture and project framing

`Edging GPT 第三版本研究报告与立项报告.pdf` establishes:

- A more complete product + modeling + delivery direction.
- State-space / Bayesian / dynamic graph / active sampling ideas.
- A staged roadmap and initial project framing.

### 4. Engineering ontology / prototype library direction

`Edging项目《64卦基向量函数定义表 V0.1》工程化分析报告.pdf` establishes:

- The most concrete engineering direction so far.
- A `64 hexagram family -> 384 line-state prototype -> transition graph` model.
- Candidate feature dimensions, matching logic, and structured data schema direction.

## Ideal Documentation System

For this project, ideal docs should not be organized by "report versions". They should be organized by decision layers.

Recommended structure:

```text
docs/
  README.md
  00-foundations/
    vision.md
    glossary.md
    principles.md
  01-product/
    positioning.md
    prd.md
    user-scenarios.md
    mvp-scope.md
  02-domain-model/
    edgefield-model.md
    hexagram-prototype-model.md
    data-schema.md
    evaluation-metrics.md
  03-system/
    architecture.md
    sampling-engine.md
    reasoning-engine.md
    storage-and-events.md
  04-safety/
    compliance-baseline-cn.md
    risk-boundaries.md
    pii-policy.md
    forbidden-use-cases.md
  05-research/
    literature-map.md
    assumptions.md
    open-questions.md
  06-delivery/
    roadmap.md
    milestones.md
    backlog.md
```

## Gap Analysis

Relative to that ideal structure, the current gaps are clear:

### Strong already

- Vision has direction.
- Theory has a distinct vocabulary.
- Compliance awareness is unusually early and strong.
- Engineering modeling is starting to become spec-like.

### Missing or weak

- No canonical product definition.
- No single agreed glossary.
- No source-of-truth data schema in Markdown/JSON/YAML form.
- No evaluation plan that connects theory to measurable product quality.
- No architecture doc translating theory into services, storage, APIs, and workflows.
- No decision log explaining which assumptions are fixed and which are experimental.
- No milestone plan tied to concrete deliverables.

## Recommended Immediate Direction

The best next step is not "write more research PDFs".

The best next step is:

1. Freeze terminology.
2. Convert report conclusions into canonical Markdown docs.
3. Split "product truth", "model truth", and "compliance truth".
4. Define the MVP as a spec, not as a narrative.
5. Build the smallest structured prototype library before attempting a full intelligent system.

## Suggested Execution Plan

### Phase 1: Documentation normalization

Goal: turn scattered research into an executable knowledge base.

Deliverables:

- `glossary.md`
- `positioning.md`
- `mvp-scope.md`
- `risk-boundaries.md`
- `roadmap.md`

Rules for this phase:

- Pick one official product name convention and use it everywhere.
- Mark one V3 report as canonical; archive duplicates.
- Every concept must have one definition only.
- Every major claim should be labeled as one of:
  - Confirmed
  - Working assumption
  - To validate

### Phase 2: Domain model solidification

Goal: decide what the system actually computes.

Deliverables:

- `edgefield-model.md`
- `hexagram-prototype-model.md`
- `data-schema.md`
- initial JSON/YAML schema drafts

This phase should answer:

- Is the core representation `64D continuous vector`, `384 prototypes`, or both?
- What is the exact relationship between hexagram family, line-state, transition, and explanation?
- Which dimensions are first-class in V0.1?
- What data is user-provided, inferred, or forbidden?

### Phase 3: MVP product spec

Goal: define the first buildable product, not the final vision.

Deliverables:

- `prd.md`
- `user-scenarios.md`
- `evaluation-metrics.md`
- `forbidden-use-cases.md`

Recommended MVP boundary:

- Self-assessment
- Two-person consensual co-reading
- Non-human object analysis such as role, project, or brand

Explicitly avoid in MVP:

- Third-party covert profiling
- High-stakes predictions
- Emotional dependency / companion framing
- Sensitive data ingestion

### Phase 4: Prototype implementation planning

Goal: make the first engineering slice testable.

Recommended first slice:

- Handcraft 2 to 4 hexagram families fully.
- Expand them into 12 to 24 line-state prototypes.
- Define their feature vectors, semantic anchors, and transition rules.
- Create a deterministic scorer before adding LLM-driven adaptive reasoning.

Why this slice first:

- It validates the ontology.
- It exposes whether the schema is usable.
- It avoids overbuilding a full system before the representation is stable.

## Practical Priorities For The Next 2 Weeks

### Priority P0

- Build `glossary.md`
- Build `positioning.md`
- Build `mvp-scope.md`
- Build `risk-boundaries.md`
- Build `roadmap.md`

### Priority P1

- Build `hexagram-prototype-model.md`
- Build `data-schema.md`
- Draft `prototype-registry` format in JSON or YAML

### Priority P2

- Archive duplicate PDFs
- Add file naming convention
- Add decision log and versioning rules

## Recommended Working Decisions

These are the best current decisions based on the existing docs:

- Treat `Edging` as a structured change-analysis system, not a divination app.
- Use compliance constraints as product design inputs, not a late review item.
- Keep the LLM in the system, but do not let the LLM define the ontology.
- Make the ontology and scoring rules inspectable before doing large-scale automation.
- Start with documentation and schema discipline before building UI or agents.

## Next Concrete Outputs

If we continue from here, the most valuable next documents to produce are:

1. `docs/00-foundations/glossary.md`
2. `docs/01-product/mvp-scope.md`
3. `docs/02-domain-model/data-schema.md`
4. `docs/04-safety/risk-boundaries.md`
5. `docs/06-delivery/roadmap.md`

## Bottom Line

The project is not blocked by lack of ideas.

It is blocked by lack of canonical structure.

The current PDFs already contain enough material to start a real documentation system. The highest-value next step is to convert them into a layered, versioned, Markdown-first source of truth, then use that to constrain MVP scope and prototype implementation.
