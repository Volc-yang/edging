"""Pure assembly of the approved six-place technical universe. No solver or Store I/O."""
from __future__ import annotations
from dataclasses import dataclass
import copy
from .codec import ContractError, DOMAIN, canonical, digest
from .records import validate_record, validate_closure

# Authored v0.2 geography/physics literals, never runtime measurements.
_STATIC = [('physics-config',
  'physics_config',
  {'config': {'authority_version': '0.2',
              'backend': 'metal',
              'cases': [{'case_id': 'weak',
                         'gravity_m_s2': [{'$f64': '0000000000000000'},
                                          {'$f64': '0000000000000000'},
                                          {'$f64': 'c000000000000000'}]},
                        {'case_id': 'strong',
                         'gravity_m_s2': [{'$f64': '0000000000000000'},
                                          {'$f64': '0000000000000000'},
                                          {'$f64': 'c0239eb851eb851f'}]}],
              'dt_s': {'$f64': '3f847ae147ae147b'},
              'entities': [{'existence_id': 'existence-dynamic',
                            'fixed': False,
                            'genesis_name': 'i7-dynamic',
                            'morph': 'sphere',
                            'physical_id': 'body-dynamic',
                            'position_m': [{'$f64': '0000000000000000'},
                                           {'$f64': '0000000000000000'},
                                           {'$f64': '3ff0000000000000'}],
                            'quaternion_wxyz': [{'$f64': '3ff0000000000000'},
                                                {'$f64': '0000000000000000'},
                                                {'$f64': '0000000000000000'},
                                                {'$f64': '0000000000000000'}],
                            'radius_m': {'$f64': '3fb999999999999a'},
                            'size_m': None},
                           {'existence_id': 'existence-support',
                            'fixed': True,
                            'genesis_name': 'i7-support',
                            'morph': 'box',
                            'physical_id': 'body-support',
                            'position_m': [{'$f64': '0000000000000000'},
                                           {'$f64': '0000000000000000'},
                                           {'$f64': 'bfb999999999999a'}],
                            'quaternion_wxyz': [{'$f64': '3ff0000000000000'},
                                                {'$f64': '0000000000000000'},
                                                {'$f64': '0000000000000000'},
                                                {'$f64': '0000000000000000'}],
                            'radius_m': None,
                            'size_m': [{'$f64': '4010000000000000'},
                                       {'$f64': '4010000000000000'},
                                       {'$f64': '3fc999999999999a'}]}],
              'frame': 'genesis-world-si-zup.v0.1',
              'genesis_version': '1.4.3',
              'horizon_advances': 32,
              'init_gravity_m_s2': [{'$f64': '0000000000000000'},
                                    {'$f64': '0000000000000000'},
                                    {'$f64': 'c000000000000000'}],
              'limits': {'angular_velocity_abs_rad_s': {'$f64': '4059000000000000'},
                         'checkpoint_bytes_max': 8388608,
                         'contact_force_abs_n': {'$f64': '412e848000000000'},
                         'contacts_max': 32,
                         'fixed_pose_error_m': {'$f64': '3eb0c6f7a0b5ed8d'},
                         'ground_gap_max_m': {'$f64': '3f847ae147ae147b'},
                         'ground_gap_min_m': {'$f64': 'bf747ae147ae147b'},
                         'influence_mm_abs_max': 1000,
                         'linear_velocity_abs_m_s': {'$f64': '4059000000000000'},
                         'position_abs_m': {'$f64': '4024000000000000'},
                         'quaternion_norm_sq_error': {'$f64': '3f1a36e2eb1c432d'},
                         'samples_per_candidate': 2,
                         'settled_vz_abs_m_s': {'$f64': '3fa999999999999a'}},
              'material': {'friction': {'$f64': '3fe0000000000000'},
                           'gravity_compensation': {'$f64': '0000000000000000'},
                           'needs_coup': False,
                           'rho_kg_m3': {'$f64': '408f400000000000'}},
              'physics_profile': 'genesis-rigid-support.v0.1',
              'requires_grad': False,
              'rigid_options': {'constraint_timeconst_s': {'$f64': '3f847ae147ae147b'},
                                'enable_collision': True,
                                'enable_mujoco_compatibility': False,
                                'enable_rolling_friction': False,
                                'enable_self_collision': True,
                                'enable_torsional_friction': False,
                                'iterations': 25,
                                'ls_iterations': 50,
                                'max_collision_pairs': 16,
                                'max_contacts': 32,
                                'use_hibernation': False},
              'seed': 7,
              'solver_precision': '32',
              'steps_per_advance': 8,
              'substeps': 1,
              'viewer': False}},
  {'build': 'provider-build', 'options': 'resolved-options'}),
 ('existence-world',
  'existence',
  {'category': 'world', 'existence_id': 'existence-world', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-dynamic',
  'existence',
  {'category': 'physical', 'existence_id': 'existence-dynamic', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-support',
  'existence',
  {'category': 'physical', 'existence_id': 'existence-support', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-city',
  'existence',
  {'category': 'place', 'existence_id': 'existence-city', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-wildland',
  'existence',
  {'category': 'place', 'existence_id': 'existence-wildland', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-plain',
  'existence',
  {'category': 'place', 'existence_id': 'existence-plain', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-forest',
  'existence',
  {'category': 'place', 'existence_id': 'existence-forest', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-river_marsh',
  'existence',
  {'category': 'place', 'existence_id': 'existence-river_marsh', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('existence-ocean',
  'existence',
  {'category': 'place', 'existence_id': 'existence-ocean', 'spirit_record': 'not_separately_assigned'},
  {}),
 ('physics-binding',
  'physics_binding',
  {'bindings': [{'config_entity_index': 0,
                 'existence_id': 'existence-dynamic',
                 'genesis_name': 'i7-dynamic',
                 'physical_id': 'body-dynamic',
                 'role': 'dynamic'},
                {'config_entity_index': 1,
                 'existence_id': 'existence-support',
                 'genesis_name': 'i7-support',
                 'physical_id': 'body-support',
                 'role': 'support'}]},
  {'config': 'physics-config', 'dynamic_exists': 'existence-dynamic', 'support_exists': 'existence-support'}),
 ('place-city',
  'place',
  {'elevation_cm': 200,
   'footprint_cm': [[10000, 10000], [20000, 10000], [20000, 20000], [10000, 20000], [10000, 10000]],
   'place_id': 'city-1',
   'place_kind': 'city'},
  {'existence': 'existence-city'}),
 ('place-wildland',
  'place',
  {'elevation_cm': 600,
   'footprint_cm': [[5000, 70000], [30000, 70000], [30000, 90000], [5000, 90000], [5000, 70000]],
   'place_id': 'wildland-1',
   'place_kind': 'wildland'},
  {'existence': 'existence-wildland'}),
 ('place-plain',
  'place',
  {'elevation_cm': 150,
   'footprint_cm': [[20000, 10000], [50000, 10000], [50000, 30000], [20000, 30000], [20000, 10000]],
   'place_id': 'plain-1',
   'place_kind': 'plain'},
  {'existence': 'existence-plain'}),
 ('place-forest',
  'place',
  {'elevation_cm': 350,
   'footprint_cm': [[30000, 30000], [60000, 30000], [60000, 60000], [30000, 60000], [30000, 30000]],
   'place_id': 'forest-1',
   'place_kind': 'forest'},
  {'existence': 'existence-forest'}),
 ('place-river-marsh',
  'place',
  {'elevation_cm': 50,
   'footprint_cm': [[50000, 30000], [70000, 30000], [70000, 50000], [50000, 50000], [50000, 30000]],
   'place_id': 'river-marsh-1',
   'place_kind': 'river_marsh'},
  {'existence': 'existence-river_marsh'}),
 ('place-ocean',
  'place',
  {'elevation_cm': 0,
   'footprint_cm': [[70000, 0], [100000, 0], [100000, 100000], [70000, 100000], [70000, 0]],
   'place_id': 'ocean-1',
   'place_kind': 'ocean'},
  {'existence': 'existence-ocean'}),
 ('route-main',
  'route',
  {'place_ids': ['city-1', 'plain-1', 'forest-1', 'river-marsh-1', 'ocean-1'],
   'polyline_cm': [[15000, 15000], [35000, 20000], [45000, 40000], [60000, 40000], [80000, 40000]],
   'route_id': 'route-main'},
  {'p0': 'place-city',
   'p1': 'place-plain',
   'p2': 'place-forest',
   'p3': 'place-river-marsh',
   'p4': 'place-ocean'}),
 ('route-branch',
  'route',
  {'place_ids': ['forest-1', 'wildland-1'],
   'polyline_cm': [[45000, 40000], [17500, 80000]],
   'route_id': 'route-branch'},
  {'p0': 'place-forest', 'p1': 'place-wildland'}),
 ('watercourse-main',
  'watercourse',
  {'polyline_cm': [[40000, 55000], [60000, 40000], [80000, 40000]], 'watercourse_id': 'river-1'},
  {'marsh': 'place-river-marsh', 'outlet': 'place-ocean', 'upstream': 'place-forest'}),
 ('unit-transform',
  'unit_transform',
  {'origin_cm': [{'$f64': '40e5f90000000000'}, {'$f64': '40e3880000000000'}, {'$f64': '4075e00000000000'}],
   'scale': {'$f64': '4059000000000000'},
   'signs': [1, -1, 1],
   'source_frame': 'genesis-world-si-zup.v0.1',
   'target_frame': 'ue-world-cm.v0.2',
   'transform_version': 'si-to-ue.v0.2'},
  {}),
 ('projection',
  'projection',
  {'decorations': [{'asset_id': 'asset-cube',
                    'instance_id': 'marker-city',
                    'place_id': 'city-1',
                    'position_cm': [15000, 15000, 200],
                    'scale_milli': [1000, 1000, 1000]},
                   {'asset_id': 'asset-cube',
                    'instance_id': 'marker-wildland',
                    'place_id': 'wildland-1',
                    'position_cm': [17500, 80000, 600],
                    'scale_milli': [1000, 1000, 1000]},
                   {'asset_id': 'asset-cube',
                    'instance_id': 'marker-plain',
                    'place_id': 'plain-1',
                    'position_cm': [35000, 20000, 150],
                    'scale_milli': [1000, 1000, 1000]},
                   {'asset_id': 'asset-cube',
                    'instance_id': 'marker-forest',
                    'place_id': 'forest-1',
                    'position_cm': [45000, 45000, 350],
                    'scale_milli': [1000, 1000, 1000]},
                   {'asset_id': 'asset-cube',
                    'instance_id': 'marker-river-marsh',
                    'place_id': 'river-marsh-1',
                    'position_cm': [60000, 40000, 50],
                    'scale_milli': [1000, 1000, 1000]},
                   {'asset_id': 'asset-cube',
                    'instance_id': 'marker-ocean',
                    'place_id': 'ocean-1',
                    'position_cm': [85000, 50000, 0],
                    'scale_milli': [1000, 1000, 1000]}],
   'development_cm_per_mm': {'$f64': '3ff0000000000000'},
   'development_layout': 'abstract-magnified',
   'physical_layout': 'versioned-transform',
   'projection_version': 'basicshapes-proxy.v0.2'},
  {'assets': 'asset-manifest', 'transform': 'unit-transform'}),
 ('world-manifest',
  'world_manifest',
  {'artifact_class': 'synthetic-contract-only',
   'extent_cm': [0, 0, 100000, 100000],
   'geography_version': 'six-place-proxy.v0.2',
   'physics_rule': 'rigid-support-influence.v0.1',
   'revision_rule': 'technical-retain-snapshot.v0.2',
   'world_seed': 7},
  {'branch_route': 'route-branch',
   'city': 'place-city',
   'dynamic_existence': 'existence-dynamic',
   'forest': 'place-forest',
   'main_route': 'route-main',
   'ocean': 'place-ocean',
   'plain': 'place-plain',
   'projection': 'projection',
   'river_marsh': 'place-river-marsh',
   'support_existence': 'existence-support',
   'watercourse': 'watercourse-main',
   'wildland': 'place-wildland',
   'world_existence': 'existence-world'})]

def physics_parameters():
    return copy.deepcopy(_STATIC[0][2]['config'])

def record(context, identifier, kind, body, refs):
    value = dict(domain=DOMAIN, version='0.2', world_id=context.world_id,
                 id=identifier, kind=kind, body=copy.deepcopy(body), refs=dict(refs))
    validate_record(value)
    return value

@dataclass(frozen=True)
class StaticWorldDraft:
    context: object
    _bytes: tuple[bytes, ...]
    @property
    def records(self):
        import json
        return tuple(json.loads(raw) for raw in self._bytes)
    def by_kind(self, kind):
        return next(r for r in self.records if r['kind'] == kind)

@dataclass(frozen=True)
class InitialWorldBundle:
    records: tuple
    head: str
    blobs: tuple
    closure: object

def compose_static_world(context, *, build, options, assets):
    records, hashes = [], {}
    for source, kind, pin in ((build,'provider_build',context.expected_build),
                              (options,'resolved_options',context.expected_options)):
        validate_record(source)
        if source['world_id'] != context.world_id or source['kind'] != kind or digest(source) != pin:
            raise ContractError('BUILD_MISMATCH' if kind == 'provider_build' else 'OPTIONS_MISMATCH')
        records.append(copy.deepcopy(source))
        hashes['provider-build' if kind == 'provider_build' else 'resolved-options'] = digest(source)
    validate_record(assets)
    if assets['kind'] != 'asset_manifest' or assets['id'] != 'asset-manifest-runtime':
        raise ContractError('SCHEMA')
    assets = copy.deepcopy(assets)
    assets['world_id'] = context.world_id
    hashes['asset-manifest'] = digest(assets)
    for identifier,kind,body,refs in _STATIC:
        if kind == 'unit_transform':
            records.append(assets)
        body = copy.deepcopy(body)
        if kind == 'world_manifest':
            body['artifact_class'] = context.artifact_class
        value = record(context,identifier,kind,body,{key:hashes[target] for key,target in refs.items()})
        records.append(value)
        hashes[identifier] = digest(value)
    if len(records) != 26:
        raise ContractError('SCHEMA')
    return StaticWorldDraft(context, tuple(canonical(r) for r in records))

def compose_initial_world(static, physics, *, context, verifier):
    if static.context != context:
        raise ContractError('AUTHORIZATION')
    records = list(static.records) + list(physics.records)
    world = static.by_kind('world_manifest')
    state = record(context,'state-0','state',
        dict(tick=0,revision=0,budget=8,random_cursor=0,development_mm=None),
        dict(world=digest(world),snapshot=physics.snapshot_digest))
    records.append(state)
    manifest = record(context,'manifest-0','manifest',dict(tick=0,revision=0,watermark=0),
                      dict(state=digest(state)))
    records.append(manifest)
    closure = validate_closure(records,digest(manifest),world_id=context.world_id,
        domain_version='0.2',context=context,trust_verifier=verifier,
        blobs={physics.blob.sha256:physics.blob.payload})
    return InitialWorldBundle(tuple(records),digest(manifest),(physics.blob,),closure)

def enumerate_world(closure):
    records = closure.records
    from collections import Counter
    counts = Counter(r['kind'] for r in records.values())
    current = set()
    def visit(reference):
        if reference not in current:
            current.add(reference)
            for child in records[reference]['refs'].values():
                visit(child)
    visit(records[closure.head]['refs']['state'])
    return dict(json_records=len(records),current_json_records=len(current),typed_slots=36,
                kinds=dict(sorted(counts.items())),
                record_bytes=sum(len(canonical(r)) for r in records.values()),
                raw_blobs=len(closure.binary_refs),
                locators={r['id']:key for key,r in records.items()})
