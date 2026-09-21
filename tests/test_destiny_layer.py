"""Tests for the destiny layer (risk R3: wiring the edging 64D/384 scorer in)."""

import shutil
import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR))

from destiny_layer import (
    ACTION_AXES,
    DESTINY_SCHEMA_VERSION,
    EDGING_DIMENSIONS,
    DestinyLayer,
    EdgingDeterministicScorer,
    ScorerUnavailable,
    build_observation_yaml,
    derive_observation,
)

RUBY_AVAILABLE = shutil.which("ruby") is not None
SCORER_PRESENT = (REPO_ROOT / "edging" / "bin" / "deterministic_scorer.rb").exists()
REAL_SCORER = RUBY_AVAILABLE and SCORER_PRESENT


def minimal_snapshot(tick=3, governing_position=3, changing=(2, 3), pressures=None):
    pressures = pressures or {"awaken": 0.8, "illuminate": 0.6, "stabilize": 0.2}
    return {
        "schema_version": "edgeworld.chapter-one-snapshot.v2",
        "tick": tick,
        "validation": {"score": 0.9},
        "cycle": {"completed": True, "final_integrity": 0.6},
        "decision": {"source": "rule_fallback", "model": "none", "action_intents": dict(pressures)},
        "encounter": {
            "primary_hexagram": {"name": "无妄"},
            "changed_hexagram": {"name": "讼"},
            "changing_positions": list(changing),
            "governing_line": {"position": governing_position, "polarity": "yang", "name": "六三"},
            "abstraction": {
                "declared_action_axis": "awaken",
                "player_expression": "玩家唤醒眼前之物。",
                "combined_action_pressures": pressures,
                "line_evidence": [{"position": 2, "score": 0.7}],
            },
        },
        "spirits": [
            {
                "slug": f"spirit{i}",
                "entity": {
                    "signature": {
                        "consciousness": 0.5 + 0.05 * i,
                        "coherence": 0.4 + 0.05 * i,
                        "entropy": 0.001 * i,
                        "yin_intent": 0.5,
                        "yang_intent": 0.5,
                    }
                },
            }
            for i in range(8)
        ],
    }


class DeriveObservationTests(unittest.TestCase):
    def test_every_edging_dimension_is_produced_within_range(self):
        vector, derivation = derive_observation(minimal_snapshot())
        self.assertEqual(set(EDGING_DIMENSIONS), set(vector))
        self.assertEqual(set(EDGING_DIMENSIONS), set(derivation))
        for name, value in vector.items():
            with self.subTest(dimension=name):
                self.assertIsInstance(value, float)
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_derivation_explains_every_dimension(self):
        _, derivation = derive_observation(minimal_snapshot())
        for name, explanation in derivation.items():
            with self.subTest(dimension=name):
                self.assertIsInstance(explanation, str)
                self.assertGreater(len(explanation), 10)

    def test_empty_snapshot_still_yields_a_bounded_vector(self):
        vector, _ = derive_observation({})
        self.assertEqual(set(EDGING_DIMENSIONS), set(vector))
        for value in vector.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_constraint_pressure_follows_the_governing_line_position(self):
        low, _ = derive_observation(minimal_snapshot(governing_position=1))
        mid, _ = derive_observation(minimal_snapshot(governing_position=3))
        high, _ = derive_observation(minimal_snapshot(governing_position=6))
        self.assertGreater(low["constraint_pressure"], mid["constraint_pressure"])
        self.assertGreater(mid["constraint_pressure"], high["constraint_pressure"])
        self.assertAlmostEqual(5 / 6, low["constraint_pressure"], places=6)
        self.assertAlmostEqual(0.0, high["constraint_pressure"], places=6)

    def test_coordination_is_one_minus_the_yin_yang_imbalance(self):
        snapshot = minimal_snapshot()
        for spirit in snapshot["spirits"]:
            spirit["entity"]["signature"]["yin_intent"] = 0.25
            spirit["entity"]["signature"]["yang_intent"] = 0.75
        vector, _ = derive_observation(snapshot)
        self.assertAlmostEqual(0.5, vector["coordination"], places=6)

    def test_visibility_and_stability_track_the_spirit_signatures(self):
        vector, _ = derive_observation(minimal_snapshot())
        consciousness = [0.5 + 0.05 * i for i in range(8)]
        coherence = [0.4 + 0.05 * i for i in range(8)]
        self.assertAlmostEqual(sum(consciousness) / 8, vector["visibility"], places=6)
        self.assertAlmostEqual(sum(coherence) / 8, vector["stability"], places=6)

    def test_agency_uses_the_declared_axis_pressure(self):
        weak, _ = derive_observation(minimal_snapshot(pressures={"awaken": 0.1, "flow": 0.1}))
        strong, _ = derive_observation(minimal_snapshot(pressures={"awaken": 1.0, "flow": 1.0}))
        self.assertLess(weak["agency"], strong["agency"])

    def test_risk_exposure_normalises_entropy(self):
        vector, _ = derive_observation(minimal_snapshot())
        entropies = [0.001 * i for i in range(8)]
        expected = min(1.0, (sum(entropies) / 8) / 0.05)
        self.assertAlmostEqual(expected, vector["risk_exposure"], places=6)

    def test_deterministic_for_the_same_snapshot(self):
        first, _ = derive_observation(minimal_snapshot())
        second, _ = derive_observation(minimal_snapshot())
        self.assertEqual(first, second)

    def test_momentum_counts_the_changing_lines(self):
        few, _ = derive_observation(minimal_snapshot(changing=(1,)))
        many, _ = derive_observation(minimal_snapshot(changing=(1, 2, 3, 4, 5, 6)))
        self.assertLess(few["momentum"], many["momentum"])


