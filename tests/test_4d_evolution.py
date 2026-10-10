"""Focused checks for the experimental pure-Python evolution slice."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from evolution_4d import (  # noqa: E402
    EnvironmentSample,
    EvolutionRules,
    TimePhase,
    TreeStage,
    TreeState,
    advance_tree,
)


class Evolution4DTests(unittest.TestCase):
    def setUp(self) -> None:
        self.initial = TreeState(
            stable_id="tree-1",
            logical_tick=0,
            stage=TreeStage.SEEDLING,
            health=0.65,
            biomass=0.20,
            water_reserve=0.50,
        )

    def test_fixed_tick_trace_replays_exactly(self) -> None:
        """The same explicit inputs reproduce every state and reason tuple."""
        inputs = (
            EnvironmentSample(TimePhase.TAIYANG, moisture=0.8, light=0.7),
            EnvironmentSample(TimePhase.SHAOYIN, moisture=0.1, light=0.2),
            EnvironmentSample(TimePhase.SHAOYANG, moisture=0.8, light=0.9),
            EnvironmentSample(TimePhase.TAIYANG, moisture=0.8, light=0.9),
            EnvironmentSample(TimePhase.SHAOYIN, moisture=0.8, light=0.9),
        )

        def replay():
            state = self.initial
            trace = []
            for tick, environment in enumerate(inputs, start=1):
                result = advance_tree(state, environment, tick)
                state = result.state
                trace.append((state, result.reasons))
            return trace

        first = replay()
        second = replay()
        self.assertEqual(first, second)
        self.assertEqual(
            [entry[0].stage for entry in first],
            [TreeStage.SEEDLING] * 4 + [TreeStage.MATURE],
        )
        self.assertAlmostEqual(first[0][0].biomass, 0.2672)
        self.assertAlmostEqual(first[1][0].biomass, 0.2784)
        self.assertAlmostEqual(first[2][0].biomass, 0.3504)
        self.assertAlmostEqual(first[3][0].biomass, 0.4368)
        self.assertAlmostEqual(first[4][0].biomass, 0.4872)
        self.assertEqual(first[1][1], ("tick_advanced", "water_uptake", "drought_stress", "biomass_grew"))
        self.assertEqual(first[4][1][-1], "stage:seedling->mature")

    def test_invalid_state_environment_and_rules_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TreeState("tree", 0, TreeStage.SEEDLING, 1.1, 0.2, 0.5)
        with self.assertRaises(ValueError):
            EnvironmentSample(TimePhase.SHAOYANG, moisture=float("nan"), light=0.5)
        with self.assertRaises(ValueError):
            EvolutionRules(version="unrecognized.rules.v9")
        with self.assertRaises(ValueError):
            EvolutionRules(phase_growth_multipliers=((TimePhase.SHAOYANG, 1.0),))

    def test_only_the_next_contiguous_tick_is_accepted(self) -> None:
        environment = EnvironmentSample(TimePhase.SHAOYANG, moisture=0.5, light=0.5)
        with self.assertRaises(ValueError):
            advance_tree(self.initial, environment, logical_tick=2)
        with self.assertRaises(ValueError):
            advance_tree(self.initial, environment, logical_tick=True)

    def test_drought_can_kill_tree_and_dead_state_stops_growing(self) -> None:
        near_dead = TreeState("tree-2", 0, TreeStage.SEEDLING, 0.06, 0.4, 0.2)
        drought = EnvironmentSample(TimePhase.TAIYIN, moisture=0.0, light=1.0)
        died = advance_tree(near_dead, drought, 1)
        self.assertIs(died.state.stage, TreeStage.DEAD)
        self.assertEqual(died.state.biomass, near_dead.biomass)
        self.assertIn("stage:seedling->dead", died.reasons)

        dead_next = advance_tree(died.state, drought, 2)
        self.assertIs(dead_next.state.stage, TreeStage.DEAD)
        self.assertEqual(dead_next.state.biomass, died.state.biomass)
        self.assertIn("dead_no_growth", dead_next.reasons)

    def test_declining_stage_does_not_move_backward_after_recovery(self) -> None:
        declining = TreeState("tree-3", 19, TreeStage.DECLINING, 0.20, 0.7, 0.5)
        wet = EnvironmentSample(TimePhase.SHAOYANG, moisture=1.0, light=0.0)
        result = advance_tree(declining, wet, 20)
        self.assertIs(result.state.stage, TreeStage.DECLINING)
        self.assertGreater(result.state.health, declining.health)
        self.assertNotIn("stage:declining->mature", result.reasons)

    def test_all_state_resources_remain_in_declared_bounds(self) -> None:
        state = self.initial
        for tick in range(1, 41):
            phase = tuple(TimePhase)[tick % len(TimePhase)]
            moisture = (tick % 5) / 4
            light = ((tick * 3) % 5) / 4
            result = advance_tree(state, EnvironmentSample(phase, moisture, light), tick)
            state = result.state
            self.assertGreaterEqual(state.health, 0.0)
            self.assertLessEqual(state.health, 1.0)
            self.assertGreaterEqual(state.biomass, 0.0)
            self.assertLessEqual(state.biomass, 1.0)
            self.assertGreaterEqual(state.water_reserve, 0.0)
            self.assertLessEqual(state.water_reserve, 1.0)


if __name__ == "__main__":
    unittest.main()
