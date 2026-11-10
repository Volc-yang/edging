"""Read-only checks for the exact I20 asset receipt, not a general glTF importer."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import math
import struct
import sys
from urllib.parse import urlsplit, unquote


def digest(raw):return hashlib.sha256(raw).hexdigest()


def safe(root,relative):
    p=PurePosixPath(relative)
    if not relative or p.is_absolute() or '\\' in relative or '\0' in relative or '..' in p.parts:
        raise ValueError('unsafe dependency path: '+relative)
    result=root.joinpath(*p.parts)
    for parent in (result,*result.parents):
        if parent.is_symlink():raise ValueError('symlink rejected: '+str(parent))
    if not result.is_file():raise ValueError('missing file: '+str(result))
    return result


def image_info(raw):
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):
        if raw[12:16]!=b'IHDR':raise ValueError('invalid PNG header')
        w,h,depth,color=struct.unpack('>IIBB',raw[16:26])
        return {'format':'PNG','width':w,'height':h,'bit_depth':depth,'color_type':color}
    if not raw.startswith(b'\xff\xd8') or not raw.endswith(b'\xff\xd9'):raise ValueError('invalid JPEG framing')
    offset=2
    while offset<len(raw):
        if raw[offset]!=255:raise ValueError('invalid JPEG marker')
        while raw[offset]==255:offset+=1
        marker=raw[offset];offset+=1
        size=int.from_bytes(raw[offset:offset+2],'big')
        if size<2:raise ValueError('invalid JPEG segment')
        if marker in (0xc0,0xc1,0xc2):
            depth,h,w,channels=struct.unpack('>BHHB',raw[offset+2:offset+8])
            return {'format':'JPEG','width':w,'height':h,'bit_depth':depth,'channels':channels}
        offset+=size
    raise ValueError('missing JPEG dimensions')


def verify(root):
    root=Path(root).absolute()
    receipt=json.loads(safe(root,'acquisition-receipt.json').read_bytes())
    if receipt['status']!='complete':raise ValueError('acquisition incomplete')
    plan_raw=safe(root,'acquisition-plan.json').read_bytes()
    if digest(plan_raw)!=receipt['plan_sha256']:raise ValueError('frozen plan identity mismatch')
    plan=json.loads(plan_raw);index={};images={}
    if {f['relative'] for f in plan['files']}!={f['relative'] for f in receipt['files']}:
        raise ValueError('receipt does not cover frozen plan')
    for entry in receipt['files']:
        raw=safe(root,entry['relative']).read_bytes();actual=entry['actual']
        if len(raw)!=entry['size'] or hashlib.md5(raw).hexdigest()!=entry['md5'] or digest(raw)!=actual['sha256']:
            raise ValueError('source size/hash mismatch: '+entry['relative'])
        index[entry['relative']]=entry
        if entry['relative'].endswith(('.jpg','.png')):
            info=image_info(raw)
            if max(info['width'],info['height'])>2048:raise ValueError('unexpected resolution')
            images[entry['relative']]=info
    models=[]
    for asset in plan['assets']:
        path=safe(root,asset['gltf']);base=path.parent
        gltf=json.loads(path.read_bytes())
        if gltf['asset']['version']!='2.0' or gltf.get('extensionsRequired'):
            raise ValueError('unsupported required glTF version/extension')
        dependency_paths=[];buffers=[]
        for kind in ('buffers','images'):
            for item in gltf[kind]:
                uri=item['uri'];parts=urlsplit(uri)
                if parts.scheme or parts.netloc or parts.query or parts.fragment or unquote(uri)!=uri:
                    raise ValueError('nonlocal/encoded dependency URI')
                dependency=safe(base,uri);relative=str(dependency.relative_to(root))
                if relative not in index:raise ValueError('dependency absent from frozen receipt')
                dependency_paths.append(relative)
                if kind=='buffers':
                    raw=dependency.read_bytes()
                    if len(raw)!=item['byteLength']:raise ValueError('buffer byteLength mismatch')
                    buffers.append(raw)
        for view in gltf['bufferViews']:
            start=view.get('byteOffset',0);end=start+view['byteLength']
            if start<0 or end>len(buffers[view['buffer']]):raise ValueError('bufferView out of bounds')
        values=[]
        for acc in gltf['accessors']:
            if 'sparse' in acc:raise ValueError('unexpected sparse accessor')
            view=gltf['bufferViews'][acc['bufferView']]
            fmt={5121:'B',5123:'H',5125:'I',5126:'f'}[acc['componentType']]
            width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[acc['type']]
            element=struct.calcsize('<'+fmt*width);stride=view.get('byteStride',element)
            offset=acc.get('byteOffset',0);count=acc['count']
            if count<=0 or stride<element or offset<0 or offset+(count-1)*stride+element>view['byteLength']:
                raise ValueError('accessor out of bounds')
            start=view.get('byteOffset',0)+offset;raw=buffers[view['buffer']]
            decoded=[struct.unpack_from('<'+fmt*width,raw,start+i*stride) for i in range(count)]
            if any(not math.isfinite(v) for row in decoded for v in row):raise ValueError('nonfinite accessor')
            values.append(decoded)
        meshes=[]
        for mesh in gltf['meshes']:
            primitives=[]
            for primitive in mesh['primitives']:
                if primitive.get('mode',4)!=4:raise ValueError('nontriangle primitive')
                points=values[primitive['attributes']['POSITION']];indices=values[primitive['indices']]
                if len(indices)%3 or max(v[0] for v in indices)>=len(points):raise ValueError('bad triangle indices')
                primitives.append({'vertices':len(points),'triangles':len(indices)//3,
                    'material_index':primitive['material'],'position_min':[min(p[i] for p in points) for i in range(3)],
                    'position_max':[max(p[i] for p in points) for i in range(3)]})
            meshes.append({'name':mesh.get('name'),'primitives':primitives})
        models.append({'id':asset['id'],'gltf_sha256':digest(path.read_bytes()),
            'dependency_closure':sorted(dependency_paths),'nodes':gltf['nodes'],
            'materials':gltf['materials'],'meshes':meshes,
            'triangle_count':sum(p['triangles'] for m in meshes for p in m['primitives'])})
    ledger=json.loads(safe(root,'binary-ledger.json').read_bytes())
    body_bytes=sum(row['body_bytes'] for row in ledger['requests'])
    if ledger['error'] or body_bytes!=ledger['actual_received_bytes'] or body_bytes>268435456:
        raise ValueError('network accounting failure')
    if ledger['elapsed_seconds']>1200 or any(row['ended_monotonic']-row['started_monotonic']>60 for row in ledger['requests']):
        raise ValueError('network time budget failure')
    all_files=list(root.rglob('*'))
    if any(p.is_symlink() for p in all_files):raise ValueError('symlink in acquired tree')
    count=sum(p.is_file() for p in all_files)
    if count>64:raise ValueError('file budget failure')
    return {'format':'universe-i20-asset-verification.v1','result':'PASS','root':str(root),
        'plan_sha256':receipt['plan_sha256'],'acquisition_receipt_sha256':digest(safe(root,'acquisition-receipt.json').read_bytes()),
        'verified_asset_files':len(index),'binary_bytes':sum(f['size'] for f in index.values()),
        'response_body_bytes':body_bytes,'network_elapsed_seconds':ledger['elapsed_seconds'],
        'actual_file_count_at_check':count,'image_headers':images,'models':models,
        'limitations':['Not a full glTF conformance check or image decode','No UE import/build/Metal/render run',
          'Ground glTF sphere is preview geometry; use textures on approved ground',
          'Fern JPEG has no alpha; bind the separately acquired Alpha PNG explicitly']}


if __name__=='__main__':
    try:print(json.dumps(verify(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
    except Exception as e:
        print(json.dumps({'result':'FAIL','error':str(e)}));sys.exit(1)
