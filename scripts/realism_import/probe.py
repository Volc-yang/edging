"""Real commandlet capability calls on transient clones; no import or save."""
from pathlib import Path
import json
import traceback
import unreal as u
from common import ENGINE,checked,require,sha


def _texture_state(obj):
    return {'path':obj.get_path_name(),'class':obj.get_class().get_path_name(),
        'srgb':obj.get_editor_property('srgb'),
        'compression':obj.get_editor_property('compression_settings'),
        'flip_green_channel':obj.get_editor_property('flip_green_channel'),
        'width':obj.blueprint_get_size_x(),'height':obj.blueprint_get_size_y()}


def _serial_texture_state(state):
    return {**state,'compression':str(state['compression'])}


def run_probe(job,mesh_metadata,configure_pipeline):
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    require(subsystem is not None,'probe subsystem missing')
    original_cube=u.EditorAssetLibrary.load_asset('/Engine/BasicShapes/Cube.Cube')
    original_texture=u.EditorAssetLibrary.load_asset('/Engine/EngineResources/DefaultTexture.DefaultTexture')
    require(isinstance(original_cube,u.StaticMesh) and isinstance(original_texture,u.Texture2D),'original probe fixture type mismatch')
    original_before={'mesh':mesh_metadata(original_cube,subsystem),
        'texture':_serial_texture_state(_texture_state(original_texture))}
    guards=[];restoration=[];failures=[];primary=None;primary_traceback=None
    try:result=_run_probe(job,mesh_metadata,configure_pipeline,guards)
    except BaseException as error:
        primary=error;primary_traceback=traceback.format_exc()
    for obj,before in guards:
        try:
            # Texture.ValidateSettings forces sRGB=false for current MASKS/NORMAL compression.
            # Restore the original compression before its original sRGB value.
            obj.set_editor_property('compression_settings',before['compression'])
            obj.set_editor_property('srgb',before['srgb'])
            obj.set_editor_property('flip_green_channel',before['flip_green_channel'])
            after=_texture_state(obj)
            row={'path':obj.get_path_name(),'before':_serial_texture_state(before),
                'after':_serial_texture_state(after),'diff':{key:{'before':str(before[key]),'after':str(after[key])} for key in before if before[key]!=after[key]}}
            restoration.append(row)
            if after!=before:failures.append({'case':'texture_restore','actual':row})
        except BaseException as error:
            failures.append({'case':'texture_restore_getter_or_setter','path':obj.get_path_name(),
                'before':_serial_texture_state(before),'error':str(error),'traceback':traceback.format_exc()})
    try:
        original_after={'mesh':mesh_metadata(original_cube,subsystem),
            'texture':_serial_texture_state(_texture_state(original_texture))}
        if original_after!=original_before:failures.append({'case':'original_fixture_getters_changed','before':original_before,'after':original_after})
        for path,row in job['preflight']['probe_fixtures'].items():
            require(sha(checked(path).read_bytes())==row['sha256'],'probe/restoration changed original fixture package bytes')
    except BaseException as error:
        failures.append({'case':'original_fixture_recheck','error':str(error),'traceback':traceback.format_exc()})
    if primary is not None or failures:
        diagnostic={'primary_error':None if primary is None else str(primary),
            'primary_traceback':primary_traceback,'restoration':restoration,'failures':failures}
        message=json.dumps(diagnostic,sort_keys=True,allow_nan=False)
        u.log_error('I22_PROBE_FAILURE_DIAGNOSTICS '+message)
        raise ValueError('I22 probe failed with preserved diagnostics: '+message) from primary
    return {**result,'texture_restoration':restoration,
        'original_fixture_getters_before':original_before,'original_fixture_getters_after':original_after}


