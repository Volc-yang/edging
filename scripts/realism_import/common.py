"""Strict stdlib input and immutable-file helpers; never launches an application."""
import hashlib
import json
import math
import os
import sys
from pathlib import Path, PurePosixPath

ENGINE = Path('/Users/Shared/Epic Games/UE_5.8/Engine')
SOURCE = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets')
OUTPUT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import')
INDEX_SHA = 'd9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7'
CONTENT_PATH = '/Game/EdgeWorldRealism/I22'
ACTIVATE_MODULES=('AssetTools','MaterialEditor','InterchangeEngine','InterchangeImport',
    'InterchangePipelines','EditorScriptingUtilities','StaticMeshEditor')
PROBE_FIXTURES=('Content/BasicShapes/Cube.uasset','Content/EngineResources/DefaultTexture.uasset')


def require(value, message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def finite(value):
    if isinstance(value,float):require(math.isfinite(value),'nonfinite number')
    elif isinstance(value,dict):
        for v in value.values():finite(v)
    elif isinstance(value,list):
        for v in value:finite(v)
    return value


def pairs(items):
    result={}
    for key,value in items:
        require(key not in result,'duplicate JSON key: '+key);result[key]=value
    return result


def load(path, expected=None):
    path=checked(path);raw=path.read_bytes()
    if expected:require(sha(raw)==expected,'SHA mismatch: '+str(path))
    return finite(json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON'))))


def checked(path):
    path=Path(path).absolute()
    require('..' not in path.parts,'parent traversal')
    for p in (path,*path.parents):require(not p.is_symlink(),'symlink: '+str(p))
    return path


def child(root,relative):
    p=PurePosixPath(relative)
    require(bool(relative) and not p.is_absolute() and '..' not in p.parts and '\\' not in relative and '\0' not in relative,'unsafe relative path')
    result=checked(Path(root).joinpath(*p.parts))
    require(result.is_relative_to(checked(root)),'path escape')
    return result


def write_new(path,value):
    raw=(json.dumps(finite(value),indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    path=checked(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return sha(raw)


def file_map(root):
    root=checked(root);result={}
    if not root.exists():return result
    for path in sorted(root.rglob('*')):
        checked(path)
        if path.is_file():
            raw=path.read_bytes();result[str(path.relative_to(root))]={'bytes':len(raw),'sha256':sha(raw)}
    return result


def validate_sources(index_path,source_root=SOURCE):
    index=load(index_path,INDEX_SHA)
    require(index['root']==str(SOURCE),'unexpected declared source root')
    require(len(index['files'])==20,'expected exactly 20 source files')
    seen=set()
    for entry in index['files']:
        relative=entry['path'];require(relative not in seen,'duplicate source path');seen.add(relative)
        path=child(source_root,relative);require(path.is_file(),'missing source: '+relative)
        raw=path.read_bytes()
        require(len(raw)==entry['bytes'] and sha(raw)==entry['sha256'],'source identity mismatch: '+relative)
        require(hashlib.md5(raw).hexdigest()==entry['provider_md5'],'source MD5 mismatch: '+relative)
    require('assets/fern_02/textures/fern_02_alpha_2k.png' in seen,'missing required Alpha')
    return index


def startup_inventory(engine=ENGINE,documents=None,extra_roots=()):
    """Conservative allowlist: installed Content/Python only; user startup is refused."""
    engine=checked(engine)
    lookup='explicit-fixture-parameter' if documents is not None else 'Foundation.NSSearchPathForDirectoriesInDomains(NSDocumentDirectory=9,NSUserDomainMask=1,expandTilde=True)'
    documents=checked(documents if documents is not None else mac_documents_directory())
    untrusted=[documents/'UnrealEngine/Python',*map(Path,extra_roots)]
    for directory in untrusted:
        checked(directory)
        require(not (directory/'init_unreal.py').exists(),'unreviewed user/project startup: '+str(directory/'init_unreal.py'))
        if directory.exists():
            require(not any(directory.glob('*.pth')),'unreviewed Python path hook: '+str(directory))
    roots=[engine/'Content/Python']
    roots.extend(p for p in (engine/'Plugins').rglob('Python') if p.is_dir() and p.parent.name=='Content')
    scripts=[]
    for directory in sorted(set(roots)):
        checked(directory)
        if not directory.exists():continue
        for path in sorted(directory.rglob('*')):
            checked(path)
            if path.is_file() and path.suffix in ('.py','.pth','.so','.dylib'):
                raw=path.read_bytes();scripts.append({'path':str(path),'bytes':len(raw),'sha256':sha(raw)})
    # All installed plugins are included, a conservative superset of mounted enabled Content.
    return {'format':'i21-installed-python-inventory.v1','policy':'installed Engine/Plugins Content/Python only',
        'user_documents_path':str(documents/'UnrealEngine/Python'),'scripts':scripts,
        'documents_lookup':lookup,
        'untrusted_roots_checked':[str(p) for p in untrusted]}


def clean_environment(source=None):
    source=os.environ if source is None else source
    result={key:source[key] for key in ('HOME','USER','LOGNAME','LANG','LC_CTYPE','__CF_USER_TEXT_ENCODING') if key in source}
    result['PATH']='/usr/bin:/bin:/usr/sbin:/sbin'
    # No inherited UE_PYTHONPATH, PYTHON*, EDGEWORLD*, loader injection, or remote/service variables.
    return result


def mac_documents_directory():
    """Same Foundation Documents query as installed ApplePlatformProcess.cpp."""
    require(sys.platform=='darwin','actual Documents lookup requires Mac Foundation')
    import ctypes as ct
    foundation=ct.CDLL('/System/Library/Frameworks/Foundation.framework/Foundation')
    objc=ct.CDLL('/usr/lib/libobjc.A.dylib')
    objc.sel_registerName.argtypes=[ct.c_char_p];objc.sel_registerName.restype=ct.c_void_p
    objc.objc_getClass.argtypes=[ct.c_char_p];objc.objc_getClass.restype=ct.c_void_p
    def sender(restype,*args):return ct.CFUNCTYPE(restype,ct.c_void_p,ct.c_void_p,*args)(('objc_msgSend',objc))
    send_obj=sender(ct.c_void_p);selector=objc.sel_registerName
    pool=send_obj(objc.objc_getClass(b'NSAutoreleasePool'),selector(b'alloc'))
    pool=send_obj(pool,selector(b'init'))
    try:
        search=foundation.NSSearchPathForDirectoriesInDomains
        search.argtypes=[ct.c_ulong,ct.c_ulong,ct.c_bool];search.restype=ct.c_void_p
        array=search(9,1,True)
        count=sender(ct.c_ulong)(array,selector(b'count'));require(count>0,'Foundation Documents query returned no path')
        string=sender(ct.c_void_p,ct.c_ulong)(array,selector(b'objectAtIndex:'),0)
        raw=sender(ct.c_char_p)(string,selector(b'UTF8String'));require(raw is not None,'Foundation Documents path has no UTF8 representation')
        return Path(os.fsdecode(raw))
    finally:sender(None)(pool,selector(b'drain'))


def plugin_inventory(descriptor,engine=ENGINE):
    """Resolve explicit enabled plugin dependency closure; reject pip requirements."""
    require(descriptor.get('DisableEnginePluginsByDefault') is True,'engine default plugins must be disabled')
    catalog={}
    for path in (checked(engine)/'Plugins').rglob('*.uplugin'):catalog.setdefault(path.stem,[]).append(path)
    pending=[entry['Name'] for entry in descriptor['Plugins'] if entry.get('Enabled')]
    result={}
    while pending:
        name=pending.pop()
        if name in result:continue
        matches=catalog.get(name,[]);require(len(matches)==1,'missing/ambiguous installed plugin '+name)
        path=checked(matches[0]);data=load_engine_descriptor(path)
        require(not data.get('PythonRequirements'),'enabled plugin has pip requirements: '+name)
        result[name]={'path':str(path),'sha256':sha(path.read_bytes()),'PythonRequirements':[]}
        for entry in data.get('Plugins',[]):
            if not entry.get('Enabled'):continue
            if entry.get('TargetAllowList') and 'Editor' not in entry['TargetAllowList']:continue
            if entry.get('PlatformAllowList') and 'Mac' not in entry['PlatformAllowList']:continue
            if 'Editor' in entry.get('TargetDenyList',[]) or 'Mac' in entry.get('PlatformDenyList',[]):continue
            pending.append(entry['Name'])
    return result


def load_engine_descriptor(path):
    """Installed .uplugin JSON permits trailing commas; keep quoted bytes intact.

    This does not relax JSON parsing for source indexes, jobs, recipes or evidence.
    """
    text=checked(path).read_text(encoding='utf-8-sig');result=[];quoted=False;escaped=False
    for i,char in enumerate(text):
        if quoted:
            result.append(char)
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True;result.append(char)
        elif char==',' and text[i+1:].lstrip().startswith(('}',']')):continue
        else:result.append(char)
    try:return finite(json.loads(''.join(result),object_pairs_hook=pairs))
    except ValueError as error:raise ValueError('installed descriptor parse failed '+str(path)+': '+str(error)) from error


def check_probe_result(probe,job):
    """Byte-pinned result consistency only; root separately accepts execution/quiet gates."""
    require(probe.get('format')=='edgeworld.i22.native-import-result.v0.1' and probe.get('mode')=='probe' and probe.get('status')=='PASS','probe did not produce correct positive Native result')
    require(probe.get('job_sha256')==job['probe_job_sha256'],'probe job identity mismatch')
    require(probe.get('recipe_sha256')==job['recipe_sha256'] and probe.get('source_index_sha256')==INDEX_SHA,'probe recipe/source identity mismatch')
    require(probe.get('source_scripts')==job['source_scripts'],'probe/import source snapshots differ')
    capability=probe.get('capability',{})
    require(capability.get('complete') is True,'probe capabilities incomplete')
    for field in ('subsystem','mesh_before','mesh_restored','texture_calls','material_links'):
        require(bool(capability.get(field)),'probe actual getter evidence missing: '+field)
    require(capability['mesh_before']==capability['mesh_restored'],'probe mesh restoration mismatch')
    require(capability.get('actual_alpha_disconnected') is True and capability.get('actual_alpha_restored') is True,'probe actual Alpha checks incomplete')
    policy=capability.get('pipeline_observed',{})
    require(policy.get('collision') is False and policy.get('build_nanite') is False,'probe live collision/Nanite policy mismatch')
    return True
