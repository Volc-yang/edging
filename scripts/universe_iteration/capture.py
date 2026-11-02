"""Passive native-Shot evidence, not proof of UE/Metal provenance or G-B2.

No UI, subprocess, authority traversal, external decoder or import-time IO.
Only explicit public evidence and the requested original PNG are read. See the
I13C report for the public observation/command wrappers required by this API.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from functools import wraps
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import time
import zlib

FORMAT = 'universe-i13-capture.v1'
BINDING_KEYS = {'run_id', 'session', 'world_id', 'authority_root', 'source_sha',
                'host_pid', 'worker_pid', 'generation'}
MAX_PNG_BYTES = 32 * 1024 * 1024
MAX_DECODED_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 16 * 1024 * 1024
MAX_PUBLIC_BYTES = 8 * 1024 * 1024


class CaptureError(ValueError):
    """Incomplete, mismatching or unsafe capture evidence."""


def _checked(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except CaptureError:
            raise
        except (KeyError, TypeError, AttributeError, OSError, OverflowError, struct.error) as exc:
            raise CaptureError('malformed or unavailable capture evidence') from exc
    return checked


def _require(condition, message):
    if not condition:
        raise CaptureError(message)


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _path(value):
    _require(isinstance(value, (str, Path)), 'path required')
    text = str(value)
    path = Path(text)
    _require(path.is_absolute() and str(path) == text and
             not any(x in ('.', '..') for x in text.split('/')) and '\x00' not in text,
             'canonical absolute path required')
    return path


@contextmanager
def _parent(value):
    """Anchor every component with openat/O_NOFOLLOW; never follow a redirect."""
    path = _path(value)
    _require(path.name != '', 'file path required')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:-1]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield path, fd, os.fstat(fd)
    except OSError as exc:
        raise CaptureError('unsafe or unavailable path') from exc
    finally:
        os.close(fd)


def _identity(st):
    return {'device': st.st_dev, 'inode': st.st_ino}


def _stat_identity(st):
    return (_identity(st), st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _parent_identity(path):
    with _parent(path) as (_, _, parent):
        return _identity(parent)


def _public_path(path):
    path = _path(path)
    _require(not re.search(r'(^|[/._-])(key|keys|secret|owner)([/._-]|$)',
                           str(path), re.I), 'private paths are not public evidence')
    return path


def _read(path, limit, *, public=False, single_link=False):
    path = _public_path(path) if public else _path(path)
    with _parent(path) as (_, parent_fd, parent_st):
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent_fd)
        except OSError as exc:
            raise CaptureError('missing or redirected evidence file') from exc
        try:
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
                     'regular bounded evidence file required')
            _require(not single_link or before.st_nlink == 1, 'linked original rejected')
            chunks, remaining = [], limit + 1
            while remaining:
                chunk = os.read(fd, min(remaining, 1024 * 1024))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b''.join(chunks)
            after = os.fstat(fd)
            current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            _require(len(data) <= limit and _stat_identity(before) ==
                     _stat_identity(after) == _stat_identity(current),
                     'file replaced or changed during read')
            _require(_parent_identity(path) == _identity(parent_st), 'parent redirected')
            return data, before
        finally:
            os.close(fd)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def _json(data):
    try:
        return json.loads(data, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(CaptureError('nonfinite JSON')))
    except (ValueError, UnicodeError) as exc:
        raise CaptureError('invalid public JSON') from exc


def _reference(reference, *, as_json=True):
    _require(isinstance(reference, dict) and set(reference) == {'path', 'sha256'}
             and _sha(reference['sha256']), 'exact public reference required')
    data, _ = _read(reference['path'], MAX_PUBLIC_BYTES, public=True)
    _require(hashlib.sha256(data).hexdigest() == reference['sha256'], 'reference digest mismatch')
    return _json(data) if as_json else data


def _write_new(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    _require(len(data) <= MAX_PUBLIC_BYTES, 'receipt too large')
    with _parent(path) as (path, parent_fd, parent_st):
        try:
            fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent_fd)
        except OSError as exc:
            raise CaptureError('exclusive receipt path required') from exc
        try:
            view = memoryview(data)
            while view:
                count = os.write(fd, view)
                _require(count > 0, 'receipt write failed')
                view = view[count:]
            os.fsync(fd)
            _require(_parent_identity(path) == _identity(parent_st), 'receipt parent redirected')
        finally:
            os.close(fd)
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}


def _binding(value, expected):
    for binding in (value, expected):
        _require(isinstance(binding, dict) and set(binding) == BINDING_KEYS, 'exact binding fields required')
        for name in ('run_id', 'world_id'):
            _require(isinstance(binding[name], str) and
                     re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', binding[name]), 'invalid run/world ID')
        _require(binding['session'] in ('initialize', 'existing'), 'invalid session')
        _require(isinstance(binding['source_sha'], str) and
                 re.fullmatch('[0-9a-f]{40}', binding['source_sha']), 'invalid source SHA')
        authority = _path(binding['authority_root'])
        _parent_identity(authority / '.metadata-only-check')
        for name in ('host_pid', 'worker_pid', 'generation'):
            _require(_integer(binding[name], 1), 'positive process/generation required')
    _require(value == expected, 'binding mismatch')


def _selection(value):
    _require(isinstance(value, dict) and set(value) == {'tick', 'revision', 'watermark'}
             and all(_integer(x) for x in value.values()), 'exact observation triple required')


def _clock(value):
    _require(isinstance(value, dict) and set(value) == {'id', 'anchor_monotonic', 'anchor_utc'}, 'clock required')
    _require(isinstance(value['id'], str) and bool(value['id']) and
             _seconds(value['anchor_monotonic']), 'invalid controller clock')
    try:
        utc = datetime.fromisoformat(value['anchor_utc'])
        _require(utc.tzinfo is not None and utc.utcoffset() is not None, 'timezone required')
        return utc.timestamp()
    except (TypeError, ValueError) as exc:
        raise CaptureError('invalid UTC clock anchor') from exc


def _context(value, expected_binding, expected_trusted_head, expected_selected_observation,
             expected_observation_ref):
    _binding(value['binding'], expected_binding)
    _selection(value['trusted_head']); _selection(value['selected_observation'])
    _selection(expected_trusted_head); _selection(expected_selected_observation)
    _require(value['trusted_head'] == expected_trusted_head and
             value['selected_observation'] == expected_selected_observation,
             'head/observation mismatch')
    _require(value['observation_ref'] == expected_observation_ref, 'observation reference mismatch')
    observation = _reference(expected_observation_ref)
    _require(isinstance(observation, dict), 'public observation wrapper required')
    _binding(observation.get('binding'), expected_binding)
    _selection(observation.get('trusted_head')); _selection(observation.get('selected_observation'))
    for name in ('trusted_head', 'selected_observation'):
        _require(observation.get(name) == value[name], 'observation evidence binding mismatch')
    _require(observation.get('clock_id') == value['clock']['id'] and
             _seconds(observation.get('verified_monotonic')), 'observation clock/time missing')
    # This public wrapper is supplied by R AFTER strict observation verification.
    # Matching it does not itself perform or certify that upstream verification.
    _reference(observation.get('verification_ref'), as_json=False)
    return observation


def _map(reference, authority_root):
    value = _reference(reference)
    _require(isinstance(value, dict) and value.get('root') == authority_root and
             isinstance(value.get('files'), dict), 'authority map shape/root mismatch')
    total = 0
    for name, item in value['files'].items():
        _require(isinstance(name, str) and name and not name.startswith('/') and
                 all(x not in ('', '.', '..') for x in name.split('/')),
                 'invalid map relative path')
        _require(isinstance(item, dict) and set(item) == {'bytes', 'sha256'} and
                 _integer(item['bytes']) and _sha(item['sha256']), 'invalid map entry')
        total += item['bytes']
    _require('bytes' not in value or (_integer(value['bytes']) and value['bytes'] == total), 'map byte count mismatch')
    return value


def _log_prefix(path, offset, pin=None):
    _require(_integer(offset) and offset <= MAX_PUBLIC_BYTES, 'bounded log offset required')
    with _parent(_public_path(path)) as (path, parent_fd, parent_st):
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        except OSError as exc:
            raise CaptureError('log unavailable') from exc
        try:
            st = os.fstat(fd)
            _require(stat.S_ISREG(st.st_mode) and st.st_size >= offset, 'log prefix missing')
            remaining, digest = offset, hashlib.sha256()
            while remaining:
                data = os.read(fd, min(remaining, 1024 * 1024))
                _require(data, 'log truncated')
                digest.update(data); remaining -= len(data)
            now = os.fstat(fd); current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            _require(_identity(st) == _identity(now) == _identity(current) and
                     now.st_size >= offset and current.st_size >= offset and
                     _parent_identity(path) == _identity(parent_st), 'log replaced/truncated')
            result = dict(path=str(path), device=st.st_dev, inode=st.st_ino,
                          before_offset=offset, prefix_sha256=digest.hexdigest())
            _require(pin is None or result == pin, 'log prefix identity mismatch')
            return result
        finally:
            os.close(fd)


@_checked
def decode_png(data, *, expected_width, expected_height):
    """Strict bounded SDR RGB/RGBA8 noninterlaced PNG decode, no image provenance."""
    _require(isinstance(data, bytes) and 0 < len(data) <= MAX_PNG_BYTES, 'PNG byte limit')
    _require(_integer(expected_width, 1) and _integer(expected_height, 1) and
             expected_width * expected_height <= MAX_PIXELS, 'PNG dimension limit')
    _require(data.startswith(b'\x89PNG\r\n\x1a\n'), 'native PNG signature required (no EXR/JPEG)')
    pos, chunks, idat, seen_idat_end, info = 8, [], [], False, None
    while pos < len(data):
        _require(len(data) - pos >= 12, 'truncated PNG chunk')
        size = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        _require(size <= MAX_PNG_BYTES and pos + 12 + size <= len(data), 'PNG chunk bounds')
        _require(re.fullmatch(b'[A-Za-z]{4}', kind) and not kind[2] & 32, 'invalid PNG chunk type')
        payload = data[pos + 8:pos + 8 + size]
        crc = struct.unpack('>I', data[pos + 8 + size:pos + 12 + size])[0]
        _require(zlib.crc32(kind + payload) & 0xffffffff == crc, 'PNG CRC mismatch')
        _require(chunks or kind == b'IHDR', 'IHDR must be first')
        if kind == b'IHDR':
            _require(not chunks and size == 13, 'duplicate/invalid IHDR')
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            _require((width, height) == (expected_width, expected_height), 'viewport dimensions mismatch')
            _require(depth == 8 and color in (2, 6) and
                     (compression, filtering, interlace) == (0, 0, 0), 'unsupported SDR PNG format')
            channels = 3 if color == 2 else 4
            decoded_size = (width * channels + 1) * height
            _require(decoded_size <= MAX_DECODED_BYTES, 'PNG decompression limit')
            info = (width, height, channels, decoded_size)
        elif kind == b'IDAT':
            _require(not seen_idat_end, 'noncontiguous IDAT')
            idat.append(payload)
        elif kind == b'IEND':
            _require(size == 0 and idat and pos + 12 == len(data), 'IEND/trailing bytes')
            chunks.append(kind); pos += 12; break
        else:
            if idat:
                seen_idat_end = True
            _require(kind not in (b'acTL', b'fcTL', b'fdAT'), 'animated PNG rejected')
            _require(kind in (b'PLTE', b'tRNS', b'sRGB', b'gAMA', b'cHRM', b'pHYs', b'sBIT', b'tEXt'),
                     'unsupported PNG chunk/profile')
            _require(kind == b'tEXt' or (not idat and kind not in chunks), 'duplicate/misordered ancillary chunk')
            if kind == b'sRGB':
                _require(size == 1 and payload[0] <= 3, 'invalid sRGB')
            elif kind == b'gAMA':
                _require(size == 4 and int.from_bytes(payload, 'big') > 0, 'invalid gAMA')
            elif kind == b'cHRM':
                _require(size == 32, 'invalid cHRM')
            elif kind == b'pHYs':
                _require(size == 9 and payload[-1] <= 1, 'invalid pHYs')
            elif kind == b'sBIT':
                _require(size == info[2] and all(1 <= x <= 8 for x in payload), 'invalid sBIT')
            elif kind == b'tRNS':
                _require(info[2] == 3 and size == 6 and
                         all(x <= 255 for x in struct.unpack('>HHH', payload)), 'invalid tRNS')
            elif kind == b'tEXt':
                keyword, separator, text = payload.partition(b'\0')
                _require(separator and 1 <= len(keyword) <= 79 and b'\0' not in text, 'invalid tEXt')
            if kind == b'PLTE':
                _require(not idat and kind not in chunks and size and size <= 768 and size % 3 == 0,
                         'invalid PLTE')
        chunks.append(kind); pos += 12 + size
    _require(chunks and chunks[-1] == b'IEND' and pos == len(data) and info is not None,
             'missing terminal IEND')
    width, height, channels, decoded_size = info
    try:
        decoder = zlib.decompressobj()
        scanlines = decoder.decompress(b''.join(idat), decoded_size + 1)
        _require(len(scanlines) == decoded_size and decoder.eof and not decoder.unused_data and
                 not decoder.unconsumed_tail, 'PNG zlib size/EOF/trailing stream')
    except zlib.error as exc:
        raise CaptureError('invalid PNG zlib stream') from exc
    stride = width * channels
    prior = bytearray(stride); pixels = hashlib.sha256()
    for y in range(height):
        begin = y * (stride + 1); mode = scanlines[begin]
        _require(mode <= 4, 'invalid PNG row filter')
        row = bytearray(scanlines[begin + 1:begin + 1 + stride])
        if mode:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                above = prior[x]; upper_left = prior[x - channels] if x >= channels else 0
                if mode == 1: predictor = left
                elif mode == 2: predictor = above
                elif mode == 3: predictor = (left + above) // 2
                else:
                    p = left + above - upper_left
                    a, b, c = abs(p - left), abs(p - above), abs(p - upper_left)
                    predictor = left if a <= b and a <= c else above if b <= c else upper_left
                row[x] = (row[x] + predictor) & 255
        pixels.update(row); prior = row
    return dict(width=width, height=height, bit_depth=8, color_type=2 if channels == 3 else 6,
                decoded_pixel_sha256=pixels.hexdigest(), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())


@_checked
def prepare_native_shot(*, target_path, expected_binding, trusted_head, selected_observation,
                        observation_ref, before_map_ref, before_map_monotonic, log_path,
                        log_offset, clock, expected_width, expected_height, show_ui=False):
    """Reserve one absent target via exclusive .prepare.json; return its ref/command."""
    _binding(expected_binding, expected_binding); _selection(trusted_head); _selection(selected_observation)
    _clock(clock)
    _require(type(show_ui) is bool, 'explicit HUD choice required')
    target = _path(target_path)
    _require(target.suffix == '.png' and not any(c in str(target) for c in '"\\\r\n;'), 'safe exact .png target required')
    _require(_integer(expected_width, 1) and _integer(expected_height, 1) and
             expected_width * expected_height <= MAX_PIXELS and
             (expected_width * 4 + 1) * expected_height <= MAX_DECODED_BYTES, 'viewport dimension limit')
    with _parent(target) as (_, fd, parent_st):
        try:
            os.stat(target.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CaptureError('target must not exist, including symlink')
        parent_identity = _identity(parent_st)
    now = time.monotonic()
    value = dict(format=FORMAT, phase='prepared', binding=expected_binding,
                 trusted_head=trusted_head, selected_observation=selected_observation,
                 observation_ref=observation_ref, before_map_ref=before_map_ref,
                 before_map_monotonic=before_map_monotonic, clock=clock,
                 prepared_monotonic=now, target_path=str(target), parent_identity=parent_identity,
                 target_absent=True, expected_width=expected_width, expected_height=expected_height,
                 sdr=True, show_ui=show_ui,
                 command='Shot filename="' + str(target) + '" nosuffix' + (' showui' if show_ui else ''),
                 log=_log_prefix(log_path, log_offset))
    observation = _context(value, expected_binding, trusted_head, selected_observation, observation_ref)
    _require(_seconds(before_map_monotonic) and clock['anchor_monotonic'] <= before_map_monotonic <= now and
             clock['anchor_monotonic'] <= observation['verified_monotonic'] <= now,
             'observation/map must precede prepare in controller clock')
    _map(before_map_ref, expected_binding['authority_root'])
    preparation_ref = _write_new(str(target) + '.prepare.json', value)
    # A concurrent target arrival is a retained failed preparation, never deleted/reused.
    with _parent(target) as (_, fd, parent_st):
        _require(_identity(parent_st) == parent_identity, 'target parent changed')
        try:
            os.stat(target.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return {'preparation_ref': preparation_ref, 'command': value['command']}
    raise CaptureError('target appeared during preparation')


def _prepared(reference, expected_binding, trusted_head, selected, observation_ref, expected_clock):
    value = _reference(reference)
    _require(value.get('format') == FORMAT and value.get('phase') == 'prepared' and
             value.get('target_absent') is True and value.get('sdr') is True, 'prepared native Shot required')
    _clock(value['clock']); _clock(expected_clock)
    _require(value['clock'] == expected_clock, 'independent clock mismatch')
    observation = _context(value, expected_binding, trusted_head, selected, observation_ref)
    target = _path(value['target_path'])
    _require(target.suffix == '.png' and not any(c in str(target) for c in '"\\\r\n;') and
             reference['path'] == str(target) + '.prepare.json' and type(value.get('show_ui')) is bool,
             'exact original preparation/target required')
    command = 'Shot filename="' + str(target) + '" nosuffix' + (' showui' if value['show_ui'] else '')
    _require(value.get('command') == command, 'native command must be derived from preparation')
    _require(_integer(value.get('expected_width'), 1) and _integer(value.get('expected_height'), 1) and
             value['expected_width'] * value['expected_height'] <= MAX_PIXELS and
             (value['expected_width'] * 4 + 1) * value['expected_height'] <= MAX_DECODED_BYTES,
             'prepared viewport limits')
    _require(_seconds(value.get('prepared_monotonic')) and _seconds(value.get('before_map_monotonic')) and
             value['clock']['anchor_monotonic'] <= value['before_map_monotonic'] <= value['prepared_monotonic'] and
             value['clock']['anchor_monotonic'] <= observation['verified_monotonic'] <= value['prepared_monotonic'] <= time.monotonic(),
             'prepared evidence interval mismatch')
    _map(value['before_map_ref'], expected_binding['authority_root'])
    _require(_parent_identity(value['target_path']) == value['parent_identity'], 'target parent replaced')
    _log_prefix(value['log']['path'], value['log']['before_offset'], value['log'])
    return value


def _command(reference, preparation_ref, prepared):
    value = _reference(reference)
    _require(value.get('format') == FORMAT and value.get('phase') == 'cua-command' and
             value.get('preparation_ref') == preparation_ref and
             value.get('command') == prepared['command'] and
             value.get('clock_id') == prepared['clock']['id'], 'actual command receipt mismatch')
    _binding(value.get('binding'), prepared['binding'])
    _selection(value.get('trusted_head')); _selection(value.get('selected_observation'))
    for name in ('trusted_head', 'selected_observation', 'observation_ref'):
        _require(value.get(name) == prepared[name], 'command observation/binding mismatch')
    _reference(value.get('cua_result_ref'), as_json=False)
    start, end = value.get('start_monotonic'), value.get('end_monotonic')
    _require(_seconds(start) and _seconds(end) and prepared['prepared_monotonic'] <= start <= end,
             'command interval missing/stale')
    log = value.get('log')
    _require(isinstance(log, dict) and set(log) == set(prepared['log']) | {'after_offset'} and
             {k: log[k] for k in prepared['log']} == prepared['log'] and
             all(_integer(log[k]) for k in ('device', 'inode', 'before_offset', 'after_offset')) and
             log['after_offset'] >= log['before_offset'],
             'command log range mismatch')
    # Ensure actual after-offset exists; the pinned prefix still binds the original log.
    _log_prefix(log['path'], log['after_offset'])
    return value


@_checked
def collect_native_shot(preparation_ref, command_receipt_ref, *, expected_binding,
                        expected_trusted_head, expected_selected_observation,
                        expected_observation_ref, expected_clock, receipt_path, max_wait_seconds=2.0,
                        stability_seconds=0.05):
    """Read only a new stable original; write provisional receipt, no UI/provenance claim."""
    _require(_seconds(max_wait_seconds) and _seconds(stability_seconds) and
             0.01 <= stability_seconds <= max_wait_seconds <= 10, 'bounded stability window required')
    p = _prepared(preparation_ref, expected_binding, expected_trusted_head,
                  expected_selected_observation, expected_observation_ref, expected_clock)
    command = _command(command_receipt_ref, preparation_ref, p)
    started = time.monotonic()
    _require(command['end_monotonic'] <= started, 'command receipt is from the future')
    data, first = _read(p['target_path'], MAX_PNG_BYTES, single_link=True)
    first_read = time.monotonic()
    # Not a timestamp of the rendered frame. This is only a stale-file sanity check.
    command_utc = _clock(p['clock']) + command['start_monotonic'] - p['clock']['anchor_monotonic']
    _require(first.st_mtime_ns >= int(command_utc * 1_000_000_000), 'stale original timestamp')
    png = decode_png(data, expected_width=p['expected_width'], expected_height=p['expected_height'])
    _require(time.monotonic() - started <= max_wait_seconds, 'PNG validation deadline exceeded')
    time.sleep(stability_seconds)
    second_data, second = _read(p['target_path'], MAX_PNG_BYTES, single_link=True)
    stable = time.monotonic()
    _require(stable - started <= max_wait_seconds and _stat_identity(first) == _stat_identity(second) and
             data == second_data, 'PNG not stable or inode replaced')
    _require(_parent_identity(p['target_path']) == p['parent_identity'], 'PNG parent changed')
    value = dict(format=FORMAT, phase='collected', preparation_ref=preparation_ref,
                 command_receipt_ref=command_receipt_ref, binding=p['binding'],
                 trusted_head=p['trusted_head'], selected_observation=p['selected_observation'],
                 observation_ref=p['observation_ref'], clock=p['clock'],
                 original_ref={'path': p['target_path'], 'sha256': png['sha256']},
                 original_identity=_identity(second), original_size=second.st_size,
                 original_mtime_ns=second.st_mtime_ns, original_ctime_ns=second.st_ctime_ns,
                 png=png, first_read_monotonic=first_read, stable_monotonic=stable,
                 request_to_stable={'start_monotonic': command['start_monotonic'], 'end_monotonic': stable},
                 scope='Structural public-evidence consistency only; UE/Metal/viewport provenance requires independent review')
    return _write_new(receipt_path, value)


@_checked
def verify_native_shot(capture_ref, *, expected_binding, expected_trusted_head,
                       expected_selected_observation, expected_observation_ref, expected_clock,
                       after_map_ref, after_map_monotonic, before_exit_monotonic, before_exit_ref):
    """Finalize using independent expectations and ACTUAL exit boundary, not a deadline."""
    value = _reference(capture_ref)
    _require(value.get('format') == FORMAT and value.get('phase') == 'collected', 'capture receipt required')
    p = _prepared(value['preparation_ref'], expected_binding, expected_trusted_head,
                  expected_selected_observation, expected_observation_ref, expected_clock)
    _context(value, expected_binding, expected_trusted_head, expected_selected_observation, expected_observation_ref)
    _require(value['clock'] == p['clock'], 'capture clock mismatch')
    command = _command(value['command_receipt_ref'], value['preparation_ref'], p)
    exit_receipt = _reference(before_exit_ref)
    _require(isinstance(exit_receipt, dict) and exit_receipt.get('format') == FORMAT and
             exit_receipt.get('phase') == 'actual-before-exit' and
             exit_receipt.get('binding') == expected_binding and
             exit_receipt.get('clock_id') == expected_clock['id'] and
             exit_receipt.get('before_exit_monotonic') == before_exit_monotonic,
             'actual before-exit receipt mismatch')
    _binding(exit_receipt.get('binding'), expected_binding)
    _require(_seconds(exit_receipt.get('before_exit_monotonic')), 'actual exit time type')
    _reference(exit_receipt.get('exit_evidence_ref'), as_json=False)
    first, stable = value.get('first_read_monotonic'), value.get('stable_monotonic')
    _require(all(_seconds(x) for x in (first, stable, after_map_monotonic, before_exit_monotonic)) and
             command['end_monotonic'] <= first <= stable <= after_map_monotonic <= before_exit_monotonic and
             before_exit_monotonic <= time.monotonic(), 'capture/map/actual-exit interval mismatch')
    _require(value.get('request_to_stable') == {'start_monotonic': command['start_monotonic'], 'end_monotonic': stable},
             'request-to-stable interval mismatch')
    _require(value['original_ref']['path'] == p['target_path'], 'original target mismatch')
    data, st = _read(value['original_ref']['path'], MAX_PNG_BYTES, single_link=True)
    png = decode_png(data, expected_width=p['expected_width'], expected_height=p['expected_height'])
    _require(value['original_ref']['sha256'] == png['sha256'] and value['png'] == png and
             value['original_identity'] == _identity(st) and value['original_size'] == st.st_size and
             value['original_mtime_ns'] == st.st_mtime_ns and value['original_ctime_ns'] == st.st_ctime_ns,
             'original changed after collection')
    before = _map(p['before_map_ref'], expected_binding['authority_root'])
    after = _map(after_map_ref, expected_binding['authority_root'])
    _require(before['files'] == after['files'], 'full authority map changed')
    return dict(format=FORMAT, phase='checks_complete_requires_review', capture_ref=capture_ref,
                binding=expected_binding, after_map_ref=after_map_ref, before_exit_ref=before_exit_ref,
                after_map_monotonic=after_map_monotonic, before_exit_monotonic=before_exit_monotonic,
                request_to_stable=value['request_to_stable'], scope=value['scope'])
