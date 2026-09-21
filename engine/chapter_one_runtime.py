"""Rule-gated Chapter One runtime with an optional local Ollama decision source."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional

from mathEdge import Hexagram, TRIGRAMS
from snapshot_store import SNAPSHOT_SCHEMA_VERSION, write_snapshot_atomic
from subjective_world import PRIMAL_ACTION_AXES, SubjectiveWorldModel


DECISION_SCHEMA_VERSION = "edgeworld.chapter-one-decision.v2"
DEFAULT_ACTION_INTENTS = {"awaken": 1.0, "stabilize": 0.35}

ACTION_TO_SPIRIT = {
    "ascend": "heaven", "receive": "earth", "flow": "water", "illuminate": "fire",
    "awaken": "thunder", "adapt": "wind", "stabilize": "mountain", "exchange": "lake",
}
SPIRIT_TO_TRIGRAM_KEY = {
    "heaven": "qian", "earth": "kun", "water": "kan", "fire": "li",
    "thunder": "zhen", "wind": "xun", "mountain": "gen", "lake": "dui",
}
SPIRIT_LABELS = {
    "heaven": "乾灵", "earth": "坤灵", "water": "坎灵", "fire": "离灵",
    "thunder": "震灵", "wind": "巽灵", "mountain": "艮灵", "lake": "兑灵",
}
XIANTIAN_SEQUENCE = ("heaven", "lake", "fire", "thunder", "wind", "water", "mountain", "earth")
XIANTIAN_DIRECTIONS = {
    "heaven": "S", "lake": "SE", "fire": "E", "thunder": "NE",
    "wind": "SW", "water": "W", "mountain": "NW", "earth": "N",
}
HOUTIAN_POSITIONS = {
    "water": {"direction": "N", "number": 1},
    "earth": {"direction": "SW", "number": 2},
    "thunder": {"direction": "E", "number": 3},
    "wind": {"direction": "SE", "number": 4},
    "heaven": {"direction": "NW", "number": 6},
    "lake": {"direction": "W", "number": 7},
    "mountain": {"direction": "NE", "number": 8},
    "fire": {"direction": "S", "number": 9},
}
ACTION_EFFECTS = {
    "ascend": ("升举", "lift"),
    "receive": ("承载", "settle"),
    "flow": ("流通", "circulate"),
    "illuminate": ("显明", "reveal"),
    "awaken": ("震发", "pulse"),
    "adapt": ("渗入", "drift"),
    "stabilize": ("止定", "anchor"),
    "exchange": ("感通", "resonate"),
}
EXPRESSION_AXIS_KEYWORDS = {
    "ascend": ("上升", "升起", "飞", "开创", "命令", "抬高"),
    "receive": ("接纳", "承载", "保存", "容纳", "孕育", "拾取"),
    "flow": ("流", "水", "河", "穿越", "下潜", "循环", "游"),
    "illuminate": ("火", "火焰", "燃烧", "照亮", "发光", "光芒", "显现"),
    "awaken": ("唤醒", "苏醒", "震动", "启动", "敲击", "召唤"),
    "adapt": ("渗透", "扩散", "适应", "传播", "风", "转向"),
    "stabilize": ("停止", "守护", "稳定", "固定", "成形", "阻挡"),
    "exchange": ("回应", "语言", "交谈", "交易", "交换", "共享"),
}
EXPRESSION_EVIDENCE_PRESSURE = 0.8
POSITIVE_OMEN_MARKERS = {"亨": 1, "吉": 2, "无咎": 1, "利": 1}
CAUTION_OMEN_MARKERS = {"凶": 3, "悔": 1, "吝": 1, "厉": 1, "灾": 2, "勿用": 2, "难": 1}


class DecisionError(ValueError):
    """Raised when a model proposal cannot cross the world-rule boundary."""


@dataclass(frozen=True)
class DevelopmentDecision:
    schema_version: str
    tick: int
    focus_spirit: str
    action_intents: Mapping[str, float]
    rationale: str


@dataclass(frozen=True)
class DecisionEnvelope:
    source: str
    model: str
    accepted: bool
    fallback_reason: Optional[str]
    decision: DevelopmentDecision


@dataclass(frozen=True)
class PlayerIntervention:
    action_axis: str
    intensity: float
    expression: str


@dataclass(frozen=True)
class EncounterPresentation:
    source: str
    title: str
    scene: str
    omen: str
    player_prompt: str
    fallback_reason: Optional[str] = None


class ChapterOneRuleValidator:
    """The model proposes intent; this validator retains authority over the world."""

    max_total_intent = 2.5
    max_rationale_length = 240
    spirit_slugs = frozenset(("heaven", "earth", "water", "fire", "thunder", "wind", "mountain", "lake"))
    primary_axis_by_spirit = {
        "heaven": "ascend",
        "earth": "receive",
        "water": "flow",
        "fire": "illuminate",
        "thunder": "awaken",
        "wind": "adapt",
        "mountain": "stabilize",
        "lake": "exchange",
    }

    def validate(self, payload: Mapping[str, Any], expected_tick: int) -> DevelopmentDecision:
        if not isinstance(payload, Mapping):
            raise DecisionError("decision must be a JSON object")
        expected_keys = {"schema_version", "tick", "action_intents", "rationale"}
        if set(payload) != expected_keys:
            raise DecisionError("decision fields do not match the Chapter One contract")
        if payload["schema_version"] != DECISION_SCHEMA_VERSION:
            raise DecisionError("unsupported decision schema_version")
        if type(payload["tick"]) is not int or payload["tick"] != expected_tick:
            raise DecisionError("decision tick does not match the requested world tick")
        raw_intents = payload["action_intents"]
        if not isinstance(raw_intents, Mapping) or not raw_intents:
            raise DecisionError("action_intents must be a non-empty object")
        if not set(raw_intents).issubset(PRIMAL_ACTION_AXES):
            raise DecisionError("action_intents contains an axis outside Chapter One")

        intents: dict[str, float] = {}
        for axis, raw_value in raw_intents.items():
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise DecisionError(f"intent {axis} must be numeric")
            value = float(raw_value)
            if not 0.0 <= value <= 1.0:
                raise DecisionError(f"intent {axis} must be between 0 and 1")
            if value > 0.0:
                intents[axis] = round(value, 4)
        if not intents:
            raise DecisionError("at least one action intent must be positive")
        if sum(intents.values()) > self.max_total_intent:
            raise DecisionError("total action intent exceeds the Chapter One budget")
        focus_axis = max(PRIMAL_ACTION_AXES, key=lambda axis: (intents.get(axis, 0.0), -PRIMAL_ACTION_AXES.index(axis)))
        focus_spirit = ACTION_TO_SPIRIT[focus_axis]

        rationale = payload["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            raise DecisionError("rationale must be a non-empty string")
        if len(rationale) > self.max_rationale_length:
            raise DecisionError("rationale is too long")
        return DevelopmentDecision(
            schema_version=DECISION_SCHEMA_VERSION,
            tick=expected_tick,
            focus_spirit=focus_spirit,
            action_intents=intents,
            rationale=rationale.strip(),
        )


class OllamaDecisionClient:
    def __init__(self, model: str = "llama3.2:latest", base_url: str = "http://127.0.0.1:11434", timeout: float = 90.0):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def propose(self, observation: Mapping[str, Any], tick: int) -> Mapping[str, Any]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["schema_version", "tick", "action_intents", "rationale"],
            "properties": {
                "schema_version": {"type": "string", "const": DECISION_SCHEMA_VERSION},
                "tick": {"type": "integer", "const": tick},
                "action_intents": {
                    "type": "object",
                    "additionalProperties": False,
                    "minProperties": 1,
                    "properties": {axis: {"type": "number", "minimum": 0.0, "maximum": 1.0} for axis in PRIMAL_ACTION_AXES},
                    "anyOf": [
                        {
                            "required": [axis],
                            "properties": {axis: {"type": "number", "minimum": 0.1, "maximum": 1.0}},
                        }
                        for axis in PRIMAL_ACTION_AXES
                    ],
                },
                "rationale": {"type": "string", "minLength": 1, "maxLength": ChapterOneRuleValidator.max_rationale_length},
            },
        }
        prompt = (
            "你是 Edge World 第一章的后天八卦演化器。先逐句分析玩家表达中的动作、对象，以及动作已经"
            "造成或试图造成的主观世界变化；不要因为动作失败就忽略它，也不要只复述句子。"
            "再把语义归纳为八个基础动作轴上的压力：ascend=上升/开创/命令，receive=接纳/承载/保存，"
            "flow=穿越/下潜/循环，illuminate=火焰/照明/显现/辨识，awaken=唤醒/震动/启动，"
            "adapt=渗透/扩散/适应，stabilize=停止/守护/成形，exchange=回应/语言/交易。"
            "一句话可以命中多个轴，例如‘唤醒之物喷出火焰’应同时识别 awaken 与 illuminate。"
            "直接明确的动作或世界变化通常给 0.6 到 1.0，间接语义才给 0.1 到 0.5。"
            "只能在八个基础动作轴上提出意图，"
            "不可创造实体、改写规则或绕过预算。根据观察选择动作压力。"
            "action_intents 至少包含一个大于等于 0.1 的动作，所有动作强度总和不得超过 2.5。"
            "重点灵体将由规则从最强动作推导，模型不得另行指定。"
            "输出必须严格符合给定 JSON Schema。\n观察："
            + json.dumps(observation, ensure_ascii=False, sort_keys=True)
        )
        return self._chat(
            schema,
            prompt,
            "先天八卦决定世界本体，玩家引入变量，后天八卦决定潜意识转变；你只提交后天演化意图。",
            observation["seed"] + tick,
        )

    def present_encounter(self, rule_result: Mapping[str, Any], seed: int, tick: int) -> Mapping[str, Any]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "scene", "omen", "player_prompt"],
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 40},
                "scene": {"type": "string", "minLength": 1, "maxLength": 360},
                "omen": {"type": "string", "minLength": 1, "maxLength": 180},
                "player_prompt": {"type": "string", "minLength": 1, "maxLength": 100},
            },
        }
        prompt = (
            "将已由规则确定的周易遭遇、主导爻、预判和世界执行反馈呈现给玩家。"
            "不得修改本卦、变卦、动爻、主导爻、卦辞、爻辞、控制指令或执行数值；"
            "不要声称玩家必然成功或失败。场景必须体现玩家变量造成的后天潜意识转变。\n规则结果："
            + json.dumps(rule_result, ensure_ascii=False, sort_keys=True)
        )
        return self._chat(schema, prompt, "你是遭遇呈现层，不是卦象规则制定者。", seed + tick + 10_000)

    def _chat(self, schema: Mapping[str, Any], prompt: str, system_prompt: str, seed: int) -> Mapping[str, Any]:
        request_body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": schema,
                "options": {"temperature": 0, "seed": seed},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_payload = json.load(response)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise DecisionError(f"Ollama request failed: {exc}") from exc
        try:
            return json.loads(response_payload["message"]["content"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise DecisionError("Ollama returned an invalid structured response") from exc


class ChapterOneRuntime:
    def __init__(self, seed: int, client: Optional[OllamaDecisionClient] = None):
        self.seed = seed
        self.client = client
        self.validator = ChapterOneRuleValidator()

    def run(
        self,
        tick: int = 1,
        player_action: str = "awaken",
        player_intensity: float = 0.7,
        player_expression: str = "玩家进入世界并尝试唤醒眼前之物。",
    ) -> dict[str, Any]:
        if tick < 1:
            raise ValueError("tick must be positive")
        intervention = self._validate_player_intervention(player_action, player_intensity, player_expression)
        world = SubjectiveWorldModel.chaos_genesis(seed=self.seed)
        evolution = world.evolve_first_chapter()
        chapter_validation = world.validate_first_chapter(evolution)
        if not chapter_validation.success:
            raise RuntimeError("first chapter rules failed before AI decision")

        xiantian_world = self._xiantian_world_state(tick)
        observation = self._observation(world, chapter_validation, xiantian_world, intervention, tick)
        envelope = self._resolve_decision(observation, tick)
        cycle = world.run_primal_cycle(envelope.decision.action_intents)
        if not cycle.completed:
            raise RuntimeError("first chapter cycle did not complete")
        encounter = self._derive_houtian_encounter(xiantian_world, intervention, envelope.decision, tick)
        world_response = self._apply_world_response(world, encounter)
        presentation = self._present_encounter(encounter, world_response, tick)

        return {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "chapter": "all_things_ensoul",
            "seed": self.seed,
            "tick": tick,
            "cosmology": {
                "world_order": "xiantian_bagua",
                "change_order": "houtian_bagua",
                "change_canon": "zhouyi_64_hexagrams",
                "xiantian_world": xiantian_world,
                "player_intervention": _jsonable(intervention),
                "houtian_transition": encounter["houtian_transition"],
            },
            "decision": _jsonable(envelope),
            "encounter": encounter,
            "world_response": world_response,
            "presentation": _jsonable(presentation),
            "validation": _jsonable(chapter_validation),
            "cycle": _jsonable(cycle),
            "spirits": [
                {
                    "slug": descriptor.slug,
                    "name": descriptor.name,
                    "trigram_name": descriptor.trigram_name,
                    "symbol": descriptor.symbol,
                    "description": descriptor.subjective_description,
                    "entity": _jsonable(world.entity(f"spirit:{descriptor.slug}")),
                }
                for descriptor in world.describe_primal_spirits()
            ],
        }

    def write_snapshot(
        self,
        path: Path,
        tick: int = 1,
        player_action: str = "awaken",
        player_intensity: float = 0.7,
        player_expression: str = "玩家进入世界并尝试唤醒眼前之物。",
    ) -> dict[str, Any]:
        """Compute one world round and write it atomically.

        This method is intentionally lock-free: callers that perform a
        read-modify-write cycle (that is, ``--advance``) must hold
        ``snapshot_store.snapshot_lock`` around the whole cycle so that two
        frontends cannot both advance from the same tick.
        """
        snapshot = self.run(tick, player_action, player_intensity, player_expression)
        write_snapshot_atomic(path, snapshot)
        return snapshot

    def _resolve_decision(self, observation: Mapping[str, Any], tick: int) -> DecisionEnvelope:
        if self.client is not None:
            try:
                proposal = self.client.propose(observation, tick)
                decision = self.validator.validate(proposal, expected_tick=tick)
                return DecisionEnvelope("ollama", self.client.model, True, None, decision)
            except DecisionError as exc:
                fallback_reason = str(exc)
        else:
            fallback_reason = "Ollama disabled by runtime option"

        fallback = self.validator.validate(
            {
                "schema_version": DECISION_SCHEMA_VERSION,
                "tick": tick,
                "action_intents": DEFAULT_ACTION_INTENTS,
                "rationale": "确定性回退：以震启动，并由艮收束第一章循环。",
            },
            expected_tick=tick,
        )
        return DecisionEnvelope("rule_fallback", self.client.model if self.client else "none", False, fallback_reason, fallback)

    def _observation(
        self,
        world: SubjectiveWorldModel,
        chapter_validation: Any,
        xiantian_world: Mapping[str, Any],
        intervention: PlayerIntervention,
        tick: int,
    ) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "tick": tick,
            "chapter": "all_things_ensoul",
            "chapter_score": chapter_validation.score,
            "allowed_action_axes": list(PRIMAL_ACTION_AXES),
            "max_total_intent": self.validator.max_total_intent,
            "xiantian_world": xiantian_world,
            "player_intervention": _jsonable(intervention),
            "spirits": [
                {
                    "slug": descriptor.slug,
                    "status": world.entity(f"spirit:{descriptor.slug}").status.value,
                    "consciousness": world.entity(f"spirit:{descriptor.slug}").signature.consciousness,
                    "coherence": world.entity(f"spirit:{descriptor.slug}").signature.coherence,
                }
                for descriptor in world.describe_primal_spirits()
            ],
        }

    def _validate_player_intervention(self, action_axis: str, intensity: float, expression: str) -> PlayerIntervention:
        if action_axis not in PRIMAL_ACTION_AXES:
            raise ValueError(f"unknown player action axis: {action_axis}")
        if isinstance(intensity, bool) or not isinstance(intensity, (int, float)) or not 0.1 <= float(intensity) <= 1.0:
            raise ValueError("player_intensity must be between 0.1 and 1.0")
        if not isinstance(expression, str) or not expression.strip() or len(expression) > 240:
            raise ValueError("player_expression must contain 1 to 240 characters")
        return PlayerIntervention(action_axis, round(float(intensity), 4), expression.strip())

    def _xiantian_world_state(self, tick: int) -> dict[str, Any]:
        spirit = XIANTIAN_SEQUENCE[(tick - 1) % len(XIANTIAN_SEQUENCE)]
        trigram = TRIGRAMS[SPIRIT_TO_TRIGRAM_KEY[spirit]]
        return {
            "phase": (tick - 1) % len(XIANTIAN_SEQUENCE) + 1,
            "spirit": spirit,
            "trigram_name": trigram["name"],
            "symbol": trigram["symbol"],
            "value": trigram["value"],
            "direction": XIANTIAN_DIRECTIONS[spirit],
            "sequence": list(XIANTIAN_SEQUENCE),
        }

    def _derive_houtian_encounter(
        self,
        xiantian_world: Mapping[str, Any],
        intervention: PlayerIntervention,
        decision: DevelopmentDecision,
        tick: int,
    ) -> dict[str, Any]:
        player_spirit = ACTION_TO_SPIRIT[intervention.action_axis]
        player_trigram = TRIGRAMS[SPIRIT_TO_TRIGRAM_KEY[player_spirit]]
        primary = Hexagram.from_trigrams(xiantian_world["value"], player_trigram["value"])

        expression_evidence = self._expression_action_evidence(intervention.expression)
        pressures = dict(decision.action_intents)
        pressure_sources = {axis: ["decision_action_pressure"] for axis in pressures}
        for axis, evidence in expression_evidence.items():
            pressures[axis] = max(pressures.get(axis, 0.0), evidence["pressure"])
            pressure_sources.setdefault(axis, []).append("expression_keyword_evidence")
        pressures[intervention.action_axis] = max(pressures.get(intervention.action_axis, 0.0), intervention.intensity)
        pressure_sources.setdefault(intervention.action_axis, []).append("player_declared_action")
        evidence_by_position: dict[int, dict[str, Any]] = {}
        for axis, pressure in pressures.items():
            if pressure < 0.1:
                continue
            spirit = ACTION_TO_SPIRIT[axis]
            luoshu_number = HOUTIAN_POSITIONS[spirit]["number"]
            position = ((luoshu_number + tick - 2) % 6) + 1
            evidence = evidence_by_position.setdefault(position, {"position": position, "score": 0.0, "axes": [], "sources": []})
            evidence["score"] += pressure
            evidence["axes"].append(axis)
            evidence["sources"].extend(pressure_sources.get(axis, ("decision_action_pressure",)))
        if intervention.intensity >= 0.75:
            player_number = HOUTIAN_POSITIONS[player_spirit]["number"]
            primary_position = ((player_number + tick - 2) % 6) + 1
            reflected_position = 7 - primary_position
            evidence = evidence_by_position.setdefault(
                reflected_position,
                {"position": reflected_position, "score": 0.0, "axes": [], "sources": []},
            )
            evidence["score"] += intervention.intensity * 0.5
            evidence["axes"].append(intervention.action_axis)
            evidence["sources"].append("high_intensity_reflection")

        line_evidence = []
        for position in sorted(evidence_by_position):
            evidence = evidence_by_position[position]
            evidence["score"] = round(evidence["score"], 4)
            evidence["axes"] = sorted(set(evidence["axes"]), key=PRIMAL_ACTION_AXES.index)
            evidence["sources"] = sorted(set(evidence["sources"]))
            evidence["rule"] = "position=((houtian_luoshu_number+tick-2)%6)+1"
            line_evidence.append(evidence)

        ordered_positions = [evidence["position"] for evidence in line_evidence]
        changed = primary.change(ordered_positions)
        resultant_axis = max(PRIMAL_ACTION_AXES, key=lambda axis: (pressures.get(axis, 0.0), -PRIMAL_ACTION_AXES.index(axis)))
        resultant_spirit = ACTION_TO_SPIRIT[resultant_axis]
        focus = HOUTIAN_POSITIONS[resultant_spirit]
        governing_evidence = max(
            line_evidence,
            key=lambda evidence: (
                evidence["score"],
                intervention.action_axis in evidence["axes"],
                evidence["position"] in (2, 5),
                -evidence["position"],
            ),
        )
        governing_line = self._line_payload(primary, governing_evidence["position"])
        governing_line.update(
            {
                "name": self._line_name(primary, governing_evidence["position"]),
                "polarity": "yang" if primary.lines[governing_evidence["position"] - 1] else "yin",
                "evidence_score": governing_evidence["score"],
                "evidence_axes": governing_evidence["axes"],
                "selection_rule": "最高动爻证据；同分时依次优先玩家主动作、中爻、较低爻位。",
            }
        )
        return {
            "primary_hexagram": self._hexagram_payload(primary),
            "changing_positions": ordered_positions,
            "changing_lines": [self._line_payload(primary, position) for position in ordered_positions],
            "governing_line": governing_line,
            "changed_hexagram": self._hexagram_payload(changed),
            "abstraction": {
                "player_expression": intervention.expression,
                "declared_action_axis": intervention.action_axis,
                "semantic_action_intents": dict(decision.action_intents),
                "expression_action_evidence": expression_evidence,
                "combined_action_pressures": pressures,
                "upper_trigram_basis": "xiantian_world_phase",
                "upper_trigram": xiantian_world["trigram_name"],
                "lower_trigram_basis": "player_declared_action",
                "lower_trigram": player_trigram["name"],
                "line_evidence": line_evidence,
            },
            "houtian_transition": {
                "focus_spirit": resultant_spirit,
                "direction": focus["direction"],
                "luoshu_number": focus["number"],
                "ai_focus_spirit": decision.focus_spirit,
                "player_spirit": player_spirit,
                "player_direction": HOUTIAN_POSITIONS[player_spirit]["direction"],
                "player_luoshu_number": HOUTIAN_POSITIONS[player_spirit]["number"],
                "pressures": pressures,
            },
        }

    def _expression_action_evidence(self, expression: str) -> dict[str, Any]:
        evidence = {}
        for axis in PRIMAL_ACTION_AXES:
            matched_keywords = [keyword for keyword in EXPRESSION_AXIS_KEYWORDS[axis] if keyword in expression]
            if matched_keywords:
                evidence[axis] = {
                    "pressure": EXPRESSION_EVIDENCE_PRESSURE,
                    "matched_keywords": matched_keywords,
                }
        return evidence

    def _line_name(self, hexagram: Hexagram, position: int) -> str:
        polarity = "九" if hexagram.lines[position - 1] else "六"
        if position == 1:
            return f"初{polarity}"
        if position == 6:
            return f"上{polarity}"
        numerals = {2: "二", 3: "三", 4: "四", 5: "五"}
        return f"{polarity}{numerals[position]}"

    def _classical_valence(self, judgment: str, line_text: str) -> str:
        text = f"{judgment}{line_text}"
        positive = sum(text.count(marker) * weight for marker, weight in POSITIVE_OMEN_MARKERS.items())
        caution = sum(text.count(marker) * weight for marker, weight in CAUTION_OMEN_MARKERS.items())
        if positive > caution:
            return "favorable"
        if caution > positive:
            return "caution"
        return "balanced"

    def _apply_world_response(self, world: SubjectiveWorldModel, encounter: Mapping[str, Any]) -> dict[str, Any]:
        transition = encounter["houtian_transition"]
        governing_line = encounter["governing_line"]
        primary = encounter["primary_hexagram"]
        changed = encounter["changed_hexagram"]
        target_spirit = transition["focus_spirit"]
        pressures = transition["pressures"]
        action_axis = max(
            PRIMAL_ACTION_AXES,
            key=lambda axis: (pressures.get(axis, 0.0), -PRIMAL_ACTION_AXES.index(axis)),
        )
        magnitude = round(float(pressures[action_axis]), 4)
        valence = self._classical_valence(primary["judgment"], governing_line["text"])

        base_deltas = {
            "favorable": (0.04, 0.05, -0.04),
            "balanced": (0.01, 0.02, 0.0),
            "caution": (-0.02, -0.03, 0.05),
        }[valence]
        consciousness_delta = base_deltas[0] * magnitude
        coherence_delta = base_deltas[1] * magnitude
        entropy_delta = base_deltas[2] * magnitude
        if governing_line["polarity"] == "yin":
            consciousness_delta += 0.02 * magnitude
        else:
            coherence_delta += 0.02 * magnitude
        if governing_line["position"] in (2, 5):
            coherence_delta += 0.02 * magnitude

        rounded_deltas = {
            "consciousness": round(consciousness_delta, 4),
            "coherence": round(coherence_delta, 4),
            "entropy": round(entropy_delta, 4),
        }
        before, after = world.apply_rule_effect(
            f"spirit:{target_spirit}",
            changed["value"],
            consciousness_delta=rounded_deltas["consciousness"],
            coherence_delta=rounded_deltas["coherence"],
            entropy_delta=rounded_deltas["entropy"],
        )
        effect_cn, renderer_effect = ACTION_EFFECTS[action_axis]
        tendency = {
            "favorable": "可推进，但仍须服从主导爻的时位约束。",
            "balanced": "先维持变化并观察反馈，再决定下一次介入。",
            "caution": "先收敛风险，不把卦辞当作必然结果。",
        }[valence]
        return {
            "forecast": {
                "primary_judgment": primary["judgment"],
                "governing_line_name": governing_line["name"],
                "governing_line_text": governing_line["text"],
                "changed_judgment": changed["judgment"],
                "valence": valence,
                "tendency": tendency,
                "summary": (
                    f"{primary['symbol']}{primary['name']}卦辞：{primary['judgment']} "
                    f"主导{governing_line['name']}：{governing_line['text']} "
                    f"预判世界以“{effect_cn}”响应，并趋向{changed['symbol']}{changed['name']}。"
                ),
            },
            "control": {
                "target_spirit": target_spirit,
                "action_axis": action_axis,
                "effect": renderer_effect,
                "effect_cn": effect_cn,
                "magnitude": magnitude,
                "duration_ticks": governing_line["position"],
                "scale_multiplier": round(1.0 + magnitude * 0.35, 4),
                "emission_multiplier": round(1.0 + magnitude * 1.5, 4),
                "vertical_offset": round((0.6 if governing_line["polarity"] == "yin" else -0.35) * magnitude, 4),
                "signature_deltas": rounded_deltas,
                "basis": "canonical_judgment+governing_line+changed_hexagram",
            },
            "feedback": {
                "status": "applied",
                "entity_id": after.id,
                "before": _jsonable(before.signature),
                "after": _jsonable(after.signature),
                "changed_hexagram_value": after.hexagram_value,
                "message": (
                    f"已对{SPIRIT_LABELS[target_spirit]}（{target_spirit}）执行{effect_cn}；"
                    "主观状态已更新并交给引擎渲染。"
                ),
            },
        }

    def _hexagram_payload(self, hexagram: Hexagram) -> dict[str, Any]:
        judgment = hexagram.judgment or {}
        image = hexagram.image or {}
        judgment_text = judgment.get("text", "")
        image_text = image.get("text", "")
        return {
            "value": hexagram.value,
            "sequence": hexagram.sequence,
            "name": hexagram.name,
            "symbol": hexagram.symbol,
            "upper_trigram": hexagram.upper["name"],
            "lower_trigram": hexagram.lower["name"],
            "judgment": judgment_text,
            "image": image_text,
            "canonical_text_available": bool(judgment_text and image_text),
            "structural_image": f"上{hexagram.upper['name']}下{hexagram.lower['name']}，六爻值 {hexagram.value}。",
        }

    def _line_payload(self, hexagram: Hexagram, position: int) -> dict[str, Any]:
        line = hexagram.line(position) or {}
        text = line.get("text", "")
        return {
            "position": position,
            "text": text,
            "commentary": line.get("commentary", ""),
            "canonical_text_available": bool(text),
        }

    def _present_encounter(
        self,
        encounter: Mapping[str, Any],
        world_response: Mapping[str, Any],
        tick: int,
    ) -> EncounterPresentation:
        if self.client is not None:
            try:
                raw = self.client.present_encounter(
                    {"encounter": encounter, "world_response": world_response},
                    self.seed,
                    tick,
                )
                expected = {"title", "scene", "omen", "player_prompt"}
                if not isinstance(raw, Mapping) or set(raw) != expected:
                    raise DecisionError("Ollama encounter presentation has invalid fields")
                limits = {"title": 40, "scene": 360, "omen": 180, "player_prompt": 100}
                values = {}
                for key, limit in limits.items():
                    value = raw[key]
                    if not isinstance(value, str) or not value.strip() or len(value) > limit:
                        raise DecisionError(f"Ollama encounter presentation has invalid {key}")
                    values[key] = value.strip()
                return EncounterPresentation("ollama", **values)
            except (DecisionError, AttributeError) as exc:
                fallback_reason = str(exc)
        else:
            fallback_reason = "Ollama disabled by runtime option"
        primary = encounter["primary_hexagram"]
        changed = encounter["changed_hexagram"]
        scene = primary["image"] or primary["structural_image"]
        omen = world_response["forecast"]["summary"]
        return EncounterPresentation(
            source="rule_fallback",
            title=f"{primary['symbol']} {primary['name']}之{changed['name']}",
            scene=scene,
            omen=omen,
            player_prompt=world_response["feedback"]["message"],
            fallback_reason=fallback_reason,
        )


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
