"""I20B bounded CPU contract check. Never loads UE, authority, keys or a solver.

The accompanying profile schema describes a source-input proposal with unresolved
UE import metadata. Success is not a loader/asset-license/visual/runtime grant.
Dependency: jsonschema==4.23.0 in an isolated test environment.
"""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import tempfile
import unittest
from jsonschema import Draft202012Validator

FIXTURES = Path(__file__).resolve().parents[2]/'fixtures/universe_realistic_presentation_profile_v0_1'
PROFILE_FORMAT = 'edgeworld.universe.realistic-presentation-profile.v0.1'
VIEW_FORMAT = 'edgeworld.universe.realistic-view-binding.v0.1'


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def unique(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def finite_float(token):
    value = float(token)
    require(math.isfinite(value), 'nonfinite JSON number')
    return value


def require_finite_numbers(value):
    """Also guard programmatic API dictionaries, which bypass JSON parsing."""
    if isinstance(value, float):
        require(math.isfinite(value), 'nonfinite contract number')
    elif isinstance(value, dict):
        for item in value.values():require_finite_numbers(item)
    elif isinstance(value, (list, tuple)):
        for item in value:require_finite_numbers(item)


def load(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_float=finite_float,
                      parse_constant=lambda _: (_ for _ in ()).throw(ContractError('nonfinite JSON')))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def schema_check(value, name):
    require_finite_numbers(value)
    schema = load((FIXTURES/name).read_bytes())
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(value))
    require(not errors, 'JSON schema: '+(errors[0].message if errors else ''))


def public_bytes(root, relative):
    root = Path(root)
    require(root.is_absolute() and root == root.resolve() and root.is_dir(), 'canonical file root')
    rel = Path(relative)
    require(not rel.is_absolute() and str(rel) == relative and relative and
            all(x not in ('.','..') for x in rel.parts), 'relative path escape')
    target = root/rel
    for path in (target, *target.parents):
        if path == root.parent:
            break
        require(not path.is_symlink(), 'symlink asset/reference')
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= 256*1024**2, 'bounded regular input')
        raw = stream.read(256*1024**2+1)
        after = os.fstat(stream.fileno())
    current = target.stat()
    sig = lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    require(sig(before) == sig(after) == sig(current) and len(raw) == before.st_size,
            'input changed during read')
    return raw


