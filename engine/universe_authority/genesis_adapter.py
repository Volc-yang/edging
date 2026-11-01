"""Explicit Genesis 1.4.3 candidate provider; no import/constructor runtime I/O.

Bootstrap measures identity before an owner freezes DeploymentContext. Only
explicit operations import Genesis. No world writer, authority handle or signer
is accepted. Isolated probes are physical families, never committed worlds.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from contextlib import contextmanager, redirect_stdout
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from enum import Enum
from functools import wraps
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import stat
import sys
import threading

from .codec import ContractError, DeploymentContext, canonical, digest, encode_f64, f64
from .physics import PhysicsDraft, PhysicsIds, PhysicsInitialDraft, PhysicsInitialIds
from .records import Record, validate_record
from .store import BlobWrite

_CRITICAL = (
    '__init__.py', 'options/options.py', 'options/scene.py', 'options/morphs.py',
    'options/solvers.py', 'engine/materials/base.py', 'engine/materials/rigid.py',
    'engine/entities/base_entity.py', 'engine/entities/rigid_entity/rigid_entity.py',
    'engine/entities/rigid_entity/description.py', 'engine/entities/rigid_entity/inertial.py',
    'engine/solvers/kinematic_solver.py', 'engine/solvers/base_solver.py',
    'engine/solvers/rigid/rigid_solver.py', 'engine/mesh.py', 'engine/scene.py', 'utils/geom.py',
)
_DEPENDENCIES = ('numpy', 'pydantic', 'quadrants', 'torch', 'trimesh')
_MAX_RAW = 8_388_608
_RUNTIME = None
_RUNTIME_LOCK = threading.Lock()
_LOG_LOCK = threading.RLock()


@contextmanager
def runtime_logs_to_stderr():
    """Scoped Python/native stdout routing for a serialized worker operation.

    Restore both streams even on failure. The owner must serialize protocol
    writes; this process-wide descriptor scope is not a concurrent worker API.
    """
    with _LOG_LOCK:
        sys.stdout.flush(); sys.stderr.flush()
        saved = os.dup(1)
        try:
            os.dup2(2, 1)
            with redirect_stdout(sys.stderr):
                yield
        finally:
            sys.stdout.flush(); sys.stderr.flush()
            os.dup2(saved, 1)
            os.close(saved)


def _logged(function):
    @wraps(function)
    def invoke(*args, **kwargs):
        with runtime_logs_to_stderr():
            return function(*args, **kwargs)
    return invoke


def _require(condition, code='PHYSICS_INVALID', detail=''):
    if not condition:
        raise ContractError(code, detail)


def _pack(value):
    # Packaging index may contain >256 files; every leaf is a bounded path/SHA.
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'),
                      allow_nan=False).encode('ascii')


def _record(world, kind, identifier, body, refs):
    result = dict(domain='edgeworld.universe.authority', version='0.2', world_id=world,
                  kind=kind, id=identifier, body=body, refs=refs)
    validate_record(result)
    return result


def _read_regular(path, maximum):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                 and 0 <= before.st_size <= maximum, 'BLOB_LIMIT' if before.st_size > maximum else 'PHYSICS_INVALID')
        pieces, total = [], 0
        while True:
            piece = os.read(descriptor, min(65536, maximum + 1 - total))
            if not piece:
                break
            pieces.append(piece); total += len(piece)
            _require(total <= maximum, 'BLOB_LIMIT')
        after = os.fstat(descriptor)
        entry = os.stat(path, follow_symlinks=False)
        _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                 == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                 and (entry.st_dev, entry.st_ino) == (after.st_dev, after.st_ino)
                 and total == before.st_size, 'PHYSICS_INVALID', 'file changed while reading')
        return b''.join(pieces)
    finally:
        os.close(descriptor)


def _metadata_bytes(distribution):
    entries = [entry for entry in (distribution.files or ())
               if entry.name == 'METADATA' and entry.parent.name.endswith('.dist-info')]
    _require(len(entries) == 1, 'BUILD', 'exact distribution METADATA is unavailable')
    return _read_regular(Path(distribution.locate_file(entries[0])), 16 << 20)


def measure_installed_build(*, world_id: str, build_id: str) -> tuple[Record, list[dict]]:
    """Explicit stdlib-only audit; never imports the Genesis package."""
    try:
        distribution = importlib.metadata.distribution('genesis-world')
        _require(distribution.version == '1.4.3', 'BUILD')
        package = Path(distribution.locate_file('genesis')).resolve(strict=True)
        files = []
        for path in sorted(package.rglob('*.py')):
            relative = path.relative_to(package).as_posix()
            _require(not path.is_symlink() and len(relative.encode('utf-8')) <= 4096, 'BUILD')
            files.append(dict(path=relative, sha256=hashlib.sha256(_read_regular(path, 16 << 20)).hexdigest()))
        _require(1 <= len(files) <= 10000, 'BUILD')
        lookup = {row['path']: row['sha256'] for row in files}
        critical = [dict(path=path, sha256=lookup[path]) for path in sorted(_CRITICAL)]
        dependencies = []
        for name in _DEPENDENCIES:
            dependency = importlib.metadata.distribution(name)
            metadata = _metadata_bytes(dependency)
            dependencies.append(dict(name=name, version=dependency.version,
                                     metadata_sha256=hashlib.sha256(metadata).hexdigest()))
        metadata = _metadata_bytes(distribution)
        body = dict(distribution='genesis-world', version=distribution.version,
                    metadata_sha256=hashlib.sha256(metadata).hexdigest(),
                    python_abi=sys.implementation.cache_tag, critical_sources=critical,
                    source_tree_sha256=hashlib.sha256(_pack(files)).hexdigest(),
                    source_file_count=len(files), dependencies=dependencies,
                    adapter_source_sha256=hashlib.sha256(_read_regular(Path(__file__), 16 << 20)).hexdigest(),
                    artifact_class='genesis-runtime')
        return _record(world_id, 'provider_build', build_id, body, {}), files
    except ContractError as exc:
        if exc.code == 'BUILD':
            raise
        raise ContractError('BUILD', 'installed build validation failed') from exc
    except Exception as exc:
        raise ContractError('BUILD', 'installed build measurement failed') from exc


def _runtime():
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            try:
                import genesis as gs  # Literal, explicit, owner-controlled runtime entry.
                gs.init(backend=gs.metal, precision='32', seed=7)
                _require(gs.backend == gs.metal, 'BUILD', 'requested Metal backend unavailable')
                _RUNTIME = (os.getpid(), gs)
            except ContractError:
                raise
            except Exception as exc:
                # Never swallow AlreadyInitialized or adopt an unknown process runtime.
                raise ContractError('PHYSICS_FAILED', 'explicit Genesis initialization failed') from exc
        _require(_RUNTIME[0] == os.getpid(), 'PHYSICS_FAILED', 'fork-inherited runtime is unavailable')
        return _RUNTIME[1]


def normalize_public(value):
    """Lossless normalization of complete public model_dump(mode='python')."""
    if isinstance(value, Enum):
        return normalize_public(value.value)
    if value is None or type(value) in (bool, str, int):
        return value
    if type(value) is float:
        _require(math.isfinite(value), 'BUILD')
        return encode_f64(value)
    if type(value) in (list, tuple):
        return [normalize_public(item) for item in value]
    if type(value) is dict:
        _require(all(type(key) is str for key in value), 'BUILD')
        return {key: normalize_public(value[key]) for key in sorted(value)}
    raise ContractError('BUILD', 'unsupported public options value')


def _dump(model):
    value = normalize_public(model.model_dump(mode='python', exclude_unset=False,
                                             exclude_defaults=False, exclude_none=False, by_alias=False))
    canonical(value)
    return value


def _objects(gs, parameters):
    p = parameters
    sim = gs.options.SimOptions(dt=f64(p['dt_s']['$f64']), substeps=p['substeps'],
                                requires_grad=p['requires_grad'],
                                gravity=tuple(f64(x['$f64']) for x in p['init_gravity_m_s2']))
    rigid_values = deepcopy(p['rigid_options'])
    rigid_values['constraint_timeconst'] = f64(rigid_values.pop('constraint_timeconst_s')['$f64'])
    scene_options = gs.options.SceneOptions(sim=sim, rigid=gs.options.RigidOptions(**rigid_values))
    morphs = []
    for entity in p['entities']:
        values = dict(pos=tuple(f64(x['$f64']) for x in entity['position_m']),
                      quat=tuple(f64(x['$f64']) for x in entity['quaternion_wxyz']), fixed=entity['fixed'])
        if entity['morph'] == 'sphere':
            morph = gs.morphs.Sphere(radius=f64(entity['radius_m']['$f64']), **values)
        else:
            _require(entity['morph'] == 'box')
            morph = gs.morphs.Box(size=tuple(f64(x['$f64']) for x in entity['size_m']), **values)
        morphs.append(morph)
    m = p['material']
    material = gs.materials.Rigid(rho=f64(m['rho_kg_m3']['$f64']),
                                 friction=f64(m['friction']['$f64']), needs_coup=m['needs_coup'],
                                 gravity_compensation=f64(m['gravity_compensation']['$f64']))
    return scene_options, morphs, material


def _exports(objects):
    scene_options, morphs, material = objects
    return dict(sim_options=_dump(scene_options.sim), rigid_options=_dump(scene_options.rigid),
                dynamic_morph=_dump(morphs[0]), support_morph=_dump(morphs[1]),
                rigid_material=_dump(material))


@_logged
def measure_runtime_options(parameters: Mapping, *, approved_build: Record, options_id: str) -> Record:
    """Explicit runtime bootstrap; no Scene/build/step/checkpoint or world HEAD."""
    validate_record(approved_build)
    _require(approved_build['kind'] == 'provider_build'
             and approved_build['body']['artifact_class'] == 'genesis-runtime', 'BUILD')
    measured, _ = measure_installed_build(world_id=approved_build['world_id'], build_id=approved_build['id'])
    _require(canonical(measured) == canonical(approved_build), 'BUILD', 'owner-audited source changed')
    try:
        exports = _exports(_objects(_runtime(), deepcopy(dict(parameters))))
        body = dict(artifact_class='genesis-runtime', resolution='runtime-exported',
                    normalizer='public-model-dump.v0.2', declarations={}, exports=exports,
                    parameter_hash=hashlib.sha256(canonical(dict(parameters))).hexdigest())
        result = _record(approved_build['world_id'], 'resolved_options', options_id, body,
                         {'build': digest(approved_build)})
        after, _ = measure_installed_build(world_id=approved_build['world_id'], build_id=approved_build['id'])
        _require(canonical(after) == canonical(approved_build), 'BUILD', 'source changed during bootstrap')
        return result
    except ContractError as exc:
        if exc.code in ('BUILD', 'PHYSICS_FAILED'):
            raise
        raise ContractError('BUILD', 'complete public options validation failed') from exc
    except Exception as exc:
        raise ContractError('BUILD', 'complete public options export failed') from exc


def _serialized(function):
    @wraps(function)
    def invoke(self, *args, **kwargs):
        _require(self._lock.acquire(blocking=False), 'PHYSICS_FAILED', 'provider operation is active')
        try:
            _require(not self._closed, 'PHYSICS_FAILED', 'provider is closed')
            with runtime_logs_to_stderr():
                return function(self, *args, **kwargs)
        except ContractError as exc:
            if exc.code in ('PHYSICS_INVALID', 'PHYSICS_FAILED', 'BUILD', 'BLOB_LIMIT'):
                raise
            raise ContractError('PHYSICS_INVALID', 'candidate input/sample rejected') from exc
        except Exception as exc:
            raise ContractError('PHYSICS_FAILED', 'candidate operation failed') from exc
        finally:
            self._lock.release()
    return invoke


def influence_mm(previous: float, current: float) -> int:
    _require(type(previous) is float and type(current) is float
             and math.isfinite(previous) and math.isfinite(current))
    with localcontext() as context:
        context.prec = 2000
        context.rounding = ROUND_HALF_EVEN
        result = int(((Decimal.from_float(current) - Decimal.from_float(previous)) * Decimal(1000))
                     .to_integral_value(rounding=ROUND_HALF_EVEN))
    _require(abs(result) <= 1000)
    return result


class GenesisProvider:
    def __init__(self, config: Record, binding: Record, *, scratch: Path,
                 context: DeploymentContext, build: Record, options: Record):
        _require(type(context) is DeploymentContext and context.artifact_class == 'genesis-runtime', 'BUILD')
        _require(isinstance(scratch, Path) and scratch.is_absolute() and '..' not in scratch.parts,
                 'PHYSICS_INVALID', 'scratch must be an explicit absolute path')
        for record, kind in ((config, 'physics_config'), (binding, 'physics_binding'),
                             (build, 'provider_build'), (options, 'resolved_options')):
            validate_record(record)
            _require(record['version'] == '0.2' and record['world_id'] == context.world_id
                     and record['kind'] == kind, 'PHYSICS_INVALID')
        _require(digest(build) == context.expected_build and digest(options) == context.expected_options
                 and options['refs'] == {'build': digest(build)}
                 and config['refs'] == {'build': digest(build), 'options': digest(options)}
                 and binding['refs']['config'] == digest(config), 'BUILD')
        _require(build['body']['artifact_class'] == options['body']['artifact_class'] == 'genesis-runtime'
                 and options['body']['resolution'] == 'runtime-exported'
                 and options['body']['parameter_hash'] == hashlib.sha256(canonical(config['body']['config'])).hexdigest(), 'BUILD')
        for i, entry in enumerate(binding['body']['bindings']):
            entity = config['body']['config']['entities'][i]
            _require(entry == dict(config_entity_index=i, existence_id=entity['existence_id'],
                                   genesis_name=entity['genesis_name'], physical_id=entity['physical_id'],
                                   role='dynamic' if i == 0 else 'support'))
        self._config, self._binding, self._build, self._options = map(deepcopy, (config, binding, build, options))
        self._context, self._scratch = context, scratch
        self._parameters = deepcopy(config['body']['config'])
        self._scene = None
        self._counter = 0
        self._closed = False
        self._lock = threading.Lock()

    def _measure(self):
        measured = measure_runtime_options(self._parameters, approved_build=self._build, options_id=self._options['id'])
        _require(canonical(measured) == canonical(self._options), 'BUILD', 'runtime defaults differ from owner pins')
        return _runtime()

    def _path(self, label):
        _require(self._scratch.resolve(strict=False) == self._scratch, 'PHYSICS_INVALID', 'scratch alias is forbidden')
        self._scratch.mkdir(mode=0o700, exist_ok=True)
        _require(self._scratch.resolve(strict=True) == self._scratch and not self._scratch.is_symlink())
        _require(stat.S_IMODE(self._scratch.stat().st_mode) == 0o700, 'PHYSICS_INVALID')
        self._counter += 1
        path = self._scratch / f'{label}-{os.getpid()}-{self._counter}.gstraj'
        _require(not path.exists() and not path.is_symlink(), 'PHYSICS_INVALID', 'scratch collision')
        return path

    def _destroy_scene(self):
        scene, self._scene = self._scene, None
        if scene is not None:
            _require(_RUNTIME is not None and _RUNTIME[0] == os.getpid(), 'PHYSICS_FAILED')
            scene.destroy()

    def _scene_identity(self):
        scene = self._scene
        _require(tuple(scene.entity_names) == tuple(e['genesis_name'] for e in self._parameters['entities'])
                 and len(scene.entities) == 2)
        entities = [scene.get_entity(name=e['genesis_name']) for e in self._parameters['entities']]
        _require(not entities[0].base_link.is_fixed and entities[1].base_link.is_fixed)
        expected = self._options['body']['exports']
        actual = dict(sim_options=_dump(scene.options.sim), rigid_options=_dump(scene.options.rigid),
                      dynamic_morph=_dump(entities[0].morph), support_morph=_dump(entities[1].morph),
                      rigid_material=_dump(entities[0].material))
        _require(actual == expected and _dump(entities[1].material) == expected['rigid_material'], 'BUILD',
                 'loaded scene options/geometry/material differ from owner pins')
        return entities

    @staticmethod
    def _vector(tensor, size):
        values = tensor.detach().cpu().tolist()
        _require(type(values) is list and len(values) == size
                 and all(type(v) is float and math.isfinite(v) for v in values))
        return [encode_f64(v) for v in values]

    def _sample(self):
        entities = self._scene_identity()
        bodies = []
        for entity, declaration in zip(entities, self._parameters['entities']):
            mass_values = entity.get_links_mass().detach().cpu().tolist()
            _require(type(mass_values) is list and len(mass_values) == 1
                     and type(mass_values[0]) is float and math.isfinite(mass_values[0]))
            mass = mass_values[0]
            if declaration['fixed']:
                _require(encode_f64(mass)['$f64'] == '0000000000000000', 'PHYSICS_INVALID',
                         'fixed support must report its actual zero inertia sentinel')
            else:
                expected = (4.0 / 3.0) * math.pi * f64(declaration['radius_m']['$f64']) ** 3 * f64(self._parameters['material']['rho_kg_m3']['$f64'])
                _require(mass > 0 and abs(mass - expected) <= max(1e-7, 1e-6 * abs(expected)),
                         'PHYSICS_INVALID', 'dynamic analytic mass mismatch')
            bodies.append(dict(physical_id=declaration['physical_id'],
                               position_m=self._vector(entity.get_pos(relative=True), 3),
                               quaternion_wxyz=self._vector(entity.get_quat(relative=True), 4),
                               linear_velocity_m_s=self._vector(entity.get_vel(relative=True), 3),
                               angular_velocity_rad_s=self._vector(entity.get_ang(), 3), mass_kg=encode_f64(mass)))
        data = entities[0].get_contacts(with_entity=entities[1], is_padded=False)
        _require('geom_a' in data and len(data['geom_a']) <= 32)
        contacts = []
        arrays = {key: data[key].detach().cpu().tolist() for key in ('geom_a', 'geom_b', 'position', 'force_a', 'force_b')}
        for i, a in enumerate(arrays['geom_a']):
            b = arrays['geom_b'][i]
            if entities[0].geom_start <= a < entities[0].geom_end and entities[1].geom_start <= b < entities[1].geom_end:
                force = arrays['force_a'][i]
            else:
                _require(entities[1].geom_start <= a < entities[1].geom_end and entities[0].geom_start <= b < entities[0].geom_end)
                force = arrays['force_b'][i]
            def encoded(values):
                _require(type(values) is list and len(values) == 3
                         and all(type(v) is float and math.isfinite(v) for v in values))
                return [encode_f64(v) for v in values]
            contacts.append(dict(pair=['body-dynamic', 'body-support'], position_m=encoded(arrays['position'][i]),
                                 force_on_dynamic_n=encoded(force)))
        contacts.sort(key=lambda c: (c['pair'], [x['$f64'] for x in c['position_m']],
                                     [x['$f64'] for x in c['force_on_dynamic_n']]))
        sample = dict(artifact_class='genesis-runtime', frame_id=self._parameters['frame'],
                      solver_precision='32', bodies=bodies, contacts=contacts)
        # The shared validator applies all physical bounds, including E7 fixed-mass semantics.
        _record(self._context.world_id, 'physics_sample', 'sample-validation', sample,
                {'config': digest(self._config), 'binding': digest(self._binding)})
        support = bodies[1]
        _require(max(abs(f64(a['$f64']) - f64(b['$f64'])) for a, b in
                     zip(support['position_m'], self._parameters['entities'][1]['position_m'])) <= 1e-6)
        return sample

    def _checkpoint_family(self, sample, *, ids, case_id, physical_steps):
        path = self._path('save')
        self._scene.save_checkpoint(path)
        payload = _read_regular(path, _MAX_RAW)
        _require(bool(payload), 'PHYSICS_FAILED', 'empty checkpoint')
        descriptor_fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            os.fsync(descriptor_fd)
        finally:
            os.close(descriptor_fd)
        h = hashlib.sha256(payload).hexdigest()
        refs = {'config': digest(self._config), 'binding': digest(self._binding)}
        sample_record = _record(self._context.world_id, 'physics_sample', ids.sample, sample, refs)
        descriptor = _record(self._context.world_id, 'checkpoint_descriptor', ids.checkpoint_descriptor,
                             dict(artifact_class='genesis-runtime', payload_sha256=h, byte_count=len(payload),
                                  format='genesis-gstraj', genesis_version='1.4.3',
                                  media_type='application/x-genesis-gstraj;version=1.4.3'),
                             {**refs, 'build': digest(self._build)})
        snapshot = _record(self._context.world_id, 'physics_snapshot', ids.snapshot,
                           dict(case_id=case_id, physical_step_count=physical_steps),
                           {**refs, 'sample': digest(sample_record), 'checkpoint': digest(descriptor)})
        return (sample_record, descriptor, snapshot), BlobWrite(h, payload, descriptor['body']['media_type'])

    def _restore(self, snapshot, records, read_blob):
        validate_record(snapshot)
        _require(snapshot['kind'] == 'physics_snapshot' and snapshot['world_id'] == self._context.world_id
                 and snapshot['refs']['config'] == digest(self._config)
                 and snapshot['refs']['binding'] == digest(self._binding))
        for record in (self._config, self._binding, self._build, self._options, snapshot):
            _require(digest(record) in records and canonical(records[digest(record)]) == canonical(record))
        expected = records[snapshot['refs']['sample']]
        descriptor = records[snapshot['refs']['checkpoint']]
        validate_record(expected); validate_record(descriptor)
        _require(expected['kind'] == 'physics_sample' and descriptor['kind'] == 'checkpoint_descriptor'
                 and expected['world_id'] == descriptor['world_id'] == self._context.world_id
                 and expected['body']['artifact_class'] == 'genesis-runtime'
                 and expected['body']['frame_id'] == self._parameters['frame']
                 and expected['body']['solver_precision'] == '32')
        refs = {'config': digest(self._config), 'binding': digest(self._binding)}
        _require(expected['refs'] == refs and descriptor['refs'] == {**refs, 'build': digest(self._build)}
                 and descriptor['body']['artifact_class'] == 'genesis-runtime'
                 and descriptor['body']['format'] == 'genesis-gstraj'
                 and descriptor['body']['media_type'] == 'application/x-genesis-gstraj;version=1.4.3')
        _require(digest(expected) == snapshot['refs']['sample'] and digest(descriptor) == snapshot['refs']['checkpoint'])
        payload = read_blob(descriptor['body']['payload_sha256'])
        _require(type(payload) is bytes and 0 < len(payload) <= _MAX_RAW, 'BLOB_LIMIT')
        _require(len(payload) == descriptor['body']['byte_count']
                 and hashlib.sha256(payload).hexdigest() == descriptor['body']['payload_sha256'])
        path = self._path('load')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            offset = 0
            while offset < len(payload):
                count = os.write(fd, payload[offset:]); _require(count > 0, 'PHYSICS_FAILED')
                offset += count
            os.fsync(fd)
        finally:
            os.close(fd)
        _require(_read_regular(path, _MAX_RAW) == payload, 'PHYSICS_INVALID', 'scratch checkpoint changed')
        self._destroy_scene()
        self._scene = _runtime().Scene.load_checkpoint(path, show_viewer=False)
        actual = self._sample()
        _require(canonical(actual) == canonical(expected['body']), 'PHYSICS_INVALID', 'checkpoint sample differs from retained bits')
        return actual

    @_serialized
    def initialize(self, *, ids: PhysicsInitialIds) -> PhysicsInitialDraft:
        _require(type(ids) is PhysicsInitialIds)
        gs = self._measure()
        self._destroy_scene()
        scene_options, morphs, material = _objects(gs, self._parameters)
        self._scene = gs.Scene(show_viewer=False, options=scene_options)
        for declaration, morph in zip(self._parameters['entities'], morphs):
            self._scene.add_entity(morph=morph, material=material, name=declaration['genesis_name'])
        self._scene.build()
        records, blob = self._checkpoint_family(self._sample(), ids=ids, case_id='initial', physical_steps=0)
        return PhysicsInitialDraft(records, digest(records[-1]), blob)

    @_serialized
    def restore(self, snapshot: Record, *, records: Mapping[str, Record], read_blob: Callable) -> Mapping:
        self._measure()
        _require(isinstance(records, Mapping) and callable(read_blob))
        return deepcopy(self._restore(deepcopy(snapshot), deepcopy(dict(records)), read_blob))

    def _advance(self, snapshot, case_id, records, read_blob, ids):
        _require(case_id in ('weak', 'strong') and type(ids) in (PhysicsInitialIds, PhysicsIds))
        validate_record(snapshot)
        steps = snapshot['body']['physical_step_count'] + 8
        _require(steps <= 256)
        previous = self._restore(snapshot, records, read_blob)
        case = next(c for c in self._parameters['cases'] if c['case_id'] == case_id)
        self._scene.rigid_solver.set_gravity(tuple(f64(v['$f64']) for v in case['gravity_m_s2']))
        for _ in range(8):
            self._scene.step(update_visualizer=False, refresh_visualizer=False)
        sample = self._sample()
        development = influence_mm(f64(previous['bodies'][0]['position_m'][2]['$f64']),
                                   f64(sample['bodies'][0]['position_m'][2]['$f64']))
        family, blob = self._checkpoint_family(sample, ids=ids, case_id=case_id, physical_steps=steps)
        return family, blob, development

    @_serialized
    def advance_isolated(self, snapshot: Record, case_id: str, *, records: Mapping,
                         read_blob: Callable, ids: PhysicsInitialIds) -> tuple:
        """Probe-only physical family/D; no State, Command, A, manifest or HEAD."""
        self._measure()
        _require(type(ids) is PhysicsInitialIds)
        return self._advance(deepcopy(snapshot), case_id, deepcopy(dict(records)), read_blob, ids)

    @_serialized
    def propose(self, prior_state: Record, command: Record, intent: Record, *,
                records: Mapping[str, Record], read_blob: Callable, ids: PhysicsIds) -> PhysicsDraft:
        for record, kind in ((prior_state, 'state'), (command, 'command'), (intent, 'intent')):
            validate_record(record)
            _require(record['version'] == '0.2' and record['world_id'] == self._context.world_id
                     and record['kind'] == kind)
        _require(type(ids) is PhysicsIds and intent['body']['action'] == 'physics_step'
                 and intent['body']['tick_delta'] == 1 and intent['refs'] == {
                     'config': digest(self._config), 'binding': digest(self._binding)}
                 and command['refs']['intent'] == digest(intent)
                 and intent['body']['expected_revision'] == prior_state['body']['revision']
                 and intent['body']['random_cursor'] == prior_state['body']['random_cursor'])
        _require(isinstance(records, Mapping) and callable(read_blob)
                 and digest(prior_state) in records and records[digest(prior_state)] == prior_state)
        world = records[prior_state['refs']['world']]
        validate_record(world)
        _require(world['kind'] == 'world_manifest' and world['world_id'] == self._context.world_id
                 and world['body']['artifact_class'] == 'genesis-runtime')
        known = {(r['kind'], r['id']) for r in records.values()}
        for kind, identifier in (('candidate', ids.candidate), ('physics_sample', ids.sample),
                                 ('physics_snapshot', ids.snapshot), ('checkpoint_descriptor', ids.checkpoint_descriptor)):
            _require((kind, identifier) not in known)
        snapshot = records[prior_state['refs']['snapshot']]
        _require(prior_state['body']['tick'] < 32 and prior_state['body']['revision'] < (1 << 53) - 1
                 and prior_state['body']['random_cursor'] == prior_state['body']['tick']
                 and snapshot['body']['physical_step_count'] == prior_state['body']['tick'] * 8
                 and intent['body']['budget'] <= prior_state['body']['budget'])
        self._measure()
        family, blob, development = self._advance(snapshot,
                                                  intent['body']['case_id'], records, read_blob, ids)
        candidate = _record(self._context.world_id, 'candidate', ids.candidate,
                            dict(adapter_kind='genesis', physics_profile='genesis-rigid-support.v0.1',
                                 tick=prior_state['body']['tick'] + 1, revision=prior_state['body']['revision'] + 1,
                                 influence_mm=development),
                            {'command': digest(command), 'prior_state': digest(prior_state),
                             'snapshot': digest(family[-1])})
        return PhysicsDraft(family + (candidate,), digest(candidate), digest(family[-1]), blob)

    @_serialized
    def calibrate_pose(self, snapshot: Record, *, records: Mapping, read_blob: Callable) -> dict:
        """Approved zero-step API calibration; restore pristine checkpoint on exit."""
        self._measure()
        pristine = self._restore(snapshot, records, read_blob)
        entity = self._scene.get_entity(name=self._parameters['entities'][0]['genesis_name'])
        position = (0.125, -0.25, 1.5)
        quaternion = tuple(v / 11.0 for v in (1, 2, 4, 10))
        try:
            entity.set_pos(position, zero_velocity=True, relative=True, skip_forward=False)
            entity.set_quat(quaternion, zero_velocity=True, relative=True, skip_forward=False)
            sample = self._sample(); body = sample['bodies'][0]
            p = [f64(v['$f64']) for v in body['position_m']]
            q = [f64(v['$f64']) for v in body['quaternion_wxyz']]
            _require(max(abs(a-b) for a,b in zip(p,position)) <= 1e-6)
            _require(min(max(abs(a-b) for a,b in zip(q,quaternion)),
                         max(abs(a+b) for a,b in zip(q,quaternion))) <= 2e-6)
            _require(abs(sum(v*v for v in q)-1.0) <= 1e-6)
            _require(all(abs(f64(v['$f64'])) <= 1e-6 for key in
                         ('linear_velocity_m_s','angular_velocity_rad_s') for v in body[key]))
            _require(sample['bodies'][1] == pristine['bodies'][1])
            return dict(scope='zero-step-asymmetric-pose-roundtrip-not-world-velocity-or-ue-frame', sample=sample)
        finally:
            restored = self._restore(snapshot, records, read_blob)
            _require(restored == pristine)

    def close(self) -> None:
        _require(self._lock.acquire(blocking=False), 'PHYSICS_FAILED', 'provider operation is active')
        try:
            if not self._closed:
                self._closed = True
                with runtime_logs_to_stderr():
                    self._destroy_scene()
        finally:
            self._lock.release()
