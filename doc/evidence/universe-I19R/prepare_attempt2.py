"""I19 root-only exclusive metadata preparation; never launches UE or solver."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

TOOL = Path(__file__).resolve().parents[3]
ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe')
OUT = ROOT / 'I19-20261109-metal-slice-attempt2'
SESSION = Path('/Users/yangacan/.codex/sessions/2026/10/10/rollout-2026-10-10T09-40-15-01a12377-c991-7550-acff-cf472fcc0b86.jsonl')


def ref(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''): h.update(block)
    return dict(path=str(path), sha256=h.hexdigest())


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return ref(path)


def main(card_format, card_scope):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(TOOL/'scripts'))
    import run_universe_slice_acceptance as common
    from universe_iteration import lifecycle as lc, capability as cap, probe_actions as probe
    tool_sha = common.product_identity(TOOL)
    inherited = ROOT/'I18-20261107-native-seal/prep/prepared.json'
    assert ref(inherited)['sha256'] == '4192e0c088e612789753ab5148bf1f666247938394c7f0059d482946f27d5ead'
    p = json.loads(inherited.read_bytes())
    assert common.product_identity(Path(p['product_root']), p['allowed_untracked']) == p['product_source_sha']
    forbidden = Path(p['key_directory'])
    # Hash only the explicit existing metadata/runtime/source/binary pins. Never
    # enumerate, read, copy or hash key-directory contents.
    for name in ('runtime_files', 'source_pins', 'native_source_pins'):
        for pin in p[name]: cap.hash_ref(pin, forbidden=forbidden)
    for pin in p['binary_pins'].values(): cap.hash_ref(pin, forbidden=forbidden)
    common.validate_python_executable(p)
    before = common.authority_map(Path(p['authority_root']))
    assert before['files'] == lc.json_ref(p['before_map_ref'])['files']
    assert not OUT.exists()
    OUT.mkdir(mode=0o700)
    (OUT/'prep').mkdir(mode=0o700); (OUT/'images').mkdir(mode=0o700)
    p.update(format='universe-i19-prepared.v2', run_id='i19-20261109-metal-slice-attempt2', tool_root=str(TOOL), tool_source_sha=tool_sha,
             created_at=datetime.now(timezone.utc).isoformat(),
             before_map_ref=save(OUT/'prep/authority-before.json', before),
             probe_manifest_ref=save(OUT/'prep/probe-manifest.json', probe.probe_manifest_v2()))
    # Owner/context/inputs/scratch/build/native are inherited unchanged. Worker
    # permits reuse of this existing scratch; no credentials or world migration.
    prepared_ref = save(OUT/'prep/prepared.json', p)
    provenance = save(OUT/'prep/provenance.json', dict(
        inherited_prepared_ref=ref(inherited), prepared_ref=prepared_ref,
        changed_fields=['format','run_id','tool_root','tool_source_sha','created_at','before_map_ref','probe_manifest_ref'],
        owner_context_inputs_build_native_unchanged=True, key_contents_read=False,
        runtime_started=False, helper_ref=ref(__file__)))
    now = datetime.now(timezone.utc)
    controller = OUT/'capability'
    for binding in (controller, controller/'metal'):
        cache, _ = cap.native_cache_arguments(ROOT, p['run_id'], binding)
        assert not cache.exists()
    card = dict(format=card_format, scope=card_scope, run_id=p['run_id'], issuer='root', approved=True,
                execute=True, issued_at=now.isoformat(), expires_at=(now+timedelta(hours=4)).isoformat(),
                g_b2_granted=False, standard_pair=False, no_retry=True, prepared_ref=prepared_ref,
                probe_manifest_ref=p['probe_manifest_ref'], controller_output=str(controller),
                policy=cap.POLICY, legacy_sources=[], public_paths=[str(OUT/'prep/provenance.json')])
    card_ref = save(OUT/'prep/capability-card.json', card)
    cap.validate_capability_card(card_ref['path'], expected_card_sha256=card_ref['sha256'],
        expected_prepared_sha256=prepared_ref['sha256'],
        expected_probe_manifest_sha256=p['probe_manifest_ref']['sha256'],
        expected_product_source=p['product_source_sha'], expected_tool_source=tool_sha,
        expected_native_source_sha=p['native_source_sha'], execute=True)
    inputs = dict(format='universe-i19-execution-inputs.v1', card_ref=card_ref, prepared_ref=prepared_ref,
                  probe_manifest_ref=p['probe_manifest_ref'], provenance_ref=provenance,
                  tool_source=tool_sha, product_source=p['product_source_sha'], native_source=p['native_source_sha'],
                  driver_ref=ref(Path(__file__).with_name('driver_attempt2.py')), session_transcript=str(SESSION),
                  transcript_start_offset=SESSION.stat().st_size,
                  transcript_scope='only future I19 CUA call/output records; no prior chat or unrelated calls copied')
    result = save(OUT/'prep/execution-inputs.json', inputs)
    print(json.dumps(dict(inputs_ref=result, run_id=p['run_id'], runtime_started=False)), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit('usage: prepare.py FROZEN_CARD_FORMAT FROZEN_CARD_SCOPE')
    main(*sys.argv[1:])
