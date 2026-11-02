"""I13 passive lifecycle evidence and pure resource guards.

No authority imports, UI actions, launches or signals. A caller owns dispatcher,
normal quit, parent wait, exact cleanup and final publication. Evidence validation
is structural: a successful result never grants the runtime acceptance gate.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import time

FORMAT = 'universe-i13-lifecycle.v1'
STAGES = {'build': 60, 'startup': 60, 'interaction': 240, 'shutdown': 40, 'seal': 20}
PS_ARGV = ('/bin/ps', '-ww', '-axo', 'pid=,ppid=,lstart=,command=')
RUN_FIELDS = {'run_id', 'source_sha', 'world_id', 'authority_root'}
READY_FIELDS = RUN_FIELDS | {'session', 'host_pid', 'worker_pid', 'generation'}
MAX_BYTES = 2 * 1024**3


class Invalid(ValueError):
    """Contradictory or malformed evidence; never coerce into success."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def number(value, label):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            label + ' must be finite nonnegative seconds')
    return value


def integer(value, label, minimum=0):
    require(type(value) is int and value >= minimum, label + ' must be integer')
    return value


def utc_seconds(value):
    require(type(value) is str, 'UTC must be an ISO string')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, 'UTC timezone missing')
    return parsed.timestamp()


def checked_path(raw):
    require(type(raw) is str and Path(raw).is_absolute(), 'absolute path required')
    path = Path(raw)
    require(str(path) == raw and '..' not in path.parts, 'noncanonical path spelling')
    for part in (path, *path.parents):
        require(not part.is_symlink(), 'symlink path refused')
    require(path.resolve() == path, 'canonical path required')
    return path


def validate_binding(binding, expected, ready=False):
    fields = READY_FIELDS if ready else RUN_FIELDS
    require(type(binding) is dict and set(binding) == fields and binding == expected,
            'binding differs from independently supplied expected binding')
    require(re.fullmatch('[0-9a-f]{40}', binding['source_sha']) is not None, 'source SHA40')
    for field in ('run_id', 'world_id'):
        require(type(binding[field]) is str and re.fullmatch('[a-z][a-z0-9._-]{0,63}', binding[field]),
                'invalid ' + field)
    checked_path(binding['authority_root'])
    if ready:
        require(binding['session'] in ('initialize', 'existing'), 'session')
        for field in ('host_pid', 'worker_pid', 'generation'):
            integer(binding[field], field, 1)


def validate_identity(row):
    require(type(row) is dict and set(row) == {'pid', 'ppid', 'start', 'argv'}, 'process identity shape')
    integer(row['pid'], 'pid', 1)
    integer(row['ppid'], 'ppid')
    for key in ('start', 'argv'):
        require(type(row[key]) is str and bool(row[key].strip()) and '\n' not in row[key],
                'empty/invalid process ' + key)
    return row


def process_key(row):
    validate_identity(row)
    return row['pid'], row['start'], row['argv']


def same_process(before, after):
    """PPID is mutable after reparenting; PID reuse changes start or argv."""
    return process_key(before) == process_key(after)


def parse_ps_snapshot(raw):
    require(type(raw) is str, 'ps text required')
    rows, pids = [], set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        fields = line.split(None, 7)
        require(len(fields) == 8, 'malformed ps row')
        row = {'pid': int(fields[0]), 'ppid': int(fields[1]),
               'start': ' '.join(fields[2:7]), 'argv': fields[7]}
        validate_identity(row)
        require(row['pid'] not in pids, 'duplicate ps PID')
        pids.add(row['pid'])
        rows.append(row)
    return rows


def exclusive_bytes(path, data):
    path = checked_path(str(path))
    require(path.parent.is_dir(), 'existing output directory required')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}


