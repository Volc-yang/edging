"""Directed I19 synthetic receipt checks; these are never real UE/input/PNG evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.universe_iteration import actions as a, probe_actions as p
from tests.test_universe_iteration_actions import encoded
from tests.test_universe_iteration_actions_v2 import V2Fixture
from tests.test_universe_iteration_probe import ProbeFixture


class SliceFixture(ProbeFixture):
    def __init__(self, root):
        self.root, self.serial, self.counter = root, 0, 0
        self.binding = dict(run_id='synthetic-i19', session='existing', world_id='test-world',
                            authority_root=str(root/'authority'), source_sha='a'*40,
                            host_pid=120, worker_pid=121, generation=1)
        self.context = dict(principal='test-owner', trust_anchor='b'*64,
                            expected_build='c'*64, expected_options='d'*64)
        self.clock = dict(id='synthetic-i19-clock', anchor_monotonic=0,
                          anchor_utc='2026-11-09T00:00:00+00:00')
        self.items = p.probe_manifest_v2()['items']
        self.frames = self.make_frames()
        self.trace_refs = self.write_trace(self.frames)
        self.v2 = True
        with patch.object(a, 'READBACK_V2', p.READBACK_FORMAT):
            V2Fixture.build_receipts(self)
        for receipt, item in zip(self.receipts, self.items):
            receipt['format'] = p.FORMAT_V2
            cua = json.loads(a.reference(receipt['cua']))
            cua['format'] = p.CUA_FORMAT_V2
            for call, command in zip(cua['calls'], item['commands']):
                call.update(step_id=command['step_id'], physical_operation_count=3,
                            physical_operations=[{'operation': name, 'arguments': {'synthetic': True}}
                                                 for name in ('pressKey', 'typeText', 'pressKey')])
            receipt['cua'] = self.ref(cua)
            receipt['image_checks'] = [dict(capture_id=item['action_id']+'/'+stage, stage=stage,
                                            capture_ref=self.ref({'synthetic_capture_only': True}))
                                       for stage in item['image_stages']]

    def check(self, receipt):
        return p.validate_probe_receipt_v2(receipt, expected_binding=self.binding,
                                          frames=self.frames, expected_context=self.context)

    def full(self, receipts=None, trace_refs=None):
        return p.validate_probe_evidence_v2(self.receipts if receipts is None else receipts,
                                            self.trace_refs if trace_refs is None else trace_refs,
                                            expected_binding=self.binding, expected_context=self.context,
                                            expected_before_map_ref=self.receipts[0]['before'],
                                            expected_after_map_ref=self.receipts[-1]['after'])

    def rewrite_marker(self, receipt, stage, edit):
        event = next(e for e in receipt['checkpoints'] if e['stage'] == stage)
        raw = a.reference(receipt['log']['ref'])
        line = raw[event['log_start']:event['log_end']]
        value = json.loads(line.split(b'EW_I13_READBACK ')[1])
        edit(value)
        replacement = b'LogTemp: Display: EW_I13_READBACK '+encoded(value)
        delta = len(replacement)-len(line)
        raw = raw[:event['log_start']]+replacement+raw[event['log_end']:]
        old_end = event['log_end']
        event['log_end'] += delta
        for other in receipt['checkpoints']:
            if other['log_start'] >= old_end:
                other['log_start'] += delta
                other['log_end'] += delta
        cua = json.loads(a.reference(receipt['cua']))
        for call in cua['calls']:
            for field in ('log_before_offset', 'log_after_offset'):
                if call[field] >= old_end:
                    call[field] += delta
        receipt['cua'] = self.ref(cua)
        ref = self.ref(raw, '.log')
        st = Path(ref['path']).stat()
        receipt['log'].update(ref=ref, device=st.st_dev, inode=st.st_ino,
                              after_offset=receipt['log']['after_offset']+delta)


class SliceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.f = SliceFixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def receipt(self, action):
        return deepcopy(next(r for r in self.f.receipts if r['action_id'] == action))

    def test_narrow_scope_counts_and_legacy_are_distinct(self):
        manifest = p.probe_manifest_v2()
        self.assertEqual(sum(len(i['commands']) for i in manifest['items']), 14)
        self.assertEqual(sum(len(i['image_stages']) for i in manifest['items']), 1)
        self.assertEqual(sum(i['max_seconds'] for i in manifest['items'] if i['phase'] == 'interaction'), 295)
        self.assertEqual(manifest['expected_operations'], ['status', 'observe', 'observe'])
        self.assertEqual(manifest['new_observe_response_count'], 2)
        self.assertEqual(p.probe_manifest()['call_count'], 48)
        self.assertEqual(p.probe_manifest()['image_count'], 8)
        for item in manifest['items']:
            self.assertAlmostEqual(sum(c['max_seconds'] for c in item['commands'])+
                                   sum(item['passive_costs'].values()), item['max_seconds'])
        result = self.f.full()
        self.assertEqual(result['logical_step_count'], 14)
        self.assertEqual(result['physical_operation_count'], 42)
        self.assertFalse(result['runtime_authenticity_verified'])
        self.assertFalse(result['g_b2_granted'])
        with self.assertRaises(p.Invalid):
            p.validate_probe_evidence(self.f.receipts, self.f.trace_refs,
                                     expected_binding=self.f.binding, expected_context=self.f.context,
                                     expected_before_map_ref=self.f.receipts[0]['before'],
                                     expected_after_map_ref=self.f.receipts[-1]['after'])

    def test_wall_round_trip_twelve_seconds_is_counted_twenty_is_boundary(self):
        for duration, accepted in ((12, True), (20, True), (20.001, False)):
            receipt = self.receipt('p1.history')
            cua = json.loads(a.reference(receipt['cua']))
            call = cua['calls'][0]
            call['completed_monotonic'] = call['started_monotonic']+duration
            receipt['completed_monotonic'] = call['completed_monotonic']+.2
            receipt['checkpoints'][0]['read_monotonic'] = call['completed_monotonic']+.1
            receipt['cua'] = self.f.ref(cua)
            if accepted:
                self.f.check(receipt)
            else:
                with self.assertRaises(p.Invalid): self.f.check(receipt)

    def test_physical_list_and_count_cannot_be_omitted_or_misreported(self):
        for edit in (lambda c:c.pop('physical_operations'),
                     lambda c:c.update(physical_operation_count=1),
                     lambda c:c.update(physical_operation_count=True),
                     lambda c:c.update(physical_operations=[]),
                     lambda c:c['physical_operations'][0].update(arguments='not-an-object')):
            receipt = self.receipt('p1.history')
            receipt['cua'] = self.f.edit_reference(receipt['cua'], lambda v:edit(v['calls'][0]))
            with self.assertRaises(p.Invalid): self.f.check(receipt)

    def test_history_selected_and_current_trusted_remain_distinct_through_final(self):
        final = self.receipt('p1.final')
        self.assertEqual(final['trusted_head'], a.H2)
        self.assertEqual(final['selected_observation'], a.H1)
        self.f.check(final)
        for field in ('trusted_head', 'selected_observation'):
            bad = deepcopy(final)
            bad[field] = deepcopy(a.H1 if field == 'trusted_head' else a.H2)
            with self.assertRaises(p.Invalid): self.f.check(bad)
        self.f.rewrite_marker(final, 'released_and_restored', lambda v:v.update(selected_observation=a.H2))
        with self.assertRaises(p.Invalid): self.f.check(final)

    def test_real_input_origin_reason_and_exact_handler_increment_are_required(self):
        for edit in (lambda v:v.update(origin='query'),
                     lambda v:v['state']['handled_input'].update(reason='not_ready'),
                     lambda v:v['state']['handled_input'].update(counter_after=3),
                     lambda v:v['state']['handled_input'].update(handled=False)):
            receipt = self.receipt('p1.history_write_rejected')
            self.f.rewrite_marker(receipt, 'space_rejected', edit)
            with self.assertRaises(p.Invalid): self.f.check(receipt)

    def test_extra_operation_deferred_action_and_missing_stage_still_fail(self):
        frames = deepcopy(self.f.frames)
        frames[-1]['request']['operation'] = 'prepare'
        with self.assertRaises(p.Invalid): self.f.full(trace_refs=self.f.write_trace(frames))
        receipts = deepcopy(self.f.receipts)
        receipts.insert(2, self.receipt('p1.probe'))
        receipts[2]['action_id'] = 'p1.camera'
        with self.assertRaises(p.Invalid): self.f.full(receipts)
        receipt = self.receipt('p1.history_write_rejected')
        receipt['checkpoints'].pop()
        with self.assertRaises(p.Invalid): self.f.check(receipt)

    def test_interaction_gaps_are_not_removed_from_wall_cost(self):
        receipts = deepcopy(self.f.receipts)
        # Keep valid per-action ordering/intervals but insert a large scheduling gap.
        for receipt in receipts[2:]:
            receipt['started_monotonic'] += 300
            receipt['completed_monotonic'] += 300
            for event in receipt['checkpoints']: event['read_monotonic'] += 300
            def shift(cua):
                for call in cua['calls']:
                    call['started_monotonic'] += 300
                    call['completed_monotonic'] += 300
            receipt['cua'] = self.f.edit_reference(receipt['cua'], shift)
        with self.assertRaisesRegex(p.Invalid, 'interaction wall'):
            self.f.full(receipts)

    def test_late_marker_wrong_step_and_stale_map_fail(self):
        for edit in (lambda r:r['checkpoints'][0].update(read_monotonic=r['completed_monotonic']+1),
                     lambda r:r['checkpoints'][0].update(map=r['before'])):
            receipt = self.receipt('p1.history')
            edit(receipt)
            with self.assertRaises(p.Invalid): self.f.check(receipt)
        receipt = self.receipt('p1.history')
        receipt['cua'] = self.f.edit_reference(receipt['cua'], lambda v:v['calls'][0].update(step_id='p1.history/99'))
        with self.assertRaises(p.Invalid): self.f.check(receipt)

    def test_schema_requires_physical_details_without_changing_old_schema(self):
        schema = p.probe_schema_v2()
        self.assertEqual(schema['properties']['format'], {'const': p.FORMAT_V2})
        self.assertEqual(schema['$defs']['readback']['properties']['format'], {'const': p.READBACK_FORMAT})
        required = schema['$defs']['cua']['properties']['calls']['items']['required']
        self.assertIn('physical_operations', required)
        self.assertIn('physical_operation_count', required)
        self.assertNotIn('physical_operations', p.probe_schema()['$defs']['cua']['properties']['calls']['items']['required'])


if __name__ == '__main__': unittest.main()
