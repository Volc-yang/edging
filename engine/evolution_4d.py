"""Experimental deterministic single-tree evolution step.

This module is a research prototype, not an approved world-law model. Its tree
state fields, coefficients, phase multipliers, and transition thresholds are
explicitly experimental. The function is pure: it performs no I/O, persistence,
random sampling, Genesis calls, or engine integration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


EXPERIMENTAL_RULE_VERSION = "experimental.tree-growth.v1"


class TimePhase(str, Enum):
    """The four prototype time phases used to select an experimental multiplier."""

    SHAOYANG = "shaoyang"
    TAIYANG = "taiyang"
    SHAOYIN = "shaoyin"
    TAIYIN = "taiyin"


class TreeStage(str, Enum):
    """Small lifecycle vocabulary for this single-object experiment."""

    SEEDLING = "seedling"
    MATURE = "mature"
    DECLINING = "declining"
    DEAD = "dead"


def _bounded_number(value: object, name: str, low: float, high: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number in [{low}, {high}]")
    # Compare against the declared bounds before calling isfinite: converting
    # an arbitrarily large Python int to a float inside isfinite may overflow.
    if value < low or value > high or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number in [{low}, {high}]")


@dataclass(frozen=True)
class TreeState:
    """Authoritative state for one experimental tree object."""

    stable_id: str
    logical_tick: int
    stage: TreeStage
    health: float
    biomass: float
    water_reserve: float

    def __post_init__(self) -> None:
        if not isinstance(self.stable_id, str) or not self.stable_id.strip():
            raise ValueError("stable_id must be a non-empty string")
        if type(self.logical_tick) is not int or self.logical_tick < 0:
            raise ValueError("logical_tick must be a non-negative integer")
        if not isinstance(self.stage, TreeStage):
            raise ValueError("stage must be a TreeStage")
        _bounded_number(self.health, "health", 0.0, 1.0)
        _bounded_number(self.biomass, "biomass", 0.0, 1.0)
        _bounded_number(self.water_reserve, "water_reserve", 0.0, 1.0)


@dataclass(frozen=True)
class EnvironmentSample:
    """Fixed environment inputs for exactly one logical tick."""

    phase: TimePhase
    moisture: float
    light: float

    def __post_init__(self) -> None:
        if not isinstance(self.phase, TimePhase):
            raise ValueError("phase must be a TimePhase")
        _bounded_number(self.moisture, "moisture", 0.0, 1.0)
        _bounded_number(self.light, "light", 0.0, 1.0)


@dataclass(frozen=True)
class EvolutionRules:
    """Versioned experimental coefficients and lifecycle thresholds.

    These defaults are demonstration parameters only. They are not calibrated
    biology, project-approved laws, or a production balance specification.
    """

    version: str = EXPERIMENTAL_RULE_VERSION
    growth_per_tick: float = 0.08
    water_uptake_per_moisture: float = 0.25
    water_use_per_tick: float = 0.12
    drought_threshold: float = 0.30
    health_loss_per_drought_tick: float = 0.08
    health_recovery_per_wet_tick: float = 0.025
    mature_at_tick: int = 5
    mature_biomass_threshold: float = 0.25
    decline_at_tick: int = 20
    decline_health_threshold: float = 0.25
    death_health_threshold: float = 0.05
    phase_growth_multipliers: Tuple[Tuple[TimePhase, float], ...] = (
        (TimePhase.SHAOYANG, 1.0),
        (TimePhase.TAIYANG, 1.2),
        (TimePhase.SHAOYIN, 0.7),
        (TimePhase.TAIYIN, 0.3),
    )

    def __post_init__(self) -> None:
        if self.version != EXPERIMENTAL_RULE_VERSION:
            raise ValueError(f"unsupported experimental rule version: {self.version!r}")
        for name in (
            "growth_per_tick",
            "water_uptake_per_moisture",
            "water_use_per_tick",
            "health_loss_per_drought_tick",
            "health_recovery_per_wet_tick",
        ):
            _bounded_number(getattr(self, name), name, 0.0, 1.0)
        for name in (
            "drought_threshold",
            "mature_biomass_threshold",
            "decline_health_threshold",
            "death_health_threshold",
        ):
            _bounded_number(getattr(self, name), name, 0.0, 1.0)
        if type(self.mature_at_tick) is not int or self.mature_at_tick < 1:
            raise ValueError("mature_at_tick must be a positive integer")
        if type(self.decline_at_tick) is not int or self.decline_at_tick < self.mature_at_tick:
            raise ValueError("decline_at_tick must be an integer >= mature_at_tick")
        if self.death_health_threshold >= self.decline_health_threshold:
            raise ValueError("death_health_threshold must be below decline_health_threshold")

        multipliers = self.phase_growth_multipliers
        if not isinstance(multipliers, tuple):
            raise ValueError("phase_growth_multipliers must be a tuple")
        phases = []
        for entry in multipliers:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError("each phase multiplier must be a (TimePhase, multiplier) tuple")
            phase, multiplier = entry
            if not isinstance(phase, TimePhase):
                raise ValueError("phase multiplier keys must be TimePhase values")
            _bounded_number(multiplier, "phase growth multiplier", 0.0, 2.0)
            phases.append(phase)
        if len(phases) != len(TimePhase) or set(phases) != set(TimePhase):
            raise ValueError("phase_growth_multipliers must define each TimePhase exactly once")

    def multiplier_for(self, phase: TimePhase) -> float:
        return next(value for key, value in self.phase_growth_multipliers if key is phase)


@dataclass(frozen=True)
class EvolutionResult:
    """The next state and stable reason codes explaining this transition."""

    state: TreeState
    reasons: Tuple[str, ...]


def advance_tree(
    state: TreeState,
    environment: EnvironmentSample,
    logical_tick: int,
    rules: EvolutionRules = EvolutionRules(),
) -> EvolutionResult:
    """Advance one tree by exactly one tick using deterministic experimental rules.

    The transition reads only its arguments and returns a new value. Ticks must
    be contiguous so callers cannot silently skip unmodeled evolution steps.
    """

    if not isinstance(state, TreeState):
        raise TypeError("state must be a TreeState")
    if not isinstance(environment, EnvironmentSample):
        raise TypeError("environment must be an EnvironmentSample")
    if not isinstance(rules, EvolutionRules):
        raise TypeError("rules must be EvolutionRules")
    if type(logical_tick) is not int or logical_tick != state.logical_tick + 1:
        raise ValueError("logical_tick must be exactly state.logical_tick + 1")
    # Re-check the version at the call boundary in case a nonstandard object or
    # deserialization path bypassed dataclass construction validation.
    if rules.version != EXPERIMENTAL_RULE_VERSION:
        raise ValueError(f"unsupported experimental rule version: {rules.version!r}")

    reasons = ["tick_advanced"]
    if state.stage is TreeStage.DEAD:
        return EvolutionResult(
            state=TreeState(
                stable_id=state.stable_id,
                logical_tick=logical_tick,
                stage=TreeStage.DEAD,
                health=state.health,
                biomass=state.biomass,
                water_reserve=state.water_reserve,
            ),
            reasons=tuple(reasons + ["dead_no_growth"]),
        )

    uptake = min(1.0 - state.water_reserve, environment.moisture * rules.water_uptake_per_moisture)
    available_water = max(0.0, min(1.0, state.water_reserve + uptake - rules.water_use_per_tick))
    if uptake > 0.0:
        reasons.append("water_uptake")

    drought = environment.moisture < rules.drought_threshold
    if drought:
        health = max(0.0, state.health - rules.health_loss_per_drought_tick)
        reasons.append("drought_stress")
    else:
        health = min(1.0, state.health + rules.health_recovery_per_wet_tick)
        if health > state.health:
            reasons.append("health_recovered")

    if health <= rules.death_health_threshold:
        stage = TreeStage.DEAD
        biomass = state.biomass
        reasons.append(f"stage:{state.stage.value}->dead")
    else:
        phase_multiplier = rules.multiplier_for(environment.phase)
        water_support = min(1.0, available_water / rules.water_use_per_tick) if rules.water_use_per_tick else 1.0
        growth = rules.growth_per_tick * environment.light * phase_multiplier * water_support
        biomass = min(1.0, state.biomass + growth)
        if growth > 0.0:
            reasons.append("biomass_grew")
        if biomass == 1.0 and state.biomass + growth > 1.0:
            reasons.append("biomass_capped")

        if state.stage is TreeStage.SEEDLING:
            if logical_tick >= rules.mature_at_tick and biomass >= rules.mature_biomass_threshold:
                stage = TreeStage.MATURE
            else:
                stage = TreeStage.SEEDLING
        elif state.stage is TreeStage.MATURE:
            if logical_tick >= rules.decline_at_tick or health <= rules.decline_health_threshold:
                stage = TreeStage.DECLINING
            else:
                stage = TreeStage.MATURE
        else:
            # Lifecycle stages do not move backward; recovery affects health,
            # while the stage remains a historical milestone.
            stage = TreeStage.DECLINING

        if stage is not state.stage:
            reasons.append(f"stage:{state.stage.value}->{stage.value}")

    next_state = TreeState(
        stable_id=state.stable_id,
        logical_tick=logical_tick,
        stage=stage,
        health=health,
        biomass=biomass,
        water_reserve=available_water,
    )
    return EvolutionResult(state=next_state, reasons=tuple(reasons))
