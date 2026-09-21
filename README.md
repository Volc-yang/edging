# edge-world

Edge World is a deterministic Yi Jing world-engine prototype. The current
Python layer contains hexagram math primitives, a tile/region world engine,
live cast generation, visualization codecs, and a small neural-network
foundation for later adaptive experiments.

`engine/subjective_world.py` adds the first subjective-world engine layer:
entities with consciousness, Yi Jing arbitration for collisions/fusion, and
chaos/split/death state rules for subjectivity-driven gameplay. The first
evolution chapter, "All Things Ensoul", awakens eight primal trigram spirits
from edge as the opening form of "万物有灵". Its success criteria are documented
in `doc/subjective_world_chapter_validation.md` and enforced by
`SubjectiveWorldModel.validate_first_chapter()`. The same layer projects world
actions onto eight primal action axes and computes nonlinear spirit resonance
with `SubjectiveWorldModel.action_resonance()`. First-chapter evolution also
records a trace for each awakened spirit, including its matrix, resonance, and
Yi Jing arbitration result. `SubjectiveWorldModel.run_primal_cycle()` implements
the base runtime loop from "帝出乎震" through "成言乎艮".

## Chapter One Engine Runtime

Chapter One now runs through a shared, rule-gated world snapshot. Godot is the
only game-engine implementation for Chapter One:

- Godot 4.7 game runtime: `engine_platforms/godot/project.godot`
- Xcode/SceneKit diagnostic preview: the `EdgeWorldChapterOne` executable in
  `preview3d/Package.swift` (not a second game-engine implementation)

An Unreal Engine 5 comparison implementation now lives at
`/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE`. It uses the same approved v2
snapshot, creates the eight-spirit scene, and includes a headless contract
commandlet. Godot remains the primary implementation while UE5 is developed as
the comparison target. Verify both consumers with:

```bash
python3 tools/validate_godot_ue5_parity.py
```

The local Ollama model may propose only bounded values on the eight Chapter One
action axes. The focus spirit is derived from the strongest action, so those two
values cannot contradict each other. `ChapterOneRuleValidator` rejects unknown
axes, invalid ticks, malformed responses, and proposals above the intent budget.
The deterministic Yi Jing engine remains the only component allowed to mutate
world state. Rejected or unavailable model output uses a deterministic fallback.

The runtime distinguishes the two Bagua orders explicitly: the subjective world
advances in Xiantian order before player intervention; the player introduces an
external action variable; Houtian directions and Luoshu numbers then determine
changing lines; and the Zhouyi hexagram pair becomes the encounter shown to the
player. The rule engine records why each pressure maps to each moving line,
selects one governing line by evidence, quotes the canonical judgment and line
text, and turns that forecast into a bounded subjective-world state change.
Godot, UE5, and SceneKit render the same control plan and before/after feedback.
Ollama proposes bounded Houtian pressures and presents the already-derived
encounter, but cannot choose or rewrite its hexagram or lines. See
`doc/chapter_one_cosmology.md` for the complete contract.

Generate the shared snapshot with the installed default model:

```bash
python3 tools/run_chapter_one.py --model llama3.2:latest
```

Example player intervention:

```bash
python3 tools/run_chapter_one.py --player-action flow --player-intensity 0.8 \
  --player-expression "玩家涉水进入世界。"
```

The Godot, UE5, and SceneKit buttons add `--advance`: each submitted
intervention reads the current snapshot and advances to the next world tick.
For a deterministic replay, omit `--advance` and pass an explicit `--tick N`.
Changing descriptive text at a fixed tick does not directly choose a hexagram;
the text informs Ollama's bounded pressure proposal while world time, action
axis, intensity, and the approved pressures remain authoritative.

`engine/yijing_text.json` is synchronized from the checked-in public-domain
display edition and the independently reconciled line corpus. It contains all
64 judgments, 64 Great Images, and 384 ordinary line statements. Regenerate it
with `ruby edging/bin/sync_engine_yijing_text.rb`.

Run without Ollama:

```bash
python3 tools/run_chapter_one.py --offline
```

Open the Godot frontend:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path engine_platforms/godot
```

For snapshot inspection only, open `preview3d/Package.swift` in Xcode and select
`EdgeWorldChapterOne`, or run the SceneKit diagnostic preview from the command line:

```bash
swift run --package-path preview3d EdgeWorldChapterOne
```

## Verification

One entry point for every gate:

```bash
./scripts/test.sh            # Python tests + edging structural validation
./scripts/test.sh --parity   # also run the Godot <-> UE5 parity gate
./scripts/test.sh --all      # everything, including the UE5 commandlet
```

Or run the Python suite directly:

```bash
./.venv/bin/python -m unittest discover tests
```

Third-party dependencies are declared in `requirements.txt` (only `numpy` and
`pillow`); everything else is Python standard library.

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

## Neural Network Foundation

`engine/neural_network.py` provides a dependency-free baseline:

- stable feature schemas for observation vectors and world tiles
- deterministic multi-layer perceptron initialization
- forward prediction
- one supervised training step for experiments
- JSON save/load for model snapshots

Example:

```python
import sys
from pathlib import Path

ROOT = Path("engine").resolve()
sys.path.insert(0, str(ROOT))

from neural_network import NeuralNetwork, WORLD_TILE_FEATURES, encode_world_tile
from world_engine import WorldEngine

engine = WorldEngine(seed=20260722)
tile = engine.tile(7, 11)
vector = encode_world_tile(tile, engine.region(tile.region_id.x, tile.region_id.y))

network = NeuralNetwork.initialized(
    input_names=WORLD_TILE_FEATURES,
    hidden_sizes=[8],
    output_names=["fertility", "risk", "stability"],
    seed=20260722,
)

print(network.predict(vector).as_dict())
```
