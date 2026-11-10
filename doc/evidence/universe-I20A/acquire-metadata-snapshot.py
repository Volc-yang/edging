"""Bounded I20 CC0 asset acquisition artifact; no third-party code execution."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import ssl
import sys
import time
import signal
from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from urllib.error import HTTPError

ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets')
LIMIT = 256 * 1024**2
MAX_FILES = 64
NETWORK_SECONDS = 1200
PER_FILE_SECONDS = 60
HOSTS = {'api.polyhaven.com','polyhaven.com','dl.polyhaven.org','creativecommons.org'}
ASSETS = ('fern_02','boulder_01','forrest_ground_01')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def checked_url(value):
    p=urlsplit(value)
    if (p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or
        p.port not in (None,443) or p.fragment or '\\' in value):
        raise ValueError('untrusted acquisition URL')
    return value


def destination(value):
    p=PurePosixPath(value)
    if p.is_absolute() or any(x in ('..','.') for x in p.parts) or '\\' in value or '\0' in value:
        raise ValueError('unsafe relative destination')
    result=ROOT/Path(*p.parts)
    if not result.is_relative_to(ROOT):raise ValueError('destination escape')
    for parent in (result,*result.parents):
        if parent.is_symlink():raise ValueError('symlink destination')
    return result


def write_new(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())


def save(relative,value):
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    path=destination(relative);write_new(path,raw)
    return {'path':str(path),'sha256':sha(raw),'bytes':len(raw)}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


class Acquisition:
    def __init__(self,prior=None):
        if prior:
            self.start=prior['started_monotonic'];self.bytes=prior['actual_received_bytes'];self.events=prior['requests'][:]
        else:
            self.start=time.monotonic();self.bytes=0;self.events=[]
        self.opener=build_opener(NoRedirect,HTTPSHandler(context=ssl.create_default_context()))
        self.requests_started=len(self.events)

    def elapsed(self):return time.monotonic()-self.start

    def local_count(self):return sum(1 for p in ROOT.rglob('*') if p.is_file())

    def get(self,url,relative):
        deadline=time.monotonic()+PER_FILE_SECONDS
        def alarm_handler(*unused):raise TimeoutError('hard per-file/global deadline exceeded')
        signal.signal(signal.SIGALRM,alarm_handler)
        target=destination(relative)
        if target.exists() or target.with_name(target.name+'.partial').exists():raise ValueError('exclusive file already exists')
        seen=set();redirects=[]
        for _ in range(6):
            checked_url(url)
            if url in seen:raise ValueError('redirect loop')
            seen.add(url)
            remaining=min(deadline-time.monotonic(),NETWORK_SECONDS-self.elapsed())
            if remaining<=0:raise TimeoutError('network budget exhausted')
            if self.local_count()>=MAX_FILES:raise ValueError('64-file limit reached')
            row={'url':url,'target':str(target),'started_monotonic':time.monotonic(),'body_bytes':0,'status':None}
            self.events.append(row)
            signal.setitimer(signal.ITIMER_REAL,remaining)
            try:
                req=Request(url,headers={'User-Agent':'edgeWorld-I20-CC0-audit/1.0','Accept-Encoding':'identity'})
                try:response=self.opener.open(req,timeout=remaining)
                except HTTPError as e:response=e
                with response:
                    row['status']=response.status
                    row['content_type']=response.headers.get('Content-Type')
                    row['content_length']=response.headers.get('Content-Length')
                    if response.headers.get('Content-Encoding') not in (None,'identity'):
                        raise ValueError('encoded body rejected; exact payload accounting required')
                    location=response.headers.get('Location')
                    redirect=response.status in (301,302,303,307,308)
                    if redirect:
                        if not location:raise ValueError('redirect without Location')
                        following=checked_url(urljoin(url,location))
                        redirects.append({'from':url,'to':following,'status':response.status})
                        output=destination('network/redirect-%02d.bin'%len(self.events))
                    else:output=target.with_name(target.name+'.partial')
                    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                    md5=hashlib.md5();digest=hashlib.sha256()
                    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                    with os.fdopen(fd,'wb') as f:
                        while True:
                            if time.monotonic()>=deadline or self.elapsed()>=NETWORK_SECONDS:
                                raise TimeoutError('actual file/global deadline exceeded')
                            if self.bytes>=LIMIT:raise ValueError('actual received body budget exhausted')
                            block=response.read(min(65536,LIMIT-self.bytes))
                            if not block:break
                            self.bytes+=len(block);row['body_bytes']+=len(block)
                            f.write(block);md5.update(block);digest.update(block)
                            if self.bytes>LIMIT:raise ValueError('actual received body bytes exceed256MiB')
                        f.flush();os.fsync(f.fileno())
                    row.update(ended_monotonic=time.monotonic(),body_ref={'path':str(output),'bytes':row['body_bytes'],
                        'sha256':digest.hexdigest(),'md5':md5.hexdigest()},redirects=redirects[:])
                    if redirect:url=following;continue
                    if response.status!=200:raise ValueError('HTTP status '+str(response.status))
                    if time.monotonic()>deadline:raise TimeoutError('per-file deadline exceeded')
                    os.rename(output,target)
                    row['body_ref']['path']=str(target);row['complete']=True
                    return row['body_ref']
            except BaseException as error:
                row['error']=str(error);row['ended_monotonic']=time.monotonic()
                if 'output' in locals() and output.exists():
                    raw=output.read_bytes()
                    row['body_ref']={'path':str(output),'bytes':len(raw),'sha256':sha(raw),
                        'md5':hashlib.md5(raw).hexdigest(),'partial':True}
                raise
            finally:signal.setitimer(signal.ITIMER_REAL,0)
        raise ValueError('too many redirects')

    def ledger(self,phase,error=None):
        return {'format':'universe-i20-acquisition-ledger.v1','phase':phase,'started_monotonic':self.start,
            'recorded_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':self.elapsed(),
            'actual_received_bytes':self.bytes,'network_limit_bytes':LIMIT,'network_seconds_limit':NETWORK_SECONDS,
            'per_file_seconds_limit':PER_FILE_SECONDS,'file_count':self.local_count(),'file_limit':MAX_FILES,
            'requests':self.events,'error':str(error) if error else None,'no_retries':True,
            'scope':'all response bodies including metadata/license/redirect/partial; no execution/import'}


def metadata():
    if ROOT.exists():raise ValueError('new acquisition root must not exist')
    for p in ROOT.parents:
        if p.is_symlink():raise ValueError('root parent symlink')
    ROOT.mkdir(mode=0o700)
    acquisition=Acquisition();refs={};error=None
    try:
        for asset in ASSETS:
            refs[asset]={}
            for kind in ('info','files'):
                refs[asset][kind]=acquisition.get('https://api.polyhaven.com/'+kind+'/'+asset,
                    'metadata/'+asset+'-'+kind+'.json')
                json.loads(Path(refs[asset][kind]['path']).read_bytes())
        refs['license']=acquisition.get('https://polyhaven.com/license','metadata/polyhaven-license.html')
        refs['cc0']=acquisition.get('https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt','metadata/CC0-1.0.txt')
    except BaseException as e:error=e
    ledger=save('metadata-ledger.json',acquisition.ledger('metadata',error))
    result=save('metadata-receipt.json',{'metadata_refs':refs,'ledger_ref':ledger,
        'helper_ref':{'path':str(Path(__file__).resolve()),'sha256':sha(Path(__file__).read_bytes())},
        'status':'metadata_complete' if error is None else 'failed'})
    print(json.dumps(result),flush=True)
    if error:raise error


if __name__=='__main__':
    if sys.argv[1:]!=['metadata']:raise SystemExit('usage: acquire.py metadata')
    metadata()
