"""I1 acceptance against literal I0 vectors and adversarial public inputs."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from engine.universe_authority.codec import (
    ContractError, DOMAIN, VERSION, MAX_BYTES, MAX_INTEGER,
    canonical, decode, digest, encode_f64, f64,
)
from engine.universe_authority.records import (
    ValidatedClosure, select, validate_archive, validate_closure, validate_record,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "doc" / "fixtures" / "universe_authority_v0_1"
WORLD = "fixture-world"


class UniverseCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fixture packaging is not itself a domain JSON value (negative raw
        # strings exceed the domain string cap). No oracle code is imported.
        cls.archive = json.loads((FIXTURES / "positive.json").read_text())
        cls.golden = json.loads((FIXTURES / "golden.json").read_text())
        cls.negative = json.loads((FIXTURES / "negative.json").read_text())
        cls.trust = json.loads((FIXTURES / "trusted_receipts.json").read_text())

    def assert_code(self, code, callable_, *args, **kwargs):
        with self.assertRaises(ContractError) as result:
            callable_(*args, **kwargs)
        self.assertEqual(code, result.exception.code)

    def closure(self, archive=None, trusted=None):
        return validate_archive(self.archive if archive is None else archive,
                                world_id=WORLD, trusted_receipts=self.trust if trusted is None else trusted)

    def test_all_literal_golden_bytes_and_domain_hashes(self):
        self.assertEqual(24, len(self.golden))
        records = decode((FIXTURES / "positive.json").read_bytes())["records"]
        self.assertEqual(24, len(records))
        prefix = bytes.fromhex("65646765776f726c642e756e6976657273652e617574686f726974790076302e3100")
        for record, expected in zip(records, self.golden):
            with self.subTest(id=expected["id"]):
                validate_record(record)
                raw = bytes.fromhex(expected["canonical_hex"])
                self.assertEqual(record["id"], expected["id"])
                self.assertEqual(raw, canonical(record))
                self.assertEqual(expected["sha256"], digest(record))
                self.assertEqual(expected["sha256"], hashlib.sha256(prefix + raw).hexdigest())
                self.assertEqual(record, decode(raw))

    def test_all_27_literal_negative_vectors(self):
        self.assertEqual(27, len(self.negative))
        closure = self.closure()
        for case in self.negative:
            with self.subTest(case=case["name"]):
                with self.assertRaises(ContractError) as result:
                    value = decode(case["raw"].encode("utf-8"))
                    if case["operation"] == "archive":
                        self.closure(value)
                    elif case["operation"] == "observe":
                        select(closure, **value)
                    else:
                        self.assertEqual("decode", case["operation"])
                self.assertEqual(case["error"], result.exception.code)

    def test_same_tick_has_three_distinct_retained_revisions(self):
        closure = self.closure()
        self.assertEqual(3, len(closure.retained))
        self.assertEqual(self.archive["head"], closure.head)
        self.assertEqual(WORLD, closure.world_id)
        for revision in (0, 1, 2):
            manifest = select(closure, tick=0, revision=revision, watermark=revision)
            self.assertEqual({"tick": 0, "revision": revision, "watermark": revision}, manifest["body"])
        self.assert_code("NOT_FOUND", select, closure, tick=1, revision=2, watermark=2)
        self.assert_code("WATERMARK", select, closure, tick=0, revision=2, watermark=1)

    def test_valid_orphan_results_never_become_committed_successes(self):
        full = self.closure()
        expected_results = {
            ("fixture-principal", r["body"]["command_id"]): digest(r)
            for r in self.archive["records"] if r["kind"] == "result"
        }
        self.assertEqual(expected_results, dict(full.commands))
        first = deepcopy(self.archive)
        first["head"] = full.retained[1]
        pinned = self.closure(first)
        self.assertEqual(24, len(pinned.records))  # Complete later objects are valid but orphaned.
        self.assertEqual(1, len(pinned.commands))
        self.assert_code("NOT_FOUND", select, pinned, tick=0, revision=2, watermark=2)
        first["head"] = full.retained[-1]
        self.assertEqual({}, dict(self.closure(first).commands))

    def test_defensive_closure_and_selection_outputs(self):
        source, trust = deepcopy(self.archive), deepcopy(self.trust)
        closure = self.closure(source, trust)
        first = closure.records[closure.retained[-1]]
        first["body"]["tick"] = 999
        selected = select(closure, tick=0, revision=0, watermark=0)
        selected["refs"].clear()
        source["records"][0]["body"]["budget"] = 999
        trust.clear()
        self.assertEqual(0, closure.records[closure.retained[-1]]["body"]["tick"])
        self.assertTrue(select(closure, tick=0, revision=0, watermark=0)["refs"])
        with self.assertRaises(TypeError):
            closure.records["new"] = {}
        with self.assertRaises(TypeError):
            closure.commands[("p", "c")] = "x"
        with self.assertRaises(FrozenInstanceError):
            closure._head = "x"
        self.assert_code("SCHEMA", ValidatedClosure)

    def test_valid_utf8_archive_is_not_relimited_by_ascii_clone_expansion(self):
        archive = deepcopy(self.archive)
        for index in range(190):
            archive["records"].append({
                "domain": DOMAIN, "version": VERSION, "world_id": WORLD,
                "kind": "proposal", "id": "orphan-" + str(index),
                "body": {"principal": "fixture-principal", "output": "𝄞" * 1024}, "refs": {},
            })
        raw = json.dumps(archive, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.assertLess(len(raw), MAX_BYTES)
        self.assertGreater(len(canonical(archive)), MAX_BYTES)
        closure = self.closure(decode(raw))
        self.assertEqual(214, len(closure.records))
        self.assertEqual(2, len(closure.commands))

    def test_trust_is_external_and_unknown_profiles_are_rejected(self):
        self.assert_code("AUTHORIZATION", self.closure, trusted={})
        archive = deepcopy(self.archive)
        archive["trusted_receipts"] = self.trust
        self.assert_code("SCHEMA", self.closure, archive)
        archive = deepcopy(self.archive)
        archive["test_profile"] = "real-physics-v1"
        self.assert_code("PROFILE", self.closure, archive)
        candidate = deepcopy(next(r for r in self.archive["records"] if r["kind"] == "candidate"))
        candidate["body"]["adapter_kind"] = "genesis"
        self.assert_code("PROFILE", validate_record, candidate)
        self.assert_code("WORLD", validate_closure, self.archive["records"], self.archive["head"],
                         world_id="other-world", trusted_receipts=self.trust)

    def test_trusted_anchor_does_not_equate_boolean_and_integer(self):
        malformed = deepcopy(self.trust)
        receipt = next(value for value in malformed.values()
                       if value["kind"] == "admission" and value["evaluated_revision"] == 0)
        receipt["evaluated_revision"] = False
        self.assert_code("AUTHORIZATION", self.closure, trusted=malformed)

    def test_canonical_unicode_order_escaping_and_no_normalization(self):
        value = {"é": "𝄞", "a": "/\b\t\n\f\r\"\\", "e\u0301": "x"}
        expected = b'{"a":"/\\b\\t\\n\\f\\r\\\"\\\\","e\\u0301":"x","\\u00e9":"\\ud834\\udd1e"}'
        self.assertEqual(expected, canonical(value))
        self.assertEqual(value, decode(expected))
        self.assertNotEqual(canonical("é"), canonical("e\u0301"))

    def test_finite_bits_preserve_signed_zero_subnormals_and_extremes(self):
        for bits in ("0000000000000000", "8000000000000000", "0000000000000001",
                     "8000000000000001", "7fefffffffffffff", "ffefffffffffffff"):
            with self.subTest(bits=bits):
                self.assertEqual({"$f64": bits}, encode_f64(f64(bits)))
                self.assertEqual(bits, struct.pack(">d", f64(bits)).hex())
        self.assertEqual(-1, math.copysign(1, f64("8000000000000000")))
        for bad in (True, 1, "1", None, float("nan"), float("inf")):
            self.assert_code("F64", encode_f64, bad)
        for bad in (True, 1, b"0000000000000000", "0000000000000000x"):
            self.assert_code("F64", f64, bad)
        self.assert_code("F64", canonical, {"$f64": "0000000000000000", "extra": 1})

    def test_public_integer_and_shape_inputs_do_not_coerce(self):
        closure = self.closure()
        for bad in (True, -1, 1.0, MAX_INTEGER + 1):
            self.assert_code("INTEGER", select, closure, tick=bad, revision=0, watermark=0)
        self.assert_code("NUMBER", canonical, 1.0)
        self.assert_code("SCHEMA", canonical, {1: "x", "s": "y"})
        self.assert_code("UNICODE", canonical, "\ud800")
        self.assert_code("UNICODE", validate_record, {"bad": "\udfff"})
        self.assert_code("JSON", decode, "{}")
        self.assert_code("UNICODE", decode, b'"\xff"')
        self.assert_code("JSON", decode, b"{} {}")
        self.assert_code("DOMAIN", digest, {"domain": "legacy", "version": VERSION})

    def test_depth_container_string_and_input_budgets(self):
        depth32 = None
        for _ in range(32):
            depth32 = [depth32]
        canonical(depth32)
        self.assert_code("LIMIT", canonical, [depth32])
        self.assert_code("LIMIT", decode, ("[" * 2000 + "0" + "]" * 2000).encode())
        canonical([None] * 256)
        self.assert_code("LIMIT", canonical, [None] * 257)
        self.assert_code("LIMIT", canonical, {str(i): None for i in range(65)})
        canonical("é" * 2048)
        self.assert_code("LIMIT", canonical, "é" * 2049)
        self.assert_code("LIMIT", decode, b" " * MAX_BYTES + b"0")
        cycle = []
        cycle.append(cycle)
        self.assert_code("LIMIT", canonical, cycle)

    def test_closure_public_input_errors_are_stable(self):
        self.assert_code("LIMIT", validate_closure, [], self.archive["head"],
                         world_id=WORLD, trusted_receipts=self.trust)
        self.assert_code("LIMIT", validate_closure, "not a sequence of records", self.archive["head"],
                         world_id=WORLD, trusted_receipts=self.trust)
        self.assert_code("REFERENCE", validate_closure, self.archive["records"], "bad",
                         world_id=WORLD, trusted_receipts=self.trust)
        self.assert_code("SCHEMA", select, {}, tick=0, revision=0, watermark=0)
        self.assert_code("ID", validate_closure, self.archive["records"], self.archive["head"],
                         world_id=True, trusted_receipts=self.trust)

    def test_diagnostics_are_bounded_even_for_invalid_unicode(self):
        error = ContractError("SCHEMA", "é" * 5000 + "\ud800")
        self.assertLessEqual(len(error.detail.encode("utf-8")), 4096)
        self.assertIsInstance(error, ValueError)
        self.assertEqual("SCHEMA", error.code)
        self.assertEqual("", ContractError("SCHEMA").detail)

    def test_imports_have_no_authority_or_process_side_effects(self):
        code = '''
import builtins, os, subprocess, threading
from unittest.mock import patch
before = (os.getcwd(), dict(os.environ))
def forbidden(*args, **kwargs):
    raise AssertionError("import attempted side effect")
with patch.object(builtins, "open", forbidden), patch.object(os, "open", forbidden), \\
     patch.object(os, "chdir", forbidden), patch.object(subprocess, "Popen", forbidden), \\
     patch.object(threading.Thread, "start", forbidden):
    import engine.universe_authority
    import engine.universe_authority.codec
    import engine.universe_authority.records
    import engine.universe_authority.trust
assert before == (os.getcwd(), dict(os.environ))
'''
        environment = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory(prefix="universe-codec-import-") as directory:
            result = subprocess.run([sys.executable, "-c", code], cwd=directory, env=environment,
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


    def test_composite_shared_types_validate_in_memory_without_filesystem(self):
        from dataclasses import replace
        from unittest.mock import patch
        from engine.universe_authority.codec import (
            DeploymentContext, HeadBinding, OwnerSession, ProvisionSpec, TrustAnchor,
            Record as SharedRecord,
        )
        from engine.universe_authority.records import Record as CompatibleRecord
        self.assertIs(SharedRecord, CompatibleRecord)
        with patch.object(os, 'open', side_effect=AssertionError('unexpected filesystem probe')), \
             patch.object(os, 'stat', side_effect=AssertionError('unexpected stat')):
            context = DeploymentContext('world', '/canonical/world', 'a' * 64, 'b' * 64, 'c' * 64)
            ProvisionSpec('world', Path('/canonical/world'))
            TrustAnchor('world', '/canonical/world', '0.2', 'local-hmac-sha256.v0.2', 'a' * 64)
            HeadBinding('d' * 64, context.world_id, context.authority_root, context.trust_algorithm,
                        context.trust_anchor, context.expected_build, context.expected_options,
                        context.artifact_class, DOMAIN, '0.2', context.archive_profile, 'ready')
            OwnerSession('owner', True, ('physics_step', 'retain_snapshot'))
            replace(context, artifact_class='synthetic-contract-only')
        for root in ('relative', '/a/../b', '//root', '/a//b', '/a/', '/bad\x00root'):
            self.assert_code('ROOT_MISMATCH', replace, context, authority_root=root)
        for field, value, code in (('world_id', True, 'ID'), ('expected_build', 'A' * 64, 'REFERENCE'),
                                   ('artifact_class', 'unknown', 'PROFILE'), ('domain_version', True, 'PROFILE')):
            self.assert_code(code, replace, context, **{field: value})
        self.assert_code('AUTHORIZATION', OwnerSession, 'owner', 1, ('physics_step',))
        self.assert_code('AUTHORIZATION', OwnerSession, 'owner', True, ('physics_step', 'physics_step'))
        self.assert_code('SCHEMA', validate_record, None)
        self.assert_code('SCHEMA', validate_record, {})
        self.assertEqual('0.1', VERSION)
        self.assertEqual({}, dict(self.closure().binary_refs))
        self.assertIsNone(self.closure().context)


if __name__ == "__main__":
    unittest.main()
