#!/usr/bin/env python3
"""I12 collection driver. Default prints plan; runtime requires an actual R12 card.

Passive commands write only with --output, using exclusive creation. Never creates authority, keys,
launcher config or requests. Runtime supervisor owns/waits one launcher session;
UI actions remain external CUA only. No implicit launch or trust provisioning.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

from verify_universe_slice_evidence import (Invalid, authority_map, file_hash,
                                            inspect_trace, read_json, require, safe_path,
                                            safe_read, unique_pairs, canonical, PREFIX)

PLAN = [
    ('bootstrap', 'session1: trusted launcher/worker identity and public pins; registered empty root status may be NOT_READY; no HEAD/scratch/solve before explicit initialize'),
    ('initialize', 'explicit initialize; wait verified observation (0,0), D=null, budget8/cursor0/step0; capture stable Metal image'),
    ('retain', 'UniverseRetain; wait (0,1); same snapshot/tick/D/budget/cursor, no solver'),
    ('physical', 'select weak explicitly; UniverseAdvance; wait (1,2); eight solver steps, independently computed exact D'),
    ('retry', 'UniverseRetryLastCommitted; new request ID, identical closure/digest; original result, no authority change'),
    ('history', 'UniverseObserveExact 0 1 1 then UniverseObserveExact 0 0 0, then latest UniverseObserveExact 1 2 2; exact tick/revision/watermark and screenshot bindings'),
    ('history_write_rejected', 'history Space/R cannot prepare or advance; per-action map and raw request interval'),
    ('held_input', 'held Space across history/current transition cannot create hidden intent; release then inspect'),
    ('camera', 'UniverseCamera scripted local view change, verify actual changed view; no claim of human relative-mouse input'),
    ('visibility', 'UniverseProjectionVisible false/true; capture actual hidden/restored view and map per action'),
    ('framerate', 'standard t.MaxFPS bounded change plus readback and per-action map'),
    ('pause', 'standard pause/resume plus actual state/readback and per-action map'),
    ('exit1', 'normal quit via explicit preflush path; worker EOF/drain/reap exit0, UE exit0, launcher exit0 separately'),
    ('revisit', 'session2 existing mode, same authority/world/anchor, distinct owned PID/pipes; fresh status and recovery, exact 1 2 and 0 1; no initialization/advance'),
    ('exit2', 'normal quit; preserve all raw, maps, actual exits and screenshot timing; account all attempts'),
]


def utc():
    return datetime.now(timezone.utc).isoformat()


def emit(value, output):
    encoded = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode()
    if output:
        path = safe_path(output)
        require(path.parent.is_dir(), 'output parent must already exist')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        sys.stdout.buffer.write(encoded)


def process_snapshot(pids):
    """Read actual process argv/PPID; absence is not an exit status."""
    require(pids and all(type(pid) is int and pid > 0 for pid in pids), 'positive owned PIDs required')
    result = subprocess.run(['/bin/ps', '-ww', '-p', ','.join(map(str, pids)),
                             '-o', 'pid=,ppid=,lstart=,command='],
                            capture_output=True, text=True, timeout=5, check=False)
    require(result.returncode in (0, 1), 'ps failed')
    return {'captured_at': utc(), 'requested_pids': pids, 'ps_returncode': result.returncode,
            'raw_stdout': result.stdout, 'raw_stderr': result.stderr,
            'warning': 'ps absence is not proof of normal exit; retain parent wait/worker-exit trace.'}


def metadata(paths):
    """lstat only: deliberately does not open private owner/key files."""
    rows = []
    for raw in paths:
        path = Path(raw).absolute()
        st = path.lstat()
        rows.append({'path': str(path), 'uid': st.st_uid, 'gid': st.st_gid,
                     'mode': oct(st.st_mode & 0o7777), 'nlink': st.st_nlink,
                     'bytes': st.st_size, 'device': st.st_dev, 'inode': st.st_ino,
                     'symlink': path.is_symlink()})
    return {'captured_at': utc(), 'metadata_only': True, 'entries': rows}


def wait_marker(path, marker, seconds, expected_hash, start_offset=None,
                expected_device=None, expected_inode=None, run_id=None, host_pid=None):
    """Read from an action-before pin, including bytes already appended after it.

    Explicit offset requires caller's before device/inode as well as prefix hash.
    Without offset, preserve the old whole-file pin/current-size behavior.
    Run/PID labels are caller declarations, not process identity authentication.
    """
    path = safe_path(path)
    require(path.is_file() and marker and 0 < seconds <= 60, 'existing log/marker and timeout<=60 required')
    if start_offset is not None:
        require(type(start_offset) is int and start_offset >= 0 and
                type(expected_device) is int and type(expected_inode) is int,
                'explicit start offset requires before device/inode pins')
    deadline = time.monotonic() + seconds
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode), 'log is not a regular file')
        identity = (opened.st_dev, opened.st_ino)
        if expected_device is not None or expected_inode is not None:
            require(identity == (expected_device, expected_inode), 'log replaced since action-before pin')
        start = opened.st_size if start_offset is None else start_offset
        offset, tail = start, b''

        def validate_prefix():
            current = path.lstat()
            retained = os.fstat(stream.fileno())
            require(stat.S_ISREG(current.st_mode) and
                    (current.st_dev, current.st_ino) == identity, 'log replaced during wait')
            require(retained.st_size >= offset and current.st_size >= offset,
                    'log truncated since action-before pin')
            stream.seek(0)
            digest, remaining = hashlib.sha256(), start
            while remaining:
                block = stream.read(min(remaining, 1024**2))
                require(block, 'log prefix truncated')
                digest.update(block)
                remaining -= len(block)
            require(digest.hexdigest() == expected_hash, 'log prefix hash does not match caller before pin')

        validate_prefix()
        while time.monotonic() <= deadline:
            # Validate path identity and prefix before accepting appended evidence.
            validate_prefix()
            stream.seek(offset)
            block = stream.read(1024**2)
            offset += len(block)
            tail += block
            require(len(tail) <= 16 * 1024**2, 'marker observation byte cap')
            if marker.encode() in tail:
                validate_prefix()
                return {'matched': True, 'captured_at': utc(), 'path': str(path), 'marker': marker,
                        'start_offset': start, 'end_offset': offset, 'prefix_sha256': expected_hash,
                        'device': identity[0], 'inode': identity[1],
                        'run_id': run_id, 'host_pid': host_pid,
                        'binding': 'caller-declared run/PID; correlate original process evidence'}
            time.sleep(.1)
        validate_prefix()
        return {'matched': False, 'captured_at': utc(), 'path': str(path), 'marker': marker,
                'start_offset': start, 'end_offset': offset, 'prefix_sha256': expected_hash,
                'device': identity[0], 'inode': identity[1], 'run_id': run_id, 'host_pid': host_pid}


def collect(spec):
    """Pin only explicitly enumerated public evidence; no recursive raw/key scan."""
    value = read_json(spec)
    require(value['format'] == 'universe-i12-evidence.v1', 'bundle format')
    artifacts = []
    seen = set()
    for item in value['artifacts']:
        path = safe_path(item['path'])
        require(str(path) not in seen and path.is_file(), 'duplicate/missing artifact')
        seen.add(str(path))
        require(item['role'] not in {'private_key', 'owner_config'}, 'private contents cannot be indexed')
        artifacts.append({'role': item['role'], 'path': str(path),
                          'bytes': path.stat().st_size, 'sha256': file_hash(path)})
    value['artifacts'] = artifacts
    value['collected_at'] = utc()
    return value


def private_metadata(path, directory=False):
    """Check deployment ownership; do not read secret/key contents."""
    path = safe_path(path)
    info = path.stat()
    require((path.is_dir() if directory else path.is_file()) and info.st_uid == os.getuid() and
            stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600) and
            (directory or info.st_nlink == 1), 'unsafe private deployment metadata: ' + str(path))
    return path


def on_devssd(path):
    return str(path).startswith('/Volumes/DevSSD/')


def product_identity(product, allowed_untracked=None):
    head = subprocess.run(['git', '-C', str(product), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    status = subprocess.run(['git', '-C', str(product), 'status', '--porcelain=v1', '-z',
                             '--untracked-files=all'], capture_output=True,
                            timeout=5, check=True).stdout
    allowed = allowed_untracked or {}
    for relative, spec in allowed.items():
        parts = Path(relative)
        require(not parts.is_absolute() and parts.parts and
                all(p not in ('.', '..') for p in parts.parts) and spec.get('provenance'),
                'unsafe/unexplained product allowlist entry')
        path = product / parts
        if spec['kind'] == 'symlink':
            require(path.is_symlink() and os.readlink(path) == spec['readlink'] and
                    str(path.resolve()) == spec['target'] and
                    on_devssd(spec['target']), 'product output mapping changed')
        else:
            require(spec['kind'] == 'file' and file_hash(path) == spec['sha256'],
                    'generated product artifact hash mismatch')
    for entry in status.split(b'\0'):
        if entry:
            require(entry.startswith(b'?? '), 'tracked product source modification')
            require(entry[3:].decode('utf-8') in allowed, 'unapproved untracked product path')
    return head


def validate_owner_deployment(card, name, owner_path, expected_sha):
    """Read typed owner metadata once; never return/log config or open key files."""
    raw = safe_read(owner_path, 65536)
    require(hashlib.sha256(raw).hexdigest() == expected_sha, 'owner metadata changed from pinned SHA')
    owner = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_pairs)
    require(set(owner) == {'config_version', 'mode', 'context', 'session', 'key_dir', 'scratch', 'inputs'} and
            owner['config_version'] == 'universe-owner-launch.v0.1', 'owner metadata shape/version')
    require(owner['mode'] == name, 'owner session mode mismatch')
    expected_context = card['context']
    require(set(expected_context) == {'world_id', 'authority_root', 'trust_anchor', 'expected_build',
            'expected_options', 'artifact_class', 'trust_algorithm', 'domain_version',
            'archive_profile', 'storage_profile'} and expected_context['world_id'] == card['world_id'] and
            expected_context['authority_root'] == card['authority_root'] and
            expected_context['artifact_class'] == 'genesis-runtime' and
            expected_context['trust_algorithm'] == 'local-hmac-sha256.v0.2' and
            expected_context['domain_version'] == '0.2' and
            expected_context['archive_profile'] == 'composite-rigid-support.v0.2' and
            expected_context['storage_profile'] == 'local-posix-blob-sync-v0.2', 'card deployment context')
    require(owner['context'] == expected_context, 'owner context/world/root differs from card')
    require(owner['key_dir'] == card['key_directory'], 'owner key directory differs from card')
    require(owner['inputs'] == card['inputs'], 'owner inputs differ from persistent four-input pins')
    require(type(owner['session']) is dict and type(owner['session'].get('can_initialize')) is bool and
            re.fullmatch('[a-z][a-z0-9._-]{0,63}', card['principal']) and
            type(card['allowed_actions']) is list and len(card['allowed_actions']) == 2 and
            set(card['allowed_actions']) == {'retain_snapshot', 'physics_step'} and
            all(type(expected_context[key]) is str and re.fullmatch('[0-9a-f]{64}', expected_context[key])
                for key in ('trust_anchor', 'expected_build', 'expected_options')), 'owner typed grants/context')
    require(owner['session'] == {'principal': card['principal'],
            'can_initialize': name == 'initialize', 'allowed_actions': card['allowed_actions']},
            'owner principal/actions/initialization grant differs from card')
    for role, context_key in (('build', 'expected_build'), ('options', 'expected_options')):
        record = read_json(card['inputs'][role]['path'])
        require(hashlib.sha256(PREFIX + canonical(record)).hexdigest() == expected_context[context_key],
                'owner context does not bind deployed ' + role)
    scratch = safe_path(owner['scratch'])
    require(scratch.is_relative_to(safe_path(card['storage_root'])), 'owner scratch outside persistent storage')
    protected = [safe_path(card[k]) for k in ('authority_root', 'deployment_root', 'key_directory')]
    require(all(not scratch.is_relative_to(p) and not p.is_relative_to(scratch) for p in protected),
            'owner scratch overlaps authority/deployment/key')


def _python_link_chain(entry, expected=None):
    """Walk executable components, validating each authorized hop before following it.

    Resolve '..' only after preceding components, matching filesystem semantics.
    This exception is private to the interpreter pin; safe_path stays unchanged.
    """
    require(type(entry) is str and Path(entry).is_absolute() and str(Path(entry)) == entry
            and '..' not in Path(entry).parts, 'canonical lexical Python entry required')
    if expected is not None:
        require(type(expected) is list and len(expected) <= 32 and
                all(type(x) is dict and set(x) == {'path', 'readlink'} and
                    type(x['path']) is str and type(x['readlink']) is str for x in expected),
                'Python link pin shape')
    pending = list(Path(entry).parts[1:])
    current, links, seen = Path('/'), [], set()
    while pending:
        part = pending.pop(0)
        if part in ('', '.'):
            continue
        if part == '..':
            require(current != Path('/'), 'Python link escapes root')
            current = current.parent
            continue
        candidate = current / part
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode):
            require(len(links) < 32 and str(candidate) not in seen, 'Python link cycle/hop limit')
            link = {'path': str(candidate), 'readlink': os.readlink(candidate)}
            if expected is not None:
                require(len(links) < len(expected) and link == expected[len(links)],
                        'unexpected Python symlink/redirection')
            links.append(link)
            seen.add(str(candidate))
            target = Path(link['readlink'])
            require(not link['readlink'].startswith('//'), 'ambiguous Python link root')
            if target.is_absolute():
                current = Path('/')
                pending = list(target.parts[1:]) + pending
            else:
                pending = list(target.parts) + pending
        else:
            require(stat.S_ISDIR(info.st_mode) if pending else stat.S_ISREG(info.st_mode),
                    'Python component is not a directory/regular executable')
            current = candidate
    if expected is not None:
        require(len(links) == len(expected), 'unused Python link pins')
    return safe_path(current), links


def _python_venv_layout(entry, cfg_raw):
    lexical = Path(entry)
    require(lexical.parent.name == 'bin', 'Python entry must belong to venv/bin')
    settings = {}
    for line in cfg_raw.decode('utf-8').splitlines():
        if '=' in line:
            key, value = (x.strip() for x in line.split('=', 1))
            require(key not in settings, 'duplicate pyvenv setting')
            settings[key] = value
    versions = []
    for key in ('version_info', 'version'):
        if key in settings:
            found = re.fullmatch(r'([0-9]+)\.([0-9]+)(?:\.[0-9]+)?', settings[key])
            require(found is not None, 'pyvenv version required')
            versions.append(found.group(1) + '.' + found.group(2))
    require(versions and len(set(versions)) == 1, 'pyvenv version inconsistent/missing')
    version = versions[0]
    require(lexical.name in ('python', 'python' + version.split('.')[0], 'python' + version),
            'Python entry/pyvenv version mismatch')
    venv = lexical.parent.parent
    return venv / 'pyvenv.cfg', venv / 'lib' / ('python' + version) / 'site-packages'


def _python_site_identity(path):
    path = safe_path(path)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode), 'venv site-packages directory missing')
    return {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino,
            'uid': info.st_uid, 'mode': stat.S_IMODE(info.st_mode)}


def collect_python_pin(entry):
    """Read-only root helper: produces proposed metadata, never executes Python."""
    target, links = _python_link_chain(entry)
    cfg = safe_path(Path(entry).parent.parent / 'pyvenv.cfg')
    cfg_raw = safe_read(cfg, 65536)
    expected_cfg, site = _python_venv_layout(entry, cfg_raw)
    require(cfg == expected_cfg and target.is_file() and os.access(target, os.X_OK),
            'venv configuration/executable binding')
    return {'entry': entry, 'links': links,
            'target': {'path': str(target), 'sha256': file_hash(target)},
            'pyvenv_cfg': {'path': str(cfg), 'sha256': hashlib.sha256(cfg_raw).hexdigest()},
            'site_packages': _python_site_identity(site)}


def validate_python_executable(card):
    """Preserve lexical venv argv; permit only its root-card-pinned link chain."""
    entry = card['python_executable']
    pin = card.get('python_environment_pin')
    if pin is None:
        require(safe_path(entry).is_file() and os.access(entry, os.X_OK),
                'runtime Python unavailable')
        return entry
    require(not os.environ.get('PYTHONHOME') and not os.environ.get('PYTHONPATH'),
            'pinned Python requires empty PYTHONHOME/PYTHONPATH')
    require(type(pin) is dict and set(pin) ==
            {'entry', 'links', 'target', 'pyvenv_cfg', 'site_packages'} and pin['entry'] == entry,
            'Python environment pin shape/entry mismatch')
    for name in ('target', 'pyvenv_cfg'):
        require(type(pin[name]) is dict and set(pin[name]) == {'path', 'sha256'} and
                type(pin[name]['path']) is str and
                type(pin[name]['sha256']) is str and re.fullmatch('[0-9a-f]{64}', pin[name]['sha256']),
                'Python file pin shape')
    target, _ = _python_link_chain(entry, pin['links'])
    require(str(target) == pin['target']['path'] and target.is_file() and
            os.access(target, os.X_OK) and file_hash(target) == pin['target']['sha256'],
            'pinned canonical Python target changed')
    cfg = safe_path(Path(entry).parent.parent / 'pyvenv.cfg')
    require(str(cfg) == pin['pyvenv_cfg']['path'], 'pyvenv.cfg outside lexical venv')
    cfg_raw = safe_read(cfg, 65536)
    require(hashlib.sha256(cfg_raw).hexdigest() == pin['pyvenv_cfg']['sha256'], 'pyvenv.cfg changed')
    expected_cfg, site = _python_venv_layout(entry, cfg_raw)
    spec = pin['site_packages']
    require(type(spec) is dict and set(spec) == {'path', 'device', 'inode', 'uid', 'mode'} and
            type(spec['path']) is str and all(type(spec[k]) is int and spec[k] >= 0
                for k in ('device', 'inode', 'uid', 'mode')),
            'site-packages identity pin shape')
    require(cfg == expected_cfg and str(site) == spec['path'] and _python_site_identity(site) == spec,
            'site-packages outside same venv/version or changed identity')
    return entry


def validate_run(card_path, card_hash, accepted_source, session, execute):
    """No writes or runtime spawn. The card is honest local-owner authorization."""
    require(execute is True, 'run requires explicit --execute; no process launched')
    require(card_path and card_hash and accepted_source, 'run requires R12 card/hash and accepted source')
    require(session in ('initialize', 'existing'), 'explicit session required')
    require(re.fullmatch('[0-9a-f]{40}', accepted_source), 'accepted source must be exact SHA40')
    card_path = private_metadata(card_path)
    private_metadata(card_path.parent, directory=True)
    require(file_hash(card_path) == card_hash, 'R12 card hash mismatch')
    card = read_json(card_path)
    require(card['format'] == 'universe-i12-r12.v1' and card['approved'] is True and
            card['issuer'] == 'root' and card['scope'] == 'two-real-ue-owned-sessions' and
            card['allow_forced_cleanup'] is True, 'missing actual R12 authorization/cleanup policy')
    now = datetime.now(timezone.utc)
    issued, expires = (datetime.fromisoformat(card[key].replace('Z', '+00:00'))
                       for key in ('issued_at', 'expires_at'))
    require(issued <= now < expires, 'R12 card not currently valid')
    require(card['product_source'] == accepted_source and
            re.fullmatch('[a-z][a-z0-9._-]{0,63}', card['run_id']) and
            re.fullmatch('[a-z][a-z0-9._-]{0,63}', card['world_id']), 'R12 source/run/world binding')
    require(set(card['accepted_gates']) == {'G-P1', 'I10B', 'G-B1'} and
            all(type(ref) is str and ref for ref in card['accepted_gates'].values()), 'accepted gate references')
    product = safe_path(card['product_root'])
    require(product_identity(product, card['allowed_untracked']) == accepted_source,
            'product HEAD differs from accepted source')
    launcher = product / 'scripts/launch_edgeworld_ue_mac.sh'
    require(file_hash(launcher) == card['launcher_sha256'], 'accepted launcher hash mismatch')
    storage = private_metadata(card['storage_root'], directory=True)
    require(on_devssd(storage), 'runtime evidence must be on DevSSD')
    deployment = private_metadata(card['deployment_root'], directory=True)
    require(deployment.is_relative_to(storage), 'deployment bundle must be persistent inside storage root')
    require(set(card['inputs']) == {'build', 'options', 'assets', 'asset_audit'}, 'exact four deployment inputs')
    for spec in card['inputs'].values():
        require(set(spec) == {'path', 'sha256'}, 'input pin shape')
        path = safe_path(spec['path'])
        require(path.is_relative_to(deployment) and file_hash(path) == spec['sha256'],
                'deployed input missing or hash mismatch')
    authority = safe_path(card['authority_root'])
    key_dir = private_metadata(card['key_directory'], directory=True)
    require(authority.is_relative_to(storage) and not storage.is_relative_to(authority) and
            not key_dir.is_relative_to(storage) and not storage.is_relative_to(key_dir),
            'authority/key/evidence locations overlap')
    expected_output = (product / 'engine_platforms/unreal/EdgeWorldHost/Saved/MacLauncher').resolve()
    launcher_output = safe_path(card['launcher_output_root'])
    require(expected_output == launcher_output and launcher_output.is_relative_to(storage) and
            launcher_output.is_dir(), 'existing launcher output mapping must resolve inside DevSSD storage')
    require(set(card['sessions']) == {'initialize', 'existing'}, 'two session resource slots required')
    limits = card['budget']
    require(type(limits['seconds']) is int and 0 < limits['seconds'] <= 1200 and
            type(limits['bytes']) is int and 0 < limits['bytes'] <= 2 * 1024**3 and
            type(limits['cleanup_seconds']) is int and 1 <= limits['cleanup_seconds'] <= 30 and
            type(limits['spent_seconds']) is int and limits['spent_seconds'] >= 0 and
            type(limits['spent_bytes']) is int and limits['spent_bytes'] >= 0 and
            sum(s['max_seconds'] for s in card['sessions'].values()) + limits['spent_seconds'] <=
            limits['seconds'], 'R12 total limits')
    for name, slot in card['sessions'].items():
        require(type(slot['max_seconds']) is int and slot['max_seconds'] > limits['cleanup_seconds'] and
                set(slot['stage_seconds']) == {'build', 'startup', 'interaction', 'shutdown'} and
                all(type(n) is int and n > 0 for n in slot['stage_seconds'].values()), 'session/stage limits')
        owner = private_metadata(slot['owner_config']['path'])
        private_metadata(owner.parent, directory=True)
        require(owner.is_relative_to(deployment) and file_hash(owner) == slot['owner_config']['sha256'],
                'persistent owner config hash mismatch')
        validate_owner_deployment(card, name, owner, slot['owner_config']['sha256'])
    # These public/binary hashes are input pins, never commands chosen by JSON.
    require(card['runtime_files'], 'explicit runtime/build identity pins required')
    for spec in card['runtime_files']:
        require(file_hash(spec['path']) == spec['sha256'], 'runtime/build identity hash mismatch')
    validate_python_executable(card)
    require(safe_path(card['ue_root']).is_dir(), 'runtime executable/environment unavailable')
    prior = None
    if session == 'existing':
        prior = read_json(storage / 'sessions/initialize/completion.json')
        require(prior['card_sha256'] == card_hash and prior['accepted_source'] == accepted_source and
                prior['normal'] is True and prior['session'] == 'initialize', 'first session not normally completed')
        require((authority / 'HEAD.json').is_file(), 'existing revisit requires authority HEAD')
    else:
        require(not (authority / 'HEAD.json').exists(), 'initialize session cannot reinitialize existing HEAD')
    destination = storage / 'sessions' / session
    require(not destination.exists(), 'session output already exists; no overwrite or hidden retry')
    require(tree_bytes(storage) + limits['spent_bytes'] + 1024**2 < limits['bytes'],
            'budget already exhausted before launcher spawn')
    argv = ['/bin/bash', str(launcher), '--launch', '--viewport-preflush', '--universe',
            '--owner-config', card['sessions'][session]['owner_config']['path'],
            '--user-dir', str(destination / 'user')]
    if session == 'initialize':
        argv.append('--universe-initialize')
    return {'card': card, 'card_path': str(card_path), 'card_hash': card_hash,
            'source': accepted_source, 'session': session, 'output': destination, 'argv': argv,
            'prior_seconds': prior['cumulative_seconds'] if prior else limits['spent_seconds']}


def tree_bytes(root):
    total = 0
    for path in safe_path(root).rglob('*'):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue  # A live Store temp file can be atomically renamed after enumeration.
        require(not stat.S_ISLNK(info.st_mode), 'symlink runtime evidence entry')
        if stat.S_ISDIR(info.st_mode):
            continue
        require(stat.S_ISREG(info.st_mode), 'nonregular runtime evidence entry')
        total += info.st_size
    return total


def observed_processes(launcher_pid, known=None):
    """Keep only descendants or previously owned exact PID/start/argv identities."""
    result = subprocess.run(['/bin/ps', '-ww', '-axo', 'pid=,ppid=,pgid=,lstart=,command='],
                            capture_output=True, text=True, timeout=5, check=True)
    rows = {}
    for line in result.stdout.splitlines():
        fields = line.split(None, 8)
        if len(fields) == 9:
            pid, parent, group = map(int, fields[:3])
            rows[pid] = {'pid': pid, 'ppid': parent, 'pgid': group,
                         'start': ' '.join(fields[3:8]), 'argv': fields[8]}
    owned = {launcher_pid}
    while True:
        expanded = owned | {pid for pid, row in rows.items() if row['ppid'] in owned}
        if expanded == owned:
            break
        owned = expanded
    for pid, old in (known or {}).items():
        row = rows.get(pid)
        if row and (row['start'], row['argv']) == (old['start'], old['argv']):
            owned.add(pid)
    return {pid: rows[pid] for pid in owned if pid in rows}


def cleanup_owned(process, known, grace):
    """Failure only: normal launcher TERM forwarding first, exact identities next."""
    actions = []
    if process.poll() is None:
        process.terminate()
        actions.append({'pid': process.pid, 'signal': 'TERM', 'ownership': 'parent Popen handle'})
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    remaining = observed_processes(process.pid, known)
    for pid, row in remaining.items():
        old = known.get(pid)
        if pid == process.pid or old is None:
            continue
        if (row['start'], row['argv']) == (old['start'], old['argv']):
            try:
                os.kill(pid, signal.SIGTERM)
                actions.append({'pid': pid, 'signal': 'TERM', 'identity': row})
            except ProcessLookupError:
                pass
    if process.poll() is None:
        process.kill()
        actions.append({'pid': process.pid, 'signal': 'KILL', 'ownership': 'parent Popen handle'})
    code = process.wait(timeout=max(1, grace))
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        remaining = observed_processes(process.pid, known)
        if not remaining:
            return code, actions
        time.sleep(.1)
    for pid, row in observed_processes(process.pid, known).items():
        old = known.get(pid)
        if old and pid != process.pid and (row['start'], row['argv']) == (old['start'], old['argv']):
            try:
                os.kill(pid, signal.SIGKILL)
                actions.append({'pid': pid, 'signal': 'KILL', 'identity': row})
            except ProcessLookupError:
                pass
    return code, actions


def finalize_session(prepared, receipt, start, launcher_dir, candidate):
    """Seal first; only publish audited completion after all receipt/seal writes.

    Completion charges a conservative extra 2s (plus ceil) for its own write/audit.
    If writing/auditing exceeds that bound, retain pending/failure evidence and
    publish no usable completion. Existing session never trusts preliminary receipt.
    """
    output, card = prepared['output'], prepared['card']
    emit(receipt, output / 'supervisor-exit.json')  # Always normal=false, not a completion.
    indexed = []
    for directory in (output, launcher_dir):
        if directory:
            for path in sorted(directory.rglob('*')):
                if path.is_file():
                    indexed.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': file_hash(path)})
    emit({'format': 'universe-i12-session-seal.v1', 'captured_at': utc(), 'files': indexed,
          'note': 'exclusive snapshot at supervisor close; later screenshots need a new final bundle'},
         output / 'session-seal.json')
    observed = time.monotonic() - start
    charged = math.ceil(observed) + 2
    completion = dict(receipt, format='universe-i12-completion.v1', normal=candidate,
                      elapsed_seconds=charged, cumulative_seconds=prepared['prior_seconds'] + charged,
                      elapsed_observed_before_completion=observed, completion_required=False)
    budget = card['budget']
    if charged > card['sessions'][prepared['session']]['max_seconds'] or \
            completion['cumulative_seconds'] > budget['seconds']:
        completion.update(normal=False, failure=receipt['failure'] or 'final seal/completion time budget exceeded')
    base_bytes = tree_bytes(card['storage_root']) + budget['spent_bytes']
    completion['final_bytes_including_completion'] = base_bytes
    # This integer field affects its own encoded length; converge before writing.
    for _ in range(10):
        count = base_bytes + len((json.dumps(completion, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode())
        if count == completion['final_bytes_including_completion']:
            break
        completion['final_bytes_including_completion'] = count
    require(completion['final_bytes_including_completion'] <= budget['bytes'],
            'final seal/receipt/completion byte budget exceeded')
    pending, final = output / 'completion-pending.json', output / 'completion.json'
    emit(completion, pending)
    actual_time = time.monotonic() - start
    actual_bytes = tree_bytes(card['storage_root']) + budget['spent_bytes']
    require(actual_time <= charged and actual_bytes == completion['final_bytes_including_completion'],
            'completion write/audit exceeded conservative final accounting')
    require(not final.exists(), 'completion already exists')
    os.rename(pending, final)  # Same bytes; private exclusive session, no ready marker before audit.
    return completion


def supervise(prepared):
    """One live parent owns wait(). No UI, screenshot, solver or trust operations."""
    card, session, output = prepared['card'], prepared['session'], prepared['output']
    slot, budget = card['sessions'][session], card['budget']
    parent = output.parent
    if not parent.exists():
        parent.mkdir(mode=0o700)
    private_metadata(parent, directory=True)
    output.mkdir(mode=0o700)  # Exclusive: failed attempts can never be overwritten.
    start = time.monotonic()
    reason, process, launcher_dir, exit_code = None, None, None, None
    known, cleanup, worker_exits = {}, [], []
    stage, stage_started, launcher_text, ue_pid = 'build', start, '', None
    environment = {k: v for k, v in os.environ.items() if not k.startswith('EDGEWORLD_')}
    environment.update(UE5_ROOT=card['ue_root'], EDGEWORLD_UNIVERSE_PYTHON=card['python_executable'])
    emit({'card_sha256': prepared['card_hash'], 'accepted_source': prepared['source'],
          'run_id': card['run_id'], 'session': session, 'argv': prepared['argv'],
          'captured_at': utc(), 'supervisor_pid': os.getpid(),
          'environment': {k: environment[k] for k in ('UE5_ROOT', 'EDGEWORLD_UNIVERSE_PYTHON')}},
         output / 'launch.json')
    if Path(card['authority_root']).is_dir():
        emit(authority_map(card['authority_root']), output / 'authority-before.json')
    stdout_path = output / 'launcher-stdout.log'
    event_path = output / 'supervisor-events.jsonl'
    stdout_fd = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    event_fd = os.open(event_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(stdout_fd, 'wb') as stdout:
        events = os.fdopen(event_fd, 'w')
        def record(value):
            events.write(json.dumps(dict(value, utc=utc(), monotonic_seconds=time.monotonic())) + '\n')
            events.flush()
        def best_effort_record(value):
            try:
                record(value)
            except (OSError, ValueError):
                pass
        try:
            process = subprocess.Popen(prepared['argv'], cwd=card['product_root'], env=environment,
                                       stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record({'event': 'spawn', 'launcher_pid': process.pid, 'supervisor_pid': os.getpid()})
            offset = 0
            while True:
                now = time.monotonic()
                elapsed = now - start
                size = tree_bytes(card['storage_root']) + budget['spent_bytes']
                require(size + 1024**2 <= budget['bytes'], 'raw byte budget/reserve exhausted')
                require(elapsed + prepared['prior_seconds'] + budget['cleanup_seconds'] < budget['seconds'] and
                        elapsed + budget['cleanup_seconds'] < slot['max_seconds'], 'session/total time reserve exhausted')
                require(now - stage_started < slot['stage_seconds'][stage], 'stage time exhausted: ' + stage)
                with stdout_path.open('rb') as stream:
                    stream.seek(offset)
                    block = stream.read(1024**2)
                offset += len(block)
                launcher_text += block.decode('utf-8', errors='replace')
                require(len(launcher_text) <= 16 * 1024**2, 'launcher control-log cap')
                found = re.search(r'\[launcher\] evidence=([^\r\n]+)', launcher_text)
                if found:
                    candidate = safe_path(found.group(1))
                    require(candidate.parent == Path(card['launcher_output_root']) and candidate.is_dir(),
                            'launcher reported unowned evidence directory')
                    require(launcher_dir is None or launcher_dir == candidate, 'launcher evidence identity changed')
                    launcher_dir = candidate
                found = re.search(r'\[launcher\] process_spawned pid=([0-9]+);', launcher_text)
                if found:
                    ue_pid = int(found.group(1))
                rows = observed_processes(process.pid, known)
                known.update(rows)
                record({'event': 'poll', 'stage': stage, 'elapsed_seconds': elapsed,
                        'evidence_bytes': size, 'owned_processes': list(rows.values()),
                        'launcher_evidence': str(launcher_dir) if launcher_dir else None})
                next_stage = stage
                if stage == 'build' and '[launcher] build_succeeded;' in launcher_text:
                    next_stage = 'startup'
                if stage in ('build', 'startup') and '[launcher] validated_observation_seen;' in launcher_text:
                    next_stage = 'interaction'
                if launcher_dir and (launcher_dir / 'ue.log').is_file():
                    with (launcher_dir / 'ue.log').open('rb') as log:
                        log.seek(max(0, (launcher_dir / 'ue.log').stat().st_size - 65536))
                        if b'LogExit: Preparing to exit.' in log.read(65536):
                            next_stage = 'shutdown'
                if next_stage != stage:
                    stage, stage_started = next_stage, now
                    record({'event': 'stage', 'stage': stage})
                if process.poll() is not None:
                    exit_code = process.wait()  # Parent-owned actual wait result, never ps inference.
                    with stdout_path.open('rb') as stream:
                        stream.seek(offset)
                        tail = stream.read(16 * 1024**2 + 1)
                    require(len(launcher_text) + len(tail) <= 16 * 1024**2, 'launcher final log cap')
                    launcher_text += tail.decode('utf-8', errors='replace')
                    break
                time.sleep(.25)
        except BaseException as error:
            reason = type(error).__name__ + ': ' + str(error)
            try:
                best_effort_record({'event': 'failure', 'reason': reason})
            finally:
                if process is not None:
                    try:
                        exit_code, cleanup = cleanup_owned(process, known, max(1, budget['cleanup_seconds'] // 3))
                    except (OSError, subprocess.SubprocessError, Invalid) as cleanup_error:
                        reason += '; cleanup error: ' + str(cleanup_error)
                        if process.poll() is None:
                            process.kill()  # Only actual Popen child; no PID discovery fallback.
                        try:
                            exit_code = process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            reason += '; parent wait incomplete'
            best_effort_record({'event': 'cleanup', 'actions': cleanup, 'launcher_wait_exit': exit_code})
        finally:
            try:
                events.close()
            except OSError as close_error:
                reason = reason or 'event log close error: ' + str(close_error)
    if launcher_dir is None:
        found = re.search(r'\[launcher\] evidence=([^\r\n]+)', launcher_text)
        if found:
            candidate = safe_path(found.group(1))
            if candidate.parent == Path(card['launcher_output_root']) and candidate.is_dir():
                launcher_dir = candidate
            else:
                reason = reason or 'final launcher evidence directory outside pinned root'
    if ue_pid is None:
        found = re.search(r'\[launcher\] process_spawned pid=([0-9]+);', launcher_text)
        ue_pid = int(found.group(1)) if found else None
    if launcher_dir:
        try:
            trace = inspect_trace(launcher_dir / 'trace')
            worker_exits = trace['worker_exits']
            require(len(worker_exits) == trace['transport_count'] and trace['frames'] and
                    all(f['host_pid'] == ue_pid for f in trace['frames']), 'trace/UE ownership binding')
        except (Invalid, OSError, ValueError, KeyError, TypeError) as error:
            reason = reason or 'worker lifecycle: ' + str(error)
    if ue_pid not in known or (process is not None and known[ue_pid]['ppid'] != process.pid):
        reason = reason or 'UE child identity not observed under launcher'
    match = re.search(r'\[launcher\] ue_exit_code=(-?[0-9]+)', launcher_text)
    ue_exit = int(match.group(1)) if match else None
    try:
        remaining = observed_processes(process.pid, known) if process is not None else {}
    except (OSError, subprocess.SubprocessError, Invalid) as error:
        remaining = {}
        reason = reason or 'final process observation failed: ' + str(error)
    if remaining:
        reason = reason or 'owned processes remain after launcher wait'
        try:
            _, actions = cleanup_owned(process, known, max(1, budget['cleanup_seconds'] // 3))
            cleanup.extend(actions)
            remaining = observed_processes(process.pid, known)
        except (OSError, subprocess.SubprocessError, Invalid) as error:
            reason += '; final owned cleanup failed: ' + str(error)
    if Path(card['authority_root']).is_dir():
        try:
            emit(authority_map(card['authority_root']), output / 'authority-after.json')
        except (OSError, Invalid) as error:
            reason = reason or 'authority final map failed: ' + str(error)
    elapsed = time.monotonic() - start
    if elapsed + prepared['prior_seconds'] > budget['seconds'] or elapsed > slot['max_seconds']:
        reason = reason or 'final time budget exceeded'
    final_bytes = tree_bytes(card['storage_root']) + budget['spent_bytes']
    if final_bytes + 1024**2 > budget['bytes']:
        reason = reason or 'final byte budget/reserve exceeded'
    normal = (reason is None and exit_code == 0 and ue_exit == 0 and ue_pid is not None and
              len(worker_exits) >= 1 and all(e['exit_code'] == 0 for e in worker_exits))
    receipt = {'format': 'universe-i12-supervisor-exit.v1', 'card_sha256': prepared['card_hash'],
               'accepted_source': prepared['source'], 'run_id': card['run_id'], 'session': session,
               'world_id': card['world_id'], 'authority_root': card['authority_root'],
               'supervisor_pid': os.getpid(), 'launcher_pid': process.pid if process else None,
               'launcher_wait_exit': exit_code, 'ue_pid': ue_pid, 'ue_exit_code': ue_exit,
               'ue_exit_source': 'actual launcher parent wait status line; correlate pinned launcher source/raw',
               'worker_exits': worker_exits, 'normal': False, 'exit_candidate': normal,
               'completion_required': True, 'failure': reason,
               'forced_cleanup': cleanup, 'remaining_owned': list(remaining.values()),
               'elapsed_seconds': elapsed, 'cumulative_seconds': prepared['prior_seconds'] + elapsed,
               'evidence_bytes_before_receipt_seal': final_bytes, 'captured_at': utc(),
               'launcher_evidence': str(launcher_dir) if launcher_dir else None,
               'verdict': 'supervision only; UI/G-B2 require independent evidence review'}
    try:
        return finalize_session(prepared, receipt, start, launcher_dir, normal)
    except (OSError, Invalid, ValueError) as error:
        failure = dict(receipt, normal=False, finalization_error=str(error),
                       failure=reason or 'finalization failed: ' + str(error))
        try:
            emit(failure, output / 'finalization-failed.json')
        except (OSError, Invalid):
            pass
        return failure  # Caller stdout preserves original runtime error even on a full evidence disk.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='exclusive new evidence file; parent must exist')
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('plan')
    snapshot = commands.add_parser('snapshot')
    snapshot.add_argument('--authority', type=Path, required=True)
    processes = commands.add_parser('processes')
    processes.add_argument('--pid', type=int, action='append', required=True)
    meta = commands.add_parser('metadata')
    meta.add_argument('paths', nargs='+')
    wait = commands.add_parser('wait-marker')
    wait.add_argument('--log', type=Path, required=True)
    wait.add_argument('--marker', required=True)
    wait.add_argument('--initial-sha256', required=True)
    wait.add_argument('--start-offset', type=int, help='action-before log byte length; hash covers exactly this prefix')
    wait.add_argument('--expected-device', type=int, help='action-before st_dev, required with explicit offset')
    wait.add_argument('--expected-inode', type=int, help='action-before st_ino, required with explicit offset')
    wait.add_argument('--run-id', help='caller-bound run identity; correlate raw process evidence')
    wait.add_argument('--host-pid', type=int, help='caller-bound UE PID; not inferred or authenticated')
    wait.add_argument('--seconds', type=float, default=10)
    collection = commands.add_parser('collect')
    collection.add_argument('--spec', type=Path, required=True)
    run = commands.add_parser('run', help='one parent-owned session; explicit actual R12 execution only')
    run.add_argument('--r12-card', type=Path)
    run.add_argument('--card-sha256')
    run.add_argument('--accepted-source')
    run.add_argument('--session', choices=('initialize', 'existing'))
    run.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        if args.command in (None, 'plan'):
            value = {'format': 'universe-i12-action-plan.v1', 'runtime_authorized': False,
                     'candidate_budget': {'seconds': 1200, 'bytes': 2 * 1024**3},
                     'actions': [{'id': key, 'instruction': text} for key, text in PLAN],
                     'lod': 'N/A for this technical proxy; record rationale, do not claim coverage',
                     'pending': ['final merged SHA/build', 'G-P1/I10B/I11B accepted evidence',
                                 'actual root-issued R12', 'trusted owner inputs', 'UI automation binding']}
        elif args.command == 'snapshot':
            value = dict(authority_map(args.authority), captured_at=utc())
        elif args.command == 'processes':
            value = process_snapshot(args.pid)
        elif args.command == 'metadata':
            value = metadata(args.paths)
        elif args.command == 'wait-marker':
            value = wait_marker(args.log, args.marker, args.seconds, args.initial_sha256,
                                args.start_offset, args.expected_device, args.expected_inode,
                                args.run_id, args.host_pid)
        elif args.command == 'collect':
            value = collect(args.spec)
        else:
            require(args.output is None, 'run uses its card-bound exclusive directory, not --output')
            prepared = validate_run(args.r12_card, args.card_sha256, args.accepted_source,
                                    args.session, args.execute)
            value = supervise(prepared)
        emit(value, args.output)
        return 2 if value.get('matched') is False or value.get('normal') is False else 0
    except (Invalid, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
