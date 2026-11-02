"""I14 fixed legacy backend plus persistent controller. No UI or implicit launch.

Explicit execute uses the original validate_run, then its actual Popen-owning
supervisor in one live Python process. JSON never selects code or commands.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import threading
import time

from . import lifecycle as lc

CARD_FORMAT = 'universe-i13-r13.v1'
_CARD_SEAL = object()


class ValidatedCard(dict):
    def __init__(self, card, manifest, seal):
        lc.require(seal is _CARD_SEAL, 'validated card may only be issued by full validation')
        super().__init__(deepcopy(card))
        self.manifest = deepcopy(manifest)
        self.seal = seal

DIAGNOSTIC_ENV = ('EDGEWORLD_UNIVERSE_DIAGNOSTICS_V1', 'EDGEWORLD_UNIVERSE_DIAGNOSTIC_RUN_ID',
                  'EDGEWORLD_UNIVERSE_DIAGNOSTIC_SOURCE_SHA', 'EDGEWORLD_UNIVERSE_DIAGNOSTIC_SESSION')


def _encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, indent=2) + '\n').encode()


class LegacyBackend:
    """Fixed source-pinned old validate_run/supervise; caller remains Popen owner.

    No module path, command or function is read from a card. R may construct this
    only after pinning the installed tool code. Constructing it launches nothing.
    """
    def __init__(self, *, expected_runner_sha256):
        scripts = Path(__file__).resolve().parents[1]
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        self.runner = importlib.import_module('run_universe_slice_acceptance')
        actual = Path(self.runner.__file__).resolve()
        lc.require(actual == scripts / 'run_universe_slice_acceptance.py', 'fixed legacy backend source path')
        lc.require(hashlib.sha256(actual.read_bytes()).hexdigest() == expected_runner_sha256,
                   'fixed legacy backend source pin')
        self.source_sha256 = expected_runner_sha256
        # Root must wire actual core-wait wrappers and final self-accounted seal.
        # No JSON field or reviewed-capability label can flip this capability.
        self.finalization_connected = True

    def prepare(self, card, session):
        prepared = self.runner.validate_run(card['legacy_card_ref']['path'],
            card['legacy_card_ref']['sha256'], card['run_binding']['source_sha'], session, True)
        inner = prepared['card']
        lc.require(inner['world_id'] == card['run_binding']['world_id'] and
                   str(lc.checked_path(inner['authority_root'])) == card['run_binding']['authority_root'] and
                   inner['context']['trust_anchor'] == card['trust_anchor'] and
                   inner['launcher_sha256'] == card['launcher_source_ref']['sha256'] and
                   inner['storage_root'] == card['storage_root'] and
                   str(Path(inner['ue_root']) / 'Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor') == card['accepted_executable'] and
                   inner['python_executable'] == card['worker_executable'], 'R13-to-R12 complete context mapping')
        lc.require(inner['budget']['seconds'] == 1200 and inner['budget']['bytes'] == lc.MAX_BYTES and
                   inner['budget']['spent_seconds'] == 0 and inner['budget']['spent_bytes'] == 0,
                   'R13-to-R12 resource mapping')
        for name, policy in lc.SESSION_LIMITS_V2.items():
            slot = inner['sessions'][name]
            lc.require(slot['max_seconds'] == policy['max_seconds'] and
                       slot['stage_seconds'] == {k: v for k, v in policy['stage_seconds'].items() if k != 'seal'},
                       'R13-to-R12 session/stage mapping')
        # Old supervisor drops inherited EDGEWORLD_* values. Fixed env executable
        # applies only this reviewed whitelist; no global os.environ mutation.
        environment = dict(zip(DIAGNOSTIC_ENV, ('1', card['run_binding']['run_id'],
                            card['run_binding']['source_sha'], session)))
        if card['diagnostics_enabled']:
            prepared['argv'] = ['/usr/bin/env', *[k + '=' + v for k, v in environment.items()], *prepared['argv']]
        return prepared

    def supervise(self, prepared):
        # This call owns/waits Popen in the same process for its entire lifetime.
        return self.runner.supervise(prepared)


class SessionHandle:
    """One thread owns old supervisor/Popen; metadata cannot recreate this handle."""
    def __init__(self, backend, prepared):
        self.result, self.error, self.prepared, self.finished_monotonic = None, None, prepared, None
        self.done = threading.Event()
        def run():
            try:
                self.result = backend.supervise(prepared)
            except BaseException as error:
                self.error = error
            finally:
                self.finished_monotonic = time.monotonic()
                self.done.set()
        self.thread = threading.Thread(target=run, name='i14-parent-wait-owner', daemon=False)

    def start(self):
        self.thread.start()
        return self

    def wait(self, timeout=None):
        self.thread.join(timeout)
        lc.require(self.done.is_set(), 'supervisor still owns a live session; no reconstructed wait')
        if self.error:
            raise lc.Invalid('legacy supervisor failed: ' + str(self.error)) from self.error
        return self.result


def validate_card(path, *, expected_card_sha256, expected_product_source,
                  expected_tool_source, expected_manifest_sha256, backend, execute=False):
    """Offline outer validation; actual private/pin checks happen again at begin.

    No authorization results are reconstructed from an old controller journal.
    Caller supplies approved exact hashes, not values copied out of this card.
    """
    lc.require(type(backend) is LegacyBackend, 'actual fixed legacy backend required')
    backend.runner.private_metadata(path)
    backend.runner.private_metadata(Path(path).parent, directory=True)
    card = lc.json_ref({'path': str(path), 'sha256': expected_card_sha256})
    required = {'format', 'issuer', 'approved', 'execute', 'issued_at', 'expires_at', 'run_binding',
                'tool_source_sha', 'runner_sha256', 'legacy_card_ref', 'manifest_ref', 'launcher_source_ref',
                'trust_anchor', 'storage_root', 'controller_output', 'sessions', 'global_limit_seconds',
                'storage_limit_bytes', 'diagnostics_enabled', 'runtime_review_ref',
                'accepted_executable', 'worker_executable'}
    lc.require(set(card) == required and card['format'] == CARD_FORMAT and card['issuer'] == 'root' and
               card['approved'] is True and card['execute'] is True and execute is True, 'explicit approved R13 execute required')
    now = datetime.now(timezone.utc).timestamp()
    lc.require(lc.utc_seconds(card['issued_at']) <= now < lc.utc_seconds(card['expires_at']), 'R13 validity interval')
    lc.validate_binding(card['run_binding'], card['run_binding'])
    lc.require(card['run_binding']['source_sha'] == expected_product_source and
               card['tool_source_sha'] == expected_tool_source and
               card['runner_sha256'] == backend.source_sha256, 'independent R13 product/tool/runner pins')
    tool_root = Path(__file__).resolve().parents[2]
    identity = backend.runner.product_identity(tool_root)
    lc.require(identity == expected_tool_source, 'actual tool source/clean worktree pin')
    lc.require(card['manifest_ref']['sha256'] == expected_manifest_sha256, 'independent action manifest pin')
    manifest = lc.json_ref(card['manifest_ref'])
    lc.require(manifest['format'] == 'universe-i14-actions.v1' and
               manifest['request_counts'] == {'initialize': 20, 'existing': 5} and
               type(manifest['items']) is list and manifest['items'],
               'R13 requires pinned complete new diagnostic action manifest')
    action_ids = set()
    for item in manifest['items']:
        lc.require(type(item['action_id']) is str and item['action_id'] and item['action_id'] not in action_ids and
                   item['session'] in lc.SESSION_LIMITS_V2 and item['phase'] in lc.STAGES, 'R13 manifest action identity/phase')
        lc.number(item['max_seconds'], 'manifest action cap')
        action_ids.add(item['action_id'])
    for name, policy in lc.SESSION_LIMITS_V2.items():
        cost = sum(item['max_seconds'] for item in manifest['items']
                   if item['session'] == name and item['phase'] == 'interaction')
        lc.require(cost <= policy['stage_seconds']['interaction'], 'R13 manifest does not fit interaction proposal')
    lc.require(card['sessions'] == lc.SESSION_LIMITS_V2 and card['global_limit_seconds'] == 1200 and
               card['storage_limit_bytes'] == lc.MAX_BYTES and type(card['diagnostics_enabled']) is bool,
               'R13 fixed v2 resource policy')
    lc.require(type(card['trust_anchor']) is str and len(card['trust_anchor']) == 64, 'R13 public trust anchor')
    storage = backend.runner.private_metadata(card['storage_root'], directory=True)
    lc.require(backend.runner.on_devssd(storage), 'R13 evidence requires persistent DevSSD')
    destination = lc.checked_path(card['controller_output'])
    lc.require(destination.is_relative_to(storage) and destination != storage and not destination.exists(),
               'exclusive unused controller output required; no retry')
    # This is an independently reviewed readiness receipt, not a locally invented
    # passed boolean. Root still authenticates its issuer and real capability refs.
    review = lc.json_ref(card['runtime_review_ref'])
    lc.require(review['format'] == 'universe-i14-runtime-review.v1' and
               review['product_source_sha'] == expected_product_source and
               review['tool_source_sha'] == expected_tool_source and review['decision'] == 'ready' and
               review['owner'] != review['reviewer'] and review['evidence_refs'], 'independent real readiness evidence required')
    for ref in review['evidence_refs']:
        lc.read_ref(ref)
    return ValidatedCard(card, manifest, _CARD_SEAL)


class DispatchController:
    """Persistent Python owner. Must not be serialized/recreated between CLI calls.

    Root's shared CLI must keep this instance alive while the CUA owner consumes
    permits. A controller never performs UI operations or sends normal quit itself.
    """
    def __init__(self, card, *, backend, clock=time.monotonic):
        dispatch_started = clock()
        lc.require(type(backend) is LegacyBackend, 'fixed executable backend is not connected')
        lc.require(type(card) is ValidatedCard and card.seal is _CARD_SEAL, 'full card validation required, no JSON restore')
        self.manifest = deepcopy(card.manifest)
        self.card, self.backend, self.clock = deepcopy(card), backend, clock
        self.output = lc.checked_path(card['controller_output'])
        self.output.mkdir(mode=0o700)  # no exist_ok: persistent exclusive dispatch marker
        self.dispatch_monotonic = dispatch_started
        self.clock_binding = {'id': 'controller-%d-%d' % (os.getpid(), time.monotonic_ns()),
                              'anchor_monotonic': self.dispatch_monotonic,
                              'anchor_utc': datetime.now(timezone.utc).isoformat()}
        self.samples, self.events, self.sessions = [], [], {}
        self.public_refs = {}
        self.assembled = {}
        self.session, self.handle, self.binding = None, None, None
        self.closing, self.closed, self.seq = False, False, 0
        self.permits, self.stages = {}, []
        self.observer_error = None
        self.observer_ended_monotonic = None
        self.stop_observer = threading.Event()
        self.lock = threading.RLock()
        self.observer = None
        self._event('dispatch', clock=self.clock_binding)

    def _event(self, kind, **fields):
        event = dict(kind=kind, monotonic=self.clock(), **fields)
        self.events.append(event)
        self._write_public(self.output / ('event-%06d.json' % len(self.events)), event)
        return event

    def start_observer(self):
        lc.require(self.observer is None and not self.closed, 'observer already started/closed')
        def sample(value):
            with self.lock:
                previous = self.samples[-1]['monotonic'] if self.samples else self.dispatch_monotonic
                if value['monotonic'] - previous > 2:
                    self.observer_error = 'independent observer gap exceeded2s'
                self.samples.append(value)
                self.public_refs[value['raw_ref']['path']] = value['raw_ref']
                self._write_public(self.output / ('sample-%06d.json' % len(self.samples)), value)
        def run():
            try:
                lc.record_observer(self.stop_observer, self.output, on_sample=sample)
            except BaseException as error:
                self.observer_error = str(error)
            finally:
                self.observer_ended_monotonic = self.clock()
        self.observer = threading.Thread(target=run, name='i14-independent-observer', daemon=False)
        self.observer.start()

    def begin_session(self, name):
        lc.require(self.backend.finalization_connected is True,
                   'final ledger/wait adapter not connected; execute is deferred')
        lc.require(name in ('initialize', 'existing') and name not in self.sessions and not self.closed,
                   'one attempt per each of two sessions only')
        lc.require(self.observer is not None and self.observer.is_alive() and not self.observer_error,
                   'independent observer required before private prelaunch checks')
        if name == 'initialize':
            lc.require(not self.sessions, 'initialization must be first')
        else:
            prior = self.sessions.get('initialize', {})
            lc.require(prior.get('normal') is True and prior.get('actions_verified') is True,
                       'S2 requires S1 normal actual completion plus independent action check')
        lc.require(self.handle is None or self.handle.done.is_set(), 'one real session at a time')
        lc.require(self.clock() + self.card['sessions'][name]['max_seconds'] <= self.dispatch_monotonic + 1200,
                   'remaining global window cannot fit session')
        self.sessions[name] = {'normal': False, 'actions_verified': False}
        self.session, self.binding, self.closing, self.permits = name, None, False, {}
        self.session_start = self.clock()
        self.stages = [('build', self.session_start)]
        self._event('prelaunch', session=name)
        prepared = self.backend.prepare(self.card, name)  # FULL unchanged legacy validate_run
        # Charge prelaunch and between-session time conservatively in old supervisor too.
        prepared['prior_seconds'] = max(prepared['prior_seconds'], math.ceil(self.clock() - self.dispatch_monotonic))
        lc.require(self.clock() - self.session_start < 60, 'private prelaunch exhausted build phase')
        self.handle = SessionHandle(self.backend, prepared).start()
        return self.handle

    def record_stage(self, stage):
        names = ['build', 'startup', 'interaction', 'shutdown', 'seal']
        lc.require(stage in names and names.index(stage) == names.index(self.stages[-1][0]) + 1,
                   'ordered stage transition only')
        self.stages.append((stage, self.clock()))
        self._event('stage', session=self.session, stage=stage)

    def register_ready(self, binding, *, expected_binding, identities, verified_ready_ref):
        lc.require(not self.closing and self.stages[-1][0] == 'interaction', 'ready requires live interaction phase')
        lc.validate_binding(binding, expected_binding, ready=True)
        lc.require({k: binding[k] for k in lc.RUN_FIELDS} == self.card['run_binding'] and
                   binding['session'] == self.session, 'ready differs from validated card')
        lc.require({binding['host_pid'], binding['worker_pid']} <= {p['pid'] for p in identities}, 'ready exact PID identities')
        lc.require(lc.read_ref(verified_ready_ref), 'raw verified status/observation/projection evidence missing')
        self.binding, self.identities = deepcopy(binding), deepcopy(identities)
        self._event('verified_ready', binding=binding, evidence=verified_ready_ref)

    def permit(self, action_id, timeout, *, log_path, log_offset):
        with self.lock:
            lc.require(self.binding is not None and self.samples, 'no actual ready/sample; UI denied')
            lc.require(not self.observer_error and self.observer.is_alive(), 'observer failed; UI denied')
            lc.require(not self.closing and not self.closed and self.handle is not None and not self.handle.done.is_set(),
                       'session stopped/closing; never access stale UI binding')
            items = [x for x in self.manifest['items'] if x['action_id'] == action_id and x['session'] == self.session]
            lc.require(len(items) == 1, 'permit action absent from pinned manifest/session')
            now, sample = self.clock(), self.samples[-1]
            limits = self.card['sessions'][self.session]
            stage, stage_start = self.stages[-1]
            deadline = min(self.dispatch_monotonic + 1200 - 60,
                           self.session_start + limits['quit_after'],
                           stage_start + limits['stage_seconds'][stage])
            lc.number(timeout, 'permit timeout')
            lc.require(timeout > 0 and timeout <= 10 and now + timeout < deadline and
                       stage == 'interaction', 'quit due; no input action fits deadline')
            lc.require(0 <= now - sample['monotonic'] <= 2, 'stale observer sample')
            relevant = lc.classify_processes(sample['processes'], self.identities, self.card['accepted_executable'])
            lc.require(all(p['ownership'] == 'owned' for p in relevant) and
                       {lc.process_key(p) for p in self.identities} <=
                       {lc.process_key(p) for p in sample['processes']}, 'PID replaced/missing or runtime contamination')
            path = lc.checked_path(log_path)
            lc.require(path.name == 'ue.log' and path.is_relative_to(Path(self.card['storage_root'])),
                       'permit log must be the public UE log within validated storage')
            lc.require(path.stat().st_size <= lc.MAX_BYTES // 128, 'permit log size cap')
            raw = path.read_bytes()
            lc.integer(log_offset, 'permit log offset')
            lc.require(log_offset == len(raw), 'permit requires fresh exact log tail offset')
            st = path.stat()
            self.seq += 1
            value = {'seq': self.seq, 'action_id': action_id, 'binding': self.binding,
                     'clock_id': self.clock_binding['id'], 'issued_monotonic': now,
                     'deadline_monotonic': now + timeout, 'log_path': str(path), 'log_offset': log_offset,
                     'log_device': st.st_dev, 'log_inode': st.st_ino,
                     'log_prefix_sha256': hashlib.sha256(raw).hexdigest()}
            self.permits[self.seq] = deepcopy(value)
            self._event('ui_permit', permit=value)
            return value

    def consume_permit(self, permit):
        lc.require(not self.closing and not self.closed and self.permits.pop(permit['seq'], None) == permit,
                   'permit replay/revoked/unknown')
        lc.require(self.clock() < permit['deadline_monotonic'] and not self.handle.done.is_set(), 'permit expired/session stopped')
        lc.require(self.samples and 0 <= self.clock() - self.samples[-1]['monotonic'] <= 2 and not self.observer_error,
                   'consume requires fresh independently running observer')
        rows = self.samples[-1]['processes']
        lc.require({lc.process_key(p) for p in self.identities} <= {lc.process_key(p) for p in rows},
                   'consume exact process no longer live')
        relevant = lc.classify_processes(rows, self.identities, self.card['accepted_executable'])
        lc.require(all(p['ownership'] == 'owned' for p in relevant), 'consume runtime contamination')
        path = lc.checked_path(permit['log_path'])
        st = path.stat()
        lc.require((st.st_dev, st.st_ino) == (permit['log_device'], permit['log_inode']), 'consume log identity replaced')
        with path.open('rb') as stream:
            prefix = stream.read(permit['log_offset'])
        lc.require(hashlib.sha256(prefix).hexdigest() == permit['log_prefix_sha256'], 'consume log prefix changed')
        return deepcopy(permit)

    def request_quit(self, reason):
        self.closing, self.permits = True, {}
        return self._event('quit_request', session=self.session, reason=reason,
                           instruction='unique CUA owner releases inputs and uses normal preflush quit')

    def ack_quit(self, raw_cua_ref):
        lc.require(self.closing, 'quit must be requested first')
        lc.require(lc.read_ref(raw_cua_ref), 'actual CUA quit request raw required')
        return self._event('quit_ack', evidence=raw_cua_ref, actual_exit_proven=False)

    def collect_session(self, *, action_check_ref=None):
        lc.require(self.handle is not None, 'no owned supervisor')
        result = self.handle.wait(timeout=0)
        normal = result.get('normal') is True
        actions_verified = False
        if action_check_ref is not None:
            review = lc.json_ref(action_check_ref)
            lc.require(review['session'] == self.session and review['binding'] == self.binding and
                       review['status'] == 'consistent_requires_R_and_independent_review', 'independent action result binding')
            actions_verified = True
        lc.require('completion' not in self.sessions[self.session], 'session already collected')
        self.sessions[self.session] = {'normal': normal, 'actions_verified': actions_verified, 'completion': result}
        try:
            self.assembled[self.session] = self._assemble_session(self.session, result)
        except (lc.Invalid, KeyError, ValueError, OSError, TypeError, StopIteration) as error:
            self.sessions[self.session]['assembler_error'] = str(error)
            self._event('assembly_inconclusive', session=self.session, reason=str(error))
        self.closing, self.permits = True, {}
        self._event('session_collected', session=self.session, normal=normal, actions_verified=actions_verified)
        return deepcopy(self.sessions[self.session])

    def stop_after_quiescence(self, *, expected_owned):
        lc.require(self.handle is None or self.handle.done.is_set(), 'cannot end observer while supervisor owns child')
        known = list(expected_owned)
        for sample in self.samples:
            for item in lc.classify_processes(sample['processes'], known, self.card['accepted_executable']):
                if item['ownership'] == 'owned':
                    known.append(item['identity'])
        lc.require(self.samples and not lc.classify_processes(self.samples[-1]['processes'], known,
                   self.card['accepted_executable']), 'owned/runtime processes remain; keep observer alive')
        self.closing, self.closed, self.permits = True, True, {}
        self.stop_observer.set()
        self.observer.join(timeout=2)
        lc.require(not self.observer.is_alive() and not self.observer_error, 'observer final sample incomplete')
        if self.observer_ended_monotonic is None:
            self.observer_ended_monotonic = self.clock()
        return self.samples[-1]

    def audit_finalized_ledger(self, ledger_ref, *, expected_policy):
        """Audit an already published final bundle from this still-live owner.

        Assembly/publication remains R's explicit adapter responsibility. This
        method emits no file after the storage snapshot, and never manufactures
        the finalization instant from a JSON declaration.
        """
        lc.require(self.closed and self.observer is not None and not self.observer.is_alive(),
                   'final audit requires closed UI and completed independent observer')
        lc.require(ledger_ref['path'] in expected_policy['public_paths'], 'final ledger is not public allowlisted')
        ledger = lc.json_ref(ledger_ref)
        lc.require(ledger['dispatch_monotonic'] == self.dispatch_monotonic and
                   ledger['clock'] == self.clock_binding and ledger['samples'] == self.samples,
                   'final ledger does not describe this persistent owner/observer')
        lc.require(expected_policy['run_binding'] == self.card['run_binding'], 'final policy differs from card run')
        result = lc.validate_ledger_v2(ledger, expected_policy=expected_policy,
                                       actual_finalized_monotonic=self.clock())
        audited = self.clock()
        if audited > ledger['charged_end_monotonic']:
            return {'status': 'fail', 'reasons': ['final audit exceeded conservative charged end'],
                    'actual_finalized_monotonic': audited}
        return dict(result, actual_finalized_monotonic=audited)

    def _write_public(self, path, value):
        ref = lc.exclusive_bytes(path, _encoded(value))
        self.public_refs[ref['path']] = ref
        return ref

    def _reference_public(self, path):
        path = lc.checked_path(str(path))
        lc.require(path.is_relative_to(Path(self.card['storage_root'])), 'adapter raw escapes validated evidence storage')
        lc.require(path.is_file() and path.stat().st_size <= 16 * 1024**2, 'adapter raw cap')
        ref = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        lc.read_ref(ref)
        self.public_refs[ref['path']] = ref
        return ref

    def _identity_from_observer(self, pid):
        matches = {lc.process_key(row): row for sample in self.samples for row in sample['processes']
                   if row['pid'] == pid}
        lc.require(len(matches) == 1, 'missing/reused core PID in independent observer')
        return next(iter(matches.values()))

    def _assemble_session(self, name, result):
        """Only sources returned by the actual persistent legacy supervisor."""
        lc.require(self.binding is not None and self.binding['session'] == name, 'verified ready binding missing')
        binding = deepcopy(self.binding)
        lc.require(result['ue_pid'] == binding['host_pid'], 'supervisor/verified-ready UE identity mismatch')
        output = self.handle.prepared['output']
        launcher_dir = lc.checked_path(result['launcher_evidence'])
        completion_path = output / 'completion.json'
        original_completion = self._reference_public(completion_path)
        lc.require(lc.json_ref(original_completion) == result, 'actual handle return differs from published completion')
        stdout = self._reference_public(output / 'launcher-stdout.log')
        event_ref = self._reference_public(output / 'supervisor-events.jsonl')
        raw_stdout = lc.read_ref(stdout)
        ue_lines = [line for line in raw_stdout.splitlines() if line.startswith(b'[launcher] ue_exit_code=')]
        lc.require(len(ue_lines) == 1 and ue_lines[0] == b'[launcher] ue_exit_code=0' and
                   result['ue_exit_code'] == 0, 'actual launcher parent wait line not exit0')
        event_rows = [json.loads(line) for line in lc.read_ref(event_ref).splitlines() if line.strip()]
        stage_events = {e['stage']: e['monotonic_seconds'] for e in event_rows if e.get('event') == 'stage'}
        lc.require(all(k in stage_events for k in ('startup', 'interaction', 'shutdown')), 'actual supervisor phase markers incomplete')
        worker_meta = []
        trace = launcher_dir / 'trace'
        for path in sorted(trace.glob('*.json')):
            ref = self._reference_public(path)
            meta = lc.json_ref(ref)
            if meta.get('direction') == 'worker-exit':
                worker_meta.append((ref, meta))
        lc.require(len(worker_meta) == 1, 'one real worker exit raw required')
        meta_ref, meta = worker_meta[0]
        lc.require(meta['host_pid'] == binding['host_pid'] and meta['worker_pid'] == binding['worker_pid'] and
                   str(meta['generation']) == str(binding['generation']), 'real worker trace identity mismatch')
        lc.require(Path(meta['raw_file']).name == meta['raw_file'], 'worker raw path escape')
        worker_ref = self._reference_public(trace / meta['raw_file'])
        worker_event = lc.json_ref(worker_ref)
        lc.require(worker_event == result['worker_exits'][0] and len(result['worker_exits']) == 1,
                   'worker original does not match supervised inspected EOF/reap result')
        normalized = deepcopy(result)
        # Native FString normalization is limited to this documented wire field.
        lc.require(str(worker_event['generation']) == str(binding['generation']), 'native generation mismatch')
        normalized['worker_exits'][0]['generation'] = binding['generation']
        destination = self.output / ('session-' + name)
        destination.mkdir(mode=0o700)
        waits_dir = destination / 'waits'; waits_dir.mkdir(mode=0o700)
        observed = self.clock()
        pids = {'launcher': result['launcher_pid'], 'ue': binding['host_pid'], 'worker': binding['worker_pid']}
        identities = {kind: self._identity_from_observer(pid) for kind, pid in pids.items()}
        parents = {'launcher': identities['launcher']['ppid'], 'ue': pids['launcher'], 'worker': pids['ue']}
        sources = {'launcher': original_completion, 'ue': stdout, 'worker': worker_ref}
        waits = {}
        for kind, identity in identities.items():
            code = result['launcher_wait_exit'] if kind == 'launcher' else result['ue_exit_code'] if kind == 'ue' else worker_event['exit_code']
            lc.require(type(code) is int and code == 0, 'unknown/nonzero core wait cannot be normalized')
            waits[kind] = self._write_public(waits_dir / (kind + '.json'), {
                'kind': 'actual-parent-wait', 'observed': True, 'identity': identity,
                'parent_pid': parents[kind], 'exit_code': code, 'monotonic': observed,
                'time_kind': 'controller-read-upper-bound', 'source_ref': sources[kind],
                'worker_metadata_ref': meta_ref if kind == 'worker' else None})
        completion_ref = self._write_public(destination / 'completion-adapter.json',
                                           dict(normalized, original_completion_ref=original_completion))
        build_line = b'[launcher] build_exit_code=0\n'
        lc.require(raw_stdout.count(build_line) == 1, 'unique actual official build PIPESTATUS result missing')
        build_start = self.session_start
        build_end = stage_events['startup']
        parent_ref = self._write_public(destination / 'build-parent.json', {
            'format': 'universe-i14-build-parent.v1', 'launcher_identity': identities['launcher'],
            'session': name, 'stdout_ref': stdout,
            'line_start': raw_stdout.index(build_line), 'line_end': raw_stdout.index(build_line) + len(build_line),
            'build_start_monotonic': build_start, 'build_end_monotonic': build_end,
            'launcher_source_ref': self.card['launcher_source_ref']})
        # Actual return of pinned supervisor bounds its own wait/seal. The outer
        # wrapper writes are an additional visible session seal phase.
        preseal_ref = self._reference_public(output / 'supervisor-exit.json')
        preseal_receipt = lc.json_ref(preseal_ref)
        polls = [e for e in event_rows if e.get('event') == 'poll']
        lc.require(polls, 'same-domain actual poll/elapsed origin required for seal boundary')
        starts_upper = [lc.number(e['monotonic_seconds'], 'supervisor poll mono') -
                        lc.number(e['elapsed_seconds'], 'supervisor poll elapsed') for e in polls]
        # record() timestamps after the poll's elapsed calculation. The minimum
        # remains an upper bound on true supervisor start, not an invented instant.
        seal_start = min(starts_upper) + lc.number(preseal_receipt['elapsed_seconds'], 'actual preseal elapsed')
        lc.require(seal_start <= self.handle.finished_monotonic, 'inconsistent preseal/actual return boundary')
        lc.require(build_start <= build_end <= stage_events['interaction'] <=
                   stage_events['shutdown'] <= seal_start <= self.clock(), 'same-process actual stage order')
        ends = [build_start, build_end, stage_events['interaction'], stage_events['shutdown'], seal_start, self.clock()]
        limits = self.card['sessions'][name]
        stages = [dict(stage=kind, start_monotonic=ends[i], end_monotonic=ends[i+1],
                       deadline_monotonic=min(ends[i]+limits['stage_seconds'][kind], build_start+limits['max_seconds']),
                       timing_bound_source='preseal-poll-conservative-upper' if kind in ('shutdown','seal') else 'actual-supervisor-events',
                       preseal_ref=preseal_ref if kind in ('shutdown','seal') else None)
                  for i, kind in enumerate(('build','startup','interaction','shutdown','seal'))]
        return {'session': dict(session=name, start_monotonic=build_start, end_monotonic=ends[-1],
                                binding=binding, stages=stages, completion_ref=completion_ref),
                'identities': identities, 'waits': waits, 'wait_read_monotonic': observed,
                'build_parent_ref': parent_ref}

    def finalize_run(self, *, expected_policy):
        try:
            if set(self.assembled) != {'initialize', 'existing'}:
                return {'status': 'inconclusive', 'reasons': ['actual core/session adapters incomplete; preserve failure evidence']}
            return self._finalize_run(expected_policy=expected_policy)
        except (KeyError, FileNotFoundError) as error:
            return {'status': 'inconclusive', 'reasons': ['missing final evidence: ' + str(error)]}
        except (lc.Invalid, ValueError, TypeError, OSError) as error:
            return {'status': 'fail', 'reasons': [str(error)]}

    def _finalize_run(self, *, expected_policy):
        """Assemble actual source-bound ledger and exclusive self-counted snapshot.

        Missing signals return inconclusive, never create a successful completion.
        No UI is called; while any owned supervisor/process is live observer stays on.
        """
        lc.require(self.handle is None or self.handle.done.is_set(), 'live supervisor cannot be sealed')
        lc.require(set(self.assembled) == {'initialize','existing'}, 'core/session raw adapter incomplete; keep failed evidence')
        known = [row for item in self.assembled.values() for row in item['identities'].values()]
        self.stop_after_quiescence(expected_owned=known)
        observed = self.clock()
        lc.require(observed - self.samples[-1]['monotonic'] <= 2, 'final observer tail exceeded2s')
        lc.require(expected_policy['run_binding'] == self.card['run_binding'] and
                   expected_policy['clock_id'] == self.clock_binding['id'], 'independent final policy binding')
        processes, seen, owned = [], {}, known[:]
        for sample in self.samples:
            relevant = lc.classify_processes(sample['processes'], owned, self.card['accepted_executable'])
            for item in relevant:
                lc.require(item['ownership'] == 'owned', 'extra UE contamination cannot be sealed normal')
                row = item['identity']; key = lc.process_key(row)
                owned.append(row)
                seen.setdefault(key, {'identity':row,'times':[]})['times'].append(sample['monotonic'])
        for key, entry in seen.items():
            first, last = min(entry['times']), max(entry['times'])
            before = [s['monotonic'] for s in self.samples if s['monotonic'] < first]
            after = [s['monotonic'] for s in self.samples if s['monotonic'] > last]
            row = dict(identity=entry['identity'], ownership='owned', first_seen_monotonic=first,
                       last_seen_monotonic=last, start_lower_bound=max(before) if before else self.dispatch_monotonic,
                       end_upper_bound=min(after) if after else observed,
                       boundary_source='observer-bracket', wait_ref=None, exit_status=None,
                       role='build_descendant', build_parent_ref=None)
            for name, assembled in self.assembled.items():
                for kind, identity in assembled['identities'].items():
                    if lc.same_process(identity, entry['identity']):
                        row.update(role='runtime_core',core_kind=kind,session=name,exit_status=0,
                                   wait_ref=assembled['waits'][kind], boundary_source='parent-wait',
                                   end_upper_bound=max(row['end_upper_bound'],assembled['wait_read_monotonic']))
            if row['role'] == 'build_descendant':
                candidates = [x for x in self.assembled.values() if x['session']['stages'][0]['start_monotonic'] <= first <= x['session']['stages'][0]['end_monotonic']]
                lc.require(len(candidates)==1, 'non-build unknown descendant cannot be labelled build')
                row['build_parent_ref'] = candidates[0]['build_parent_ref']
            processes.append(row)
        ledger = dict(format=lc.FORMAT_V2, run_binding=self.card['run_binding'],clock=self.clock_binding,
            dispatch_monotonic=self.dispatch_monotonic, limit_seconds=1200,max_observer_gap_seconds=2,
            samples=self.samples,sessions=[self.assembled[n]['session'] for n in ('initialize','existing')],processes=processes)
        ledger_path=self.output/'ledger-v2.json'; snapshot_path=self.output/'storage-snapshot.json'
        lc.require(not ledger_path.exists() and not snapshot_path.exists(), 'final seal already exists')
        root=lc.checked_path(self.card['storage_root'])
        fixed={}
        for directory, dirs, files in os.walk(root,followlinks=False):
            for name in dirs+files:
                path=Path(directory)/name
                lc.require(not path.is_symlink(), 'final storage symlink')
                if path.is_file(): fixed[str(path)]=path.stat().st_size
        # Fixed point counts both ledger and snapshot, while end remains an explicit
        # conservative upper bound. Actual publish/audit is measured after writing.
        now=self.clock(); charged=now+2
        ledger.update(actual_observed_end_monotonic=now,charged_end_monotonic=charged,end_monotonic=charged)
        ledger['seal']=dict(started_monotonic=observed,ended_monotonic=now,
            observer_ended_monotonic=self.observer_ended_monotonic,storage_bytes=0,
            storage_limit_bytes=lc.MAX_BYTES,storage_snapshot_ref={'path':str(snapshot_path),'sha256':'0'*64})
        sizes=dict(fixed); sizes[str(ledger_path)]=0; sizes[str(snapshot_path)]=0
        for _ in range(20):
            snapshot=dict(kind='whole-storage',includes_all_attempts=True,storage_root=str(root),
                monotonic=now,files=[dict(path=p,bytes=n) for p,n in sorted(sizes.items())])
            snapshot_raw=_encoded(snapshot)
            ledger['seal']['storage_snapshot_ref']['sha256']=hashlib.sha256(snapshot_raw).hexdigest()
            ledger['seal']['storage_bytes']=sum(sizes.values())
            ledger_raw=_encoded(ledger)
            updated=dict(sizes,**{str(ledger_path):len(ledger_raw),str(snapshot_path):len(snapshot_raw)})
            if updated==sizes: break
            sizes=updated
        else:
            raise lc.Invalid('final storage self-byte fixed point did not converge')
        lc.require(sum(sizes.values())<=lc.MAX_BYTES and charged-self.dispatch_monotonic<=1200,'final budget exceeded before publish')
        lc.exclusive_bytes(snapshot_path,snapshot_raw); ledger_ref=lc.exclusive_bytes(ledger_path,ledger_raw)
        return self.audit_finalized_ledger(ledger_ref,expected_policy=expected_policy)