def validate_profile(profile_path, *, file_root, expected_profile_sha256, expected_authority):
    """Exact external pin, structure, real file bytes and semantic relationships."""
    require_finite_numbers(expected_authority)
    path = Path(profile_path)
    require(path.is_absolute() and path == path.resolve() and not path.is_symlink(), 'canonical profile path')
    raw = public_bytes(path.parent, path.name)
    require(sha(raw) == expected_profile_sha256, 'independent profile SHA mismatch')
    p = load(raw)
    schema_check(p, 'profile.schema.json')
    authority = {k:v for k,v in expected_authority.items() if k != 'places'}
    require(p['authority'] == authority, 'authority context mismatch')
    require(p['target']['platform']=='Mac' and p['target']['rhi']=='Metal', 'target platform/RHI mismatch')
    files = {}; paths = set(); checked = {}; total = 0
    for spec in p['files']:
        require(spec['file_id'] not in files and spec['path'] not in paths, 'duplicate file identity/path')
        require(type(spec['byte_count']) is int, 'exact integer byte count')
        data = public_bytes(file_root, spec['path'])
        require(len(data)==spec['byte_count'] and sha(data)==spec['sha256'], 'source file bytes/SHA mismatch')
        files[spec['file_id']] = spec; paths.add(spec['path']); checked[spec['path']] = len(data)
        license_ref = spec['license_ref']
        license_data = public_bytes(file_root, license_ref['path'])
        require(sha(license_data)==license_ref['sha256'], 'license-reference SHA mismatch')
        checked[license_ref['path']] = len(license_data)
        if p['evidence_class']=='synthetic-contract-only':
            require(spec['source_uri'].startswith('urn:synthetic:'), 'synthetic fixture source must be explicit')
    require(len(checked)<=64 and sum(checked.values())<=256*1024**2, 'source-input bound exceeded')
    assets = {}; objects = set(); imports = set()
    for asset in p['assets']:
        require(asset['asset_id'] not in assets and asset['object_path'] not in objects, 'duplicate asset identity/object')
        require(set(asset['source_file_ids']) <= set(files), 'missing source file reference')
        native=asset['native_import']; imports.add(native['status'])
        if p['evidence_class'] in ('synthetic-contract-only','source-inputs-pending-native-import'):
            require(native['status']=='unresolved', 'pending/synthetic input cannot claim native import')
        else:
            require(native['status']=='native-observed', 'mixed/incomplete native-import proposal')
            evidence=public_bytes(file_root,native['evidence_ref']['path'])
            require(sha(evidence)==native['evidence_ref']['sha256'], 'native-import evidence SHA mismatch')
            checked[native['evidence_ref']['path']]=len(evidence)
            if asset['kind']=='static_mesh':
                bounds=native['bounds_cm']
                require(type(bounds) is list and all(bounds[i]<bounds[i+3] for i in range(3)) and
                        type(native['source_unit_cm']) in (int,float) and native['source_unit_cm']>0,
                        'native mesh metadata invalid')
            else:
                require(all(native[k] is None for k in ('source_unit_cm','pivot_cm','bounds_cm')) and
                        native['material_slots']==[], 'material cannot claim mesh dimensions/slots')
        assets[asset['asset_id']] = asset; objects.add(asset['object_path'])
    active = set(); done = set()
    def visit(identity):
        require(identity in assets and identity not in active, 'missing/cyclic asset dependency')
        if identity in done:return
        active.add(identity)
        for dependency in assets[identity]['dependencies']:visit(dependency)
        active.remove(identity);done.add(identity)
    for identity in assets:visit(identity)
    recipes=set()
    for recipe in p['material_recipes']:
        mid=recipe['material_asset_id']
        require(mid not in recipes and mid in assets and assets[mid]['kind']=='material', 'wrong/duplicate material recipe')
        recipes.add(mid); roles=set()
        for tex in recipe['textures']:
            require(tex['role'] not in roles and tex['source_file_id'] in files and
                    tex['source_file_id'] in assets[mid]['source_file_ids'], 'missing/duplicate/unclaimed texture source')
            roles.add(tex['role'])
            if tex['role']=='BaseColor':require(tex['srgb'] is True and tex['normal_basis'] is None, 'basecolor color-space mismatch')
            else:require(tex['srgb'] is False, 'data texture must be linear')
            if tex['role']=='Normal':require(tex['channels']=='RGB' and tex['normal_basis'] in ('DirectX','OpenGL'), 'normal convention missing')
            else:require(tex['normal_basis'] is None, 'non-normal texture has normal convention')
        require('BaseColor' in roles, 'basecolor source required')
        if recipe['blend_mode']=='Masked':
            require('OpacityMask' in roles and type(recipe['mask_cutoff']) in (int,float), 'masked recipe missing coverage/cutoff')
        else:require('OpacityMask' not in roles and recipe['mask_cutoff'] is None, 'opaque recipe cannot silently carry unused mask')
    require(recipes=={a['asset_id'] for a in assets.values() if a['kind']=='material'}, 'unclaimed material recipe')
    used_files = {f for asset in assets.values() for f in asset['source_file_ids']}
    require(used_files == set(files), 'unclaimed source files')
    place = p['region']['place_id']; places = expected_authority['places']
    require(place in places, 'unknown source place')
    box = p['region']['bounds_xy_cm']; outer = places[place]['bounds_xy_cm']
    require(all(type(x) is int for x in box) and outer[0]<=box[0]<box[2]<=outer[2] and
            outer[1]<=box[1]<box[3]<=outer[3], 'region outside verified initial rectangular place')
    bindings = {}; used_assets = set()
    for binding in p['bindings']:
        bid = binding['binding_id']; pid = binding['place_id']
        require(bid not in bindings and pid == place and pid in places and
                binding['place_kind'] == places[pid]['kind'], 'duplicate/wrong place binding')
        role = binding['role']; mesh = binding['mesh_asset_id']
        if binding['geometry_source']=='declared-mesh':
            require(mesh in assets and assets[mesh]['kind']=='static_mesh', 'mesh role/class mismatch')
            used_assets.add(mesh)
        else:
            require(mesh is None and role in ('ground','water'), 'procedural geometry role mismatch')
        if role in ('vegetation','rock'):
            require(binding['geometry_source']=='declared-mesh', 'natural instance needs declared full mesh')
        if role=='water':
            require(binding['place_kind'] in ('river_marsh','ocean'), 'water role is outside initial slice mapping')
        slots = set()
        for item in binding['material_bindings']:
            material = item['material_asset_id']
            require(item['slot_name'] not in slots and material in assets and assets[material]['kind']=='material',
                    'duplicate material slot or wrong material kind')
            slots.add(item['slot_name']);used_assets.add(material)
        if mesh is not None and assets[mesh]['native_import']['status']=='native-observed':
            require(slots==set(assets[mesh]['native_import']['material_slots']), 'declared/native slot coverage mismatch')
        bindings[bid] = binding
    for identity in tuple(used_assets):
        def include(name):
            for dep in assets[name]['dependencies']:
                if dep not in used_assets:used_assets.add(dep);include(dep)
        include(identity)
    require(used_assets == set(assets), 'unclaimed render assets')
    instances = set(); bound = set()
    for instance in p['derived_recipe']['instances']:
        identity = instance['instance_id']; bid = instance['binding_id']
        require(identity not in instances and bid in bindings, 'duplicate instance or missing binding')
        require(all(type(n) is int for field in ('position_cm','rotation_mdeg','scale_ppm') for n in instance[field]),
                'exact integer transform components')
        x,y,z = instance['position_cm']
        require(box[0]<=x<=box[2] and box[1]<=y<=box[3], 'derived instance outside fixed slice')
        require(z==places[place]['elevation_cm'], 'initial slice placement must use verified elevation')
        instances.add(identity);bound.add(bid)
    require(bound == set(bindings), 'unclaimed binding')
    require(len(checked)<=64 and sum(checked.values())<=256*1024**2, 'source/import input bound exceeded')
    return dict(status='source_contract_consistent_requires_native_review', profile_sha256=sha(raw),
                checked_files=len(checked), checked_bytes=sum(checked.values()),
                assets=len(assets), instances=len(instances), native_import_status=','.join(sorted(imports)),
                runtime_authenticity_verified=False, license_authenticity_verified=False,
                visual_gate='not_run', authority_written=False)