class ObservationYamlTests(unittest.TestCase):
    def test_renders_the_scorer_input_contract(self):
        text = build_observation_yaml({d: 0.5 for d in EDGING_DIMENSIONS}, free_text="hi", context_tags=["a", "b"])
        self.assertIn("observation_input:", text)
        self.assertIn("subject_type: non_human_object", text)
        for dimension in EDGING_DIMENSIONS:
            self.assertIn(f"    {dimension}: 0.500000", text)
        self.assertIn("    - a", text)

    def test_escapes_quotes_newlines_and_backslashes(self):
        text = build_observation_yaml({d: 0.1 for d in EDGING_DIMENSIONS}, free_text='say "hi"\nnow\\then')
        self.assertIn('\\"hi\\"', text)
        self.assertNotIn("\nnow", text.replace("\n", "", 1))
        self.assertIn("\\\\then", text)

    def test_rejects_a_vector_missing_a_dimension(self):
        with self.assertRaises(ScorerUnavailable):
            build_observation_yaml({"agency": 0.5})


class ScorerAvailabilityTests(unittest.TestCase):
    def test_missing_script_reports_a_reason_without_raising(self):
        scorer = EdgingDeterministicScorer(Path("/nonexistent-repo-root"))
        available, reason = scorer.available()
        self.assertFalse(available)
        self.assertIn("not found", reason)

    def test_score_raises_when_unavailable(self):
        scorer = EdgingDeterministicScorer(Path("/nonexistent-repo-root"))
        with self.assertRaises(ScorerUnavailable):
            scorer.score("observation_input: {}")


