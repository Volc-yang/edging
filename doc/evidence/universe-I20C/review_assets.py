"""Independent I20A read-only review; writes only requested C evidence directory.

Arguments: reviewed repository checkout, durable acquired asset root, output directory.
No network, UE, worker, solver or authority input is used.
"""
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from PIL import Image


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(repo, root, out):
    repo, root, out = (Path(p).resolve() for p in (repo, root, out))
    ev = repo / 'doc/evidence/universe-I20A'
    def read_json(p):
        return json.loads(p.read_bytes())
    result = {'format': 'universe-i20-independent-assets-review.v1',
              'reviewed_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
              'asset_root': str(root), 'checks': {}}
    ledger = read_json(root/'binary-ledger.json')
    metadata_ledger = read_json(root/'metadata-ledger.json')
    total = 0
    for row in ledger['requests']:
        ref = row['body_ref']; raw = Path(ref['path']).read_bytes()
        assert Path(ref['path']).is_relative_to(root)
        assert len(raw) == row['body_bytes'] == ref['bytes']
        assert sha(raw) == ref['sha256'] and hashlib.md5(raw).hexdigest() == ref['md5']
        assert row['status'] == 200 and row['complete'] and not row['redirects']
        assert 0 <= row['ended_monotonic'] - row['started_monotonic'] < 60
        total += len(raw)
    assert ledger['started_monotonic'] == metadata_ledger['started_monotonic']
    assert ledger['requests'][:len(metadata_ledger['requests'])] == metadata_ledger['requests']
    assert total == ledger['actual_received_bytes'] < 256*1024**2
    assert ledger['elapsed_seconds'] < 1200 and ledger['error'] is None
    result['checks']['actual_network_bodies'] = {
        'result': 'pass', 'requests': len(ledger['requests']), 'response_body_bytes': total,
        'same_persistent_origin': True, 'elapsed_seconds': ledger['elapsed_seconds'],
        'maximum_request_seconds': max(r['ended_monotonic']-r['started_monotonic'] for r in ledger['requests'])}
    plan = read_json(root/'acquisition-plan.json')
    receipt = read_json(root/'acquisition-receipt.json')
    assert sha((root/'acquisition-plan.json').read_bytes()) == receipt['plan_sha256']
    by_path = {f['relative']: f for f in receipt['files']}
    assert len(by_path) == len(receipt['files']) == len(plan['files']) == 20
    for f in plan['files']:
        raw = (root/f['relative']).read_bytes(); got = by_path[f['relative']]
        assert f['size'] == got['size'] == len(raw)
        assert f['md5'] == got['md5'] == hashlib.md5(raw).hexdigest()
        assert sha(raw) == got['actual']['sha256']
    result['checks']['all_frozen_payload_bytes'] = {
        'result': 'pass', 'files': len(by_path), 'bytes': sum(f['size'] for f in by_path.values()),
        'plan_sha256': sha((root/'acquisition-plan.json').read_bytes()),
        'receipt_sha256': sha((root/'acquisition-receipt.json').read_bytes())}
    # No-follow enumeration reports traversal/stat errors instead of silently skipping.
    files = []; errors = []
    for base, dirs, names in os.walk(root, followlinks=False, onerror=errors.append):
        for name in dirs+names:
            path = Path(base)/name
            assert not stat.S_ISLNK(path.lstat().st_mode)
        files.extend(str((Path(base)/name).relative_to(root)) for name in names)
    assert not errors and len(files) <= 64
    result['checks']['final_tree'] = {'result': 'pass', 'file_count': len(files), 'symlinks': 0, 'walk_errors': 0}
    mapping = read_json(ev/'phased-source-provenance.json')
    phases = []
    for phase in mapping['phases']:
        ref = phase['preserved_source']; raw = (repo/ref['repository_path']).read_bytes()
        blob = subprocess.check_output(['git', 'show', ref['git_object_ref']], cwd=repo)
        old_ref = phase['original_recorded_helper_ref']
        rec_ref = phase['immutable_receipt']; rec_raw = (repo/rec_ref['repository_path']).read_bytes()
        original = json.loads(rec_raw)
        assert sha(raw) == sha(blob) == ref['sha256'] == old_ref['sha256']
        assert sha(rec_raw) == rec_ref['sha256']
        if phase['phase'] == 'metadata':
            assert original['helper_ref'] == old_ref
        else:
            assert original['helper_sha256'] == old_ref['sha256']
        assert rec_raw == (root/Path(rec_ref['repository_path']).name).read_bytes()
        phases.append({'phase': phase['phase'], 'source_sha256': sha(raw), 'stable_git_object_ref': ref['git_object_ref'],
                       'receipt_sha256': sha(rec_raw), 'same_preserved_source_and_git_blob': True})
    idx = mapping['durable_asset_input']
    idx_raw = (repo/idx['index_repository_path']).read_bytes()
    assert sha(idx_raw) == idx['index_sha256']
    assert idx_raw == subprocess.check_output(['git', 'show', idx['index_git_object_ref']], cwd=repo)
    assert idx['asset_root'] == str(root)
    result['checks']['phase_source_provenance'] = {'result': 'pass', 'phases': phases,
        'original_receipts_unchanged': True, 'asset_index_sha256': sha(idx_raw),
        'old_metadata_helper_path_is_not_valid_for_original_hash': True,
        'stable_source_resolution_required_after_cleanup': True}
    class Text(HTMLParser):
        def __init__(self): super().__init__(); self.parts = []
        def handle_data(self, data): self.parts.append(data)
    html = (root/'metadata/polyhaven-license.html').read_bytes()
    text = Text(); text.feed(html.decode()); license_text = ' '.join(' '.join(text.parts).split())
    start = license_text.index('All assets ( HDRIs , textures and 3D models )')
    snippet = license_text[start:start+340]
    assert 'Our assets are all licensed as CC0' in snippet
    legal = (root/'metadata/CC0-1.0.txt').read_bytes()
    assert b'CC0 1.0 Universal' in legal and legal == (ev/'CC0-1.0.txt').read_bytes()
    result['checks']['retained_primary_license'] = {'result': 'pass',
        'official_html_sha256': sha(html), 'official_text_excerpt': snippet,
        'cc0_legal_sha256': sha(legal), 'scope': 'CC0 asset data; website/template code licenses are separate'}
    # Additional CPU decode checks, beyond A's explicitly limited image headers.
    decoded = {}
    for rel in by_path:
        if not rel.endswith(('.jpg', '.png')): continue
        with Image.open(root/rel) as image:
            image.load()
            assert image.size == (2048, 2048)
            decoded[rel] = {'mode': image.mode, 'size': list(image.size), 'bands': list(image.getbands()),
                            'extrema': image.getextrema()}
    assert len(decoded) == 14
    assert decoded['assets/fern_02/textures/fern_02_diff_2k.jpg']['mode'] == 'RGB'
    alpha = decoded['assets/fern_02/textures/fern_02_alpha_2k.png']
    assert len(alpha['bands']) == 1 and alpha['extrema'][0] < alpha['extrema'][1]
    result['checks']['full_texture_decode'] = {'result': 'pass', 'images': decoded,
        'scope': 'CPU image decoding only; no UE sampler, material, normal or visual correctness claim'}
    material_sources = {}
    for asset in plan['assets']:
        gltf = read_json(root/asset['gltf'])
        normal_paths = []
        for material in gltf['materials']:
            normal = gltf['textures'][material['normalTexture']['index']]['source']
            uri = gltf['images'][normal]['uri']
            assert '_nor_gl_' in uri
            assert material['pbrMetallicRoughness']['metallicFactor'] == 0
            normal_paths.append(uri)
        material_sources[asset['id']] = {'original_gltf_normal_uris': normal_paths,
            'original_materials': gltf['materials']}
    fern = material_sources['fern_02']['original_materials'][0]
    assert fern['alphaMode'] == 'MASK' and fern['alphaCutoff'] == 0.5 and fern['doubleSided']
    result['checks']['original_material_source_semantics'] = {'result': 'pass', 'assets': material_sources,
        'fern_requires_explicit_separate_grayscale_alpha': True,
        'original_gl_normal_dependencies_preserved_dx_is_additional_input': True,
        'ground_model_is_material_preview_sphere_not_world_terrain': True,
        'ue_material_native_appearance_check': 'not_run'}
    # Re-run the owner's bounded closure verifier, then independent fault injection.
    spec = importlib.util.spec_from_file_location('i20a_verifier', ev/'verify.py')
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    verified = verifier.verify(root)
    (out/'a-owner-verifier-rerun.json').write_text(json.dumps(verified, indent=2, sort_keys=True)+'\n')
    negatives = []
    def reject(name, operation):
        try: operation()
        except (ValueError, OSError, KeyError, IndexError) as exc:
            negatives.append({'case': name, 'result': 'pass_rejected', 'reason': str(exc)})
        else: raise AssertionError('negative input accepted: '+name)
    with tempfile.TemporaryDirectory(prefix='i20c-assets-review-') as tmp:
        copied = Path(tmp)/'assets-root'; shutil.copytree(root, copied)
        target = copied/'assets/fern_02/fern_02.bin'; original = target.read_bytes()
        target.unlink(); reject('missing_required_buffer', lambda: verifier.verify(copied))
        target.write_bytes(bytes([original[0]^1])+original[1:])
        reject('corrupted_required_buffer', lambda: verifier.verify(copied))
        target.unlink(); target.symlink_to(root/'assets/fern_02/fern_02.bin')
        reject('symlinked_required_buffer', lambda: verifier.verify(copied))
        reject('parent_traversal', lambda: verifier.safe(copied, '../escape'))
    result['checks']['owner_closure_verifier'] = {'result': verified['result'],
        'checker_sha256': sha((ev/'verify.py').read_bytes()),
        'rerun_output_repository_path': 'doc/evidence/universe-I20C/a-owner-verifier-rerun.json',
        'rerun_output_sha256': sha((out/'a-owner-verifier-rerun.json').read_bytes()), 'independent_negatives': negatives}
    result['result'] = 'accept_source_file_license_closure_gate_only'
    result['unexecuted_gates'] = ['UE import/compiled classes/slots/pivots/units', 'UE/Metal build and load',
        'actual material/alpha/normal wiring', 'authority readonly and atomic HUD/scene', 'visual quality/performance']
    (out/'a-independent-review.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k: v for k,v in result.items() if k != 'checks'}, indent=2))
    print('Independent A checks:', ', '.join(result['checks']))


if __name__ == '__main__':
    run(*sys.argv[1:])
