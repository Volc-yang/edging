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
