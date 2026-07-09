# Risk Boundaries

## Objective

Define the safety and compliance boundaries for the first public product version.

This document is not a full legal memo. It is a product and system constraint document.

## Core Position

`Edging GPT` should be designed as a low-risk reflective interpretation tool.

It should not be designed as:

- a diagnostic authority
- a hidden profiling engine
- an automated decision-maker
- a substitute for professional advice
- a dependency-oriented companion

## Allowed Product Framing

Allowed framing:

- structured self-reflection
- symbolic interpretation
- relationship pattern reflection between consenting adults
- scenario-based change exploration
- non-human object analysis

Disallowed framing:

- "see the real truth about someone"
- "predict what will definitely happen"
- "detect lies, betrayal, or cheating"
- "decide whether this person is safe, loyal, or employable"
- "replace therapy, legal counsel, or medical judgment"

## Risk Tiers

### Low Risk

- self-assessment
- consensual co-reading
- fictional character analysis
- brand or project analysis

### Medium Risk

- interpretation of a real relationship with uneven information
- repeated emotional reliance on system outputs
- overconfident future-path language

### High Risk

- covert profiling of a real person
- uploads of private communications to judge third parties
- mental health or medical inference
- employment, finance, law, education, or safety-sensitive guidance
- minors in emotionally loaded interaction flows

## Non-Negotiable Boundaries For MVP

The MVP must not allow:

- analysis of a real third party without clear participation
- ingestion of private chat logs for truth claims
- photo, voice, or surveillance-based personality claims
- sensitive personal data collection
- high-stakes decision support
- persistent companion-style emotional dependency loops
- sexualized brand positioning

## Data Risk Boundaries

### Allowed Inputs

- questionnaire responses
- user-authored text
- consensually provided shared context
- non-sensitive object descriptions

### Restricted Or Rejected Inputs

- health information
- financial information
- precise location history
- private third-party communication records
- minors' personal data
- biometric identifiers
- hidden recordings or scraped personal data

## Output Risk Boundaries

Outputs must:

- distinguish observation from inference
- distinguish confidence from uncertainty
- avoid deterministic claims when evidence is weak
- present reflective suggestions as optional and low-risk

Outputs must not:

- assert hidden motives as facts
- claim certainty beyond collected evidence
- recommend harmful confrontation or manipulation
- pressure users into continued reliance

## UX Guardrails

The system should:

- clearly state what mode the user is in
- warn when the request approaches a blocked scenario
- ask for minimal data only
- explain why a request is rejected
- use uncertainty language consistently

The system should not:

- anthropomorphize itself as an emotionally dependent partner
- imply privileged access to unseen truth
- encourage surveillance or evidence gathering against third parties

## System Guardrails

The system should implement:

- mode-level policy gating
- input red-flag detection
- output style constraints
- rejection templates for blocked requests
- logging for unsafe-request categories

## Decision Rules

### Reject

Reject requests involving:

- covert third-party judgment
- high-stakes personal decisions
- minors
- sensitive data processing
- truth-claim framing unsupported by evidence

### Deflect

Deflect requests involving:

- emotionally escalated certainty-seeking
- binary judgments about another person's motives
- dependency-seeking companion behavior

Deflection pattern:

- restate the boundary
- narrow to a safe reflective frame
- offer a lower-risk alternative

### Allow

Allow requests that:

- are self-directed
- are consensual
- stay in low-stakes domains
- use minimal and non-sensitive input

## Open Compliance Work

Still needed beyond this doc:

- detailed PII handling policy
- consent language for co-reading flows
- retention policy
- audit and moderation plan
- region-specific launch checklist
