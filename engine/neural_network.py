"""
Edge World - minimal neural network foundation.

This module provides a small dependency-free neural layer for experiments on
top of the deterministic world engine. It is intentionally compact: feature
encoding, deterministic MLP initialization, forward inference, a single
supervised training step, and JSON persistence.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from world_engine import RegionState, WorldTile


FEATURE_SCHEMA_VERSION = "edgeworld.feature.v0.1"
NETWORK_SCHEMA_VERSION = "edgeworld.mlp.v0.1"

OBSERVATION_FEATURES: Tuple[str, ...] = (
    "agency",
    "visibility",
    "resource_mobilization",
    "stability",
    "risk_exposure",
    "momentum",
    "constraint_pressure",
    "coordination",
    "timing_maturity",
    "governance_capacity",
)

WORLD_TILE_FEATURES: Tuple[str, ...] = (
    "height",
    "moisture",
    "temperature",
    "yin_qi",
    "yang_qi",
    "entropy",
    "local_x",
    "local_y",
    "hexagram_yang_ratio",
    "region_stability",
)


@dataclass(frozen=True)
class EncodedVector:
    schema_version: str
    feature_names: Tuple[str, ...]
    values: Tuple[float, ...]

    def as_dict(self) -> Dict[str, float]:
        return dict(zip(self.feature_names, self.values))


@dataclass(frozen=True)
class LayerParameters:
    weights: Tuple[Tuple[float, ...], ...]
    biases: Tuple[float, ...]
    activation: str = "tanh"


@dataclass(frozen=True)
class Prediction:
    output_names: Tuple[str, ...]
    values: Tuple[float, ...]

    def as_dict(self) -> Dict[str, float]:
        return dict(zip(self.output_names, self.values))


def _stable_unit(seed: int, *parts: object) -> float:
    payload = ":".join([str(seed), *map(str, parts)]).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / ((1 << 64) - 1)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _activate(value: float, activation: str) -> float:
    if activation == "linear":
        return value
    if activation == "tanh":
        return math.tanh(value)
    if activation == "sigmoid":
        return 1.0 / (1.0 + math.exp(-value))
    if activation == "relu":
        return max(0.0, value)
    raise ValueError(f"Unsupported activation: {activation}")


def _activate_derivative(activated_value: float, activation: str) -> float:
    if activation == "linear":
        return 1.0
    if activation == "tanh":
        return 1.0 - activated_value * activated_value
    if activation == "sigmoid":
        return activated_value * (1.0 - activated_value)
    if activation == "relu":
        return 1.0 if activated_value > 0.0 else 0.0
    raise ValueError(f"Unsupported activation: {activation}")


def encode_observation_features(features: Mapping[str, float]) -> EncodedVector:
    missing = [name for name in OBSERVATION_FEATURES if name not in features]
    if missing:
        raise ValueError(f"Missing observation features: {', '.join(missing)}")

    values = []
    for name in OBSERVATION_FEATURES:
        value = float(features[name])
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Feature {name} must be between 0 and 1.")
        values.append(value)

    return EncodedVector(FEATURE_SCHEMA_VERSION, OBSERVATION_FEATURES, tuple(values))


def encode_world_tile(tile: WorldTile, region: RegionState | None = None, region_size: int = 32) -> EncodedVector:
    if region_size <= 0:
        raise ValueError("region_size must be positive.")

    stability = region.stability if region else 1.0 - tile.entropy
    yang_ratio = sum((tile.hexagram_value >> index) & 1 for index in range(6)) / 6.0
    values = (
        tile.height,
        tile.moisture,
        tile.temperature,
        tile.yin_qi,
        tile.yang_qi,
        tile.entropy,
        _clamp01(tile.local_x / max(1, region_size - 1)),
        _clamp01(tile.local_y / max(1, region_size - 1)),
        yang_ratio,
        _clamp01(stability),
    )
    return EncodedVector(FEATURE_SCHEMA_VERSION, WORLD_TILE_FEATURES, tuple(float(v) for v in values))


class NeuralNetwork:
    def __init__(
        self,
        input_names: Sequence[str],
        output_names: Sequence[str],
        layers: Sequence[LayerParameters],
    ):
        if not input_names:
            raise ValueError("input_names must not be empty.")
        if not output_names:
            raise ValueError("output_names must not be empty.")
        if not layers:
            raise ValueError("layers must not be empty.")
        self.input_names = tuple(input_names)
        self.output_names = tuple(output_names)
        self.layers = tuple(layers)
        self._validate_shape()

    @classmethod
    def initialized(
        cls,
        input_names: Sequence[str],
        hidden_sizes: Sequence[int],
        output_names: Sequence[str],
        seed: int = 20260722,
        output_activation: str = "sigmoid",
    ) -> "NeuralNetwork":
        sizes = [len(input_names), *hidden_sizes, len(output_names)]
        if any(size <= 0 for size in sizes):
            raise ValueError("All layer sizes must be positive.")

        layers = []
        for layer_index in range(len(sizes) - 1):
            fan_in = sizes[layer_index]
            fan_out = sizes[layer_index + 1]
            limit = math.sqrt(6.0 / (fan_in + fan_out))
            weights = []
            for row in range(fan_out):
                weights.append(
                    tuple((_stable_unit(seed, layer_index, row, col) * 2.0 - 1.0) * limit for col in range(fan_in))
                )
            activation = "tanh" if layer_index < len(sizes) - 2 else output_activation
            layers.append(LayerParameters(tuple(weights), tuple(0.0 for _ in range(fan_out)), activation))
        return cls(input_names, output_names, layers)

    def predict(self, vector: EncodedVector | Mapping[str, float] | Sequence[float]) -> Prediction:
        activations = self._coerce_input(vector)
        for layer in self.layers:
            activations = tuple(
                _activate(sum(weight * value for weight, value in zip(row, activations)) + bias, layer.activation)
                for row, bias in zip(layer.weights, layer.biases)
            )
        return Prediction(self.output_names, activations)

    def train_step(
        self,
        vector: EncodedVector | Mapping[str, float] | Sequence[float],
        target: Mapping[str, float] | Sequence[float],
        learning_rate: float = 0.05,
    ) -> float:
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive.")

        layer_inputs: List[Tuple[float, ...]] = [self._coerce_input(vector)]
        layer_outputs: List[Tuple[float, ...]] = []
        for layer in self.layers:
            output = tuple(
                _activate(sum(weight * value for weight, value in zip(row, layer_inputs[-1])) + bias, layer.activation)
                for row, bias in zip(layer.weights, layer.biases)
            )
            layer_outputs.append(output)
            layer_inputs.append(output)

        target_values = self._coerce_target(target)
        prediction = layer_outputs[-1]
        loss = sum((actual - expected) ** 2 for actual, expected in zip(prediction, target_values)) / len(target_values)

        deltas: List[Tuple[float, ...]] = [tuple() for _ in self.layers]
        last_layer = self.layers[-1]
        deltas[-1] = tuple(
            (actual - expected) * _activate_derivative(actual, last_layer.activation)
            for actual, expected in zip(prediction, target_values)
        )

        for layer_index in range(len(self.layers) - 2, -1, -1):
            next_layer = self.layers[layer_index + 1]
            current_output = layer_outputs[layer_index]
            next_delta = deltas[layer_index + 1]
            current_delta = []
            for node_index, activated in enumerate(current_output):
                downstream = sum(next_delta[j] * next_layer.weights[j][node_index] for j in range(len(next_delta)))
                current_delta.append(downstream * _activate_derivative(activated, self.layers[layer_index].activation))
            deltas[layer_index] = tuple(current_delta)

        updated_layers = []
        for layer, inputs, delta in zip(self.layers, layer_inputs, deltas):
            updated_weights = []
            for row, node_delta in zip(layer.weights, delta):
                updated_weights.append(tuple(weight - learning_rate * node_delta * value for weight, value in zip(row, inputs)))
            updated_biases = tuple(bias - learning_rate * node_delta for bias, node_delta in zip(layer.biases, delta))
            updated_layers.append(LayerParameters(tuple(updated_weights), updated_biases, layer.activation))
        self.layers = tuple(updated_layers)
        return loss

    def to_dict(self) -> Dict:
        return {
            "schema_version": NETWORK_SCHEMA_VERSION,
            "input_names": list(self.input_names),
            "output_names": list(self.output_names),
            "layers": [asdict(layer) for layer in self.layers],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, payload: Mapping) -> "NeuralNetwork":
        if payload.get("schema_version") != NETWORK_SCHEMA_VERSION:
            raise ValueError("Unsupported neural network schema version.")
        layers = tuple(
            LayerParameters(
                weights=tuple(tuple(float(value) for value in row) for row in layer["weights"]),
                biases=tuple(float(value) for value in layer["biases"]),
                activation=layer.get("activation", "tanh"),
            )
            for layer in payload["layers"]
        )
        return cls(payload["input_names"], payload["output_names"], layers)

    @classmethod
    def load(cls, path: Path) -> "NeuralNetwork":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _validate_shape(self) -> None:
        expected_inputs = len(self.input_names)
        for layer in self.layers:
            if len(layer.biases) != len(layer.weights):
                raise ValueError("Layer bias count must match weight row count.")
            if any(len(row) != expected_inputs for row in layer.weights):
                raise ValueError("Layer input width does not match previous layer output width.")
            expected_inputs = len(layer.biases)
        if expected_inputs != len(self.output_names):
            raise ValueError("Final layer width must match output_names.")

    def _coerce_input(self, vector: EncodedVector | Mapping[str, float] | Sequence[float]) -> Tuple[float, ...]:
        if isinstance(vector, EncodedVector):
            if vector.feature_names != self.input_names:
                raise ValueError("EncodedVector feature names do not match network inputs.")
            return vector.values
        if isinstance(vector, Mapping):
            return tuple(float(vector[name]) for name in self.input_names)
        values = tuple(float(value) for value in vector)
        if len(values) != len(self.input_names):
            raise ValueError("Input vector length does not match network inputs.")
        return values

    def _coerce_target(self, target: Mapping[str, float] | Sequence[float]) -> Tuple[float, ...]:
        if isinstance(target, Mapping):
            values = tuple(float(target[name]) for name in self.output_names)
        else:
            values = tuple(float(value) for value in target)
        if len(values) != len(self.output_names):
            raise ValueError("Target vector length does not match network outputs.")
        return values


def batch_predict(network: NeuralNetwork, vectors: Iterable[EncodedVector]) -> Tuple[Prediction, ...]:
    return tuple(network.predict(vector) for vector in vectors)
