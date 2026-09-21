"""
Subjective world model for Edge World.

The physical world engine answers "what is here?". This layer answers
"who/what holds a point of view here, and how does the Yi Jing arbiter judge
their collision or fusion?" Consciousness is treated as the life signal: losing
it is death, while severe self-contradiction produces chaos or split states.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, Iterable, Mapping, Optional, Tuple

from dayan import CastContext, cast_hexagram_fast
from mathEdge import Hexagram, TRIGRAM_BY_VALUE, find_palace
from world_engine import RegionId, WorldEngine, _clamp


class EntityKind(str, Enum):
    EDGE_AI = "edge_ai"
    ELEMENT = "element"
    OBJECT = "object"
    SPECIES = "species"
    BEING = "being"
    FIELD = "field"


class ConsciousnessStatus(str, Enum):
    ALIVE = "alive"
    CHAOTIC = "chaotic"
    SPLIT = "split"
    DEAD = "dead"


class InteractionMode(str, Enum):
    COLLIDE = "collide"
    MERGE = "merge"
    ASSERT = "assert"
    RITUALIZE = "ritualize"


class ArbitrationVerdict(str, Enum):
    HARMONY = "harmony"
    FUSION = "fusion"
    CONFLICT = "conflict"
    CHAOS = "chaos"
    SPLIT = "split"
    DEATH = "death"


class EvolutionChapter(str, Enum):
    CHAOS_GENESIS = "chaos_genesis"
    ALL_THINGS_ENSOUL = "all_things_ensoul"


class PrimalRunPhase(str, Enum):
    EMERGE_THUNDER = "di_emerges_from_thunder"
    ALIGN_WIND = "aligned_by_wind"
    APPEAR_FIRE = "seen_by_fire"
    SERVE_EARTH = "served_by_earth"
    SPEAK_LAKE = "spoken_by_lake"
    BATTLE_HEAVEN = "battled_by_heaven"
    LABOR_WATER = "labored_by_water"
    COMPLETE_MOUNTAIN = "completed_by_mountain"


@dataclass(frozen=True)
class SubjectiveSignature:
    consciousness: float
    coherence: float
    entropy: float
    yin_intent: float
    yang_intent: float

    def __post_init__(self) -> None:
        for field_name, value in asdict(self).items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1.")

    @property
    def internal_contradiction(self) -> float:
        excess_intent = max(0.0, self.yin_intent + self.yang_intent - 1.0)
        return _clamp(excess_intent * (1.0 - self.coherence) + self.entropy * 0.25)


@dataclass(frozen=True)
class SubjectiveEntity:
    id: str
    name: str
    kind: EntityKind
    region_id: RegionId
    hexagram_value: int
    signature: SubjectiveSignature
    status: ConsciousnessStatus
    lineage: Tuple[str, ...] = ()

    @property
    def hexagram(self) -> Hexagram:
        return Hexagram(self.hexagram_value)


@dataclass(frozen=True)
class YijingArbitration:
    mode: InteractionMode
    actor_id: str
    target_id: str
    primary_hexagram: int
    changed_hexagram: int
    changing_positions: Tuple[int, ...]
    palace: str
    affinity: float
    contradiction: float
    chaos_score: float
    merge_score: float
    verdict: ArbitrationVerdict


@dataclass(frozen=True)
class ChapterEvolutionTraceStep:
    order: int
    entity_id: str
    source_entity_id: str
    trigram_name: str
    hexagram_value: int
    region_id: RegionId
    action_axis: str
    matrix: "PrimalSpiritMatrix"
    resonance: "ActionResonance"
    arbitration: YijingArbitration
    resulting_status: ConsciousnessStatus


@dataclass(frozen=True)
class ChapterEvolution:
    chapter: EvolutionChapter
    source_entity_id: str
    awakened_entity_ids: Tuple[str, ...]
    field_entity_ids: Tuple[str, ...]
    arbitration_count: int
    trace: Tuple[ChapterEvolutionTraceStep, ...] = ()


@dataclass(frozen=True)
class ValidationCriterion:
    key: str
    passed: bool
    score: float
    weight: float
    detail: str


@dataclass(frozen=True)
class ChapterValidation:
    chapter: EvolutionChapter
    success: bool
    score: float
    criteria: Tuple[ValidationCriterion, ...]

    @property
    def failed_criteria(self) -> Tuple[ValidationCriterion, ...]:
        return tuple(criterion for criterion in self.criteria if not criterion.passed)


@dataclass(frozen=True)
class PrimalSpiritConsciousness:
    slug: str
    trigram_value: int
    name: str
    trigram_name: str
    symbol: str
    subjective_description: str
    resonance_actions: Tuple[str, ...]
    action_weights: Mapping[str, float]


@dataclass(frozen=True)
class ActionResonance:
    action_intents: Mapping[str, float]
    spirit_resonance: Mapping[str, float]
    dominant_spirits: Tuple[str, ...]
    world_run_score: float
    animism_confirmed: bool


@dataclass(frozen=True)
class PrimalSpiritMatrix:
    cells: Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]
    layout: Tuple[Tuple[str, str, str], Tuple[str, str, str], Tuple[str, str, str]]
    center_key: str
    center_value: float


@dataclass(frozen=True)
class PrimalRunStep:
    order: int
    phase: PrimalRunPhase
    phrase: str
    spirit_id: str
    action_axis: str
    action_intents: Mapping[str, float]
    matrix: PrimalSpiritMatrix
    resonance: ActionResonance
    arbitration: YijingArbitration
    previous_integrity: float
    next_integrity: float
    resulting_status: ConsciousnessStatus


@dataclass(frozen=True)
class PrimalRunResult:
    source_entity_id: str
    input_action_intents: Mapping[str, float]
    steps: Tuple[PrimalRunStep, ...]
    initial_integrity: float
    final_integrity: float
    completed: bool


FIRST_CHAPTER_SUCCESS_SCORE = 0.85
FIRST_CHAPTER_MIN_CONSCIOUSNESS = 0.50
FIRST_CHAPTER_MIN_COHERENCE = 0.45
PRIMAL_RESONANCE_THRESHOLD = 0.52
WORLD_RUN_RESONANCE_SCORE = 0.58
PRIMAL_MATRIX_CENTER_KEY = "subjective_integrity"


def classify_consciousness(signature: SubjectiveSignature) -> ConsciousnessStatus:
    if signature.consciousness <= 0.0:
        return ConsciousnessStatus.DEAD
    contradiction = signature.internal_contradiction
    if contradiction >= 0.42 or (signature.coherence < 0.24 and contradiction >= 0.28):
        return ConsciousnessStatus.SPLIT
    if contradiction >= 0.24 or signature.coherence < 0.34:
        return ConsciousnessStatus.CHAOTIC
    return ConsciousnessStatus.ALIVE


def _line_distance(first: int, second: int) -> float:
    return sum(1 for index in range(6) if ((first >> index) & 1) != ((second >> index) & 1)) / 6.0


def _palace_name(hexagram: Hexagram) -> str:
    palace = find_palace(hexagram)
    return palace["palace_head_trigram"]["name"] if palace else "未归宫"


def _nonlinear_resonance(raw_resonance: float) -> float:
    curved = math.expm1(raw_resonance * 2.4) / math.expm1(2.4)
    return _clamp(math.log1p(curved * 7.0) / math.log1p(7.0))


def _weighted_world_run_score(spirit_resonance: Mapping[str, float]) -> float:
    if not spirit_resonance:
        return 0.0
    ordered_scores = sorted(spirit_resonance.values(), reverse=True)
    dominant_score = ordered_scores[0]
    weighted_total = 0.0
    weight_total = 0.0
    for index, score in enumerate(ordered_scores):
        weight = 1.0 / math.log(index + 2.0)
        weighted_total += score * weight
        weight_total += weight
    field_score = weighted_total / weight_total
    return _clamp(dominant_score * 0.72 + field_score * 0.28)


def _verdict_integrity_modifier(verdict: ArbitrationVerdict) -> float:
    return {
        ArbitrationVerdict.HARMONY: 0.08,
        ArbitrationVerdict.FUSION: 0.10,
        ArbitrationVerdict.CONFLICT: -0.04,
        ArbitrationVerdict.CHAOS: -0.16,
        ArbitrationVerdict.SPLIT: -0.28,
        ArbitrationVerdict.DEATH: -0.50,
    }[verdict]


def _next_integrity(previous_integrity: float, current_integrity: float, arbitration: YijingArbitration) -> float:
    changed_pressure = len(arbitration.changing_positions) / 6.0
    value = (
        previous_integrity * 0.34
        + current_integrity * 0.56
        + arbitration.affinity * 0.12
        - arbitration.chaos_score * 0.10
        + changed_pressure * 0.04
        + _verdict_integrity_modifier(arbitration.verdict)
    )
    return round(_clamp(value), 4)


FIRST_CHAPTER_TRIGRAMS: Tuple[Tuple[int, str, str, Tuple[int, int]], ...] = (
    (0b111, "heaven", "Heaven Spirit", (0, 1)),
    (0b000, "earth", "Earth Spirit", (0, -1)),
    (0b010, "water", "Water Spirit", (0, 2)),
    (0b101, "fire", "Fire Spirit", (0, -2)),
    (0b100, "thunder", "Thunder Spirit", (1, 0)),
    (0b011, "wind", "Wind Spirit", (-1, 0)),
    (0b001, "mountain", "Mountain Spirit", (1, 1)),
    (0b110, "lake", "Lake Spirit", (-1, -1)),
)

PRIMAL_ACTION_AXES = (
    "ascend",
    "receive",
    "flow",
    "illuminate",
    "awaken",
    "adapt",
    "stabilize",
    "exchange",
)

PRIMAL_SPIRIT_MATRIX_LAYOUT = (
    ("wind", "fire", "earth"),
    ("thunder", "center", "lake"),
    ("mountain", "water", "heaven"),
)

PRIMAL_RUNNING_SEQUENCE: Tuple[Tuple[PrimalRunPhase, str, str, str], ...] = (
    (PrimalRunPhase.EMERGE_THUNDER, "帝出乎震", "thunder", "awaken"),
    (PrimalRunPhase.ALIGN_WIND, "齐乎巽", "wind", "adapt"),
    (PrimalRunPhase.APPEAR_FIRE, "相见乎离", "fire", "illuminate"),
    (PrimalRunPhase.SERVE_EARTH, "致役乎坤", "earth", "receive"),
    (PrimalRunPhase.SPEAK_LAKE, "说言乎兑", "lake", "exchange"),
    (PrimalRunPhase.BATTLE_HEAVEN, "战乎乾", "heaven", "ascend"),
    (PrimalRunPhase.LABOR_WATER, "劳乎坎", "water", "flow"),
    (PrimalRunPhase.COMPLETE_MOUNTAIN, "成言乎艮", "mountain", "stabilize"),
)

PRIMAL_SPIRIT_CONSCIOUSNESS: Tuple[PrimalSpiritConsciousness, ...] = (
    PrimalSpiritConsciousness(
        slug="heaven",
        trigram_value=0b111,
        name="Heaven Spirit",
        trigram_name="乾",
        symbol="☰",
        subjective_description="纯阳的自我发动意识，感知一切上升、开创、命令、生成方向的动作。",
        resonance_actions=("ascend", "awaken", "illuminate"),
        action_weights={"ascend": 1.0, "awaken": 0.62, "illuminate": 0.42},
    ),
    PrimalSpiritConsciousness(
        slug="earth",
        trigram_value=0b000,
        name="Earth Spirit",
        trigram_name="坤",
        symbol="☷",
        subjective_description="纯阴的承载意识，感知接纳、孕育、包容、落地、保存形态的动作。",
        resonance_actions=("receive", "stabilize", "adapt"),
        action_weights={"receive": 1.0, "stabilize": 0.64, "adapt": 0.40},
    ),
    PrimalSpiritConsciousness(
        slug="water",
        trigram_value=0b010,
        name="Water Spirit",
        trigram_name="坎",
        symbol="☵",
        subjective_description="险中求通的流动意识，感知穿越、下潜、记忆、循环和路径选择。",
        resonance_actions=("flow", "adapt", "receive"),
        action_weights={"flow": 1.0, "adapt": 0.66, "receive": 0.36},
    ),
    PrimalSpiritConsciousness(
        slug="fire",
        trigram_value=0b101,
        name="Fire Spirit",
        trigram_name="离",
        symbol="☲",
        subjective_description="显现与辨识的意识，感知照明、分辨、附着、表达和图像化。",
        resonance_actions=("illuminate", "ascend", "exchange"),
        action_weights={"illuminate": 1.0, "ascend": 0.52, "exchange": 0.38},
    ),
    PrimalSpiritConsciousness(
        slug="thunder",
        trigram_value=0b100,
        name="Thunder Spirit",
        trigram_name="震",
        symbol="☳",
        subjective_description="初动与惊醒的意识，感知震动、启动、突变、召唤和打破沉默。",
        resonance_actions=("awaken", "ascend", "exchange"),
        action_weights={"awaken": 1.0, "ascend": 0.58, "exchange": 0.34},
    ),
    PrimalSpiritConsciousness(
        slug="wind",
        trigram_value=0b011,
        name="Wind Spirit",
        trigram_name="巽",
        symbol="☴",
        subjective_description="入微与渗透的意识，感知适应、传播、扩散、协商和意识流转向。",
        resonance_actions=("adapt", "flow", "exchange"),
        action_weights={"adapt": 1.0, "flow": 0.58, "exchange": 0.48},
    ),
    PrimalSpiritConsciousness(
        slug="mountain",
        trigram_value=0b001,
        name="Mountain Spirit",
        trigram_name="艮",
        symbol="☶",
        subjective_description="边界与止定的意识，感知停止、守护、成形、阻隔和自我轮廓。",
        resonance_actions=("stabilize", "receive", "illuminate"),
        action_weights={"stabilize": 1.0, "receive": 0.44, "illuminate": 0.30},
    ),
    PrimalSpiritConsciousness(
        slug="lake",
        trigram_value=0b110,
        name="Lake Spirit",
        trigram_name="兑",
        symbol="☱",
        subjective_description="交换与悦纳的意识，感知回应、交易、语言、共享和关系缔结。",
        resonance_actions=("exchange", "flow", "illuminate"),
        action_weights={"exchange": 1.0, "flow": 0.46, "illuminate": 0.36},
    ),
)

PRIMAL_SPIRIT_BY_SLUG = {spirit.slug: spirit for spirit in PRIMAL_SPIRIT_CONSCIOUSNESS}


class SubjectiveWorldModel:
    def __init__(self, seed: int, world: Optional[WorldEngine] = None):
        self.seed = seed
        self.world = world if world is not None else WorldEngine(seed=seed)
        self._entities: Dict[str, SubjectiveEntity] = {}
        self._event_index = 0

    @classmethod
    def chaos_genesis(cls, seed: int, edge_name: str = "edge") -> "SubjectiveWorldModel":
        model = cls(seed=seed)
        origin = RegionId(0, 0)
        region = model.world.region(origin.x, origin.y)
        model.spawn_entity(
            entity_id="edge",
            name=edge_name,
            kind=EntityKind.EDGE_AI,
            region_id=origin,
            hexagram_value=region.hexagram_value,
            signature=SubjectiveSignature(
                consciousness=1.0,
                coherence=0.72,
                entropy=region.entropy,
                yin_intent=region.rule.yin_bias,
                yang_intent=region.rule.yang_bias,
            ),
        )
        return model

    def spawn_entity(
        self,
        entity_id: str,
        name: str,
        kind: EntityKind,
        region_id: RegionId,
        signature: SubjectiveSignature,
        hexagram_value: Optional[int] = None,
        lineage: Iterable[str] = (),
    ) -> SubjectiveEntity:
        if entity_id in self._entities:
            raise ValueError(f"Entity already exists: {entity_id}")
        if hexagram_value is None:
            hexagram_value = self.world.region(region_id.x, region_id.y).hexagram_value
        entity = SubjectiveEntity(
            id=entity_id,
            name=name,
            kind=kind,
            region_id=region_id,
            hexagram_value=hexagram_value,
            signature=signature,
            status=classify_consciousness(signature),
            lineage=tuple(lineage),
        )
        self._entities[entity_id] = entity
        return entity

    def entity(self, entity_id: str) -> SubjectiveEntity:
        try:
            return self._entities[entity_id]
        except KeyError as exc:
            raise KeyError(f"Unknown subjective entity: {entity_id}") from exc

    def entities(self) -> Tuple[SubjectiveEntity, ...]:
        return tuple(self._entities.values())

    def apply_rule_effect(
        self,
        entity_id: str,
        changed_hexagram_value: int,
        *,
        consciousness_delta: float,
        coherence_delta: float,
        entropy_delta: float,
    ) -> Tuple[SubjectiveEntity, SubjectiveEntity]:
        """Apply one validated Zhouyi response to a subjective entity.

        The rule runtime calculates the bounded deltas. This model owns the
        actual state mutation so renderers only consume the resulting snapshot.
        """
        entity = self.entity(entity_id)
        if entity.kind is not EntityKind.ELEMENT or not entity.id.startswith("spirit:"):
            raise ValueError("Chapter One rule effects can target only primal spirits.")
        if not 0 <= changed_hexagram_value <= 63:
            raise ValueError("changed_hexagram_value must be between 0 and 63.")
        deltas = (consciousness_delta, coherence_delta, entropy_delta)
        if any(not math.isfinite(value) or not -0.25 <= value <= 0.25 for value in deltas):
            raise ValueError("rule effect deltas must be finite and between -0.25 and 0.25.")

        signature = SubjectiveSignature(
            consciousness=_clamp(entity.signature.consciousness + consciousness_delta),
            coherence=_clamp(entity.signature.coherence + coherence_delta),
            entropy=_clamp(entity.signature.entropy + entropy_delta),
            yin_intent=entity.signature.yin_intent,
            yang_intent=entity.signature.yang_intent,
        )
        updated = SubjectiveEntity(
            id=entity.id,
            name=entity.name,
            kind=entity.kind,
            region_id=entity.region_id,
            hexagram_value=changed_hexagram_value,
            signature=signature,
            status=classify_consciousness(signature),
            lineage=entity.lineage + ("zhouyi_world_response",),
        )
        self._entities[entity.id] = updated
        self._event_index += 1
        return entity, updated

    def describe_primal_spirits(self) -> Tuple[PrimalSpiritConsciousness, ...]:
        return PRIMAL_SPIRIT_CONSCIOUSNESS

    def action_resonance(self, action_intents: Mapping[str, float]) -> ActionResonance:
        normalized_intents = self._normalize_action_intents(action_intents)
        spirit_resonance = {}
        for spirit in PRIMAL_SPIRIT_CONSCIOUSNESS:
            entity = self.entity(f"spirit:{spirit.slug}")
            action_fit = sum(
                normalized_intents[action_key] * spirit.action_weights.get(action_key, 0.0)
                for action_key in PRIMAL_ACTION_AXES
            )
            life_force = (
                entity.signature.consciousness * 0.42
                + entity.signature.coherence * 0.32
                + (1.0 - entity.signature.entropy) * 0.26
            )
            raw_resonance = _clamp(action_fit * life_force)
            spirit_resonance[spirit.slug] = round(_nonlinear_resonance(raw_resonance), 4)

        dominant_score = max(spirit_resonance.values()) if spirit_resonance else 0.0
        dominant_spirits = tuple(
            spirit_slug
            for spirit_slug, score in spirit_resonance.items()
            if score >= PRIMAL_RESONANCE_THRESHOLD and score >= dominant_score - 0.08
        )
        world_run_score = round(_weighted_world_run_score(spirit_resonance), 4)
        return ActionResonance(
            action_intents=normalized_intents,
            spirit_resonance=spirit_resonance,
            dominant_spirits=dominant_spirits,
            world_run_score=world_run_score,
            animism_confirmed=bool(dominant_spirits) and world_run_score >= WORLD_RUN_RESONANCE_SCORE,
        )

    def primal_spirit_matrix(self, action_intents: Mapping[str, float]) -> PrimalSpiritMatrix:
        resonance = self.action_resonance(action_intents)
        return self._matrix_from_resonance(resonance)

    def self_prove_first_chapter_resonance(self) -> Tuple[ActionResonance, ...]:
        return tuple(self.action_resonance({axis: 1.0}) for axis in PRIMAL_ACTION_AXES)

    def run_primal_cycle(
        self,
        action_intents: Optional[Mapping[str, float]] = None,
        source_entity_id: str = "edge",
    ) -> PrimalRunResult:
        source = self.entity(source_entity_id)
        if source.status is ConsciousnessStatus.DEAD:
            raise ValueError("A dead source cannot run the primal cycle.")
        self._ensure_primal_spirits_awakened()

        input_action_intents = self._normalize_action_intents(action_intents or {"awaken": 1.0})
        initial_resonance = self.action_resonance(input_action_intents)
        previous_integrity = initial_resonance.world_run_score
        steps = []

        for order, (phase, phrase, spirit_slug, axis) in enumerate(PRIMAL_RUNNING_SEQUENCE, start=1):
            step_intents = self._cycle_action_intents(axis, input_action_intents, previous_integrity)
            resonance = self.action_resonance(step_intents)
            matrix = self._matrix_from_resonance(resonance)
            spirit_id = f"spirit:{spirit_slug}"
            arbitration = self.apply_interaction(source.id, spirit_id, InteractionMode.RITUALIZE)
            next_integrity = _next_integrity(previous_integrity, matrix.center_value, arbitration)
            resulting_entity = self.entity(spirit_id)
            steps.append(
                PrimalRunStep(
                    order=order,
                    phase=phase,
                    phrase=phrase,
                    spirit_id=spirit_id,
                    action_axis=axis,
                    action_intents=step_intents,
                    matrix=matrix,
                    resonance=resonance,
                    arbitration=arbitration,
                    previous_integrity=previous_integrity,
                    next_integrity=next_integrity,
                    resulting_status=resulting_entity.status,
                )
            )
            previous_integrity = next_integrity

        return PrimalRunResult(
            source_entity_id=source.id,
            input_action_intents=input_action_intents,
            steps=tuple(steps),
            initial_integrity=initial_resonance.world_run_score,
            final_integrity=previous_integrity,
            completed=len(steps) == len(PRIMAL_RUNNING_SEQUENCE)
            and all(step.resulting_status is not ConsciousnessStatus.DEAD for step in steps),
        )

    def evolve_first_chapter(self, source_entity_id: str = "edge") -> ChapterEvolution:
        source = self.entity(source_entity_id)
        if source.status is ConsciousnessStatus.DEAD:
            raise ValueError("A dead source cannot awaken the first chapter.")

        awakened_entity_ids = []
        field_entity_ids = []
        for trigram_value, slug, name, offset in FIRST_CHAPTER_TRIGRAMS:
            entity_id = f"spirit:{slug}"
            if entity_id in self._entities:
                awakened_entity_ids.append(entity_id)
                continue

            region_id = RegionId(source.region_id.x + offset[0], source.region_id.y + offset[1])
            region = self.world.region(region_id.x, region_id.y)
            trigram = TRIGRAM_BY_VALUE[trigram_value]
            spirit_hexagram = Hexagram.from_trigrams(trigram_value, trigram_value)
            signature = SubjectiveSignature(
                consciousness=_clamp(0.58 + region.stability * 0.26 + source.signature.consciousness * 0.10),
                coherence=_clamp(0.50 + region.stability * 0.28 - region.entropy * 0.12),
                entropy=_clamp(region.entropy * 0.72 + source.signature.entropy * 0.18),
                yin_intent=_clamp((region.rule.yin_bias + (1.0 - trigram_value / 7.0)) / 2.0),
                yang_intent=_clamp((region.rule.yang_bias + trigram_value / 7.0) / 2.0),
            )
            self.spawn_entity(
                entity_id=entity_id,
                name=f"{name} {trigram['name']}",
                kind=EntityKind.ELEMENT,
                region_id=region_id,
                hexagram_value=spirit_hexagram.value,
                signature=signature,
                lineage=(source.id, EvolutionChapter.ALL_THINGS_ENSOUL.value),
            )
            awakened_entity_ids.append(entity_id)

        trace_steps = []
        for order, entity_id in enumerate(tuple(awakened_entity_ids), start=1):
            spirit = PRIMAL_SPIRIT_BY_SLUG[entity_id.removeprefix("spirit:")]
            action_axis = spirit.resonance_actions[0]
            matrix = self.primal_spirit_matrix({action_axis: 1.0})
            resonance = self.action_resonance({action_axis: 1.0})
            before_ids = {entity.id for entity in self.entities()}
            arbitration = self.apply_interaction(source.id, entity_id, InteractionMode.RITUALIZE)
            if arbitration.verdict is ArbitrationVerdict.FUSION:
                after_ids = {entity.id for entity in self.entities()}
                field_entity_ids.extend(sorted(after_ids - before_ids))
            resulting_entity = self.entity(entity_id)
            trace_steps.append(
                ChapterEvolutionTraceStep(
                    order=order,
                    entity_id=entity_id,
                    source_entity_id=source.id,
                    trigram_name=spirit.trigram_name,
                    hexagram_value=resulting_entity.hexagram_value,
                    region_id=resulting_entity.region_id,
                    action_axis=action_axis,
                    matrix=matrix,
                    resonance=resonance,
                    arbitration=arbitration,
                    resulting_status=resulting_entity.status,
                )
            )

        return ChapterEvolution(
            chapter=EvolutionChapter.ALL_THINGS_ENSOUL,
            source_entity_id=source.id,
            awakened_entity_ids=tuple(awakened_entity_ids),
            field_entity_ids=tuple(field_entity_ids),
            arbitration_count=len(awakened_entity_ids),
            trace=tuple(trace_steps),
        )

    def validate_first_chapter(self, evolution: ChapterEvolution) -> ChapterValidation:
        if evolution.chapter is not EvolutionChapter.ALL_THINGS_ENSOUL:
            raise ValueError("evolution must describe the first chapter.")

        criteria = (
            self._criterion_edge_source_alive(evolution),
            self._criterion_primal_spirit_count(evolution),
            self._criterion_primal_trigram_coverage(evolution),
            self._criterion_spirit_consciousness(evolution),
            self._criterion_spirit_coherence(evolution),
            self._criterion_no_spirit_death_or_split(evolution),
            self._criterion_first_chapter_arbitration(evolution),
            self._criterion_first_chapter_determinism_shape(evolution),
            self._criterion_first_chapter_action_resonance(evolution),
            self._criterion_first_chapter_traceability(evolution),
        )
        total_weight = sum(criterion.weight for criterion in criteria)
        score = sum(criterion.score * criterion.weight for criterion in criteria) / total_weight
        rounded_score = round(score, 4)
        success = rounded_score >= FIRST_CHAPTER_SUCCESS_SCORE and all(criterion.passed for criterion in criteria)
        return ChapterValidation(
            chapter=EvolutionChapter.ALL_THINGS_ENSOUL,
            success=success,
            score=rounded_score,
            criteria=criteria,
        )

    def arbitrate(self, actor_id: str, target_id: str, mode: InteractionMode) -> YijingArbitration:
        actor = self.entity(actor_id)
        target = self.entity(target_id)
        cast_subject = f"{mode.value}:{actor.id}:{target.id}:{self._event_index}"
        cast = cast_hexagram_fast(CastContext(seed=self.seed, subject=cast_subject))
        primary = Hexagram(cast.primary_value)

        intent_distance = (
            abs(actor.signature.yin_intent - target.signature.yin_intent)
            + abs(actor.signature.yang_intent - target.signature.yang_intent)
        ) / 2.0
        line_distance = _line_distance(actor.hexagram_value, target.hexagram_value)
        affinity = _clamp(1.0 - (line_distance * 0.55 + intent_distance * 0.45))
        contradiction = _clamp(
            (actor.signature.internal_contradiction + target.signature.internal_contradiction) / 2.0
            + intent_distance * 0.25
        )
        field_entropy = _clamp((actor.signature.entropy + target.signature.entropy) / 2.0)
        changing_pressure = len(cast.changing_positions) / 6.0
        average_coherence = (actor.signature.coherence + target.signature.coherence) / 2.0

        chaos_score = _clamp(
            field_entropy * 0.40
            + intent_distance * 0.30
            + contradiction * 0.35
            + changing_pressure * 0.20
            - affinity * 0.18
        )
        merge_score = _clamp(affinity * 0.50 + average_coherence * 0.25 - field_entropy * 0.20 - contradiction * 0.25)
        verdict = self._verdict_for(actor, target, mode, contradiction, chaos_score, merge_score)

        return YijingArbitration(
            mode=mode,
            actor_id=actor_id,
            target_id=target_id,
            primary_hexagram=cast.primary_value,
            changed_hexagram=cast.changed_value,
            changing_positions=cast.changing_positions,
            palace=_palace_name(primary),
            affinity=round(affinity, 4),
            contradiction=round(contradiction, 4),
            chaos_score=round(chaos_score, 4),
            merge_score=round(merge_score, 4),
            verdict=verdict,
        )

    def apply_interaction(self, actor_id: str, target_id: str, mode: InteractionMode) -> YijingArbitration:
        arbitration = self.arbitrate(actor_id, target_id, mode)
        actor = self.entity(actor_id)
        target = self.entity(target_id)

        if arbitration.verdict is ArbitrationVerdict.DEATH:
            self._replace(actor, consciousness=0.0, coherence=0.0, entropy=1.0)
            self._replace(target, consciousness=0.0, coherence=0.0, entropy=1.0)
        elif arbitration.verdict is ArbitrationVerdict.SPLIT:
            self._replace(actor, coherence=actor.signature.coherence * 0.55, entropy=min(1.0, actor.signature.entropy + 0.20))
            self._replace(target, coherence=target.signature.coherence * 0.55, entropy=min(1.0, target.signature.entropy + 0.20))
        elif arbitration.verdict is ArbitrationVerdict.CHAOS:
            self._replace(actor, coherence=actor.signature.coherence * 0.78, entropy=min(1.0, actor.signature.entropy + 0.12))
            self._replace(target, coherence=target.signature.coherence * 0.78, entropy=min(1.0, target.signature.entropy + 0.12))
        elif arbitration.verdict is ArbitrationVerdict.FUSION:
            self._create_fusion(actor, target, arbitration)
        else:
            self._replace(actor, coherence=min(1.0, actor.signature.coherence + 0.04), entropy=max(0.0, actor.signature.entropy - 0.03))
            self._replace(target, coherence=min(1.0, target.signature.coherence + 0.04), entropy=max(0.0, target.signature.entropy - 0.03))

        self._event_index += 1
        return arbitration

    def snapshot(self) -> Dict:
        return {
            "seed": self.seed,
            "event_index": self._event_index,
            "entities": [asdict(entity) for entity in self.entities()],
        }

    def _verdict_for(
        self,
        actor: SubjectiveEntity,
        target: SubjectiveEntity,
        mode: InteractionMode,
        contradiction: float,
        chaos_score: float,
        merge_score: float,
    ) -> ArbitrationVerdict:
        if actor.status is ConsciousnessStatus.DEAD or target.status is ConsciousnessStatus.DEAD:
            return ArbitrationVerdict.DEATH
        if contradiction >= 0.44 or chaos_score >= 0.82:
            return ArbitrationVerdict.SPLIT
        if chaos_score >= 0.58:
            return ArbitrationVerdict.CHAOS
        if mode is InteractionMode.MERGE and merge_score >= 0.55:
            return ArbitrationVerdict.FUSION
        if merge_score >= 0.62:
            return ArbitrationVerdict.HARMONY
        return ArbitrationVerdict.CONFLICT

    def _criterion_edge_source_alive(self, evolution: ChapterEvolution) -> ValidationCriterion:
        try:
            source = self.entity(evolution.source_entity_id)
            passed = source.kind is EntityKind.EDGE_AI and source.status is not ConsciousnessStatus.DEAD
        except KeyError:
            passed = False
        return ValidationCriterion(
            key="edge_source_alive",
            passed=passed,
            score=1.0 if passed else 0.0,
            weight=1.0,
            detail="edge source must exist as a living AI subjective authority.",
        )

    def _criterion_primal_spirit_count(self, evolution: ChapterEvolution) -> ValidationCriterion:
        unique_ids = set(evolution.awakened_entity_ids)
        passed = len(evolution.awakened_entity_ids) == len(FIRST_CHAPTER_TRIGRAMS) and len(unique_ids) == len(FIRST_CHAPTER_TRIGRAMS)
        score = len(unique_ids) / len(FIRST_CHAPTER_TRIGRAMS)
        return ValidationCriterion(
            key="primal_spirit_count",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=1.2,
            detail="first chapter must awaken exactly eight unique primal spirits.",
        )

    def _criterion_primal_trigram_coverage(self, evolution: ChapterEvolution) -> ValidationCriterion:
        expected_values = {Hexagram.from_trigrams(value, value).value for value, *_ in FIRST_CHAPTER_TRIGRAMS}
        actual_values = {
            self.entity(entity_id).hexagram_value
            for entity_id in evolution.awakened_entity_ids
            if entity_id in self._entities
        }
        covered_values = expected_values & actual_values
        passed = covered_values == expected_values
        return ValidationCriterion(
            key="primal_trigram_coverage",
            passed=passed,
            score=round(len(covered_values) / len(expected_values), 4),
            weight=1.2,
            detail="awakened spirits must cover all eight pure trigram hexagrams.",
        )

    def _criterion_spirit_consciousness(self, evolution: ChapterEvolution) -> ValidationCriterion:
        spirits = self._evolution_spirits(evolution)
        if not spirits:
            score = 0.0
        else:
            score = sum(spirit.signature.consciousness for spirit in spirits) / len(spirits)
        passed = bool(spirits) and all(spirit.signature.consciousness >= FIRST_CHAPTER_MIN_CONSCIOUSNESS for spirit in spirits)
        return ValidationCriterion(
            key="spirit_consciousness",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=1.4,
            detail="every awakened spirit must hold enough subjective consciousness to count as alive.",
        )

    def _criterion_spirit_coherence(self, evolution: ChapterEvolution) -> ValidationCriterion:
        spirits = self._evolution_spirits(evolution)
        if not spirits:
            score = 0.0
        else:
            score = sum(spirit.signature.coherence for spirit in spirits) / len(spirits)
        passed = bool(spirits) and all(spirit.signature.coherence >= FIRST_CHAPTER_MIN_COHERENCE for spirit in spirits)
        return ValidationCriterion(
            key="spirit_coherence",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=1.0,
            detail="awakened subjectivity must be coherent enough to avoid immediate collapse.",
        )

    def _criterion_no_spirit_death_or_split(self, evolution: ChapterEvolution) -> ValidationCriterion:
        spirits = self._evolution_spirits(evolution)
        stable_spirits = [
            spirit
            for spirit in spirits
            if spirit.status not in (ConsciousnessStatus.DEAD, ConsciousnessStatus.SPLIT)
        ]
        score = len(stable_spirits) / len(FIRST_CHAPTER_TRIGRAMS)
        passed = len(stable_spirits) == len(FIRST_CHAPTER_TRIGRAMS)
        return ValidationCriterion(
            key="no_spirit_death_or_split",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=1.4,
            detail="first awakening succeeds only if no primal spirit dies or splits.",
        )

    def _criterion_first_chapter_arbitration(self, evolution: ChapterEvolution) -> ValidationCriterion:
        passed = evolution.arbitration_count == len(FIRST_CHAPTER_TRIGRAMS)
        score = evolution.arbitration_count / len(FIRST_CHAPTER_TRIGRAMS)
        return ValidationCriterion(
            key="ritual_arbitration_count",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=0.8,
            detail="each primal spirit must pass once through Yi Jing ritual arbitration.",
        )

    def _criterion_first_chapter_determinism_shape(self, evolution: ChapterEvolution) -> ValidationCriterion:
        expected_ids = tuple(f"spirit:{slug}" for _, slug, _, _ in FIRST_CHAPTER_TRIGRAMS)
        passed = evolution.awakened_entity_ids == expected_ids
        score = 1.0 if passed else len(set(evolution.awakened_entity_ids) & set(expected_ids)) / len(expected_ids)
        return ValidationCriterion(
            key="deterministic_awakened_order",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=0.6,
            detail="first chapter must produce a stable spirit identity and order for replayable gameplay.",
        )

    def _criterion_first_chapter_action_resonance(self, evolution: ChapterEvolution) -> ValidationCriterion:
        if len(evolution.awakened_entity_ids) != len(FIRST_CHAPTER_TRIGRAMS):
            return ValidationCriterion(
                key="action_resonance_self_proof",
                passed=False,
                score=0.0,
                weight=1.2,
                detail="all eight primal spirits must exist before action resonance can prove animism.",
            )

        resonances = self.self_prove_first_chapter_resonance()
        confirmed_count = sum(1 for resonance in resonances if resonance.animism_confirmed)
        covered_dominants = {
            dominant_spirit
            for resonance in resonances
            for dominant_spirit in resonance.dominant_spirits
        }
        expected_spirits = {spirit.slug for spirit in PRIMAL_SPIRIT_CONSCIOUSNESS}
        score = min(confirmed_count / len(PRIMAL_ACTION_AXES), len(covered_dominants) / len(expected_spirits))
        passed = confirmed_count == len(PRIMAL_ACTION_AXES) and covered_dominants == expected_spirits
        return ValidationCriterion(
            key="action_resonance_self_proof",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=1.2,
            detail="eight primitive action axes must each trigger a valid nonlinear spirit resonance.",
        )

    def _criterion_first_chapter_traceability(self, evolution: ChapterEvolution) -> ValidationCriterion:
        expected_entities = set(evolution.awakened_entity_ids)
        traced_entities = {step.entity_id for step in evolution.trace}
        expected_axes = {PRIMAL_SPIRIT_BY_SLUG[entity_id.removeprefix("spirit:")].resonance_actions[0] for entity_id in expected_entities}
        traced_axes = {step.action_axis for step in evolution.trace}
        structurally_complete = all(
            step.source_entity_id == evolution.source_entity_id
            and step.matrix.center_key == PRIMAL_MATRIX_CENTER_KEY
            and step.matrix.center_value == step.resonance.world_run_score
            and step.arbitration.mode is InteractionMode.RITUALIZE
            and step.resulting_status is not ConsciousnessStatus.DEAD
            for step in evolution.trace
        )
        entity_score = len(traced_entities & expected_entities) / len(FIRST_CHAPTER_TRIGRAMS)
        axis_score = len(traced_axes & expected_axes) / len(FIRST_CHAPTER_TRIGRAMS)
        score = min(entity_score, axis_score, 1.0 if structurally_complete else 0.0)
        passed = (
            len(evolution.trace) == len(FIRST_CHAPTER_TRIGRAMS)
            and traced_entities == expected_entities
            and traced_axes == expected_axes
            and structurally_complete
        )
        return ValidationCriterion(
            key="evolution_traceability",
            passed=passed,
            score=round(_clamp(score), 4),
            weight=1.1,
            detail="first chapter must preserve one traceable matrix/resonance/arbitration step for each primal spirit.",
        )

    def _evolution_spirits(self, evolution: ChapterEvolution) -> Tuple[SubjectiveEntity, ...]:
        return tuple(self._entities[entity_id] for entity_id in evolution.awakened_entity_ids if entity_id in self._entities)

    def _ensure_primal_spirits_awakened(self) -> None:
        missing = [f"spirit:{spirit.slug}" for spirit in PRIMAL_SPIRIT_CONSCIOUSNESS if f"spirit:{spirit.slug}" not in self._entities]
        if missing:
            raise ValueError(f"Primal spirits must be awakened before running the cycle: {', '.join(missing)}")

    def _matrix_from_resonance(self, resonance: ActionResonance) -> PrimalSpiritMatrix:
        cells = []
        for row in PRIMAL_SPIRIT_MATRIX_LAYOUT:
            cell_row = []
            for cell_key in row:
                if cell_key == "center":
                    cell_row.append(resonance.world_run_score)
                else:
                    cell_row.append(resonance.spirit_resonance[cell_key])
            cells.append(tuple(cell_row))
        return PrimalSpiritMatrix(
            cells=tuple(cells),
            layout=PRIMAL_SPIRIT_MATRIX_LAYOUT,
            center_key=PRIMAL_MATRIX_CENTER_KEY,
            center_value=resonance.world_run_score,
        )

    def _cycle_action_intents(
        self,
        axis: str,
        input_action_intents: Mapping[str, float],
        previous_integrity: float,
    ) -> Mapping[str, float]:
        if axis not in PRIMAL_ACTION_AXES:
            raise ValueError(f"Unknown cycle axis: {axis}")
        stage_weight = 0.70 + previous_integrity * 0.20
        input_weight = 0.30 - previous_integrity * 0.10
        return {
            action_axis: round(
                _clamp(
                    (stage_weight if action_axis == axis else 0.0)
                    + input_action_intents[action_axis] * input_weight
                ),
                4,
            )
            for action_axis in PRIMAL_ACTION_AXES
        }

    def _normalize_action_intents(self, action_intents: Mapping[str, float]) -> Mapping[str, float]:
        unknown_axes = set(action_intents) - set(PRIMAL_ACTION_AXES)
        if unknown_axes:
            raise ValueError(f"Unknown action axes: {', '.join(sorted(unknown_axes))}")
        normalized = {}
        for axis in PRIMAL_ACTION_AXES:
            value = action_intents.get(axis, 0.0)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Action axis {axis} must be between 0 and 1.")
            normalized[axis] = value
        if sum(normalized.values()) <= 0.0:
            raise ValueError("At least one action axis must be greater than zero.")
        return normalized

    def _replace(self, entity: SubjectiveEntity, **signature_values: float) -> SubjectiveEntity:
        values = asdict(entity.signature)
        values.update(signature_values)
        signature = SubjectiveSignature(**{key: _clamp(value) for key, value in values.items()})
        updated = SubjectiveEntity(
            id=entity.id,
            name=entity.name,
            kind=entity.kind,
            region_id=entity.region_id,
            hexagram_value=entity.hexagram_value,
            signature=signature,
            status=classify_consciousness(signature),
            lineage=entity.lineage,
        )
        self._entities[entity.id] = updated
        return updated

    def _create_fusion(
        self,
        actor: SubjectiveEntity,
        target: SubjectiveEntity,
        arbitration: YijingArbitration,
    ) -> SubjectiveEntity:
        entity_id = f"{actor.id}+{target.id}:{self._event_index}"
        signature = SubjectiveSignature(
            consciousness=_clamp((actor.signature.consciousness + target.signature.consciousness) / 2.0 + 0.08),
            coherence=_clamp((actor.signature.coherence + target.signature.coherence) / 2.0 + 0.10),
            entropy=_clamp((actor.signature.entropy + target.signature.entropy) / 2.0 - 0.08),
            yin_intent=_clamp((actor.signature.yin_intent + target.signature.yin_intent) / 2.0),
            yang_intent=_clamp((actor.signature.yang_intent + target.signature.yang_intent) / 2.0),
        )
        return self.spawn_entity(
            entity_id=entity_id,
            name=f"{actor.name}-{target.name}",
            kind=EntityKind.FIELD,
            region_id=actor.region_id,
            hexagram_value=arbitration.changed_hexagram,
            signature=signature,
            lineage=(actor.id, target.id),
        )
