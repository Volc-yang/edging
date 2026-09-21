"""Destiny layer: the edging 64D/384 deterministic scorer inside Chapter One.

This closes the largest remaining gap in the project: the ``edging`` prototype
layer reached full structural coverage (64 families, 384 line-state
prototypes, 320 adjacent transitions, deterministic scorer) but nothing in the
game runtime consumed it.

How it is wired in — and what it deliberately does **not** do:

* The Yi Jing rule layer remains the only authority that decides the hexagram,
  the changing lines and the world state. The destiny layer runs *after* the
  round is already approved and never feeds back into it.
* It projects only quantities that the approved snapshot already contains
  (spirit signatures, action pressures, the governing line, chapter
  validation) onto the ten `edging` feature dimensions, runs the existing
  Ruby scorer unchanged, and stores a bounded, auditable summary.
* If Ruby or the registry is unavailable the block is recorded as
  ``source: "unavailable"`` with a reason. It is never faked and never
  approximated in Python, so the scorer stays the single source of truth.
* The full 384-cell prototype distribution and the 64-cell family
  distribution are intentionally **not** copied into the snapshot (they would
  dominate the file). Only the ranked tops, uncertainty and version basis are
  kept.

See ``doc/destiny_layer.md`` for the dimension derivation table.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional

#: The ten dimensions defined by edging/docs/02-domain-model/feature-schema.v0.1.yaml
EDGING_DIMENSIONS = (
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

DESTINY_SCHEMA_VERSION = "edgeworld.chapter-one-destiny.v1"

#: The eight primal action axes, in the order subjective_world defines them.
ACTION_AXES = (
    "ascend",
    "receive",
    "flow",
    "illuminate",
    "awaken",
    "adapt",
    "stabilize",
    "exchange",
)

#: Entropy is a small absolute quantity in the subjective signature; this is the
#: value treated as "fully exposed to risk" when normalising.
ENTROPY_FULL_SCALE = 0.05

#: How many ranked entries are copied out of the scorer result.
TOP_FAMILY_COUNT = 3
TOP_PROTOTYPE_COUNT = 5

SCORER_RELATIVE_PATH = Path("edging") / "bin" / "deterministic_scorer.rb"

DEFAULT_SCORER_TIMEOUT_SECONDS = 30.0


class ScorerUnavailable(RuntimeError):
    """Raised when the edging scorer cannot be executed."""


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _mean(values) -> float:
    values = [float(v) for v in values]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _round6(value: float) -> float:
    return round(float(value), 6)


# --------------------------------------------------------------------- derive
def _signatures(snapshot: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    signatures = []
    for spirit in snapshot.get("spirits") or []:
        entity = spirit.get("entity") if isinstance(spirit, Mapping) else None
        signature = entity.get("signature") if isinstance(entity, Mapping) else None
        if isinstance(signature, Mapping):
            signatures.append(signature)
    return signatures


def derive_observation(snapshot: Mapping[str, Any]) -> tuple[dict[str, float], dict[str, str]]:
    """Project an approved snapshot onto the ten edging dimensions.

    Returns ``(feature_vector, derivation)`` where ``derivation`` explains, per
    dimension, which approved quantity produced the value. Every value is
    clamped to ``0..1``; nothing is invented.
    """
    signatures = _signatures(snapshot)

    encounter = snapshot.get("encounter") or {}
    abstraction = encounter.get("abstraction") or {}
    pressures: Mapping[str, float] = abstraction.get("combined_action_pressures") or {}
    declared_axis = abstraction.get("declared_action_axis")
    governing = encounter.get("governing_line") or {}
    changing_positions = encounter.get("changing_positions") or []

    validation = snapshot.get("validation") or {}
    cycle = snapshot.get("cycle") or {}

    tick = snapshot.get("tick")
    tick = tick if type(tick) is int and tick > 0 else 1

    mean_consciousness = _mean(s.get("consciousness", 0.0) for s in signatures)
    mean_coherence = _mean(s.get("coherence", 0.0) for s in signatures)
    mean_entropy = _mean(s.get("entropy", 0.0) for s in signatures)
    mean_imbalance = _mean(abs(float(s.get("yin_intent", 0.0)) - float(s.get("yang_intent", 0.0))) for s in signatures)

    pressure_values = {axis: float(pressures.get(axis, 0.0)) for axis in ACTION_AXES}
    pressure_peak = max(pressure_values.values()) if pressure_values else 0.0
    pressure_mean = _mean(pressure_values.values())
    player_pressure = float(pressure_values.get(declared_axis, 0.0)) if declared_axis in ACTION_AXES else 0.0
    engaged_axes = sum(1 for value in pressure_values.values() if value >= 0.2) / len(ACTION_AXES)

    governing_position = governing.get("position")
    governing_position = (
        governing_position
        if type(governing_position) is int and 1 <= governing_position <= 6
        else 3
    )
    changing_ratio = len(changing_positions) / 6.0

    chapter_score = float(validation.get("score", 0.0))
    final_integrity = float(cycle.get("final_integrity", 0.0))
    cycle_completed = 1.0 if cycle.get("completed") else 0.0
    # The Xiantian world advances one primal position per tick and cycles every 8.
    phase_progress = ((tick - 1) % 8) / 7.0

    vector = {
        "agency": _round6(_clamp(0.5 * player_pressure + 0.5 * pressure_peak)),
        "visibility": _round6(_clamp(mean_consciousness)),
        "resource_mobilization": _round6(_clamp(0.5 * engaged_axes + 0.5 * pressure_mean)),
        "stability": _round6(_clamp(mean_coherence)),
        "risk_exposure": _round6(_clamp(mean_entropy / ENTROPY_FULL_SCALE)),
        "momentum": _round6(_clamp(0.5 * changing_ratio + 0.5 * pressure_mean)),
        "constraint_pressure": _round6(_clamp((6 - governing_position) / 6.0)),
        "coordination": _round6(_clamp(1.0 - mean_imbalance)),
        "timing_maturity": _round6(_clamp(0.5 * phase_progress + 0.5 * cycle_completed)),
        "governance_capacity": _round6(_clamp(0.5 * chapter_score + 0.5 * final_integrity)),
    }

    derivation = {
        "agency": "0.5×玩家动作轴压力 + 0.5×八轴峰值压力（encounter.abstraction.combined_action_pressures）",
        "visibility": "八灵 consciousness 均值（spirits[].entity.signature.consciousness）",
        "resource_mobilization": "0.5×已激活动作轴占比(≥0.2) + 0.5×八轴压力均值",
        "stability": "八灵 coherence 均值（spirits[].entity.signature.coherence）",
        "risk_exposure": "八灵 entropy 均值 ÷ 满量程 0.05",
        "momentum": f"0.5×动爻比例({len(changing_positions)}/6) + 0.5×八轴压力均值",
        "constraint_pressure": f"(6 − 主导爻位 {governing_position}) ÷ 6：爻位越低，时位约束越强",
        "coordination": "1 − 八灵 |yin_intent − yang_intent| 均值",
        "timing_maturity": f"0.5×先天相位进度((tick−1) mod 8)/7 + 0.5×本轮循环是否完成({cycle_completed:g})",
        "governance_capacity": f"0.5×章内评分 {chapter_score:g} + 0.5×末态自洽 {final_integrity:g}",
    }
    return vector, derivation


# ---------------------------------------------------------------------- score
def _scorer_script(repo_root: "str | Path") -> Path:
    override = os.environ.get("EDGEWORLD_SCORER")
    if override:
        return Path(override)
    return Path(repo_root) / SCORER_RELATIVE_PATH


def _ruby_executable() -> Optional[str]:
    override = os.environ.get("EDGEWORLD_RUBY")
    if override:
        return override if Path(override).exists() else None
    return shutil.which("ruby")


def _yaml_quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
    return f'"{escaped}"'


def build_observation_yaml(
    feature_vector: Mapping[str, float],
    free_text: str = "",
    context_tags: Optional[list[str]] = None,
    subject_type: str = "non_human_object",
    mode: str = "hybrid",
    timestamp: str = "1970-01-01T00:00:00Z",
) -> str:
    """Render the scorer's input contract as YAML.

    Written by hand because the runtime deliberately has no YAML dependency;
    the shape matches ``edging/examples/sample-observation.v0.1.yaml``.
    """
    lines = ["observation_input:", f"  subject_type: {subject_type}", f"  mode: {mode}", f"  timestamp: {_yaml_quote(timestamp)}", "  feature_vector:"]
    for dimension in EDGING_DIMENSIONS:
        if dimension not in feature_vector:
            raise ScorerUnavailable(f"feature vector is missing dimension {dimension!r}")
        lines.append(f"    {dimension}: {float(feature_vector[dimension]):.6f}")
    if free_text:
        lines.append(f"  free_text: {_yaml_quote(free_text)}")
    if context_tags:
        lines.append("  context_tags:")
        for tag in context_tags:
            lines.append(f"    - {tag}")
    return "\n".join(lines) + "\n"


class EdgingDeterministicScorer:
    """Thin, replaceable wrapper around the Ruby deterministic scorer."""

    def __init__(self, repo_root: "str | Path", timeout: float = DEFAULT_SCORER_TIMEOUT_SECONDS) -> None:
        self.repo_root = Path(repo_root)
        self.timeout = timeout

    def available(self) -> tuple[bool, str]:
        script = _scorer_script(self.repo_root)
        if not script.exists():
            return False, f"scorer script not found: {script}"
        if _ruby_executable() is None:
            return False, "ruby executable not found on PATH (set EDGEWORLD_RUBY)"
        return True, ""

    def score(self, observation_yaml: str) -> dict[str, Any]:
        """Run the scorer and return its parsed ``score_result``."""
        ok, reason = self.available()
        if not ok:
            raise ScorerUnavailable(reason)

        script = _scorer_script(self.repo_root)
        ruby = _ruby_executable()
        if ruby is None:  # defensive: available() already checked
            raise ScorerUnavailable("ruby executable not found on PATH (set EDGEWORLD_RUBY)")
        temporary_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", suffix=".yaml", delete=False
            ) as handle:
                handle.write(observation_yaml)
                temporary_path = Path(handle.name)

            completed = subprocess.run(
                [ruby, str(script), str(temporary_path)],
                cwd=str(script.parent.parent),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ScorerUnavailable(f"scorer timed out after {self.timeout:g}s") from exc
        except OSError as exc:
            raise ScorerUnavailable(f"could not execute the scorer: {exc}") from exc
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

        if completed.returncode != 0:
            raise ScorerUnavailable(
                f"scorer exited {completed.returncode}: {completed.stderr.strip()[:400]}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ScorerUnavailable(f"scorer output was not JSON: {exc}") from exc
        result = payload.get("score_result")
        if not isinstance(result, Mapping):
            raise ScorerUnavailable("scorer output has no score_result object")
        return dict(result)


class DestinyLayer:
    """Attach a bounded, auditable 64D/384 reading to an approved round."""

    def __init__(self, repo_root: "str | Path", enabled: bool = True) -> None:
        self.repo_root = Path(repo_root)
        self.enabled = enabled
        self.scorer = EdgingDeterministicScorer(self.repo_root)

    def evaluate(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        """Never raises: an unusable scorer degrades to an ``unavailable`` block."""
        vector, derivation = derive_observation(snapshot)
        block: dict[str, Any] = {
            "schema_version": DESTINY_SCHEMA_VERSION,
            "role": "第一章的世界族谱读数；由 edging 确定性评分器计算，不参与卦象决定。",
            "subject_type": "non_human_object",
            "feature_vector": vector,
            "derivation": derivation,
            "top_families": [],
            "top_prototypes": [],
            "uncertainty": None,
            "probe_target": None,
            "scorer_version": None,
            "validation_status": "unavailable",
        }

        if not self.enabled:
            block.update({"source": "disabled", "reason": "destiny layer disabled by the caller"})
            return block

        ok, reason = self.scorer.available()
        if not ok:
            block.update({"source": "unavailable", "reason": reason})
            return block

        try:
            result = self.scorer.score(self._observation_yaml(snapshot, vector))
        except ScorerUnavailable as exc:
            block.update({"source": "unavailable", "reason": str(exc)})
            return block

        basis = result.get("explanation_basis") or {}
        validation = result.get("validation") or {}
        block.update(
            {
                "source": "edging-deterministic-scorer",
                "validation_status": result.get("validation_status"),
                "validation": {
                    "status": validation.get("status"),
                    "policy_flags": validation.get("policy_flags", []),
                    "missing_dimensions": validation.get("missing_dimensions", []),
                    "out_of_range_dimensions": validation.get("out_of_range_dimensions", []),
                },
                "top_families": list(result.get("top_families") or [])[:TOP_FAMILY_COUNT],
                "top_prototypes": list(result.get("top_prototypes") or [])[:TOP_PROTOTYPE_COUNT],
                "uncertainty": result.get("uncertainty"),
                "probe_target": result.get("probe_target"),
                "scorer_version": basis.get("scoring_version"),
                "explanation_basis": {
                    "feature_schema_version": basis.get("feature_schema_version"),
                    "family_registry_version": basis.get("family_registry_version"),
                    "prototype_registry_version": basis.get("prototype_registry_version"),
                    "transition_rules_version": basis.get("transition_rules_version"),
                },
            }
        )
        return block

    def _observation_yaml(self, snapshot: Mapping[str, Any], vector: Mapping[str, float]) -> str:
        encounter = snapshot.get("encounter") or {}
        abstraction = encounter.get("abstraction") or {}
        tick = snapshot.get("tick")
        primary = (encounter.get("primary_hexagram") or {}).get("name")
        changed = (encounter.get("changed_hexagram") or {}).get("name")
        expression = abstraction.get("player_expression") or ""
        free_text = f"第一章第 {tick} 轮：本卦{primary}，变卦{changed}。玩家表达：{expression}"
        tags = ["edge_world", "chapter_one", "world_state", f"tick_{tick}"]
        return build_observation_yaml(
            vector,
            free_text=free_text,
            context_tags=tags,
            timestamp=f"chapter-one-tick-{tick}",
        )