def _run_probe(job,mesh_metadata,configure_pipeline,texture_guards):
    me=u.MaterialEditingLibrary
    fixture_before={path:sha(checked(path).read_bytes()) for path in job['preflight']['probe_fixtures']}
    require(all(fixture_before[p]==row['sha256'] for p,row in job['preflight']['probe_fixtures'].items()),'installed fixture changed before probe')
    transient=u.find_package('/Engine/Transient')
    require(transient is not None,'engine transient package unavailable')
    cube=u.EditorAssetLibrary.load_asset('/Engine/BasicShapes/Cube.Cube')
    texture=u.EditorAssetLibrary.load_asset('/Engine/EngineResources/DefaultTexture.DefaultTexture')
    require(isinstance(cube,u.StaticMesh) and isinstance(texture,u.Texture2D),'wrong installed fixture class')
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    require(subsystem is not None,'StaticMeshEditorSubsystem missing after module activation')
    mesh=u.SystemLibrary.duplicate_object(cube,transient,'I22ProbeMesh')
    color=u.SystemLibrary.duplicate_object(texture,transient,'I22ProbeColor')
    data=u.SystemLibrary.duplicate_object(texture,transient,'I22ProbeData')
    normal=u.SystemLibrary.duplicate_object(texture,transient,'I22ProbeNormal')
    for obj in (mesh,color,data,normal):require(obj is not None and obj.get_outermost()==transient,'probe clone is not transient')
    for obj in (color,data,normal):texture_guards.append((obj,_texture_state(obj)))
    before=mesh_metadata(mesh,subsystem)
    require(all(before[key]>0 for key in ('native_source_model_lod_count','native_render_lod_count',
        'render_lod0_triangles','native_render_lod0_vertices','native_editor_lod0_uv_channels',
        'native_render_lod0_texcoords')),'mesh getter returned invalid/sentinel count')
    require(bool(before['slots']) and bool(before['sections']),'mesh fixture has no actual sections/slots')
    require(before['simple_collision_count']>=0 and before['convex_collision_count']>=0,'collision getter returned error sentinel')
    require(all(s['slot_index']>=0 for s in before['sections']),'slot getter returned INDEX_NONE')
    material=u.Material(outer=transient,name='I22ProbeMaterial')
    require(material.get_outermost()==transient,'probe material is not transient')
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    material.set_editor_property('two_sided',True);material.set_editor_property('opacity_mask_clip_value',0.5)
    material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    original_material=mesh.get_material(0);original_collision=subsystem.is_section_collision_enabled(mesh,0,0)
    try:
        mesh.set_material(0,material)
        require(mesh.get_material(0)==material,'actual transient slot material assignment failed')
        # Invoke section-to-slot setter as well as getter; do not invent a second slot.
        slot=subsystem.get_lod_material_slot(mesh,0,0)
        subsystem.set_lod_material_slot(mesh,slot,0,0)
        require(subsystem.get_lod_material_slot(mesh,0,0)==slot,'actual section slot setter/getter mismatch')
        subsystem.enable_section_collision(mesh,not original_collision,0,0)
        fault_collision=subsystem.is_section_collision_enabled(mesh,0,0)
        require(fault_collision==(not original_collision),'actual collision toggle did not take effect')
        slot_fault=mesh_metadata(mesh,subsystem)['slots']
    finally:
        mesh.set_material(0,original_material)
        subsystem.enable_section_collision(mesh,original_collision,0,0)
    restored=mesh_metadata(mesh,subsystem)
    require(restored==before,'transient mesh was not restored after real setter calls')
    texture_rows=[]
    for obj,srgb,compression in ((color,True,u.TextureCompressionSettings.TC_DEFAULT),
            (data,False,u.TextureCompressionSettings.TC_MASKS),(normal,False,u.TextureCompressionSettings.TC_NORMALMAP)):
        obj.set_editor_property('srgb',srgb);obj.set_editor_property('compression_settings',compression)
        obj.set_editor_property('flip_green_channel',True)
        require(obj.get_editor_property('flip_green_channel') is True,'actual texture flip setter failed')
        obj.set_editor_property('flip_green_channel',False)
        width=obj.blueprint_get_size_x();height=obj.blueprint_get_size_y()
        require(width>0 and height>0,'texture dimensions getter returned invalid/sentinel size')
        require(obj.get_editor_property('srgb') is srgb and obj.get_editor_property('compression_settings')==compression and obj.get_editor_property('flip_green_channel') is False,'actual texture flags mismatch')
        texture_rows.append({'path':obj.get_path_name(),'class':obj.get_class().get_path_name(),
            'width':width,'height':height,'srgb':obj.get_editor_property('srgb'),
            'compression':str(obj.get_editor_property('compression_settings')),'flip_green_channel':obj.get_editor_property('flip_green_channel')})
    # Exercise the actual native source-filename getter without following Epic fixture paths.
    import_data=u.AssetImportData(outer=transient,name='I22ProbeImportData')
    filenames=list(import_data.extract_filenames())
    require(filenames==[],'fresh native import-data fixture unexpectedly has source filenames')
    nodes={};links={}
    recipes={'base_color':(color,u.MaterialSamplerType.SAMPLERTYPE_COLOR,[('',u.MaterialProperty.MP_BASE_COLOR)]),
        'normal':(normal,u.MaterialSamplerType.SAMPLERTYPE_NORMAL,[('',u.MaterialProperty.MP_NORMAL)]),
        'arm':(data,u.MaterialSamplerType.SAMPLERTYPE_MASKS,[('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]),
        'alpha':(data,u.MaterialSamplerType.SAMPLERTYPE_MASKS,[('R',u.MaterialProperty.MP_OPACITY_MASK)])}
    for role,(tex,sampler,connections) in recipes.items():
        node=me.create_material_expression(material,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',tex);node.set_editor_property('sampler_type',sampler);nodes[role]=node
        for output,mp in connections:
            require(me.connect_material_property(node,output,mp),'probe actual material connection failed')
            actual=me.get_material_property_input_node(material,mp)
            actual_output=me.get_material_property_input_node_output_name(material,mp)
            require(actual==node and actual.get_editor_property('texture')==tex,'probe property input did not retain actual node/texture')
            if output:require(actual_output==output,'probe material channel readback mismatch')
            links[str(mp)]={'node_class':actual.get_class().get_path_name(),'texture':actual.get_editor_property('texture').get_path_name(),
                'sampler':str(actual.get_editor_property('sampler_type')),'output':actual_output}
    require(not me.recompile_material(material),'probe transient material compiler returned errors')
    require(me.get_num_material_expressions(material)==4,'probe actual expression count mismatch')
    alpha=nodes['alpha']
    try:
        require(me.disconnect_material_property(material,u.MaterialProperty.MP_OPACITY_MASK),'probe actual Alpha disconnect failed')
        disconnected=me.get_material_property_input_node(material,u.MaterialProperty.MP_OPACITY_MASK)
        require(disconnected is None,'probe actual Alpha input still connected')
    finally:require(me.connect_material_property(alpha,'R',u.MaterialProperty.MP_OPACITY_MASK),'probe actual Alpha restore failed')
    require(me.get_material_property_input_node(material,u.MaterialProperty.MP_OPACITY_MASK)==alpha,'probe actual Alpha restore getter mismatch')
    pipeline,policy=configure_pipeline()
    stack=u.InterchangePipelineStackOverride();stack.add_pipeline(pipeline)
    overrides=list(stack.get_editor_property('OverridePipelines'))
    require(len(overrides)==1,'probe actual pipeline stack override missing')
    fixture_after={path:sha(checked(path).read_bytes()) for path in job['preflight']['probe_fixtures']}
    require(fixture_after==fixture_before,'probe altered installed fixture file bytes')
    return {'format':'edgeworld.i22.native-capability.v0.1','complete':True,
        'subsystem':{'path':subsystem.get_path_name(),'class':subsystem.get_class().get_path_name()},
        'transient_package':transient.get_path_name(),'mesh_before':before,'mesh_restored':restored,
        'actual_slot_fault':slot_fault,'actual_collision_fault':fault_collision,
        'texture_calls':texture_rows,'native_import_data_filenames':filenames,
        'material_links':links,'actual_alpha_disconnected':disconnected is None,
        'actual_alpha_restored':me.get_material_property_input_node(material,u.MaterialProperty.MP_OPACITY_MASK)==alpha,
        'pipeline_observed':policy,'stack_override_count':len(overrides),'fixture_file_sha256':fixture_after,
        'no_project_import_or_save':True,
        'limitations':['Capability fixtures only; no I20 texture source provenance or visual/Metal acceptance']}
