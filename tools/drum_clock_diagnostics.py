"""Fixed 32-frame callback-clock mapping for drum routing diagnostics.

This models the declared FIFO, not an audio alignment search. -1 marks host
passthrough slots not overwritten by a generated block. Never use this map to
realign candidate/reference audio for acceptance.
"""
import numpy as np


def clock_map(case,frames):
    indices=np.full(frames,-1,dtype=np.int64);received=available=head=generated=0;pending=np.zeros(32,dtype=np.int64)
    times=sorted({0,frames,*case['hits'],*[at+32 for at in case['hits']]});start=0;event=1
    while start<frames:
        count=min(case['block'],frames-start,times[event]-start);read=written=0
        while read<count:
            take=min(32-received,count-read);received+=take;read+=take;emit=min(available,count-written)
            indices[start+written:start+written+emit]=pending[head:head+emit];written+=emit;available-=emit;head+=emit
            if received==32:pending=np.arange(generated,generated+32);generated+=32;received=0;available=32;head=0
        start+=count
        if start==times[event]:event+=1
    return indices


def generated_view(audio,indices):
    output=np.zeros_like(audio);valid=np.zeros(len(audio),dtype=bool);mask=indices>=0
    output[indices[mask]]=audio[mask];valid[indices[mask]]=True
    return output,valid
