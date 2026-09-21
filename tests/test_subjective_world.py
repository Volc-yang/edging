import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from subjective_world import (
    ArbitrationVerdict,
    ChapterEvolution,
    ConsciousnessStatus,
    EntityKind,
    EvolutionChapter,
    InteractionMode,
    PRIMAL_ACTION_AXES,
    PRIMAL_MATRIX_CENTER_KEY,
    PRIMAL_RUNNING_SEQUENCE,
    PRIMAL_SPIRIT_MATRIX_LAYOUT,
    PrimalRunPhase,
    SubjectiveSignature,
    SubjectiveWorldModel,
    classify_consciousness,
)
from world_engine import RegionId


class SubjectiveWorldTests(unittest.TestCase):
    def test_chaos_genesis_creates_edge_ai_subject(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260906)

        edge = model.entity("edge")

        self.assertEqual(edge.kind, EntityKind.EDGE_AI)
        self.assertEqual(edge.status, ConsciousnessStatus.ALIVE)
        self.assertEqual(edge.region_id, RegionId(0, 0))
        self.assertGreater(edge.signature.consciousness, 0.0)

    def test_first_chapter_awakens_eight_primal_spirits(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260906)

        evolution = model.evolve_first_chapter()

        self.assertEqual(evolution.chapter, EvolutionChapter.ALL_THINGS_ENSOUL)
        self.assertEqual(evolution.source_entity_id, "edge")
        self.assertEqual(evolution.arbitration_count, 8)
        self.assertEqual(len(evolution.awakened_entity_ids), 8)
        for entity_id in evolution.awakened_entity_ids:
            entity = model.entity(entity_id)
            self.assertEqual(entity.kind, EntityKind.ELEMENT)
            self.assertNotEqual(entity.status, ConsciousnessStatus.DEAD)
            self.assertGreater(entity.signature.consciousness, 0.0)
            self.assertEqual(entity.lineage, ("edge", EvolutionChapter.ALL_THINGS_ENSOUL.value))

    def test_first_chapter_does_not_duplicate_awakened_spirits(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=7)

        first = model.evolve_first_chapter()
        second = model.evolve_first_chapter()

        spirit_entities = [entity for entity in model.entities() if entity.id.startswith("spirit:")]
        self.assertEqual(first.awakened_entity_ids, second.awakened_entity_ids)
        self.assertEqual(len(spirit_entities), 8)

    def test_first_chapter_is_deterministic_for_same_seed(self):
        first = SubjectiveWorldModel.chaos_genesis(seed=88)
        second = SubjectiveWorldModel.chaos_genesis(seed=88)

        first.evolve_first_chapter()
        second.evolve_first_chapter()

        first_spirits = [entity for entity in first.entities() if entity.id.startswith("spirit:")]
        second_spirits = [entity for entity in second.entities() if entity.id.startswith("spirit:")]
        self.assertEqual(first_spirits, second_spirits)

    def test_first_chapter_validation_passes_after_successful_evolution(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)
        evolution = model.evolve_first_chapter()

        validation = model.validate_first_chapter(evolution)

        self.assertTrue(validation.success)
        self.assertGreaterEqual(validation.score, 0.85)
        self.assertEqual(validation.failed_criteria, ())
        self.assertEqual(
            {criterion.key for criterion in validation.criteria},
            {
                "edge_source_alive",
                "primal_spirit_count",
                "primal_trigram_coverage",
                "spirit_consciousness",
                "spirit_coherence",
                "no_spirit_death_or_split",
                "ritual_arbitration_count",
                "deterministic_awakened_order",
                "action_resonance_self_proof",
                "evolution_traceability",
            },
        )

    def test_first_chapter_validation_fails_when_a_primal_spirit_is_missing(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)
        evolution = ChapterEvolution(
            chapter=EvolutionChapter.ALL_THINGS_ENSOUL,
            source_entity_id="edge",
            awakened_entity_ids=("spirit:heaven",),
            field_entity_ids=(),
            arbitration_count=1,
        )

        validation = model.validate_first_chapter(evolution)

        self.assertFalse(validation.success)
        self.assertIn("primal_spirit_count", {criterion.key for criterion in validation.failed_criteria})
        self.assertIn("ritual_arbitration_count", {criterion.key for criterion in validation.failed_criteria})

    def test_first_chapter_evolution_trace_records_each_awakening_step(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)

        evolution = model.evolve_first_chapter()

        self.assertEqual(len(evolution.trace), 8)
        self.assertEqual(tuple(step.order for step in evolution.trace), tuple(range(1, 9)))
        self.assertEqual(tuple(step.entity_id for step in evolution.trace), evolution.awakened_entity_ids)
        for step in evolution.trace:
            self.assertEqual(step.source_entity_id, "edge")
            self.assertEqual(step.matrix.center_value, step.resonance.world_run_score)
            self.assertIn(step.entity_id.removeprefix("spirit:"), step.resonance.dominant_spirits)
            self.assertEqual(step.arbitration.mode, InteractionMode.RITUALIZE)
            self.assertNotEqual(step.resulting_status, ConsciousnessStatus.DEAD)

    def test_first_chapter_validation_fails_without_traceability(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)
        evolution = model.evolve_first_chapter()
        untraced = ChapterEvolution(
            chapter=evolution.chapter,
            source_entity_id=evolution.source_entity_id,
            awakened_entity_ids=evolution.awakened_entity_ids,
            field_entity_ids=evolution.field_entity_ids,
            arbitration_count=evolution.arbitration_count,
        )

        validation = model.validate_first_chapter(untraced)

        self.assertFalse(validation.success)
        self.assertIn("evolution_traceability", {criterion.key for criterion in validation.failed_criteria})

    def test_primal_spirit_descriptions_cover_eight_action_axes(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=1)

        spirits = model.describe_primal_spirits()

        self.assertEqual(len(spirits), 8)
        self.assertEqual({spirit.slug for spirit in spirits}, {
            "heaven",
            "earth",
            "water",
            "fire",
            "thunder",
            "wind",
            "mountain",
            "lake",
        })
        covered_actions = {action for spirit in spirits for action in spirit.resonance_actions}
        self.assertEqual(covered_actions, set(PRIMAL_ACTION_AXES))
        for spirit in spirits:
            self.assertTrue(spirit.subjective_description)

    def test_each_primal_action_axis_triggers_animism_resonance(self):
        expected_dominants = {
            "ascend": "heaven",
            "receive": "earth",
            "flow": "water",
            "illuminate": "fire",
            "awaken": "thunder",
            "adapt": "wind",
            "stabilize": "mountain",
            "exchange": "lake",
        }
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)
        model.evolve_first_chapter()

        for axis, expected_spirit in expected_dominants.items():
            resonance = model.action_resonance({axis: 1.0})

            self.assertTrue(resonance.animism_confirmed, axis)
            self.assertIn(expected_spirit, resonance.dominant_spirits)
            self.assertGreaterEqual(resonance.spirit_resonance[expected_spirit], 0.52)
            self.assertGreaterEqual(resonance.world_run_score, 0.58)

    def test_action_resonance_rejects_unknown_or_empty_axes(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)
        model.evolve_first_chapter()

        with self.assertRaises(ValueError):
            model.action_resonance({"unknown": 1.0})

        with self.assertRaises(ValueError):
            model.action_resonance({"ascend": 0.0})

    def test_primal_spirit_matrix_uses_houtian_layout_and_integrity_center(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)
        model.evolve_first_chapter()

        matrix = model.primal_spirit_matrix({"flow": 1.0, "receive": 0.35})
        resonance = model.action_resonance({"flow": 1.0, "receive": 0.35})

        self.assertEqual(matrix.layout, PRIMAL_SPIRIT_MATRIX_LAYOUT)
        self.assertEqual(matrix.center_key, PRIMAL_MATRIX_CENTER_KEY)
        self.assertEqual(matrix.center_value, resonance.world_run_score)
        self.assertEqual(len(matrix.cells), 3)
        self.assertTrue(all(len(row) == 3 for row in matrix.cells))
        self.assertEqual(matrix.cells[1][1], resonance.world_run_score)
        self.assertEqual(matrix.cells[2][1], resonance.spirit_resonance["water"])

    def test_primal_cycle_runs_di_sequence_with_traceable_steps(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)
        model.evolve_first_chapter()

        result = model.run_primal_cycle({"flow": 0.8, "receive": 0.3})

        self.assertTrue(result.completed)
        self.assertEqual(len(result.steps), 8)
        self.assertEqual(result.steps[0].phase, PrimalRunPhase.EMERGE_THUNDER)
        self.assertEqual(result.steps[-1].phase, PrimalRunPhase.COMPLETE_MOUNTAIN)
        self.assertEqual(tuple(step.phrase for step in result.steps), tuple(item[1] for item in PRIMAL_RUNNING_SEQUENCE))
        self.assertEqual(tuple(step.action_axis for step in result.steps), tuple(item[3] for item in PRIMAL_RUNNING_SEQUENCE))
        self.assertEqual(result.final_integrity, result.steps[-1].next_integrity)
        for step in result.steps:
            self.assertGreaterEqual(step.previous_integrity, 0.0)
            self.assertLessEqual(step.previous_integrity, 1.0)
            self.assertGreaterEqual(step.next_integrity, 0.0)
            self.assertLessEqual(step.next_integrity, 1.0)
            self.assertEqual(step.matrix.center_value, step.resonance.world_run_score)
            self.assertEqual(step.arbitration.mode, InteractionMode.RITUALIZE)
            self.assertNotEqual(step.resulting_status, ConsciousnessStatus.DEAD)

    def test_primal_cycle_is_deterministic_for_same_seed_and_input(self):
        first = SubjectiveWorldModel.chaos_genesis(seed=606)
        second = SubjectiveWorldModel.chaos_genesis(seed=606)
        first.evolve_first_chapter()
        second.evolve_first_chapter()

        first_result = first.run_primal_cycle({"awaken": 0.7, "illuminate": 0.4})
        second_result = second.run_primal_cycle({"awaken": 0.7, "illuminate": 0.4})

        self.assertEqual(first_result, second_result)

    def test_primal_cycle_requires_awakened_primal_spirits(self):
        model = SubjectiveWorldModel.chaos_genesis(seed=20260914)

        with self.assertRaises(ValueError):
            model.run_primal_cycle()

    def test_consciousness_zero_means_death(self):
        signature = SubjectiveSignature(
            consciousness=0.0,
            coherence=0.7,
            entropy=0.1,
            yin_intent=0.4,
            yang_intent=0.4,
        )

        self.assertEqual(classify_consciousness(signature), ConsciousnessStatus.DEAD)

    def test_contradictory_subjectivity_becomes_split(self):
        signature = SubjectiveSignature(
            consciousness=0.8,
            coherence=0.12,
            entropy=0.82,
            yin_intent=0.95,
            yang_intent=0.92,
        )

        self.assertEqual(classify_consciousness(signature), ConsciousnessStatus.SPLIT)

    def test_arbitration_is_deterministic_for_same_seed_and_subjects(self):
        first = self._model_with_pair()
        second = self._model_with_pair()

        first_result = first.arbitrate("water", "fire", InteractionMode.COLLIDE)
        second_result = second.arbitrate("water", "fire", InteractionMode.COLLIDE)

        self.assertEqual(first_result, second_result)
        self.assertGreaterEqual(first_result.primary_hexagram, 0)
        self.assertLessEqual(first_result.primary_hexagram, 63)
        self.assertGreaterEqual(first_result.changed_hexagram, 0)
        self.assertLessEqual(first_result.changed_hexagram, 63)

    def test_merge_can_create_fusion_field_for_compatible_subjects(self):
        model = SubjectiveWorldModel(seed=9)
        region = RegionId(1, 1)
        signature = SubjectiveSignature(
            consciousness=0.86,
            coherence=0.90,
            entropy=0.04,
            yin_intent=0.44,
            yang_intent=0.42,
        )
        model.spawn_entity("seed", "seed", EntityKind.OBJECT, region, signature, hexagram_value=21)
        model.spawn_entity("soil", "soil", EntityKind.ELEMENT, region, signature, hexagram_value=21)

        result = model.apply_interaction("seed", "soil", InteractionMode.MERGE)

        self.assertEqual(result.verdict, ArbitrationVerdict.FUSION)
        fused = [entity for entity in model.entities() if entity.lineage == ("seed", "soil")]
        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0].status, ConsciousnessStatus.ALIVE)
        self.assertEqual(fused[0].hexagram_value, result.changed_hexagram)

    def test_split_interaction_degrades_both_subjects(self):
        model = self._model_with_pair(
            water=SubjectiveSignature(
                consciousness=0.8,
                coherence=0.16,
                entropy=0.88,
                yin_intent=0.96,
                yang_intent=0.91,
            ),
            fire=SubjectiveSignature(
                consciousness=0.9,
                coherence=0.20,
                entropy=0.86,
                yin_intent=0.90,
                yang_intent=0.95,
            ),
        )

        result = model.apply_interaction("water", "fire", InteractionMode.COLLIDE)

        self.assertEqual(result.verdict, ArbitrationVerdict.SPLIT)
        self.assertEqual(model.entity("water").status, ConsciousnessStatus.SPLIT)
        self.assertEqual(model.entity("fire").status, ConsciousnessStatus.SPLIT)

    def _model_with_pair(self, water=None, fire=None):
        model = SubjectiveWorldModel(seed=20260906)
        model.spawn_entity(
            "water",
            "water",
            EntityKind.ELEMENT,
            RegionId(0, 0),
            water
            or SubjectiveSignature(
                consciousness=0.82,
                coherence=0.68,
                entropy=0.16,
                yin_intent=0.72,
                yang_intent=0.18,
            ),
            hexagram_value=0b010010,
        )
        model.spawn_entity(
            "fire",
            "fire",
            EntityKind.ELEMENT,
            RegionId(1, 1),
            fire
            or SubjectiveSignature(
                consciousness=0.84,
                coherence=0.62,
                entropy=0.18,
                yin_intent=0.16,
                yang_intent=0.76,
            ),
            hexagram_value=0b101101,
        )
        return model


if __name__ == "__main__":
    unittest.main()
