#!/usr/bin/env python3
"""Losslessly store a WAV as its exact container plus XOR against a native WAV.

This changes storage only: decoding must reproduce the complete WAV SHA256.
The native base is retained in each archive, using APFS copies where available.
"""
import argparse,base64,gzip,hashlib,json,os,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
import numpy as np


def digest(data):return hashlib.sha256(data).hexdigest()


def split(data):
    if data[:4]!=b'RIFF' or data[8:12]!=b'WAVE':raise ValueError('Requires little-endian RIFF/WAVE')
    offset=12
    while offset+8<=len(data):
        tag,size=struct.unpack_from('<4sI',data,offset);start=offset+8;end=start+size
        if end>len(data):raise ValueError('Truncated WAV chunk')
        if tag==b'data':return data[:start],data[start:end],data[end:]
        offset=end+(size&1)
    raise ValueError('Missing WAV data chunk')


def gzip_write(path,data):
    with Path(path).open('xb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',compresslevel=1,mtime=0) as z:z.write(data)


def file_hash(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def native_base(native,cache):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);sha=digest(native);path=cache/(sha+'.wav.gz')
    if not path.exists():
        handle=tempfile.NamedTemporaryFile(prefix='pending-',dir=cache,delete=False);tmp=Path(handle.name);handle.close()
        try:
            with tmp.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',compresslevel=1,mtime=0) as z:z.write(native)
            if path.exists():
                if file_hash(path)!=file_hash(tmp):raise ValueError('Native cache collision')
            else:os.replace(tmp,path)
        finally:
            if tmp.exists():tmp.unlink()
    with gzip.open(path,'rb') as z:
        if hashlib.file_digest(z,'sha256').hexdigest()!=sha:raise ValueError('Native cache bytes differ')
    return path


def pack(wav,native,directory,base_archive=None,cache=None):
    directory=Path(directory);prefix,pcm,suffix=split(wav);_,native_pcm,_=split(native)
    if len(pcm)!=len(native_pcm):raise ValueError('PCM lengths differ')
    source=Path(base_archive) if base_archive else native_base(native,cache)
    base=directory/'native-base.wav.gz';before=file_hash(source)
    if base.exists():raise FileExistsError(base)
    if sys.platform=='darwin':subprocess.run(['/bin/cp','-c',str(source),str(base)],check=True)
    else:shutil.copyfile(source,base)
    if file_hash(base)!=before or file_hash(source)!=before:raise ValueError('Native archive copy differs')
    delta=np.bitwise_xor(np.frombuffer(pcm,dtype=np.uint8),np.frombuffer(native_pcm,dtype=np.uint8)).tobytes()
    differences=directory/'audio-xor.bin.gz';gzip_write(differences,delta)
    meta=dict(kind='lossless-wav-xor-v1',wav_sha256=digest(wav),wav_bytes=len(wav),pcm_bytes=len(pcm),
        prefix=base64.b64encode(prefix).decode(),suffix=base64.b64encode(suffix).decode(),
        native_wav_sha256=digest(native),native_archive_sha256=before,xor_archive_sha256=file_hash(differences))
    path=directory/'audio.delta.json'
    with path.open('x') as f:json.dump(meta,f,indent=2);f.write('\n')
    if unpack(path)!=wav:raise ValueError('Lossless WAV round trip differs')
    return path


def unpack(path):
    path=Path(path);meta=json.loads(path.read_text())
    if meta['kind']!='lossless-wav-xor-v1':raise ValueError('Unsupported archive')
    base=path.parent/'native-base.wav.gz';delta=path.parent/'audio-xor.bin.gz'
    if file_hash(base)!=meta['native_archive_sha256'] or file_hash(delta)!=meta['xor_archive_sha256']:raise ValueError('Compressed archive changed')
    with gzip.open(base,'rb') as z:native=z.read()
    if digest(native)!=meta['native_wav_sha256']:raise ValueError('Native WAV changed')
    _,pcm,_=split(native)
    with gzip.open(delta,'rb') as z:difference=z.read()
    if len(pcm)!=len(difference) or len(pcm)!=meta['pcm_bytes']:raise ValueError('PCM archive extent differs')
    restored=np.bitwise_xor(np.frombuffer(pcm,dtype=np.uint8),np.frombuffer(difference,dtype=np.uint8)).tobytes()
    wav=base64.b64decode(meta['prefix'],validate=True)+restored+base64.b64decode(meta['suffix'],validate=True)
    if len(wav)!=meta['wav_bytes'] or digest(wav)!=meta['wav_sha256']:raise ValueError('Restored WAV bytes differ')
    return wav


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    data=unpack(a.archive)
    with a.output.open('xb') as f:f.write(data)
    print('Restored',len(data),'bytes; SHA256',digest(data))


if __name__=='__main__':main()
