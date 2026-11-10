"""Executed only by root's reviewed UE PythonScriptCommandlet, never by CPU tests."""
from pathlib import Path
import json
import os
import re
import sys
import time

# The only additional Python directory is this reviewed, immutable script snapshot.
sys.path.insert(0,str(Path(__file__).absolute().parent))
from common import (CONTENT_PATH,ENGINE,OUTPUT,SOURCE,checked,child,file_map,load,
                    require,sha,startup_inventory,validate_sources,write_new)
import unreal as u

ME=u.MaterialEditingLibrary
JOB_PATH=Path(__file__).absolute().parent.parent/'job.json'


def load_job():
    expected=os.environ.get('I21_IMPORT_JOB_SHA256','')
    require(len(expected)==64 and all(c in '0123456789abcdef' for c in expected),'missing independent root job SHA')
    return load(JOB_PATH,expected)


def prop(obj,name):return obj.get_editor_property(name)
def objpath(obj):return obj.get_path_name() if obj else None
def enum(value):return str(value)
def vector(value):return [float(value.x),float(value.y),float(value.z)]
def identity(obj):return {'path':objpath(obj),'class':obj.get_class().get_path_name()}


def texture_source(texture,index):
    data=prop(texture,'asset_import_data');require(data is not None,'missing Native texture import data')
    paths=data.extract_filenames();require(len(paths)==1,'texture source is ambiguous')
    source=checked(paths[0]);raw=source.read_bytes()
    candidates=[entry for entry in index['files'] if child(SOURCE,entry['path'])==source and entry['sha256']==sha(raw)]
    require(len(candidates)==1,'Native texture source does not match pinned input')
    return candidates[0]['path']


def texture_metadata(texture,index):
    return {**identity(texture),'source_file_id':texture_source(texture,index),
        'width':texture.blueprint_get_size_x(),'height':texture.blueprint_get_size_y(),
        'srgb':bool(prop(texture,'srgb')),'compression':enum(prop(texture,'compression_settings')),
        'flip_green_channel':bool(prop(texture,'flip_green_channel'))}


def material_metadata(material,index):
    properties={'base_color':u.MaterialProperty.MP_BASE_COLOR,'normal':u.MaterialProperty.MP_NORMAL,
        'ao':u.MaterialProperty.MP_AMBIENT_OCCLUSION,'roughness':u.MaterialProperty.MP_ROUGHNESS,
        'metallic':u.MaterialProperty.MP_METALLIC,'opacity_mask':u.MaterialProperty.MP_OPACITY_MASK}
    links={}
    for name,mp in properties.items():
        node=ME.get_material_property_input_node(material,mp)
        if node:
            require(isinstance(node,u.MaterialExpressionTextureSample),'unexpected material node class')
            texture=prop(node,'texture');require(texture is not None,'material node missing actual texture')
            links[name]={'expression_class':node.get_class().get_path_name(),
                'texture':objpath(texture),'source_file_id':texture_source(texture,index),
                'sampler':enum(prop(node,'sampler_type')),
                'output':ME.get_material_property_input_node_output_name(material,mp)}
        else:links[name]=None
    return {**identity(material),'blend_mode':enum(prop(material,'blend_mode')),
        'two_sided':bool(prop(material,'two_sided')),'opacity_mask_clip_value':float(prop(material,'opacity_mask_clip_value')),
        'shading_model':enum(prop(material,'shading_model')),'links':links,
        'expression_count':ME.get_num_material_expressions(material)}


def mesh_metadata(mesh,subsystem):
    box=mesh.get_bounding_box();bounds=mesh.get_bounds()
    slots=[{'index':i,'name':str(prop(slot,'material_slot_name')),
        'imported_name':str(prop(slot,'imported_material_slot_name')),
        'material':objpath(prop(slot,'material_interface'))} for i,slot in enumerate(prop(mesh,'static_materials'))]
    sections=[{'index':i,'slot_index':subsystem.get_lod_material_slot(mesh,0,i),
        'collision':subsystem.is_section_collision_enabled(mesh,0,i)} for i in range(mesh.get_num_sections(0))]
    return {**identity(mesh),'bounds_cm':{'min':vector(box.min),'max':vector(box.max)},
        'bounds_center_cm':vector(bounds.origin),'bounds_extent_cm':vector(bounds.box_extent),
        'lod_count':subsystem.get_lod_count(mesh),'lod0_triangles':mesh.get_num_triangles(0),
        'lod0_vertices':subsystem.get_number_verts(mesh,0),'uv_channels':subsystem.get_num_uv_channels(mesh,0),
        'slots':slots,'sections':sections,'simple_collision_count':subsystem.get_simple_collision_count(mesh),
        'convex_collision_count':subsystem.get_convex_collision_count(mesh),
        'origin_semantics':'StaticMesh asset-local origin; no Actor/pivot transform was synthesized'}


