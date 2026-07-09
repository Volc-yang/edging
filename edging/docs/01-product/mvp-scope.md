# MVP Scope

## Objective

Define the first buildable product boundary for `Edging GPT` so the team can avoid over-expanding into risky or under-specified features.

## Product Goal

The MVP should help adult users understand a current state, relationship pattern, or change trajectory through a structured symbolic-computational framework.

The MVP is not:

- a truth machine
- a divination engine
- a mental health diagnostic tool
- a covert profiling tool
- a high-stakes decision system

## Target Users

Primary users:

- adults interested in self-reflection
- adults exploring low-risk relationship or communication patterns
- creators analyzing fictional roles, projects, brands, or team dynamics

Not targeted in MVP:

- minors
- employers screening real candidates
- users seeking medical, legal, or financial judgment
- users trying to infer hidden intent from private third-party data

## MVP Use Cases

### In Scope

#### 1. Self-assessment

The user reflects on their current state, tension, and likely next-step options.

Allowed inputs:

- structured questionnaire
- short free-text self-description
- explicit user-selected context tags

Expected outputs:

- current state summary
- dominant pattern explanation
- uncertainty-aware interpretation
- low-risk next-step probes

#### 2. Consensual co-reading

Two adults voluntarily analyze a shared relationship or interaction pattern.

Allowed inputs:

- each participant's self-entered data
- shared context entered by participants
- optional explicit comparison prompts

Expected outputs:

- overlapping or conflicting change patterns
- relation tension summary
- safer communication suggestions

#### 3. Non-human object analysis

The user analyzes a role, brand, team pattern, fictional character, or project.

Allowed inputs:

- text description
- scenario framing
- goals and constraints

Expected outputs:

- state pattern interpretation
- change risks
- path options

## Out Of Scope

The MVP must explicitly reject:

- third-party covert profiling
- use of private chats, recordings, or photos to judge a real person
- lie detection claims
- infidelity detection claims
- diagnosis of mental illness
- hiring or firing recommendations
- credit, legal, medical, or school decision support
- persistent AI companion framing
- emotional dependency loops
- sexually suggestive positioning

## Input Boundaries

### Allowed

- questionnaire answers
- user-written descriptions
- consensually provided relationship context
- non-sensitive project or brand context

### Not Allowed

- scraped third-party personal data
- hidden surveillance material
- exact location trails
- financial account data
- health records
- biometric material
- minor-related data

## Output Boundaries

The MVP should produce:

- state descriptions
- possible tensions
- scenario-based projections
- reflective prompts
- low-risk action suggestions

The MVP should not produce:

- deterministic fate statements
- claims of hidden truth discovery
- certainty without evidence
- ranking of human worth or trustworthiness

## Product Shape

Recommended MVP flow:

1. User chooses a mode: self, co-reading, or non-human object.
2. System collects minimal structured context.
3. System computes an initial state representation.
4. System asks one or more uncertainty-reducing follow-up questions.
5. System returns an explanation plus 1 to 3 low-risk probes.

## Success Criteria

The MVP is successful if it can:

- keep users in low-risk flows
- produce explanations users can understand
- distinguish certainty from uncertainty
- demonstrate repeatable output structure
- avoid unsafe data collection patterns

## Non-Goals For MVP

- full longitudinal life tracking
- automatic ingestion from social platforms
- multi-agent relationship ecosystems
- enterprise deployment
- fully dynamic graph simulation
- open-ended therapeutic companionship

## Decisions To Lock Before Build

- official external product naming
- minimum questionnaire shape
- whether `64D vector`, `384 prototypes`, or hybrid scoring is the first implementation
- exact rejection behavior for unsafe user requests
