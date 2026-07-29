# Hexagram Spacetime Abstraction Schema

## Objective

Define the source-of-truth structure used to abstract all `64` hexagrams and `384` lines without mixing objective coordinates with interpretive language.

## Layer 1: Generated Structural Basis

The generated structural basis contains only values that can be derived deterministically from the hexagram and line position.

Generated artifacts:

- `hexagram-spacetime.v0.1.yaml`: `64` square-space and circle-time records
- `line-structures.v0.1.yaml`: `384` fixed line positions and single-line changes

Generation command:

```bash
ruby bin/generate_spacetime_basis.rb
```

Visualization command:

```bash
ruby bin/generate_spacetime_visualizations.rb
```

Generated visualizations:

- `visualizations/hexagram-square-circle-map.svg`: square-space and circle-time projection of all `64` hexagrams
- `visualizations/line-change-six-layer-map.svg`: six line-position layers containing all `384` directed single-line changes

The SVG files are generated from the YAML basis and confirmed interpretation registry. They are outputs, not independent sources of truth.

### Square Space

Each hexagram has a square coordinate:

```text
S(G) = (upper_xiantian_number, lower_xiantian_number)
```

The Xiantian trigram sequence is:

```text
Qian 1, Dui 2, Li 3, Zhen 4, Xun 5, Kan 6, Gen 7, Kun 8
```

The square is displayed with Kun at the top-left and Qian at the bottom-right:

- rows fix the lower trigram
- columns fix the upper trigram
- both axes display `8 -> 1`

### Circle Time

Two indexes are retained because geometry and temporal interpretation use different origins:

- `circle_index_qian_origin_clockwise`: Qian is `0`, matching the diagram
- `cycle_index_fu_origin`: Fu is `0`, matching the start of Yang return

The engineering four-phase partition is:

```text
0..15   shaoyang
16..31  taiyang
32..47  shaoyin
48..63  taiyin
```

This partition is a project convention derived from the circle. It is not presented as a classical textual claim.

### Six-Line Order

All line vectors and indexes are bottom-to-top:

```text
line 1, line 2, line 3, line 4, line 5, line 6
```

Each line record includes:

- polarity
- lower/upper trigram realm
- local lower/middle/upper level
- centrality
- positional correctness
- paired correspondence line and whether polarity makes it effective
- stable and changing line values
- changed hexagram and changed square/time coordinates

## Layer 2: Confirmed Interpretive Abstraction

Interpretive records are authored and reviewed one line at a time. They must not override generated structural values.

Required fields per line:

```yaml
state_name: string
core_abstraction: string
fixed_pattern: string
variable_pattern: string
short_definition: string
semantic_anchor: string
stable_path: string
changing_path: string
principle: string
scale_anchors:
  cosmic_max: string
  planetary_natural: string
  social_organizational: string
  individual: string
  biological: string
  microscopic_min: string
scale_mapping: string
scale_boundary: string
review:
  status: confirmed_or_draft
  notes: string
```

Every interpretive record carries a mechanically verified classical-source
correspondence:

```yaml
source_correspondence:
  canonical:
    record_id: proto_hex_NN_line_N
    source_status: dual_source_normalized_agreement_or_reviewed_variant
    resolution: string
  primary_display_edition:
    king_wen_index: integer
    line_index: integer
    line_json_pointer: string
    commentary_json_pointer: string
  independent_check_edition:
    king_wen_index: integer
    line_index: integer
    line_json_pointer: string
    commentary_json_pointer: string
```

The confirmed and draft registries share the same `source_registry`, which
resolves the two edition keys to immutable files under `sources/`, including
their SHA-256 checksums. JSON Pointers are
zero-based RFC 6901 paths. `canonical` links to the reconciled record in
`classical-line-texts.v0.1.yaml`; it records whether the editions normalize to
agreement or require an explicitly reviewed resolution.

Every scale anchor is a structural analogy, not evidence that the classical text predicted the example. `scale_mapping` names the shared spatial, temporal, and change structure. `scale_boundary` states where the analogies stop.

## Fixed Versus Variable

`fixed_pattern` describes what is already structurally true at the current line-state.

`variable_pattern` describes the available branch:

- stable line value: preserve the current polarity and structural state
- changing line value: flip one line and enter the deterministically derived target hexagram

Interpretive prose may explain these branches, but it may not change the target hexagram.

## Eight-Palace Soul Associations

Every hexagram belongs to exactly one of the eight palaces. It therefore has
two palace-level associations:

- the wandering-soul hexagram of its palace
- the returning-soul hexagram of its palace

The eight members of one palace share the same wandering-soul and
returning-soul hexagrams. For example, every member of the Qian palace refers
to Jin as its wandering-soul hexagram and Dayou as its returning-soul
hexagram. Qian's returning-soul association is therefore Dayou, not Pi.

`eight_palace_memberships` contains one record for each of the `64`
hexagrams. It records the palace root, palace stage, cumulative changed lines
from the root, and both soul associations with their target square/time data.

There are only eight actual wandering-to-returning-soul composite changes,
one per palace. Each changes the complete lower trigram:

```text
wandering soul -> returning soul: flip lines 1, 2, and 3
```

This transition has Hamming distance `3` and no classically specified order
for the three atomic flips. It is stored in `returning_soul_changes` as a
composite relation, not as one of the `384` single-line edges.

## Validation Invariants

The basis is valid only when all conditions hold:

- exactly `64` unique hexagrams
- exactly `384` unique line records
- exactly `6` lines per family
- every changed target differs by exactly one line
- every square coordinate is unique
- every circle and cycle index is unique
- every confirmed interpretation has all six scale anchors
- every interpretation has resolvable primary and check-edition source pointers
- every structural line has a non-empty canonical line statement and 小象 commentary
- the canonical corpus records dual-source agreement or an explicit variant resolution for every line
- generated and interpretive records agree on line id and changed target
- exactly `64` unique eight-palace memberships exist
- every hexagram references its palace wandering-soul and returning-soul hexagrams
- exactly `8` wandering-to-returning-soul composite changes exist

## Important Boundary

The square and circle are two projections of the same `64` states:

- square adjacency is not automatically a single-line change
- circle adjacency is not automatically a causal transition
- single-line change is defined only by flipping one component of the six-line vector

This distinction prevents visual proximity from being mistaken for transformation law.
