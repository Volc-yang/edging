"""Strict stdlib input and immutable-file helpers; never launches an application."""
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath

ENGINE = Path('/Users/Shared/Epic Games/UE_5.8/Engine')
SOURCE = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets')
OUTPUT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I21-20261110-import')
INDEX_SHA = 'd9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7'
CONTENT_PATH = '/Game/EdgeWorldRealism/I21'


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
    documents=checked(documents or Path.home()/'Documents')
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
        'untrusted_roots_checked':[str(p) for p in untrusted]}


def clean_environment(source=None):
    source=os.environ if source is None else source
    result={key:source[key] for key in ('HOME','USER','LOGNAME','LANG','LC_CTYPE','__CF_USER_TEXT_ENCODING') if key in source}
    result['PATH']='/usr/bin:/bin:/usr/sbin:/sbin'
    # No inherited UE_PYTHONPATH, PYTHON*, EDGEWORLD*, loader injection, or remote/service variables.
    return result