class DestinyLayerTests(unittest.TestCase):
    def test_disabled_layer_marks_itself_without_calling_the_scorer(self):
        block = DestinyLayer(REPO_ROOT, enabled=False).evaluate(minimal_snapshot())
        self.assertEqual("disabled", block["source"])
        self.assertEqual(DESTINY_SCHEMA_VERSION, block["schema_version"])
        self.assertEqual(set(EDGING_DIMENSIONS), set(block["feature_vector"]))

    def test_unavailable_scorer_degrades_instead_of_raising(self):
        block = DestinyLayer(Path("/nonexistent-repo-root")).evaluate(minimal_snapshot())
        self.assertEqual("unavailable", block["source"])
        self.assertIn("reason", block)
        self.assertEqual([], block["top_families"])
        # The derived reading is still recorded, so the round stays auditable.
        self.assertEqual(set(EDGING_DIMENSIONS), set(block["feature_vector"]))

    @unittest.skipUnless(REAL_SCORER, "ruby and the edging scorer are required")
    def test_real_scorer_returns_bounded_family_and_prototype_readings(self):
        block = DestinyLayer(REPO_ROOT).evaluate(minimal_snapshot())
        self.assertEqual("edging-deterministic-scorer", block["source"])
        self.assertEqual("valid", block["validation_status"])
        self.assertTrue(block["top_families"], "expected ranked families")
        self.assertTrue(block["top_prototypes"], "expected ranked prototypes")
        self.assertLessEqual(len(block["top_families"]), 3)
        self.assertLessEqual(len(block["top_prototypes"]), 5)
        for family in block["top_families"]:
            self.assertIn("family_id", family)
            self.assertTrue(family["family_id"].startswith("hex_"), family["family_id"])
            self.assertIn("name_cn", family)
            self.assertIsInstance(family["score"], float)
        for prototype in block["top_prototypes"]:
            self.assertIn("prototype_id", prototype)
            self.assertTrue(1 <= prototype["line_index"] <= 6)
        self.assertIsNotNone(block["uncertainty"])
        self.assertIsNotNone(block["scorer_version"])

    @unittest.skipUnless(REAL_SCORER, "ruby and the edging scorer are required")
    def test_real_scorer_is_deterministic_for_the_same_round(self):
        layer = DestinyLayer(REPO_ROOT)
        first = layer.evaluate(minimal_snapshot())
        second = layer.evaluate(minimal_snapshot())
        self.assertEqual(first["top_families"], second["top_families"])
        self.assertEqual(first["top_prototypes"], second["top_prototypes"])
        self.assertEqual(first["feature_vector"], second["feature_vector"])


class StubClient:
    model = "stub-model"

    def propose(self, observation, tick):
        return {
            "schema_version": "edgeworld.chapter-one-decision.v2",
            "tick": tick,
            "action_intents": {"awaken": 0.9, "stabilize": 0.3},
            "rationale": "stub",
        }

    def present_encounter(self, rule_result, seed, tick):
        return {"text": "stub", "source": "stub"}


class RuntimeIntegrationTests(unittest.TestCase):
    """The runtime must attach the reading without letting it change the round."""

    def _runtime(self, **kwargs):
        from chapter_one_runtime import ChapterOneRuntime

        return ChapterOneRuntime(seed=20260920, **kwargs)

    def test_run_attaches_a_destiny_block(self):
        snapshot = self._runtime().run(tick=3, player_action="awaken", player_intensity=0.7)
        self.assertIn("destiny", snapshot)
        self.assertEqual(DESTINY_SCHEMA_VERSION, snapshot["destiny"]["schema_version"])
        self.assertEqual(set(EDGING_DIMENSIONS), set(snapshot["destiny"]["feature_vector"]))

    def test_destiny_does_not_change_the_hexagram_or_the_world_state(self):
        with_destiny = self._runtime(destiny=True).run(tick=5, player_action="flow", player_intensity=0.8)
        without_destiny = self._runtime(destiny=False).run(tick=5, player_action="flow", player_intensity=0.8)

        self.assertEqual(without_destiny["encounter"], with_destiny["encounter"])
        self.assertEqual(without_destiny["world_response"], with_destiny["world_response"])
        self.assertEqual(without_destiny["spirits"], with_destiny["spirits"])
        self.assertEqual(without_destiny["cycle"], with_destiny["cycle"])
        self.assertEqual("disabled", without_destiny["destiny"]["source"])
        # Deleting the two destiny blocks must leave byte-identical rounds.
        stripped_with = {k: v for k, v in with_destiny.items() if k != "destiny"}
        stripped_without = {k: v for k, v in without_destiny.items() if k != "destiny"}
        self.assertEqual(stripped_without, stripped_with)

    def test_snapshot_stays_json_serialisable(self):
        import json

        snapshot = self._runtime().run(tick=2)
        json.dumps(snapshot, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
