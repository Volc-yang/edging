import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from neural_network import (
    OBSERVATION_FEATURES,
    WORLD_TILE_FEATURES,
    NeuralNetwork,
    batch_predict,
    encode_observation_features,
    encode_world_tile,
)
from world_engine import WorldEngine


class NeuralNetworkTests(unittest.TestCase):
    def test_observation_encoder_uses_stable_schema_order(self):
        features = {name: index / 10 for index, name in enumerate(OBSERVATION_FEATURES)}

        encoded = encode_observation_features(features)

        self.assertEqual(encoded.feature_names, OBSERVATION_FEATURES)
        self.assertEqual(encoded.values[0], 0.0)
        self.assertEqual(encoded.values[-1], 0.9)

    def test_world_tile_encoder_outputs_normalized_features(self):
        engine = WorldEngine(seed=20260722)
        tile = engine.tile(7, 11)
        region = engine.region(tile.region_id.x, tile.region_id.y)

        encoded = encode_world_tile(tile, region, engine.region_size)

        self.assertEqual(encoded.feature_names, WORLD_TILE_FEATURES)
        self.assertEqual(len(encoded.values), 10)
        for value in encoded.values:
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_network_initialization_is_deterministic(self):
        first = NeuralNetwork.initialized(WORLD_TILE_FEATURES, [8], ["growth", "risk"], seed=7)
        second = NeuralNetwork.initialized(WORLD_TILE_FEATURES, [8], ["growth", "risk"], seed=7)

        self.assertEqual(first.to_dict(), second.to_dict())

    def test_prediction_shape_matches_output_names(self):
        engine = WorldEngine(seed=1)
        tile = engine.tile(1, 2)
        vector = encode_world_tile(tile)
        network = NeuralNetwork.initialized(WORLD_TILE_FEATURES, [6], ["fertility", "danger"], seed=99)

        prediction = network.predict(vector)

        self.assertEqual(prediction.output_names, ("fertility", "danger"))
        self.assertEqual(set(prediction.as_dict()), {"fertility", "danger"})
        self.assertEqual(len(prediction.values), 2)

    def test_training_step_reduces_loss_for_simple_target(self):
        vector = [0.2, 0.7]
        network = NeuralNetwork.initialized(["a", "b"], [4], ["score"], seed=3)
        target = {"score": 0.9}

        first_loss = network.train_step(vector, target, learning_rate=0.2)
        second_loss = network.train_step(vector, target, learning_rate=0.2)

        self.assertLess(second_loss, first_loss)

    def test_model_round_trip_preserves_prediction(self):
        network = NeuralNetwork.initialized(["a", "b"], [3], ["score"], seed=11)
        expected = network.predict([0.25, 0.75]).values

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "network.json"
            network.save(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            restored = NeuralNetwork.from_dict(payload)

        self.assertEqual(restored.predict([0.25, 0.75]).values, expected)

    def test_batch_predict_returns_all_predictions(self):
        network = NeuralNetwork.initialized(["a"], [], ["score"], seed=5)

        predictions = batch_predict(network, [[0.1], [0.2], [0.3]])

        self.assertEqual(len(predictions), 3)


if __name__ == "__main__":
    unittest.main()
