"""Root-only exclusive preparation and argv emission; no subprocess/UE execution."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from common import (ENGINE,SOURCE,OUTPUT,INDEX_SHA,checked,clean_environment,file_map,
                    load,plugin_inventory,require,sha,startup_inventory,validate_sources,write_new)

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
INDEX=REPO/'doc/evidence/universe-I20A/asset-index.json'
SNAPSHOTS=('common.py','ue_entry.py','recipe.json','EdgeWorldAssetImport.uproject','DefaultEngine.ini')


def preflight(index_path=INDEX):
    index=validate_sources(index_path)
    recipe=load(HERE/'recipe.json')
    require(recipe['index_sha256']==INDEX_SHA,'recipe index mismatch')
    require(len(recipe['textures'])==14 and sum(len(m['meshes']) for m in recipe['models'])==5,'recipe count mismatch')
    require({m['id'] for m in recipe['models']}=={'fern_02','boulder_01'},'ground preview must not import')
    for name in SNAPSHOTS:require(checked(HERE/name).is_file(),'missing reviewed source: '+name)
    version=load(ENGINE/'Build/Build.version')
    require((version['MajorVersion'],version['MinorVersion'],version['PatchVersion'],version['Changelist'])==(5,8,3,58210709),'installed UE version mismatch')
    binary=checked(ENGINE/'Binaries/Mac/UnrealEditor-Cmd');require(binary.is_file(),'missing commandlet binary')
    modules=[]
    for directory in (ENGINE/'Binaries/Mac',ENGINE/'Plugins/Interchange/Runtime/Binaries/Mac',
        ENGINE/'Plugins/Interchange/Editor/Binaries/Mac',ENGINE/'Plugins/Experimental/PythonScriptPlugin/Binaries/Mac',
        ENGINE/'Plugins/Editor/EditorScriptingUtilities/Binaries/Mac'):
        for path in sorted(directory.glob('*.dylib')):
            if any(part in path.name for part in ('Interchange','PythonScriptPlugin','GLTFCore','EditorScriptingUtilities','MaterialEditor','StaticMeshEditor','AssetTools')):
                path=checked(path);modules.append({'path':str(path),'sha256':sha(path.read_bytes())})
    startup=startup_inventory(extra_roots=(OUTPUT/'host/Content/Python',OUTPUT/'user/Python'))
    plugins=plugin_inventory(load(HERE/'EdgeWorldAssetImport.uproject'))
    # Conservatively reject any installed config that adds startup code/extra paths.
    config_evidence=[]
    for directory in (ENGINE/'Config',ENGINE/'Plugins'):
        for path in directory.rglob('*.ini'):
            if directory.name=='Plugins' and 'Config' not in path.parts:continue
            relevant=[line.strip() for line in path.read_text(errors='replace').splitlines()
                if line.strip().lstrip('+').startswith(('StartupScripts=','AdditionalPaths='))]
            require(not relevant,'installed Python startup/extra path config requires review: '+str(path))
    return {'format':'edgeworld.i21.preflight.v0.1','status':'ready_requires_C1_and_root_dispatch',
        'version':version,'binary':{'path':str(binary),'sha256':sha(binary.read_bytes())},
        'installed_modules':modules,
        'enabled_plugin_closure':plugins,
        'source_index_sha256':INDEX_SHA,'source_files':len(index['files']),
        'snapshot_sources':{name:sha((HERE/name).read_bytes()) for name in SNAPSHOTS},
        'startup':startup,'config_additions':config_evidence,
        'environment':clean_environment(),'does_not_run_UE':True}


def prepare(mode,attempt):
    require(mode in ('import','reload') and attempt in (1,2),'invalid mode/attempt')
    check=preflight();root=checked(OUTPUT)
    root.mkdir(exist_ok=True)
    selected=root/('a'+str(attempt));host=selected/'host'
    if mode=='import':
        selected.mkdir();host.mkdir();session=selected
        (host/'Config').mkdir();(host/'Content').mkdir()
        shutil.copyfile(HERE/'EdgeWorldAssetImport.uproject',host/'EdgeWorldAssetImport.uproject')
        shutil.copyfile(HERE/'DefaultEngine.ini',host/'Config/DefaultEngine.ini')
    else:
        require(host.is_dir(),'missing selected import host')
        imported=load(selected/'result.json')
        require(imported['status']=='PASS' and imported['mode']=='import','selected import did not pass')
        require(file_map(host/'Content')==imported['content_files'],'selected Content changed after import')
        session=root/'reload';session.mkdir()
    snapshots=session/'scripts';snapshots.mkdir()
    for name in SNAPSHOTS:shutil.copyfile(HERE/name,snapshots/name)
    shutil.copyfile(INDEX,snapshots/'source-index.json')
    for name in ('user','tmp','ddc'):checked(session/name).mkdir()
    startup=startup_inventory(extra_roots=(host/'Content/Python',session/'user/Python',host/'Plugins'))
    job={'format':'edgeworld.i21.import-job.v0.1','mode':mode,'attempt':attempt,
        'source_root':str(SOURCE),'source_index':str(snapshots/'source-index.json'),'source_index_sha256':INDEX_SHA,
        'recipe':str(snapshots/'recipe.json'),'recipe_sha256':sha((snapshots/'recipe.json').read_bytes()),
        'host':str(host),'session':str(session),'output':str(session/'result.json'),
        'startup':startup,'preflight':check,'source_scripts':{name:sha((snapshots/name).read_bytes()) for name in SNAPSHOTS},
        'import_result':str(selected/'result.json') if mode=='reload' else None}
    job_sha=write_new(session/'job.json',job)
    ddc=session/'ddc';require(len(str(ddc))<119,'Mac DDC path too long')
    require(' ' not in str(session),'script paths must be literal whitespace-free')
    argv=[str(ENGINE/'Binaries/Mac/UnrealEditor-Cmd'),str(host/'EdgeWorldAssetImport.uproject'),
        '-run=pythonscript','-script='+str(snapshots/'ue_entry.py'),'-NullRHI','-unattended','-NoSplash','-NoSound',
        '-notraceserver','-traceautostart=0','-UserDir='+str(session/'user'),'-abslog='+str(session/'ue.log'),
        '-DDC=(Isolated=(Type=FileSystem,Path='+str(ddc)+',PromptIfMissing=false,Clean=false,DeleteUnused=false))','-DDC-NoDefaultGraph',
        '-NoSourceControl','-NoP4','-NoLiveCoding','-NoAutoRecompileBlueprints']
    env=clean_environment();env['TMPDIR']=str(session/'tmp')+'/'
    env['I21_IMPORT_JOB_SHA256']=job_sha
    dispatch={'format':'edgeworld.i21.root-dispatch.v0.1','mode':mode,'attempt':attempt,
        'argv':argv,'env':env,'cwd':str(host),'job_sha256':job_sha,'job':str(session/'job.json'),
        'deadline_seconds':240 if mode=='import' else 180,'result':str(session/'result.json'),
        'root_supervision_required':{'continuous_total_seconds':900,'max_root_bytes':4*1024**3,
          'max_all_Content_bytes':512*1024**2,'max_import_attempts':2,'max_reload':1,
          'external_before_after_maps':True,'real_parent_wait_and_descendant_quiet':True}}
    write_new(session/'dispatch.json',dispatch)
    return dispatch


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('preflight','import','reload'))
    parser.add_argument('--attempt',type=int,choices=(1,2),default=1);args=parser.parse_args()
    try:print(json.dumps(preflight() if args.mode=='preflight' else prepare(args.mode,args.attempt),indent=2,sort_keys=True))
    except Exception as error:print(json.dumps({'status':'FAIL','error':str(error)}));sys.exit(2)