def all_assets():
    paths=u.EditorAssetLibrary.list_assets(CONTENT_PATH,recursive=True,include_folder=False)
    result=[]
    for path in paths:
        obj=u.EditorAssetLibrary.load_asset(path);require(obj is not None,'cannot load Native asset '+path);result.append(obj)
    return sorted(result,key=objpath)


def native_snapshot(index):
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    assets=all_assets();groups={'StaticMesh':[],'Texture2D':[],'Material':[]}
    for obj in assets:
        name=obj.get_class().get_name();require(name in groups,'unexpected project asset class '+name)
        if name=='StaticMesh':row=mesh_metadata(obj,subsystem)
        elif name=='Texture2D':row=texture_metadata(obj,index)
        else:row=material_metadata(obj,index)
        groups[name].append(row)
    dependencies={};external={};registry=u.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous([CONTENT_PATH],force_rescan=True)
    options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,
        include_hard_package_references=True,include_searchable_names=False,
        include_soft_management_references=False,include_hard_management_references=False)
    pending=[obj.get_outermost().get_name() for obj in assets];visited=set()
    while pending:
        package=pending.pop()
        if package in visited:continue
        visited.add(package)
        deps=sorted(str(x) for x in registry.get_dependencies(package,options));dependencies[package]=deps
        for dep in deps:
            if dep.startswith(CONTENT_PATH+'/'):pending.append(dep)
            elif dep.startswith('/Script/'):
                module=dep.removeprefix('/Script/')
                require(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',module) is not None,'invalid script module dependency')
                package_object=u.find_package(dep)
                require(package_object is not None,'script dependency package is not already loaded: '+dep)
                filename='libUnrealEditor-'+module+'.dylib'
                main=ENGINE/'Binaries/Mac'/filename
                candidates=[main] if main.is_file() else list((ENGINE/'Plugins').rglob(filename))
                require(len(candidates)==1,'missing/ambiguous installed script module binary: '+dep)
                binary=checked(candidates[0]);require(binary.is_relative_to(ENGINE),'module binary outside installed engine')
                external[dep]={'kind':'installed-native-module','loaded_package':objpath(package_object),
                    'binary_path':str(binary),'binary_sha256':sha(binary.read_bytes())}
            else:
                require(not dep.startswith('/Game/'),'unexpected external project dependency '+dep)
                obj=u.EditorAssetLibrary.load_asset(dep);require(obj is not None,'missing external dependency '+dep)
                path=checked(u.SystemLibrary.get_system_path(obj))
                require(path.is_relative_to(ENGINE),'dependency outside installed UE '+str(path))
                require(path.is_file(),'missing installed dependency package')
                sidecars={}
                for candidate in sorted(path.parent.glob(path.stem+'.*')):
                    checked(candidate)
                    if candidate.is_file():sidecars[str(candidate)]={'bytes':candidate.stat().st_size,'sha256':sha(candidate.read_bytes())}
                external[dep]={'kind':'installed-content','path':str(path),'sha256':sha(path.read_bytes()),'package_files':sidecars}
                pending.append(dep)
    return {'objects':groups,'dependencies':dependencies,'external_dependencies':external}


def validate_native(snapshot,recipe):
    groups=snapshot['objects']
    for kind,count in recipe['expected_class_counts'].items():require(len(groups[kind])==count,'Native class count mismatch '+kind)
    expected_textures={t['source_file_id']:t for t in recipe['textures']}
    actual_textures={t['source_file_id']:t for t in groups['Texture2D']}
    require(set(actual_textures)==set(expected_textures),'Native texture source coverage mismatch')
    for source,expected in expected_textures.items():
        actual=actual_textures[source]
        require(actual['width']==2048 and actual['height']==2048,'Native texture dimensions mismatch')
        for field in ('srgb','flip_green_channel'):require(actual[field]==expected[field],'Native texture '+field+' mismatch')
        require(actual['compression'].endswith('.'+expected['compression']) or expected['compression'] in actual['compression'],'Native compression mismatch')
    material_paths={}
    for m in recipe['materials']:
        matches=[x for x in groups['Material'] if x['path'].split('.')[-1]==m['name']]
        require(len(matches)==1,'missing actual material '+m['name']);actual=matches[0];material_paths[m['asset_id']]=actual['path']
        require(m['blend_mode'] in actual['blend_mode'] and actual['two_sided']==m['two_sided'],'Native material mode mismatch')
        require(m['shading_model'] in actual['shading_model'],'Native shading model mismatch')
        if m['asset_id']=='fern_02':require(abs(actual['opacity_mask_clip_value']-0.5)<1e-6,'Native Alpha clip mismatch')
        roles={'base_color':('base_color',None),'normal':('normal_dx',None),'ao':('arm','R'),
            'roughness':('arm','G'),'metallic':('arm','B')}
        if m['asset_id']=='fern_02':roles['opacity_mask']=('alpha','R')
        for link,(role,channel) in roles.items():
            candidates=[t for t in recipe['textures'] if t['asset_id']==m['asset_id'] and t['role']==role]
            require(len(candidates)==1,'ambiguous recipe texture role')
            expected=candidates[0];actual_link=actual['links'][link]
            require(actual_link is not None and actual_link['source_file_id']==expected['source_file_id'],'Native material source mismatch '+link)
            require(expected['sampler'] in actual_link['sampler'],'Native sampler mismatch '+link)
            if channel:require(actual_link['output']==channel,'Native channel mismatch '+link)
    mapping=[];remaining=groups['StaticMesh'][:]
    for model in recipe['models']:
        for source in model['meshes']:
            matches=[]
            for actual in remaining:
                same=actual['lod0_triangles']==source['expected_triangles']
                same=same and all(abs(actual['bounds_cm'][end][axis]-source['expected_bounds_cm'][end][axis])<=recipe['bounds_tolerance_cm'] for end in ('min','max') for axis in range(3))
                if same:matches.append(actual)
            require(len(matches)==1,'Native mesh mapping/bounds is missing or ambiguous for '+source['source_node'])
            actual=matches[0];remaining.remove(actual)
            require(len(actual['slots'])==1 and len(actual['sections'])==1,'expected one actual slot/section')
            require(actual['sections'][0]['slot_index']==0 and not actual['sections'][0]['collision'],'Native section policy mismatch')
            require(actual['slots'][0]['material']==material_paths[model['id']],'Native mesh slot material mismatch')
            require(actual['simple_collision_count']==0 and actual['convex_collision_count']==0,'unexpected generated collision')
            mapping.append({'source_asset':model['id'],'source_node':source['source_node'],
                'source_mesh':source['source_mesh'],'source_mesh_index':source['source_mesh_index'],
                'native_object_path':actual['path'],'mapping_basis':'actual triangle count and local AABB against pinned source',
                'source_convention':recipe['source_convention']})
    return mapping


def import_task(filename,destination,options=None):
    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=destination
    task.automated=True;task.save=False;task.replace_existing=False;task.async_=False
    if options is not None:task.options=options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    require(task.is_async_import_complete(),'blocking import did not complete')
    result=list(task.get_objects());require(bool(result),'import returned no actual objects: '+str(filename))
    return result


def do_import(recipe):
    tools=u.AssetToolsHelpers.get_asset_tools();objects=[]
    pipeline=u.InterchangeGenericAssetsPipeline()
    pipeline.import_offset_uniform_scale=1.0
    pipeline.common_meshes_properties.bake_meshes=False;pipeline.common_meshes_properties.bake_pivot_meshes=False
    pipeline.mesh_pipeline.combine_static_meshes_behavior=u.InterchangeCombineStaticMeshesBehavior.DO_NOT_COMBINE
    pipeline.mesh_pipeline.collision=False
    pipeline.material_pipeline.import_materials=False;pipeline.material_pipeline.texture_pipeline.import_textures=False
    stack=u.InterchangePipelineStackOverride();stack.add_pipeline(pipeline)
    for model in recipe['models']:
        imported=import_task(child(SOURCE,model['gltf']),CONTENT_PATH+'/Meshes/'+model['id'],stack)
        require(all(isinstance(x,u.StaticMesh) for x in imported),'mesh-only pipeline produced other asset class')
        objects.extend(imported)
    textures={}
    for t in recipe['textures']:
        result=import_task(child(SOURCE,t['source_file_id']),CONTENT_PATH+'/Textures')
        require(len(result)==1 and isinstance(result[0],u.Texture2D),'texture import did not return exactly one Texture2D')
        texture=result[0]
        texture.set_editor_property('srgb',t['srgb'])
        texture.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,t['compression']))
        texture.set_editor_property('flip_green_channel',t['flip_green_channel'])
        textures[(t['asset_id'],t['role'])]=(texture,t);objects.append(texture)
    materials={}
    for m in recipe['materials']:
        material=tools.create_asset(m['name'],CONTENT_PATH+'/Materials',u.Material,u.MaterialFactoryNew())
        require(material is not None,'failed creating UMaterial')
        for name,value in (('blend_mode',getattr(u.BlendMode,m['blend_mode'])),('two_sided',m['two_sided']),
            ('opacity_mask_clip_value',m['opacity_mask_clip_value']),('shading_model',getattr(u.MaterialShadingModel,m['shading_model']))):
            material.set_editor_property(name,value)
        roles={'base_color':[('',u.MaterialProperty.MP_BASE_COLOR)],'normal_dx':[('',u.MaterialProperty.MP_NORMAL)],
            'arm':[('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]}
        if m['asset_id']=='fern_02':roles['alpha']=[('R',u.MaterialProperty.MP_OPACITY_MASK)]
        for role,connections in roles.items():
            texture,t=textures[(m['asset_id'],role)]
            node=ME.create_material_expression(material,u.MaterialExpressionTextureSample)
            node.set_editor_property('texture',texture);node.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,t['sampler']))
            for output,mp in connections:require(ME.connect_material_property(node,output,mp),'failed connecting Native material property')
        errors=ME.recompile_material(material);require(not errors,'material compilation reported errors: '+str(errors))
        materials[m['asset_id']]=material;objects.append(material)
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for mesh in [x for x in objects if isinstance(x,u.StaticMesh)]:
        model_id='fern_02' if '/fern_02/' in objpath(mesh) else 'boulder_01'
        require(len(prop(mesh,'static_materials'))==1,'imported mesh slots not uniquely identified')
        mesh.set_material(0,materials[model_id])
        for section in range(mesh.get_num_sections(0)):subsystem.enable_section_collision(mesh,False,0,section)
    require(u.EditorAssetLibrary.save_loaded_assets(objects,only_if_is_dirty=False),'saving Native assets failed')
    return objects


def native_negative_checks(index,recipe,positive):
    """Mutate live UObjects, observe failure, restore; deliberately do not save."""
    fern=u.EditorAssetLibrary.load_asset(CONTENT_PATH+'/Materials/M_fern_02')
    node=ME.get_material_property_input_node(fern,u.MaterialProperty.MP_OPACITY_MASK)
    output=ME.get_material_property_input_node_output_name(fern,u.MaterialProperty.MP_OPACITY_MASK)
    require(node is not None,'positive Alpha node missing');checks=[]
    try:
        require(ME.disconnect_material_property(fern,u.MaterialProperty.MP_OPACITY_MASK),'Native Alpha disconnection failed')
        try:validate_native(native_snapshot(index),recipe)
        except ValueError as error:
            require(str(error)=='Native material source mismatch opacity_mask','unexpected error during Alpha negative: '+str(error))
            checks.append({'case':'actual_Alpha_disconnected','rejected':True,'error':str(error),
                'actual_fault_getter':material_metadata(fern,index)['links']['opacity_mask']})
        else:raise ValueError('Native missing Alpha negative unexpectedly passed')
    finally:require(ME.connect_material_property(node,output,u.MaterialProperty.MP_OPACITY_MASK),'restore Alpha failed')
    fern_mesh=next(x for x in positive['objects']['StaticMesh'] if '/fern_02/' in x['path'])
    mesh=u.EditorAssetLibrary.load_asset(fern_mesh['path']);original=mesh.get_material(0)
    wrong=u.EditorAssetLibrary.load_asset(CONTENT_PATH+'/Materials/M_boulder_01')
    try:
        mesh.set_material(0,wrong)
        require(mesh.get_material(0)==wrong,'actual slot fault injection did not take effect')
        try:validate_native(native_snapshot(index),recipe)
        except ValueError as error:
            require(str(error)=='Native mesh slot material mismatch','unexpected error during slot negative: '+str(error))
            checks.append({'case':'actual_mesh_slot_material_replaced','rejected':True,'error':str(error),
                'actual_fault_getter':mesh_metadata(mesh,u.get_editor_subsystem(u.StaticMeshEditorSubsystem))['slots']})
        else:raise ValueError('Native wrong slot negative unexpectedly passed')
    finally:mesh.set_material(0,original)
    restored=native_snapshot(index);validate_native(restored,recipe)
    require(restored==positive,'restored live UObject metadata differs from positive snapshot')
    return checks


def main():
    job=load_job();session=checked(job['session']);host=checked(job['host'])
    require(session.is_relative_to(OUTPUT) and host.is_relative_to(OUTPUT),'job outside approved root')
    require(job['source_root']==str(SOURCE),'source root changed')
    require(not any(k.startswith(('EDGEWORLD','PYTHON')) or k=='UE_PYTHONPATH' for k in os.environ),'unexpected inherited execution environment')
    for name,expected in job['source_scripts'].items():require(sha((Path(__file__).parent/name).read_bytes())==expected,'reviewed snapshot changed')
    for module in [job['preflight']['binary'],*job['preflight']['installed_modules']]:
        require(sha(checked(module['path']).read_bytes())==module['sha256'],'installed binary/module changed since preflight')
    for plugin in job['preflight']['enabled_plugin_closure'].values():
        require(sha(checked(plugin['path']).read_bytes())==plugin['sha256'],'installed enabled plugin descriptor changed')
    current=startup_inventory(extra_roots=job['startup']['untrusted_roots_checked'][1:])
    require(current==job['startup'],'startup inputs changed since preflight')
    index=validate_sources(job['source_index']);recipe=load(job['recipe'],job['recipe_sha256'])
    require('5.8.3-58210709' in u.SystemLibrary.get_engine_version(),'actual loaded UE version/CL mismatch')
    before=file_map(host/'Content');started=time.monotonic()
    if job['mode']=='import':
        require(not before,'import Content must be empty');do_import(recipe)
    else:require(job['mode']=='reload','unsupported mode')
    snapshot=native_snapshot(index);mapping=validate_native(snapshot,recipe)
    if job['mode']=='reload':
        previous=load(job['import_result']);require(previous['status']=='PASS','selected import failed')
        require(before==previous['content_files'],'reload input package bytes differ')
        require(snapshot==previous['native'],'fresh process Native objects differ from import')
    negatives=native_negative_checks(index,recipe,snapshot)
    after=file_map(host/'Content')
    if job['mode']=='reload':require(before==after,'read-only reload changed saved Content')
    validate_sources(job['source_index'])
    return {'format':'edgeworld.i21.native-import-result.v0.1','status':'PASS','mode':job['mode'],
        'pid':os.getpid(),'ue_version_actual':u.SystemLibrary.get_engine_version(),
        'job_sha256':os.environ['I21_IMPORT_JOB_SHA256'],'recipe_sha256':job['recipe_sha256'],'source_index_sha256':job['source_index_sha256'],
        'elapsed_script_seconds':time.monotonic()-started,'native':snapshot,'source_mesh_mapping':mapping,
        'negative_checks':negatives,'content_files':after,'content_before':before,
        'limitations':['NullRHI object/import evidence only','Pivot is asset-local origin, not bounds center',
          'Ground plane, runtime adapter, visual normal direction, Metal and quality not tested']}


if __name__=='__main__':
    output=None
    try:
        job=load_job();output=checked(job['output'])
        require(output.is_relative_to(OUTPUT),'result outside approved output root')
        result=main();write_new(output,result)
        u.log('I21_NATIVE_RESULT_PASS '+str(output))
    except BaseException as error:
        if output is not None and not output.exists():write_new(output,{'format':'edgeworld.i21.native-import-result.v0.1','status':'FAIL','pid':os.getpid(),'error':str(error)})
        raise