def validate_view_binding(binding, *, profile_sha256, expected_observation, expected_renderer_build_sha256):
    """Check a candidate presented binding, not an actual HUD/Actor transaction."""
    require_finite_numbers(expected_observation)
    schema_check(binding, 'view-binding.schema.json')
    require(binding['profile_sha256']==profile_sha256, 'view/profile mismatch')
    require(binding['renderer_build_sha256']==expected_renderer_build_sha256, 'independent renderer identity mismatch')
    for key,value in expected_observation.items():
        require(binding.get(key)==value and type(binding.get(key)) is type(value), 'view/source mismatch: '+key)
    require(binding['watermark']==binding['revision'], 'view watermark mismatch')
    return dict(status='binding_consistent_requires_native_review', hud_atomicity_verified=False,
                runtime_authenticity_verified=False, authority_written=False)


class ContractChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='edgeworld-i20b-')
        self.root = Path(self.tmp.name).resolve()
        self.p = load((FIXTURES/'positive-profile.json').read_bytes())
        self.expected = load((FIXTURES/'expected-synthetic.json').read_bytes())
        for name,data in load((FIXTURES/'synthetic-payloads.json').read_bytes()).items():
            (self.root/name).write_text(data)
        self.path = self.root/'profile.json'
    def tearDown(self):self.tmp.cleanup()
    def write(self, profile=None):
        raw = (json.dumps(self.p if profile is None else profile,sort_keys=True,indent=2)+'\n').encode()
        self.path.write_bytes(raw);return sha(raw)
    def check(self, profile=None, pin=None, authority=None):
        actual = self.write(profile)
        return validate_profile(self.path,file_root=self.root,expected_profile_sha256=pin or actual,
                                expected_authority=authority or self.expected['authority'])
    def bad(self, change):
        p=deepcopy(self.p);change(p)
        with self.assertRaises((ContractError,OSError)):self.check(p)
    def binding(self):
        return dict(format=VIEW_FORMAT,profile_sha256=self.write(),presentation_mode='realistic-readonly-sidecar.v0.1',
                    renderer_build_sha256=self.expected['renderer_build_sha256'],**self.expected['observation'])
    def test_positive_real_temp_bytes_and_binding_are_only_consistency(self):
        r=self.check();self.assertEqual((r['checked_files'],r['assets'],r['instances']),(4,3,3))
        self.assertFalse(r['runtime_authenticity_verified']);self.assertFalse(r['license_authenticity_verified'])
        b=self.binding();self.assertFalse(validate_view_binding(b,profile_sha256=b['profile_sha256'],
            expected_observation=self.expected['observation'],
            expected_renderer_build_sha256=self.expected['renderer_build_sha256'])['hud_atomicity_verified'])
    def test_external_profile_pin_checks_original_bytes(self):
        pin=self.write();self.path.write_bytes(self.path.read_bytes()+b' ')
        with self.assertRaisesRegex(ContractError,'independent profile SHA'):
            validate_profile(self.path,file_root=self.root,expected_profile_sha256=pin,expected_authority=self.expected['authority'])
    def test_missing_and_corrupt_source_files(self):
        target=self.root/'fern-source.fixture';target.unlink()
        with self.assertRaises(OSError):self.check()
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ContractError,'source file'):self.check()
    def test_license_ref_is_hashed_but_not_license_authorization(self):
        (self.root/'license.fixture').write_bytes(b'wrong source proof')
        with self.assertRaisesRegex(ContractError,'license-reference'):self.check()
    def test_path_escape_and_symlink_are_rejected(self):
        self.bad(lambda p:p['files'][0].update(path='../outside'))
        target=self.root/'fern-source.fixture';target.unlink();target.symlink_to(self.root/'rock-source.fixture')
        with self.assertRaisesRegex(ContractError,'symlink'):self.check()
    def test_dependency_missing_cycle_and_duplicate_identity(self):
        self.bad(lambda p:p['assets'][0].update(dependencies=['absent-material']))
        self.bad(lambda p:p['assets'][2].update(dependencies=['fern-mesh']))
        self.bad(lambda p:p['assets'][1].update(asset_id='fern-mesh'))
    def test_role_material_slot_and_place_are_crosschecked(self):
        self.bad(lambda p:p['bindings'][0].update(mesh_asset_id='surface-material'))
        self.bad(lambda p:p['bindings'][0]['material_bindings'][0].update(material_asset_id='fern-mesh'))
        self.bad(lambda p:p['bindings'][0]['material_bindings'].append(deepcopy(p['bindings'][0]['material_bindings'][0])))
        self.bad(lambda p:p['bindings'][0].update(place_kind='ocean'))
        self.bad(lambda p:p['bindings'][0].update(role='water'))
    def test_instance_identity_region_elevation_and_numeric_types(self):
        self.bad(lambda p:p['derived_recipe']['instances'].append(deepcopy(p['derived_recipe']['instances'][0])))
        self.bad(lambda p:p['derived_recipe']['instances'][0].update(position_cm=[0,0,350]))
        self.bad(lambda p:p['derived_recipe']['instances'][0].update(position_cm=[31000,31000,0]))
        self.bad(lambda p:p['derived_recipe']['instances'][0].update(scale_ppm=[1000000.0,1000000,1000000]))
    def test_extra_fields_legacy_version_and_fallback_fail_structure(self):
        self.bad(lambda p:p.update(fallback='basicshapes'))
        self.bad(lambda p:p.update(format='universe-i15-prepared.v1'))
        self.bad(lambda p:p.update(authority_write=True))
    def test_unknown_import_metadata_is_not_minted_as_reviewed(self):
        self.bad(lambda p:p['assets'][0]['native_import'].update(status='native-reviewed',bounds_cm=[1,1,1]))
    def test_mask_coverage_texture_source_and_color_conventions(self):
        self.bad(lambda p:p['material_recipes'][0].update(blend_mode='Masked',mask_cutoff=0.5))
        self.bad(lambda p:p['material_recipes'][0]['textures'][0].update(source_file_id='missing-alpha'))
        self.bad(lambda p:p['material_recipes'][0]['textures'][0].update(srgb=False))
        self.bad(lambda p:p['material_recipes'][0]['textures'].append(dict(role='Normal',source_file_id='pbr-source',channels='RGB',srgb=False,normal_basis=None)))
    def test_authority_context_changed(self):
        for field in ('world_id','expected_build','expected_options','authority_assets','unit_transform'):
            self.bad(lambda p,f=field:p['authority'].update({f:'other-world' if f=='world_id' else 'a'*64}))
    def test_view_cross_time_world_transform_profile_and_generation(self):
        for field,bad in [('manifest','a'*64),('tick',0),('revision',1),('watermark',1),('unit_transform','a'*64),
                          ('world_id','other-world'),('profile_sha256','a'*64),('view_generation',2),
                          ('renderer_build_sha256','a'*64),('authority_projection_version','realistic-proxy')]:
            b=self.binding();b[field]=bad
            with self.assertRaises(ContractError):
                validate_view_binding(b,profile_sha256=self.write(),expected_observation=self.expected['observation'],
                                      expected_renderer_build_sha256=self.expected['renderer_build_sha256'])
    def test_numeric_overflow_and_programmatic_nonfinite_are_rejected(self):
        # A fully consistent synthetic native proposal must still reject finite-
        # JSON number syntax that overflows Python's float, in each dimension.
        proposal=deepcopy(self.p);proposal['evidence_class']='native-observed-proposal'
        evidence=b'synthetic native evidence; no real import performed\n'
        (self.root/'native.fixture').write_bytes(evidence)
        for asset in proposal['assets']:
            mesh=asset['kind']=='static_mesh'
            asset['native_import']=dict(status='native-observed',source_unit_cm=1.0 if mesh else None,
                pivot_cm=[0,0,0] if mesh else None,bounds_cm=[-1,-1,-1,1,1,1] if mesh else None,
                material_slots=['surface'] if mesh else [],
                evidence_ref=dict(path='native.fixture',sha256=sha(evidence)))
        self.assertFalse(self.check(proposal)['runtime_authenticity_verified'])
        for field,index in [('source_unit_cm',None),('pivot_cm',2),('bounds_cm',3)]:
            with self.subTest(field=field):
                bad=deepcopy(proposal);native=bad['assets'][0]['native_import']
                if index is None:native[field]='OVERFLOW'
                else:native[field][index]='OVERFLOW'
                raw=json.dumps(bad).encode().replace(b'"OVERFLOW"',b'1e999')
                self.path.write_bytes(raw)
                with self.assertRaisesRegex(ContractError,'nonfinite JSON number'):
                    validate_profile(self.path,file_root=self.root,expected_profile_sha256=sha(raw),
                                     expected_authority=self.expected['authority'])
        for number in (float('inf'),float('-inf'),float('nan')):
            with self.subTest(programmatic=repr(number)):
                binding=self.binding();binding['tick']=number
                with self.assertRaisesRegex(ContractError,'nonfinite contract number'):
                    validate_view_binding(binding,profile_sha256=self.write(),
                        expected_observation=self.expected['observation'],
                        expected_renderer_build_sha256=self.expected['renderer_build_sha256'])
                observation=deepcopy(self.expected['observation']);observation['tick']=number
                with self.assertRaisesRegex(ContractError,'nonfinite contract number'):
                    validate_view_binding(self.binding(),profile_sha256=self.write(),
                        expected_observation=observation,
                        expected_renderer_build_sha256=self.expected['renderer_build_sha256'])
                authority=deepcopy(self.expected['authority'])
                authority['places']['forest-1']['elevation_cm']=number
                with self.assertRaisesRegex(ContractError,'nonfinite contract number'):
                    self.check(authority=authority)
    def test_duplicate_json_keys_are_rejected(self):
        raw=self.path.read_bytes() if self.path.exists() else b'{}'
        self.path.write_bytes(b'{"format":"one","format":"two"}')
        with self.assertRaisesRegex(ContractError,'duplicate JSON'):
            validate_profile(self.path,file_root=self.root,expected_profile_sha256=sha(self.path.read_bytes()),
                             expected_authority=self.expected['authority'])


if __name__=='__main__':
    unittest.main(verbosity=2)
