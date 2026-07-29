# edge-world

Edge World is a deterministic Yi Jing world-engine prototype. The current
Python layer contains hexagram math primitives, a tile/region world engine,
live cast generation, visualization codecs, and a small neural-network
foundation for later adaptive experiments.

## Python Tests

Run the core test suite from this directory:

```bash
python3 -m unittest discover tests
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