def read_ref(ref, cap=16 * 1024**2):
    require(type(ref) is dict and set(ref) == {'path', 'sha256'}, 'public ref shape')
    require(type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'ref SHA64')
    path = checked_path(ref['path'])
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        require(stat.S_ISREG(st.st_mode) and st.st_size <= cap, 'ref regular file/cap')
        data = stream.read(cap + 1)
        require(len(data) <= cap, 'ref cap')
        after = path.lstat()
        require((st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'ref changed during read')
    require(hashlib.sha256(data).hexdigest() == ref['sha256'], 'ref digest mismatch')
    return data


def json_ref(ref):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(read_ref(ref), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(Invalid('nonfinite JSON')))


def observe_once(raw_path):
    """Fixed passive CLI only. Invoke from a dedicated observer, not UI callbacks."""
    started = time.monotonic()
    result = subprocess.run(PS_ARGV, capture_output=True, timeout=1, check=True)
    observed = time.monotonic()
    rows = parse_ps_snapshot(result.stdout.decode('utf-8', errors='strict'))
    reference = exclusive_bytes(raw_path, result.stdout)
    return {'monotonic': observed, 'utc': datetime.now(timezone.utc).isoformat(),
            'processes': rows, 'raw_ref': reference, 'query_started_monotonic': started}


def record_observer(stop_event, directory, *, prefix='sample', on_sample=None):
    """Blocking observer loop for a dedicated controller thread/process.

    stop_event is independent of the supervisor. Writes one last sample after stop;
    callbacks persist returned metadata (including errors) outside this routine.
    Never stops merely because the launcher's PID exited.
    """
    require(re.fullmatch('[a-z0-9-]+', prefix) is not None, 'sample prefix')
    directory = checked_path(str(directory))
    require(directory.is_dir(), 'observer directory missing')
    samples = []
    while True:
        stopping = stop_event.is_set()
        sample = observe_once(directory / (prefix + '-%06d.ps' % len(samples)))
        samples.append(sample)
        if on_sample:
            on_sample(sample)
        if stopping:
            return samples
        stop_event.wait(.5)


def classify_processes(rows, known_owned, accepted_executable):
    """Return relevant rows; all same executable extras are unresolved contamination.

    accepted_executable and known exact roots come from the frozen outer card.
    No executable paths are executed by this function.
    """
    executable = str(checked_path(accepted_executable))
    keys = {process_key(row) for row in known_owned}
    owned_pids = {row['pid'] for row in rows if process_key(row) in keys}
    while True:
        expanded = owned_pids | {row['pid'] for row in rows if row['ppid'] in owned_pids}
        if expanded == owned_pids:
            break
        owned_pids = expanded
    relevant = []
    for row in rows:
        process_key(row)
        matches = row['argv'] == executable or row['argv'].startswith(executable + ' ')
        if row['pid'] in owned_pids or matches:
            relevant.append({'identity': row, 'ownership': 'owned' if row['pid'] in owned_pids
                             else 'contamination'})
    return relevant


def interval_union_seconds(intervals):
    merged = []
    for left, right in sorted(intervals):
        number(left, 'interval start')
        number(right, 'interval end')
        require(left <= right, 'reversed interval')
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    return sum(right - left for left, right in merged)


def budget_guard(*, now, dispatch, session_start, stage, stage_start,
                 ready_binding, expected_binding, live_processes, expected_processes, sample_monotonic,
                 contamination=False, closing=False, tool_seconds=0, global_limit=1200):
    """Pure decision. stop/quit_due allow only input release and normal quit.

    No input action may cross its deadline. Decisions are permits, never evidence
    of a normal exit. Each call must use a fresh passive process sample externally.
    """
    for label, value in [('now', now), ('dispatch', dispatch), ('session start', session_start),
                         ('stage start', stage_start), ('tool seconds', tool_seconds), ('sample time', sample_monotonic)]:
        number(value, label)
    require(stage in STAGES and dispatch <= session_start <= stage_start <= now, 'clock/stage order')
    require(type(global_limit) is int and 0 < global_limit <= 1200, 'global limit')
    deadline = min(dispatch + global_limit - 60, session_start + 360,
                   stage_start + STAGES[stage])
    def decision(kind, reason):
        return {'decision': kind, 'reason': reason, 'remaining_action_seconds': max(0, deadline - now),
                'session_end_deadline': session_start + 420, 'parent_wait_deadline': session_start + 400}
    if not (dispatch <= sample_monotonic <= now and now - sample_monotonic <= 2):
        return decision('stop', 'passive process sample stale or outside clock range')
    if contamination or closing or stage in ('shutdown', 'seal'):
        return decision('stop', 'contamination or closing; no UI binding refresh')
    if now >= session_start + 400 or now >= dispatch + global_limit:
        return decision('stop', 'parent wait/global hard deadline reached')
    if tool_seconds > 10 or now + tool_seconds >= deadline:
        return decision('quit_due', 'action/stage deadline or 10s tool bound')
    if stage != 'interaction':
        return decision('stop', 'no UI ready permit before verified interaction')
    validate_binding(ready_binding, expected_binding, ready=True)
    expected_keys = {process_key(row) for row in expected_processes}
    require({ready_binding['host_pid'], ready_binding['worker_pid']} <=
            {row['pid'] for row in expected_processes}, 'host/worker expected identity missing')
    live_keys = {process_key(row) for row in live_processes}
    if not expected_keys <= live_keys:
        return decision('stop', 'owned exact process identity no longer live')
    return decision('allow', 'fresh owner/readiness evidence and reserved exit time')


def _verify_wait(ref, identity, *, start, end):
    value = json_ref(ref)
    require(value['kind'] == 'actual-parent-wait' and value['observed'] is True,
            'actual parent wait receipt required')
    require(same_process(value['identity'], identity), 'wait identity differs')
    integer(value['parent_pid'], 'wait parent PID', 1)
    require(type(value['exit_code']) is int and value['exit_code'] == 0, 'normal exit0 missing')
    require(start <= number(value['monotonic'], 'wait time') <= end, 'wait outside charged interval')


def _verify_completion(ref, expected_binding):
    value = json_ref(ref)
    require(value['normal'] is True and not value['forced_cleanup'] and not value['remaining_owned'],
            'normal completion/clean residual required')
    for key, binding_key in [('accepted_source', 'source_sha'), ('run_id', 'run_id'),
                             ('world_id', 'world_id'), ('authority_root', 'authority_root'),
                             ('session', 'session'), ('ue_pid', 'host_pid')]:
        require(value[key] == expected_binding[binding_key], 'completion binding: ' + key)
    require(type(value['launcher_wait_exit']) is int and value['launcher_wait_exit'] == 0 and
            type(value['ue_exit_code']) is int and value['ue_exit_code'] == 0, 'completion wait exits')
    exits = value['worker_exits']
    require(len(exits) == 1 and exits[0]['worker_pid'] == expected_binding['worker_pid'] and
            exits[0]['generation'] == expected_binding['generation'] and
            type(exits[0]['exit_code']) is int and exits[0]['exit_code'] == 0 and
            exits[0]['reaped'] is True and exits[0]['return_code_available'] is True and
            exits[0]['trace_complete'] is True and exits[0]['stop_kind'] == 'normal' and
            exits[0]['hard_kill_sent'] is False and exits[0]['operational_failure'] is False,
            'worker completion requires normal EOF/reap exit0')
    require(type(value['card_sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['card_sha256']),
            'completion card SHA64')
    return value['card_sha256']


def validate_ledger(ledger, *, expected_run_binding, expected_clock_id,
                    expected_executable, expected_launchers, expected_session_bindings,
                    expected_storage_root, expected_public_paths):
    """Verify originals and frozen thresholds. Missing evidence is inconclusive.

    Returns checks_complete_requires_review only after all structural checks. Raw
    authenticity/authorization and actual parent wait origins require root review.
    No expected values are taken from ledger declarations themselves.
    """
    try:
        return _validate_ledger(ledger, expected_run_binding, expected_clock_id,
                                expected_executable, expected_launchers, expected_session_bindings,
                                expected_storage_root, expected_public_paths)
    except (KeyError, FileNotFoundError) as error:
        return {'status': 'inconclusive', 'reasons': ['missing evidence: ' + str(error)]}
    except (Invalid, ValueError, TypeError, OSError, OverflowError) as error:
        return {'status': 'fail', 'reasons': [str(error)]}


def _validate_ledger(ledger, expected_run, clock_id, executable, launchers, expected_sessions,
                     storage_root, public_paths):
    # Authoritative public allowlist is external, never inferred from evidence.
    storage_root = checked_path(storage_root)
    allowed = {str(checked_path(str(path))) for path in public_paths}
    require(bool(allowed), 'explicit public evidence allowlist required')
    def check_refs(value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256'}:
                path = checked_path(value['path'])
                require(str(path) in allowed and path.is_relative_to(storage_root),
                        'ref outside approved public evidence allowlist')
            for item in value.values():
                check_refs(item)
        elif isinstance(value, list):
            for item in value:
                check_refs(item)
    check_refs(ledger)
    require(ledger['format'] == FORMAT, 'ledger version')
    validate_binding(ledger['run_binding'], expected_run)
    clock = ledger['clock']
    require(type(clock_id) is str and bool(clock_id) and clock['id'] == clock_id, 'clock domain')
    anchor = number(clock['anchor_monotonic'], 'anchor')
    utc_anchor = utc_seconds(clock['anchor_utc'])
    start = number(ledger['dispatch_monotonic'], 'dispatch')
    end = number(ledger['end_monotonic'], 'end')
    limit = integer(ledger['limit_seconds'], 'limit', 1)
    require(anchor <= start <= end and limit <= 1200 and end - start <= limit, 'continuous global wall budget')
    gap_limit = number(ledger['max_observer_gap_seconds'], 'observer gap')
    require(0 < gap_limit <= 2, 'observer gap threshold relaxed')
    seal = ledger['seal']
    observer_end = number(seal['observer_ended_monotonic'], 'observer end')
    seal_start = number(seal['started_monotonic'], 'seal start')
    require(start <= seal_start <= end == number(seal['ended_monotonic'], 'seal end') and
            start <= observer_end <= end, 'final seal/observer clock order')
    missing, samples = [], ledger['samples']
    require(type(samples) is list, 'samples list')
    if not samples:
        missing.append('observer samples')
    previous, seen = start, {}
    owned = {process_key(row): row for row in launchers}
    last_relevant = []
    for sample in samples:
        timestamp = number(sample['monotonic'], 'sample time')
        require(previous <= timestamp <= observer_end, 'sample time order')
        if timestamp - previous > gap_limit:
            missing.append('observer gap exceeds %.1fs' % gap_limit)
        require(abs(utc_seconds(sample['utc']) - (utc_anchor + timestamp - anchor)) <= 2,
                'UTC/monotonic anchor mismatch')
        rows = parse_ps_snapshot(read_ref(sample['raw_ref']).decode('utf-8'))
        require(rows == sample['processes'], 'ps raw differs from sample metadata')
        last_relevant = classify_processes(rows, list(owned.values()), executable)
        for item in last_relevant:
            key = process_key(item['identity'])
            if item['ownership'] == 'owned':
                owned[key] = item['identity']
            require(item['ownership'] != 'contamination', 'unowned same-bundle process contamination')
            seen.setdefault(key, []).append(timestamp)
        previous = timestamp
    if observer_end - previous > gap_limit:
        missing.append('observer end gap')
    require(not last_relevant, 'related processes still live at observer close')
    declared, intervals = {}, []
    for process in ledger['processes']:
        identity = process['identity']
        key = process_key(identity)
        require(key not in declared and key in seen, 'duplicate/unobserved process interval')
        declared[key] = process
        require(process['ownership'] == 'owned', 'contamination/unresolved ownership')
        require(process['boundary_source'] in ('parent-wait', 'observer-bracket', 'conservative-upper-bound'),
                'interval boundary source')
        first, last = min(seen[key]), max(seen[key])
        require(process['first_seen_monotonic'] == first and process['last_seen_monotonic'] == last,
                'observed process extent mismatch')
        left = number(process['start_lower_bound'], 'interval start bound')
        right = number(process['end_upper_bound'], 'interval end bound')
        # No interpolation: the preceding and following samples bound unobserved life.
        prior_samples = [s['monotonic'] for s in samples if s['monotonic'] < first]
        next_samples = [s['monotonic'] for s in samples if s['monotonic'] > last]
        require(start <= left <= (max(prior_samples) if prior_samples else start) and
                (min(next_samples) if next_samples else observer_end) <= right <= observer_end,
                'interval not conservatively bracketed')
        intervals.append((left, right))
        if process['wait_ref'] is None:
            missing.append('actual parent wait for PID ' + str(identity['pid']))
        else:
            _verify_wait(process['wait_ref'], identity, start=last, end=right)
    require(set(declared) == set(seen), 'observer process omitted from ledger')
    session_names, host_pids, worker_pids, cards = [], set(), set(), set()
    previous_end = start
    for session in ledger['sessions']:
        name = session['session']
        require(name in ('initialize', 'existing') and name not in session_names, 'session identity/duplicate')
        session_names.append(name)
        binding = session['binding']
        validate_binding(binding, expected_sessions[name], ready=True)
        require({key: binding[key] for key in RUN_FIELDS} == expected_run, 'session run binding')
        host_pids.add(binding['host_pid'])
        worker_pids.add(binding['worker_pid'])
        left = number(session['start_monotonic'], 'session start')
        right = number(session['end_monotonic'], 'session end')
        require(previous_end <= left <= right <= end and right - left <= 420, 'serial session budget')
        previous_end = right
        require([s['stage'] for s in session['stages']] == list(STAGES), 'five ordered stages required')
        stage_end = left
        for stage in session['stages']:
            kind = stage['stage']
            a, b, deadline = (number(stage[k], k) for k in
                              ('start_monotonic', 'end_monotonic', 'deadline_monotonic'))
            require(a == stage_end and a <= b <= deadline <= min(a + STAGES[kind], left + 420),
                    'stage continuity/deadline')
            if kind == 'shutdown':
                require(a <= left + 360 and b <= left + 400, 'quit/wait reserve violated')
            if kind == 'seal':
                require(a <= left + 400, 'late sealing')
            stage_end = b
        require(stage_end == right, 'session stages do not cover full session')
        for pid in (binding['host_pid'], binding['worker_pid']):
            require(any(key[0] == pid for key in seen), 'bound PID not observed')
        cards.add(_verify_completion(session['completion_ref'], binding))
    if session_names != ['initialize', 'existing']:
        missing.append('two normal standard sessions')
    if len(session_names) == 2:
        require(len(host_pids) == len(worker_pids) == 2 and len(cards) == 1,
                'revisit must own distinct UE/worker PIDs and same card')
    require(storage_root.is_dir(), 'approved storage root missing')
    storage_limit = integer(seal['storage_limit_bytes'], 'storage limit', 1)
    storage_bytes = integer(seal['storage_bytes'], 'storage bytes')
    require(storage_bytes <= storage_limit <= MAX_BYTES, 'whole-storage budget')
    snapshot = json_ref(seal['storage_snapshot_ref'])
    require(snapshot['kind'] == 'whole-storage' and snapshot['includes_all_attempts'] is True,
            'whole storage snapshot required')
    require(number(snapshot['monotonic'], 'storage snapshot time') == end, 'storage final snapshot time')
    require(snapshot['storage_root'] == str(storage_root), 'storage root mismatch')
    total, paths, declared_sizes = 0, set(), {}
    for entry in snapshot['files']:
        require(entry['path'] not in paths, 'duplicate storage path')
        paths.add(entry['path'])
        path = checked_path(entry['path'])
        require(path.is_relative_to(storage_root), 'storage entry escapes approved root')
        size = integer(entry['bytes'], 'storage file bytes')
        declared_sizes[str(path)] = size
        total += size
    actual_sizes = {}
    for directory, dirs, files in os.walk(storage_root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            metadata = path.lstat()
            require(not stat.S_ISLNK(metadata.st_mode), 'storage symlink refused')
            if stat.S_ISREG(metadata.st_mode):
                actual_sizes[str(path)] = metadata.st_size
            else:
                require(stat.S_ISDIR(metadata.st_mode), 'storage nonregular entry')
    require(declared_sizes == actual_sizes and total == storage_bytes, 'whole storage snapshot/byte sum mismatch')
    if missing:
        return {'status': 'inconclusive', 'reasons': missing,
                'wall_seconds': end - start, 'process_union_seconds': interval_union_seconds(intervals)}
    return {'status': 'checks_complete_requires_review', 'reasons': [],
            'wall_seconds': end - start, 'process_union_seconds': interval_union_seconds(intervals),
            'note': 'Structure only; root must verify raw provenance, wait origins and authorization.'}


# I14 is a separate validator: no v1 thresholds, schema or code paths change.
FORMAT_V2 = 'universe-i14-lifecycle.v2'
POLICY_V2 = 'universe-i14-lifecycle-policy.v1'
SESSION_LIMITS_V2 = {
    'initialize': {'max_seconds': 540, 'quit_after': 480, 'wait_after': 520,
                   'stage_seconds': dict(build=60, startup=60, interaction=360, shutdown=40, seal=20)},
    'existing': {'max_seconds': 280, 'quit_after': 220, 'wait_after': 260,
                 'stage_seconds': dict(build=60, startup=60, interaction=100, shutdown=40, seal=20)}}
POLICY_FIELDS_V2 = {'format', 'run_binding', 'clock_id', 'accepted_executable', 'worker_executable',
                    'launcher_identities', 'launcher_source_ref', 'session_bindings', 'storage_root',
                    'public_paths', 'global_limit_seconds', 'storage_limit_bytes',
                    'observer_max_gap_seconds', 'sessions'}


def validate_policy_v2(policy):
    """Validate externally frozen policy, never derive it from a supplied ledger."""
    require(type(policy) is dict and set(policy) == POLICY_FIELDS_V2, 'v2 exact policy fields')
    require(policy['format'] == POLICY_V2, 'v2 policy version')
    validate_binding(policy['run_binding'], policy['run_binding'])
    require(type(policy['clock_id']) is str and policy['clock_id'], 'v2 clock domain')
    require(policy['sessions'] == SESSION_LIMITS_V2, 'v2 session allocation differs from freeze')
    require(type(policy['global_limit_seconds']) is int and policy['global_limit_seconds'] == 1200,
            'v2 global 1200s freeze')
    require(type(policy['storage_limit_bytes']) is int and policy['storage_limit_bytes'] == MAX_BYTES,
            'v2 storage 2GiB freeze')
    require(type(policy['observer_max_gap_seconds']) in (int, float) and
            policy['observer_max_gap_seconds'] == 2, 'v2 observer 2s freeze')
    for key in ('accepted_executable', 'storage_root'):
        checked_path(policy[key])
    worker = policy['worker_executable']
    require(type(worker) is str and Path(worker).is_absolute() and '..' not in Path(worker).parts,
            'v2 worker argv pin must be absolute; interpreter chain validated by legacy backend')
    require(set(policy['session_bindings']) == set(SESSION_LIMITS_V2), 'v2 session binding names')
    for name, binding in policy['session_bindings'].items():
        validate_binding(binding, binding, ready=True)
        require(binding['session'] == name and {k: binding[k] for k in RUN_FIELDS} == policy['run_binding'],
                'v2 run/session identity')
    require(len(policy['launcher_identities']) == 2, 'v2 exact two ordered launcher identities')
    for row in policy['launcher_identities']:
        validate_identity(row)
    require(len({process_key(r) for r in policy['launcher_identities']}) == 2, 'v2 distinct launchers')
    require(type(policy['public_paths']) is list and policy['public_paths'], 'v2 public allowlist')


def validate_ledger_v2(ledger, *, expected_policy, actual_finalized_monotonic=None):
    """Strict v2 structure and original-byte verification; root authenticates audit.

    Unknown build descendants retain null exits, not invented success. Runtime
    launcher/UE/worker still require actual normal parent wait receipts.
    """
    try:
        return _validate_ledger_v2(ledger, expected_policy, actual_finalized_monotonic)
    except (KeyError, FileNotFoundError) as error:
        return {'status': 'inconclusive', 'reasons': ['missing v2 evidence: ' + str(error)]}
    except (Invalid, ValueError, TypeError, OSError, OverflowError, IndexError) as error:
        return {'status': 'fail', 'reasons': [str(error)]}


def _validate_ledger_v2(ledger, policy, actual_finalized):
    validate_policy_v2(policy)
    root = checked_path(policy['storage_root'])
    allowed = {str(checked_path(p)) for p in policy['public_paths']}
    def public(ref):
        require(type(ref) is dict and set(ref) == {'path', 'sha256'} and ref['path'] in allowed,
                'v2 ref not independently public allowlisted')
        # Pinned launcher source may be outside storage; no other ref may escape.
        require(ref == policy['launcher_source_ref'] or checked_path(ref['path']).is_relative_to(root),
                'v2 ref escapes approved storage')
        return read_ref(ref)
    def document(ref):
        public(ref)
        return json_ref(ref)
    require(ledger['format'] == FORMAT_V2, 'v2 ledger version')
    validate_binding(ledger['run_binding'], policy['run_binding'])
    clock = ledger['clock']
    require(clock['id'] == policy['clock_id'], 'v2 independent clock domain')
    anchor = number(clock['anchor_monotonic'], 'v2 clock anchor')
    utc_anchor = utc_seconds(clock['anchor_utc'])
    start = number(ledger['dispatch_monotonic'], 'v2 dispatch')
    charged = number(ledger['charged_end_monotonic'], 'v2 charged end')
    observed = number(ledger['actual_observed_end_monotonic'], 'v2 actual observation end')
    require(anchor <= start <= observed <= charged == ledger['end_monotonic'] and
            ledger['limit_seconds'] == policy['global_limit_seconds'] and charged - start <= 1200,
            'v2 continuous charged wall budget')
    seal = ledger['seal']
    observer_end = number(seal['observer_ended_monotonic'], 'v2 observer end')
    require(start <= observer_end <= observed and observed - observer_end <= 2 and
            start <= number(seal['started_monotonic'], 'seal start') <=
            number(seal['ended_monotonic'], 'seal actual end') <= observed, 'v2 actual sealing boundaries')
    missing = []
    if actual_finalized is None:
        missing.append('independent actual finalized audit')
    else:
        require(observed <= number(actual_finalized, 'actual finalized audit') <= charged,
                'v2 actual finalization exceeded charged boundary')
    gap = policy['observer_max_gap_seconds']
    require(ledger['max_observer_gap_seconds'] == gap, 'v2 sample gap policy')
    samples = ledger['samples']
    require(type(samples) is list, 'v2 samples list')
    if not samples:
        missing.append('v2 observer samples')
    owned = {process_key(row): row for row in policy['launcher_identities']}
    seen, rows_by_time, previous = {}, [], start
    last_relevant = []
    for index, sample in enumerate(samples):
        t = number(sample['monotonic'], 'v2 sample time')
        require(previous <= t <= observer_end and (index == 0 or t > previous), 'v2 sample order')
        if t - previous > gap:
            missing.append('v2 observer gap')
        require(abs(utc_seconds(sample['utc']) - (utc_anchor + t - anchor)) <= 2, 'v2 UTC clock anchor')
        rows = parse_ps_snapshot(public(sample['raw_ref']).decode('utf-8'))
        require(rows == sample['processes'], 'v2 sample differs from raw ps')
        relevant = classify_processes(rows, list(owned.values()), policy['accepted_executable'])
        # Detached workers are also within runtime scope, not unobserved noise.
        known_keys = {process_key(x['identity']) for x in relevant}
        for row in rows:
            if _executable_matches(row['argv'], policy['worker_executable']) and process_key(row) not in known_keys:
                # Other users' Python is not automatically ours: mark unresolved only
                # when a frozen worker PID matches; generic Python is never killed.
                if row['pid'] in {b['worker_pid'] for b in policy['session_bindings'].values()}:
                    relevant.append({'identity': row, 'ownership': 'contamination'})
        for item in relevant:
            key = process_key(item['identity'])
            require(item['ownership'] == 'owned', 'v2 detached/extra runtime contamination')
            owned[key] = item['identity']
            seen.setdefault(key, []).append(t)
        rows_by_time.append((t, rows))
        last_relevant, previous = relevant, t
    if observer_end - previous > gap:
        missing.append('v2 observer closing gap')
    require(not last_relevant, 'v2 runtime/build processes remain after observer')
    session_names, session_ranges, cards = [], {}, set()
    for session in ledger['sessions']:
        name = session['session']
        require(name in SESSION_LIMITS_V2 and name not in session_names, 'v2 session identity/order')
        limits = policy['sessions'][name]
        binding = policy['session_bindings'][name]
        validate_binding(session['binding'], binding, ready=True)
        left = number(session['start_monotonic'], 'v2 session start')
        right = number(session['end_monotonic'], 'v2 session end')
        require(start <= left <= right <= observed and right - left <= limits['max_seconds'], 'v2 session wall')
        if session_ranges:
            require(left >= max(r[1] for r in session_ranges.values()), 'v2 overlapping sessions')
        require([s['stage'] for s in session['stages']] == ['build', 'startup', 'interaction', 'shutdown', 'seal'], 'v2 all five phases')
        cursor, ranges = left, {}
        for stage in session['stages']:
            kind = stage['stage']
            a, b, deadline = (number(stage[k], 'v2 stage ' + k) for k in
                              ('start_monotonic', 'end_monotonic', 'deadline_monotonic'))
            require(a == cursor and a <= b <= deadline <=
                    min(a + limits['stage_seconds'][kind], left + limits['max_seconds']), 'v2 stage budget')
            if kind == 'shutdown':
                require(a <= left + limits['quit_after'] and b <= left + limits['wait_after'], 'v2 quit/wait deadlines')
            ranges[kind] = (a, b)
            cursor = b
        require(cursor == right, 'v2 unaccounted session time')
        # Check allowlist before invoking shared completion field checks.
        public(session['completion_ref'])
        cards.add(_verify_completion(session['completion_ref'], binding))
        session_names.append(name)
        session_ranges[name] = (left, right, ranges)
    if session_names != ['initialize', 'existing']:
        missing.append('v2 two normal standard sessions')
    else:
        require(len(cards) == 1 and len({b['host_pid'] for b in policy['session_bindings'].values()}) == 2 and
                len({b['worker_pid'] for b in policy['session_bindings'].values()}) == 2,
                'v2 same-card/distinct runtime sessions')
    core_expected = {}
    for index, name in enumerate(('initialize', 'existing')):
        binding = policy['session_bindings'][name]
        launcher = policy['launcher_identities'][index]
        for kind, pid in [('launcher', launcher['pid']), ('ue', binding['host_pid']), ('worker', binding['worker_pid'])]:
            require(pid not in core_expected, 'v2 runtime core PID reuse')
            core_expected[pid] = (name, kind, launcher)
    declared, core_seen, intervals = set(), set(), []
    for process in ledger['processes']:
        identity = process['identity']
        key = process_key(identity)
        require(key in seen and key not in declared, 'v2 unknown/duplicate process')
        declared.add(key)
        first, last = min(seen[key]), max(seen[key])
        number(process['first_seen_monotonic'], 'process first seen')
        number(process['last_seen_monotonic'], 'process last seen')
        require(process['first_seen_monotonic'] == first and process['last_seen_monotonic'] == last and
                process['ownership'] == 'owned', 'v2 process extent/ownership')
        left = number(process['start_lower_bound'], 'v2 process lower')
        right = number(process['end_upper_bound'], 'v2 process upper')
        preceding = [t for t, _ in rows_by_time if t < first]
        following = [t for t, _ in rows_by_time if t > last]
        require(start <= left <= (max(preceding) if preceding else start) and
                (min(following) if following else observer_end) <= right <= observer_end,
                'v2 conservative process brackets')
        require(process['boundary_source'] in ('parent-wait', 'observer-bracket', 'conservative-upper-bound'),
                'v2 process boundary source')
        intervals.append((left, right))
        expected_core = core_expected.get(identity['pid'])
        if expected_core is not None:
            require(identity['pid'] not in core_seen, 'v2 runtime core PID has multiple startup identities')
            name, kind, launcher = expected_core
            require(process['role'] == 'runtime_core' and process['core_kind'] == kind and
                    process['session'] == name and process['build_parent_ref'] is None, 'v2 core relabelled as build')
            if kind == 'launcher':
                require(same_process(identity, launcher), 'v2 exact launcher core identity')
            else:
                executable = policy['accepted_executable'] if kind == 'ue' else policy['worker_executable']
                require(_executable_matches(identity['argv'], executable), 'v2 core executable pin')
            require(type(process['exit_status']) is int and process['exit_status'] == 0, 'v2 runtime core actual exit0')
            if process['wait_ref'] is None:
                missing.append('v2 core actual wait')
            else:
                public(process['wait_ref'])
                _verify_wait(process['wait_ref'], identity, start=last, end=right)
                wait = document(process['wait_ref'])
                expected_parent = launcher['ppid'] if kind == 'launcher' else (launcher['pid'] if kind == 'ue' else policy['session_bindings'][name]['host_pid'])
                require(wait['parent_pid'] == expected_parent, 'v2 actual parent wait relation')
            core_seen.add(identity['pid'])
        else:
            require(process['role'] == 'build_descendant' and not
                    _executable_matches(identity['argv'], policy['accepted_executable']) and not
                    _executable_matches(identity['argv'], policy['worker_executable']), 'v2 noncore runtime cannot become build')
            _verify_build_parent_v2(process, policy, document, public, rows_by_time, session_ranges)
            if process['wait_ref'] is None:
                require(process['exit_status'] is None, 'v2 unknown build exit must remain null')
            else:
                public(process['wait_ref'])
                _verify_wait(process['wait_ref'], identity, start=last, end=right)
                require(type(process['exit_status']) is int and process['exit_status'] == 0, 'v2 build wait status')
    require(declared == set(seen), 'v2 observer process omitted')
    if core_seen != set(core_expected):
        missing.append('v2 runtime core process coverage')
    snapshot = document(seal['storage_snapshot_ref'])
    require(snapshot['kind'] == 'whole-storage' and snapshot['includes_all_attempts'] is True and
            snapshot['storage_root'] == str(root), 'v2 complete storage identity')
    require(start <= number(snapshot['monotonic'], 'v2 storage sample') <= observed,
            'v2 storage snapshot chronology')
    require(seal['storage_limit_bytes'] == policy['storage_limit_bytes'], 'v2 storage bound')
    sizes = {}
    for entry in snapshot['files']:
        path = checked_path(entry['path'])
        require(path.is_relative_to(root) and str(path) not in sizes, 'v2 storage duplicate/escape')
        sizes[str(path)] = integer(entry['bytes'], 'v2 storage file bytes')
    actual = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            metadata = path.lstat()
            require(stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode), 'v2 storage symlink/special')
            if stat.S_ISREG(metadata.st_mode):
                actual[str(path)] = metadata.st_size
    require(sizes == actual and sum(sizes.values()) == seal['storage_bytes'] <= policy['storage_limit_bytes'],
            'v2 final whole-storage byte accounting')
    return {'status': 'inconclusive' if missing else 'checks_complete_requires_review',
            'reasons': missing, 'wall_seconds': charged - start,
            'actual_observed_seconds': observed - start,
            'process_union_seconds': interval_union_seconds(intervals),
            'note': 'Root authenticates actual wait/audit/source/card; no runtime gate granted.'}


def _executable_matches(argv, executable):
    return argv == executable or argv.startswith(executable + ' ')


def _verify_build_parent_v2(process, policy, document, public, rows_by_time, sessions):
    wrapper = document(process['build_parent_ref'])
    require(wrapper['format'] == 'universe-i14-build-parent.v1', 'v2 build-parent version')
    name = wrapper['session']
    require(name in sessions, 'v2 build session')
    launcher = policy['launcher_identities'][('initialize', 'existing').index(name)]
    require(same_process(wrapper['launcher_identity'], launcher), 'v2 build launcher identity')
    require(wrapper['launcher_source_ref'] == policy['launcher_source_ref'], 'v2 independent launcher source pin')
    source = public(policy['launcher_source_ref'])
    require(b'build_rc=${PIPESTATUS[0]}' in source, 'v2 official build PIPESTATUS origin')
    raw = public(wrapper['stdout_ref'])
    a, b = wrapper['line_start'], wrapper['line_end']
    integer(a, 'v2 build line start'); integer(b, 'v2 build line end')
    require(0 <= a < b <= len(raw) and (a == 0 or raw[a - 1:a] == b'\n') and
            raw[a:b].rstrip(b'\r\n') == b'[launcher] build_exit_code=0' and raw[b - 1:b] == b'\n',
            'v2 actual build exit0 stdout line')
    left, right = sessions[name][2]['build']
    require(wrapper['build_start_monotonic'] == left and wrapper['build_end_monotonic'] == right,
            'v2 build phase association')
    identity = process['identity']
    first = process['first_seen_monotonic']
    require(left <= first <= right, 'v2 build descendant first seen outside build phase')
    rows = next(rows for t, rows in rows_by_time if t == first)
    by_pid = {r['pid']: r for r in rows}
    require(identity['pid'] in by_pid and same_process(by_pid[identity['pid']], identity), 'v2 actual build first sample identity')
    row, visited = by_pid[identity['pid']], set()
    while row['pid'] != launcher['pid']:
        require(row['pid'] not in visited and row['ppid'] in by_pid, 'v2 build same-sample ancestry missing')
        visited.add(row['pid'])
        row = by_pid[row['ppid']]
    require(same_process(row, launcher), 'v2 build ancestry is not approved launcher')
