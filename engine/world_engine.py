"""
Edge World - deterministic world model prototype.

This module turns the mathEdge hexagram primitives into a small, testable world
engine layer: 64 macro regions, per-region terrain rules, deterministic tile
sampling, four-phase time, and simple entropy accumulation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from mathEdge import Hexagram, find_palace


class Era(str, Enum):
    ZHOU = "zhou"
    LIANXIAN = "lianxian"
    MIESHI = "mieshi"


class TimePhase(str, Enum):
    SHAOYANG = "shaoyang"
    TAIYANG = "taiyang"
    SHAOYIN = "shaoyin"
    TAIYIN = "taiyin"


@dataclass(frozen=True)
class TerrainRule:
    base_height: float
    roughness: float
    feature_scale: float
    moisture: float
    temperature: float
    yin_bias: float
    yang_bias: float
    entropy_bias: float
    biome_hint: str


@dataclass(frozen=True)
class RegionId:
    x: int
    y: int


@dataclass(frozen=True)
class RegionState:
    id: RegionId
    hexagram_value: int
    upper_trigram: str
    lower_trigram: str
    palace: str
    rule: TerrainRule
    entropy: float
    stability: float


@dataclass(frozen=True)
class WorldTile:
    region_id: RegionId
    local_x: int
    local_y: int
    hexagram_value: int
    height: float
    moisture: float
    temperature: float
    yin_qi: float
    yang_qi: float
    entropy: float
    biome: str


@dataclass
class WorldClock:
    era: Era = Era.ZHOU
    cycle: int = 0
    phase: TimePhase = TimePhase.SHAOYANG
    phase_progress: float = 0.0

    def advance(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Clock advance amount must be non-negative.")
        total = self.phase_progress + amount
        phase_steps = int(total)
        self.phase_progress = total - phase_steps
        phases = list(TimePhase)
        current_index = phases.index(self.phase)
        next_index = current_index + phase_steps
        self.cycle += next_index // len(phases)
        self.phase = phases[next_index % len(phases)]


TRIGRAM_TERRAIN: Dict[int, TerrainRule] = {
    0b000: TerrainRule(0.15, 0.15, 0.20, 0.50, 0.45, 0.70, 0.30, 0.06, "plain"),
    0b001: TerrainRule(0.70, 0.75, 0.45, 0.35, 0.35, 0.58, 0.42, 0.10, "mountain"),
    0b010: TerrainRule(0.05, 0.45, 0.35, 0.88, 0.25, 0.66, 0.34, 0.14, "water"),
    0b011: TerrainRule(0.32, 0.35, 0.70, 0.45, 0.55, 0.44, 0.56, 0.09, "wind_hill"),
    0b100: TerrainRule(0.42, 0.82, 0.62, 0.42, 0.52, 0.36, 0.64, 0.18, "rift"),
    0b101: TerrainRule(0.55, 0.52, 0.40, 0.18, 0.88, 0.30, 0.70, 0.16, "volcanic"),
    0b110: TerrainRule(0.18, 0.25, 0.36, 0.78, 0.48, 0.54, 0.46, 0.08, "wetland"),
    0b111: TerrainRule(0.88, 0.42, 0.55, 0.22, 0.32, 0.24, 0.76, 0.12, "highland"),
}

PHASE_MODIFIERS: Dict[TimePhase, Tuple[float, float, float]] = {
    TimePhase.SHAOYANG: (0.05, 0.08, -0.02),
    TimePhase.TAIYANG: (0.08, -0.04, 0.04),
    TimePhase.SHAOYIN: (-0.03, 0.02, 0.06),
    TimePhase.TAIYIN: (-0.08, 0.04, 0.10),
}

ERA_ENTROPY = {
    Era.ZHOU: 0.00,
    Era.LIANXIAN: 0.06,
    Era.MIESHI: 0.18,
}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _noise(seed: int, *coords: int) -> float:
    key = ":".join([str(seed), *map(str, coords)]).encode("utf-8")
    digest = hashlib.blake2b(key, digest_size=8).digest()
    raw = int.from_bytes(digest, "big") / ((1 << 64) - 1)
    return raw * 2.0 - 1.0


def blend_rules(lower: TerrainRule, upper: TerrainRule) -> TerrainRule:
    return TerrainRule(
        base_height=_lerp(lower.base_height, upper.base_height, 0.35),
        roughness=_lerp(lower.roughness, upper.roughness, 0.50),
        feature_scale=_lerp(lower.feature_scale, upper.feature_scale, 0.45),
        moisture=_lerp(lower.moisture, upper.moisture, 0.40),
        temperature=_lerp(lower.temperature, upper.temperature, 0.40),
        yin_bias=_lerp(lower.yin_bias, upper.yin_bias, 0.45),
        yang_bias=_lerp(lower.yang_bias, upper.yang_bias, 0.45),
        entropy_bias=_lerp(lower.entropy_bias, upper.entropy_bias, 0.55),
        biome_hint=f"{lower.biome_hint}+{upper.biome_hint}",
    )


def classify_biome(height: float, moisture: float, temperature: float, entropy: float, hint: str) -> str:
    if entropy > 0.78:
        return "chaos_waste"
    if height > 0.78:
        return "sky_mountain"
    if height < 0.18 and moisture > 0.70:
        return "deep_water"
    if temperature > 0.72 and moisture < 0.34:
        return "scorched_desert"
    if moisture > 0.70:
        return "wetland"
    if "mountain" in hint and height > 0.55:
        return "mountain"
    if "volcanic" in hint and temperature > 0.62:
        return "volcanic_highland"
    if moisture > 0.48 and temperature > 0.45:
        return "fertile_plain"
    return "open_field"


class WorldEngine:
    def __init__(self, seed: int, era: Era = Era.ZHOU, region_size: int = 32):
        if region_size <= 0:
            raise ValueError("region_size must be positive.")
        self.seed = seed
        self.region_size = region_size
        self.clock = WorldClock(era=era)
        self._regions: Dict[Tuple[int, int], RegionState] = {}

    def hexagram_for_region(self, region_id: RegionId) -> Hexagram:
        value = ((region_id.y & 0b111) << 3) | (region_id.x & 0b111)
        return Hexagram(value)

    def region(self, x: int, y: int) -> RegionState:
        key = (x, y)
        if key not in self._regions:
            region_id = RegionId(x, y)
            hexagram = self.hexagram_for_region(region_id)
            lower_rule = TRIGRAM_TERRAIN[hexagram.lower["value"]]
            upper_rule = TRIGRAM_TERRAIN[hexagram.upper["value"]]
            rule = blend_rules(lower_rule, upper_rule)
            palace = find_palace(hexagram)
            palace_name = palace["palace_head_trigram"]["name"] if palace else "未归宫"
            base_entropy = _clamp(rule.entropy_bias + ERA_ENTROPY[self.clock.era])
            stability = _clamp(1.0 - base_entropy - abs(rule.yin_bias - rule.yang_bias) * 0.2)
            self._regions[key] = RegionState(
                id=region_id,
                hexagram_value=hexagram.value,
                upper_trigram=hexagram.upper["name"],
                lower_trigram=hexagram.lower["name"],
                palace=palace_name,
                rule=rule,
                entropy=base_entropy,
                stability=stability,
            )
        return self._regions[key]

    def tile(self, world_x: int, world_y: int) -> WorldTile:
        region_x = math.floor(world_x / self.region_size)
        region_y = math.floor(world_y / self.region_size)
        local_x = world_x - region_x * self.region_size
        local_y = world_y - region_y * self.region_size
        region = self.region(region_x, region_y)
        phase_height, phase_moisture, phase_entropy = PHASE_MODIFIERS[self.clock.phase]

        coarse = _noise(self.seed, region_x, region_y, local_x // 4, local_y // 4)
        fine = _noise(self.seed + 17, world_x, world_y)
        terrain_noise = coarse * 0.70 + fine * 0.30

        height = _clamp(region.rule.base_height + terrain_noise * region.rule.roughness * 0.22 + phase_height)
        moisture = _clamp(region.rule.moisture + _noise(self.seed + 29, world_x, world_y) * 0.18 + phase_moisture)
        temperature = _clamp(region.rule.temperature + _noise(self.seed + 41, world_x, world_y) * 0.14 - height * 0.12)
        entropy = _clamp(region.entropy + abs(fine) * 0.08 + phase_entropy)
        yin_qi = _clamp(region.rule.yin_bias * (1.0 - entropy * 0.25) + moisture * 0.20)
        yang_qi = _clamp(region.rule.yang_bias * (1.0 - entropy * 0.20) + temperature * 0.18)
        energy_total = yin_qi + yang_qi
        if energy_total > 1.0:
            yin_qi /= energy_total
            yang_qi /= energy_total

        return WorldTile(
            region_id=region.id,
            local_x=local_x,
            local_y=local_y,
            hexagram_value=region.hexagram_value,
            height=round(height, 4),
            moisture=round(moisture, 4),
            temperature=round(temperature, 4),
            yin_qi=round(yin_qi, 4),
            yang_qi=round(yang_qi, 4),
            entropy=round(entropy, 4),
            biome=classify_biome(height, moisture, temperature, entropy, region.rule.biome_hint),
        )

    def sample_region_tiles(self, region_x: int, region_y: int, step: int = 8) -> List[WorldTile]:
        if step <= 0:
            raise ValueError("step must be positive.")
        tiles = []
        origin_x = region_x * self.region_size
        origin_y = region_y * self.region_size
        for y in range(0, self.region_size, step):
            for x in range(0, self.region_size, step):
                tiles.append(self.tile(origin_x + x, origin_y + y))
        return tiles

    def export_region_summary(self, path: Path, region_ids: Iterable[RegionId]) -> None:
        payload = {
            "seed": self.seed,
            "era": self.clock.era.value,
            "phase": self.clock.phase.value,
            "regions": [asdict(self.region(region_id.x, region_id.y)) for region_id in region_ids],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    engine = WorldEngine(seed=20260620, era=Era.ZHOU)
    regions = [engine.region(x, y) for y in range(2) for x in range(2)]
    tiles = [engine.tile(x, y) for x, y in [(0, 0), (7, 11), (32, 0), (39, 47)]]
    print("REGIONS")
    for region in regions:
        print(asdict(region))
    print("TILES")
    for tile in tiles:
        print(asdict(tile))
