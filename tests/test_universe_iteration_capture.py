"""Synthetic CPU-only negative boundaries; no UE/Metal/authority provenance claim."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zlib

MODULE = Path(__file__).resolve().parents[1] / 'scripts/universe_iteration/capture.py'
spec = importlib.util.spec_from_file_location('i13_capture_under_test', MODULE)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)


def png(width=2, height=2, color=6, filters=None, raw=None, between=b'', compressed=None):
    channels = 4 if color == 6 else 3
    if raw is None:
        filters = filters or [0] * height
        raw = b''.join(bytes([filters[y]]) + bytes(width * channels) for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, color, 0, 0, 0)) +
            between + chunk(b'IDAT', zlib.compress(raw) if compressed is None else compressed) + chunk(b'IEND', b''))


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # macOS /var is itself a symlink; use its canonical temporary root.
        self.root = Path(self.temp.name).resolve()
        self.authority = self.root / 'authority'; self.authority.mkdir()
        self.binding = dict(run_id='i13-test', session='initialize', world_id='synthetic-world',
                            authority_root=str(self.authority), source_sha='a' * 40,
                            host_pid=321, worker_pid=654, generation=1)
        self.head = dict(tick=1, revision=2, watermark=2)
        self.selected = dict(tick=0, revision=1, watermark=1)
        self.clock = dict(id='synthetic-controller', anchor_monotonic=100.,
                          anchor_utc='2000-01-01T00:00:00+00:00')
        self.now = 102.
        self.patches = [mock.patch.object(c.time, 'monotonic', side_effect=lambda: self.now),
                        mock.patch.object(c.time, 'sleep', side_effect=self.sleep)]
        for patch in self.patches: patch.start()
        self.log = self.root / 'ue.log'; self.log.write_bytes(b'verified observation\n')
        verification = self.write('strict-response.json', {'synthetic': 'verified upstream by test only'})
        self.observation = self.write('observation.json', dict(binding=self.binding, trusted_head=self.head,
            selected_observation=self.selected, clock_id=self.clock['id'], verified_monotonic=101.,
            verification_ref=verification))
        self.before = self.write('before-map.json', dict(root=str(self.authority), files={'HEAD': {'bytes': 2, 'sha256': 'b' * 64}}, bytes=2))
        self.after = self.write('after-map.json', dict(root=str(self.authority), files={'HEAD': {'bytes': 2, 'sha256': 'b' * 64}}, bytes=2))
        self.target = self.root / 'native.png'
        self.counter = 0

    def tearDown(self):
        for patch in reversed(self.patches): patch.stop()
        self.temp.cleanup()

    def sleep(self, seconds): self.now += seconds

    def write(self, name, value):
        path = self.root / name
        data = json.dumps(value, sort_keys=True).encode()
        with path.open('xb') as f: f.write(data)
        return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}

    def newref(self, value):
        self.counter += 1
        return self.write('mutation-%s.json' % self.counter, value)

    def readref(self, ref): return json.loads(Path(ref['path']).read_bytes())

    def expected(self):
        return dict(expected_binding=self.binding, expected_trusted_head=self.head,
                    expected_selected_observation=self.selected, expected_observation_ref=self.observation,
                    expected_clock=self.clock)

    def prepare(self, **updates):
        args = dict(target_path=self.target, expected_binding=self.binding, trusted_head=self.head,
                    selected_observation=self.selected, observation_ref=self.observation,
                    before_map_ref=self.before, before_map_monotonic=101., log_path=self.log,
                    log_offset=self.log.stat().st_size, clock=self.clock, expected_width=2, expected_height=2)
        args.update(updates)
        return c.prepare_native_shot(**args)

    def command(self, prepared, **updates):
        self.now = 103.
        p = self.readref(prepared['preparation_ref'])
        raw = self.write('cua-result.json', {'synthetic': 'raw native command result'})
        value = dict(format=c.FORMAT, phase='cua-command', preparation_ref=prepared['preparation_ref'],
                     command=prepared['command'], clock_id=self.clock['id'], start_monotonic=102.5,
                     end_monotonic=102.8, binding=self.binding, trusted_head=self.head,
                     selected_observation=self.selected, observation_ref=self.observation, cua_result_ref=raw,
                     log=dict(p['log'], after_offset=p['log']['before_offset']))
        value.update(updates)
        return self.newref(value)

    def collect(self, prepared=None, command=None, **updates):
        prepared = prepared or self.prepare()
        command = command or self.command(prepared)
        if not self.target.exists(): self.target.write_bytes(png())
        args = self.expected(); args.update(receipt_path=self.root / 'capture.json'); args.update(updates)
        return c.collect_native_shot(prepared['preparation_ref'], command, **args)

    def finish(self, capture, **updates):
        self.now = 105.
        raw = self.write('actual-exit-raw.json', {'synthetic': 'actual exit event'})
        exit_ref = self.write('before-exit.json', dict(format=c.FORMAT, phase='actual-before-exit',
            binding=self.binding, clock_id=self.clock['id'], before_exit_monotonic=104., exit_evidence_ref=raw))
        args = self.expected(); args.update(after_map_ref=self.after, after_map_monotonic=103.5,
            before_exit_monotonic=104., before_exit_ref=exit_ref); args.update(updates)
        return c.verify_native_shot(capture, **args)

    def reject_png(self, value, **kwargs):
        with self.assertRaises(c.CaptureError): c.decode_png(value, expected_width=2, expected_height=2, **kwargs)

    def test_end_to_end_history_has_separate_current_head_and_original_bytes(self):
        prepared = self.prepare()
        self.assertEqual(prepared['command'], 'Shot filename="%s" nosuffix' % self.target)
        capture = self.collect(prepared)
        self.assertEqual(self.readref(capture)['original_ref']['sha256'], hashlib.sha256(self.target.read_bytes()).hexdigest())
        result = self.finish(capture)
        self.assertEqual(result['phase'], 'checks_complete_requires_review')
        self.assertIn('independent review', result['scope'])
        self.assertEqual(list(self.authority.iterdir()), [])

    def test_png_rgb_rgba_and_all_filters_decode_pixels(self):
        for color in (2, 6):
            for mode in range(5):
                with self.subTest(color=color, mode=mode):
                    result = c.decode_png(png(color=color, filters=[mode, mode]), expected_width=2, expected_height=2)
                    self.assertEqual(result['decoded_pixel_sha256'], hashlib.sha256(bytes(2 * 2 * (3 if color == 2 else 4))).hexdigest())
        # Nonzero Paeth/Sub/Up/Average correctness; filtered rows reconstructed to the same pixels.
        pixels = [bytes([10, 20, 30, 40, 15, 25, 35, 45]), bytes([20, 30, 40, 50, 25, 35, 45, 55])]
        for mode in range(5):
            raw = bytearray()
            for y, row in enumerate(pixels):
                raw.append(mode)
                for x, value in enumerate(row):
                    a = row[x - 4] if x >= 4 else 0
                    b = pixels[y - 1][x] if y else 0
                    d = pixels[y - 1][x - 4] if y and x >= 4 else 0
                    p = a + b - d; dist = [abs(p-a), abs(p-b), abs(p-d)]
                    predictor = [0, a, b, (a+b)//2, [a,b,d][dist.index(min(dist))]][mode]
                    raw.append((value-predictor) & 255)
            got = c.decode_png(png(raw=bytes(raw)), expected_width=2, expected_height=2)
            self.assertEqual(got['decoded_pixel_sha256'], hashlib.sha256(b''.join(pixels)).hexdigest())

    def test_png_magic_truncation_crc_trailing_dimensions_and_limits(self):
        good = png()
        values = [b'\xff\xd8jpeg', b'v/1\x01EXR', good[:8], good[:-1], good + b'x',
                  good[:40] + bytes([good[40] ^ 1]) + good[41:], png(width=3)]
        for value in values:
            with self.subTest(length=len(value)): self.reject_png(value)
        with self.assertRaises(c.CaptureError): c.decode_png(good, expected_width=True, expected_height=2)
        with self.assertRaises(c.CaptureError): c.decode_png(good, expected_width=2**30, expected_height=2**30)
        with mock.patch.object(c, 'MAX_PNG_BYTES', len(good)-1): self.reject_png(good)
        with mock.patch.object(c, 'MAX_DECODED_BYTES', 1): self.reject_png(good)

    def test_png_zlib_eof_bomb_extra_stream_wrong_scanline_and_filter(self):
        raw = b'\0' * 18
        values = [png(compressed=b'bad'), png(compressed=zlib.compress(raw)[:-1]),
                  png(compressed=zlib.compress(raw)+zlib.compress(raw)),
                  png(raw=raw+b'x'), png(raw=raw[:-1]), png(filters=[5,0]),
                  png(compressed=zlib.compress(b'\0' * 1000000))]
        for i, value in enumerate(values):
            with self.subTest(case=i): self.reject_png(value)

    def test_png_chunk_order_critical_animation_profile_and_format(self):
        good = png(); ihdr = good[8:33]; idat = good[33:-12]
        values = [good[:8]+ihdr+ihdr+good[33:], good[:8]+idat+ihdr+good[-12:],
                  good[:8]+ihdr+idat+chunk(b'tEXt',b'k\0v')+idat+good[-12:],
                  png(between=chunk(b'ABCD',b'')), png(between=chunk(b'acTL',b'')),
                  png(between=chunk(b'cICP',b'')), png(between=chunk(b'sRGB',b'\x04')),
                  png(between=chunk(b'gAMA',b'')), png(between=chunk(b'PLTE',b'a')),
                  good[:8]+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,16,6,0,0,0))+good[33:],
                  good[:8]+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,6,0,0,1))+good[33:]]
        for i, value in enumerate(values):
            with self.subTest(case=i): self.reject_png(value)

    def test_png_standard_sdr_metadata(self):
        between = chunk(b'sRGB',b'\0')+chunk(b'gAMA',struct.pack('>I',45455))+chunk(b'pHYs',struct.pack('>IIB',1,1,1))
        self.assertEqual(c.decode_png(png(between=between),expected_width=2,expected_height=2)['width'],2)

    def test_prepare_exclusive_target_and_reservation(self):
        self.target.write_bytes(png())
        with self.assertRaises(c.CaptureError): self.prepare()
        self.target.unlink(); self.prepare()
        with self.assertRaises(c.CaptureError): self.prepare()
        self.assertFalse(self.target.exists())

    def test_prepare_rejects_symlink_parent_target_quote_and_relative(self):
        outside = self.root / 'other'; outside.mkdir()
        link = self.root / 'link'; link.symlink_to(outside, target_is_directory=True)
        targets = [link/'x.png', Path('relative.png'), self.root/'quote".png', self.root/'x;quit.png', self.root/'x.jpg']
        self.target.symlink_to(self.root/'absent')
        targets.append(self.target)
        for target in targets:
            with self.subTest(path=str(target)), self.assertRaises(c.CaptureError): self.prepare(target_path=target)

    def test_binding_types_clock_and_observation_context(self):
        for field, value in [('host_pid', True), ('worker_pid', 0), ('generation', -1), ('source_sha', 'A'*40), ('session','repair'), ('world_id','UPPER')]:
            binding = dict(self.binding); binding[field]=value
            with self.subTest(field=field), self.assertRaises(c.CaptureError): self.prepare(expected_binding=binding)
        for clock in [dict(self.clock, anchor_monotonic=float('nan')), dict(self.clock, anchor_utc='2000-01-01')]:
            with self.assertRaises(c.CaptureError): self.prepare(clock=clock)
        for changes in [dict(trusted_head=self.selected), dict(selected_observation=self.head), dict(before_map_monotonic=200.)]:
            with self.subTest(changes=changes), self.assertRaises(c.CaptureError): self.prepare(**changes)
        wrong = self.readref(self.observation); wrong['verified_monotonic']=200.
        with self.assertRaises(c.CaptureError): self.prepare(observation_ref=self.newref(wrong))

    def test_refs_reject_digest_duplicate_json_private_and_missing_proof(self):
        wrong = dict(self.observation, sha256='0'*64)
        with self.assertRaises(c.CaptureError): self.prepare(observation_ref=wrong)
        bad = self.root/'duplicate.json'; bad.write_bytes(b'{"x":1,"x":2}')
        ref = {'path':str(bad),'sha256':hashlib.sha256(bad.read_bytes()).hexdigest()}
        with self.assertRaises(c.CaptureError): self.prepare(observation_ref=ref)
        private = self.root/'owner.json'; private.write_bytes(b'never read')
        with mock.patch.object(c.os, 'read', side_effect=AssertionError('must not read private bytes')):
            with self.assertRaises(c.CaptureError): c._reference({'path':str(private),'sha256':'0'*64})
        value=self.readref(self.observation); value.pop('verification_ref')
        with self.assertRaises(c.CaptureError): self.prepare(observation_ref=self.newref(value))

    def test_missing_file_does_not_turn_command_success_into_capture(self):
        p=self.prepare(); cmd=self.command(p)
        with self.assertRaises(c.CaptureError): c.collect_native_shot(p['preparation_ref'],cmd,**self.expected(),receipt_path=self.root/'capture.json')
        self.assertFalse((self.root/'capture.json').exists())

    def test_collect_rejects_wrong_expected_binding_clock_selection(self):
        p=self.prepare(); cmd=self.command(p); self.target.write_bytes(png())
        variants=[dict(expected_binding=dict(self.binding,host_pid=999)),dict(expected_clock=dict(self.clock,id='other')),
                  dict(expected_trusted_head=self.selected),dict(expected_selected_observation=self.head),
                  dict(expected_observation_ref=self.before)]
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(c.CaptureError): self.collect(p,cmd,**changes)

    def test_command_requires_exact_receipt_times_log_and_cua_original(self):
        p=self.prepare(); cmd=self.command(p); self.target.write_bytes(png()); original=self.readref(cmd)
        changes=[dict(command='HighResShot 2'),dict(clock_id='other'),dict(start_monotonic=100.),
                 dict(end_monotonic=float('inf')),dict(end_monotonic=100.),dict(end_monotonic=900.),
                 dict(binding=dict(self.binding,worker_pid=9)),dict(selected_observation=self.head),dict(cua_result_ref=self.before|{'sha256':'0'*64}),
                 dict(log=dict(original['log'],after_offset=9999))]
        for change in changes:
            value=dict(original,**change)
            # json.dumps default accepts Infinity; the module must explicitly reject it.
            with self.subTest(change=change), self.assertRaises(c.CaptureError): self.collect(p,self.newref(value))

    def test_log_replacement_truncation_and_prefix_mutation(self):
        p=self.prepare(); cmd=self.command(p); self.target.write_bytes(png())
        original=self.log.read_bytes()
        for value in [b'', b'x'*len(original)]:
            self.log.write_bytes(value)
            with self.assertRaises(c.CaptureError): self.collect(p,cmd)
        self.log.write_bytes(original)
        self.log.rename(self.root/'old.log'); self.log.write_bytes(original)
        with self.assertRaises(c.CaptureError): self.collect(p,cmd)

    def test_collect_rejects_stale_file_hardlink_and_invalid_stability(self):
        p=self.prepare(); cmd=self.command(p); self.target.write_bytes(png())
        os.utime(self.target,(0,0))
        with self.assertRaises(c.CaptureError): self.collect(p,cmd)
        os.utime(self.target,None); os.link(self.target,self.root/'alias.png')
        with self.assertRaises(c.CaptureError): self.collect(p,cmd)
        for changes in [dict(stability_seconds=0),dict(max_wait_seconds=11),dict(max_wait_seconds=float('nan'))]:
            with self.assertRaises(c.CaptureError): self.collect(p,cmd,**changes)

    def test_collect_rejects_inode_replacement_and_receipt_overwrite(self):
        p=self.prepare(); cmd=self.command(p); self.target.write_bytes(png())
        def replace(seconds):
            self.now+=seconds; self.target.rename(self.root/'old.png'); self.target.write_bytes(png())
        with mock.patch.object(c.time,'sleep',side_effect=replace):
            with self.assertRaises(c.CaptureError): self.collect(p,cmd)
        capture=self.collect(p,cmd)
        with self.assertRaises(c.CaptureError): self.collect(p,cmd)
        self.assertTrue(Path(capture['path']).is_file())

    def test_parent_replacement_after_prepare(self):
        directory=self.root/'shots'; directory.mkdir(); self.target=directory/'native.png'
        p=self.prepare(); cmd=self.command(p)
        directory.rename(self.root/'old-shots'); directory.mkdir(); self.target.write_bytes(png())
        with self.assertRaises(c.CaptureError): self.collect(p,cmd)

    def test_verify_rejects_modified_original_or_inode(self):
        capture=self.collect(); self.target.rename(self.root/'original.png'); self.target.write_bytes(png())
        with self.assertRaises(c.CaptureError): self.finish(capture)

    def test_verify_full_map_includes_nonhead_entries(self):
        capture=self.collect(); after=self.readref(self.after)
        after['files']['objects/another.json']={'bytes':1,'sha256':'c'*64}; after['bytes']=3
        with self.assertRaises(c.CaptureError): self.finish(capture,after_map_ref=self.newref(after))

    def test_verify_actual_exit_receipt_interval_not_deadline(self):
        capture=self.collect(); value=self.readref(capture)
        for change in [dict(stable_monotonic=200.),dict(first_read_monotonic=100.),
                       dict(request_to_stable={'start_monotonic':0.,'end_monotonic':1.}),
                       dict(binding=dict(self.binding,generation=2)),dict(clock=dict(self.clock,id='other'))]:
            with self.subTest(change=change):
                changed=self.newref(dict(value,**change))
                # fresh unique final fixture names for each finalization.
                for name in ('actual-exit-raw.json','before-exit.json'):
                    path=self.root/name
                    if path.exists(): path.unlink()
                with self.assertRaises(c.CaptureError): self.finish(changed)
        for name in ('actual-exit-raw.json','before-exit.json'):
            path=self.root/name
            if path.exists(): path.unlink()
        with self.assertRaises(c.CaptureError): self.finish(capture,before_exit_monotonic=110.)

    def test_verify_rejects_missing_before_exit_ref_and_changed_public_evidence(self):
        capture=self.collect()
        with self.assertRaises(c.CaptureError): c.verify_native_shot(capture,**self.expected(),
            after_map_ref=self.after,after_map_monotonic=103.5,before_exit_monotonic=104.,before_exit_ref={})
        Path(self.observation['path']).write_bytes(b'{}')
        with self.assertRaises(c.CaptureError): self.finish(capture)

    def test_sdr_showui_explicit_command_and_safe_import(self):
        p=self.prepare(show_ui=True)
        self.assertTrue(p['command'].endswith(' nosuffix showui'))
        # Module import cannot use process/UI/FS APIs; all work is explicit calls.
        with mock.patch('os.open',side_effect=AssertionError('import IO')):
            fresh=importlib.util.module_from_spec(spec); spec.loader.exec_module(fresh)


if __name__ == '__main__': unittest.main()
