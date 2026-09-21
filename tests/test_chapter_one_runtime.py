import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from chapter_one_runtime import (
    DECISION_SCHEMA_VERSION,
    ChapterOneRuleValidator,
    ChapterOneRuntime,
    DecisionError,
)


class StubClient:
    model = "stub-model"

    def __init__(self, payload):
        self.payload = payload

    def propose(self, observation, tick):
        return self.payload


def valid_proposal():
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "tick": 1,
        "action_intents": {"flow": 0.9, "adapt": 0.4},
        "rationale": "以坎流通，以巽适应。",
    }


class ChapterOneRuntimeTests(unittest.TestCase):
    def test_validator_accepts_only_bounded_first_chapter_intents(self):
        decision = ChapterOneRuleValidator().validate(valid_proposal(), expected_tick=1)
        self.assertEqual(decision.focus_spirit, "water")
        self.assertEqual(decision.action_intents, {"flow": 0.9, "adapt": 0.4})

    def test_validator_rejects_unknown_axis_and_budget_overflow(self):
        unknown = valid_proposal()
        unknown["action_intents"] = {"destroy": 1.0}
        with self.assertRaises(DecisionError):
            ChapterOneRuleValidator().validate(unknown, expected_tick=1)

        over_budget = valid_proposal()
        over_budget["action_intents"] = {"flow": 1.0, "adapt": 1.0, "awaken": 1.0}
        with self.assertRaises(DecisionError):
            ChapterOneRuleValidator().validate(over_budget, expected_tick=1)

        attempted_hexagram_override = valid_proposal()
        attempted_hexagram_override["hexagram"] = "乾"
        with self.assertRaises(DecisionError):
            ChapterOneRuleValidator().validate(attempted_hexagram_override, expected_tick=1)

    def test_validator_derives_focus_from_strongest_action(self):
        proposal = valid_proposal()
        proposal["action_intents"] = {"flow": 0.4, "ascend": 0.9}
        decision = ChapterOneRuleValidator().validate(proposal, expected_tick=1)
        self.assertEqual(decision.focus_spirit, "heaven")

    def test_runtime_accepts_valid_model_proposal(self):
        snapshot = ChapterOneRuntime(seed=20260920, client=StubClient(valid_proposal())).run()
        self.assertEqual(snapshot["decision"]["source"], "ollama")
        self.assertTrue(snapshot["decision"]["accepted"])
        self.assertTrue(snapshot["validation"]["success"])
        self.assertTrue(snapshot["cycle"]["completed"])
        self.assertEqual(len(snapshot["spirits"]), 8)

    def test_runtime_falls_back_when_model_crosses_rule_boundary(self):
        invalid = valid_proposal()
        invalid["action_intents"] = {"rewrite_world": 1.0}
        snapshot = ChapterOneRuntime(seed=7, client=StubClient(invalid)).run()
        self.assertEqual(snapshot["decision"]["source"], "rule_fallback")
        self.assertFalse(snapshot["decision"]["accepted"])
        self.assertIn("outside Chapter One", snapshot["decision"]["fallback_reason"])

    def test_snapshot_is_json_serializable_and_written_atomically_enough_for_consumers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            ChapterOneRuntime(seed=3).write_snapshot(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "edgeworld.chapter-one-snapshot.v2")
        self.assertEqual(payload["decision"]["source"], "rule_fallback")

    def test_world_runs_xiantian_before_player_causes_houtian_change(self):
        snapshot = ChapterOneRuntime(seed=20260920).run(
            tick=1,
            player_action="flow",
            player_intensity=0.8,
            player_expression="玩家涉水前行。",
        )

        cosmology = snapshot["cosmology"]
        self.assertEqual(cosmology["world_order"], "xiantian_bagua")
        self.assertEqual(cosmology["change_order"], "houtian_bagua")
        self.assertEqual(cosmology["xiantian_world"]["spirit"], "heaven")
        self.assertEqual(cosmology["player_intervention"]["action_axis"], "flow")
        self.assertEqual(cosmology["houtian_transition"]["player_spirit"], "water")
        self.assertEqual(cosmology["houtian_transition"]["player_luoshu_number"], 1)

    def test_encounter_uses_zhouyi_text_and_rule_derived_changed_hexagram(self):
        snapshot = ChapterOneRuntime(seed=20260920).run(player_action="awaken", player_intensity=0.7)
        encounter = snapshot["encounter"]

        self.assertTrue(encounter["primary_hexagram"]["name"])
        self.assertIn("canonical_text_available", encounter["primary_hexagram"])
        self.assertTrue(encounter["primary_hexagram"]["structural_image"])
        self.assertTrue(encounter["changing_positions"])
        self.assertNotEqual(encounter["primary_hexagram"]["value"], encounter["changed_hexagram"]["value"])
        self.assertEqual(snapshot["presentation"]["source"], "rule_fallback")
        self.assertTrue(snapshot["presentation"]["scene"])
        self.assertTrue(snapshot["presentation"]["omen"])

    def test_intervention_is_abstracted_to_hexagram_and_one_governing_line(self):
        snapshot = ChapterOneRuntime(seed=20260920, client=StubClient(valid_proposal())).run(
            player_action="awaken",
            player_intensity=0.8,
            player_expression="玩家敲击石门，火光沿裂隙扩散。",
        )
        encounter = snapshot["encounter"]
        abstraction = encounter["abstraction"]
        governing_line = encounter["governing_line"]

        self.assertEqual(abstraction["player_expression"], "玩家敲击石门，火光沿裂隙扩散。")
        self.assertEqual(abstraction["upper_trigram_basis"], "xiantian_world_phase")
        self.assertEqual(abstraction["lower_trigram_basis"], "player_declared_action")
        self.assertEqual(
            abstraction["expression_action_evidence"],
            {
                "illuminate": {"pressure": 0.8, "matched_keywords": ["火"]},
                "awaken": {"pressure": 0.8, "matched_keywords": ["敲击"]},
                "adapt": {"pressure": 0.8, "matched_keywords": ["扩散"]},
            },
        )
        self.assertEqual(governing_line["position"], 3)
        self.assertEqual(governing_line["evidence_axes"], ["illuminate", "awaken"])
        self.assertTrue(governing_line["canonical_text_available"])
        self.assertTrue(governing_line["text"])

    def test_forecast_controls_subjective_world_and_reports_before_after_feedback(self):
        snapshot = ChapterOneRuntime(seed=20260920).run(
            tick=6,
            player_action="awaken",
            player_intensity=0.7,
            player_expression="玩家唤醒石像，石像喷出火焰。",
        )
        response = snapshot["world_response"]
        control = response["control"]
        feedback = response["feedback"]
        target = next(spirit for spirit in snapshot["spirits"] if spirit["slug"] == control["target_spirit"])

        self.assertTrue(response["forecast"]["primary_judgment"])
        self.assertTrue(response["forecast"]["governing_line_text"])
        self.assertEqual(feedback["status"], "applied")
        self.assertNotEqual(feedback["before"], feedback["after"])
        self.assertEqual(target["entity"]["signature"], feedback["after"])
        self.assertEqual(target["entity"]["hexagram_value"], snapshot["encounter"]["changed_hexagram"]["value"])

    def test_player_and_ai_pressures_determine_houtian_focus(self):
        snapshot = ChapterOneRuntime(seed=9, client=StubClient(valid_proposal())).run(
            player_action="flow", player_intensity=0.8
        )
        transition = snapshot["cosmology"]["houtian_transition"]
        self.assertEqual(transition["ai_focus_spirit"], "water")
        self.assertEqual(transition["focus_spirit"], "water")
        self.assertEqual(transition["direction"], "N")

    def test_player_intervention_is_validated_at_world_boundary(self):
        runtime = ChapterOneRuntime(seed=1)
        with self.assertRaises(ValueError):
            runtime.run(player_action="rewrite_world")
        with self.assertRaises(ValueError):
            runtime.run(player_intensity=0.0)


if __name__ == "__main__":
    unittest.main()
