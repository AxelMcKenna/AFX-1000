"""Read-only scalar filter/startup-gain observation of the reviewed local original.

Set RMX_SCENE_FILTER_TRACE to a new ignored JSONL path, import in LLDB, then
run the Intel host. No original sample buffers or instructions are recorded.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import struct

import lldb

POINTS={'source':0x8854,'scene':0x24574,'scene_end':0x24ae4,'return_input':0x1982c}
COUNTS={}
BASE=0
MODULE=None
OUTPUT=None


def read(process,address,size):
    error=lldb.SBError();data=process.ReadMemory(address,size,error)
    if not error.Success() or len(data)!=size:raise RuntimeError('Scalar read failed: '+str(error))
    return data


def observe(frame,location,internal):
    process=frame.GetThread().GetProcess();target=process.GetTarget()
    stage=next(k for k,v in POINTS.items() if MODULE.ResolveFileAddress(v).GetLoadAddress(target)==frame.GetPC())
    count=COUNTS.get(stage,0);COUNTS[stage]=count+1
    def floats(offset,n):return list(struct.unpack('<'+'f'*n,read(process,BASE+offset,4*n)))
    def words(offset,n):return list(struct.unpack('<'+'H'*n,read(process,BASE+offset,2*n)))
    def rms(address):
        values=struct.unpack('<32f',read(process,address,128));return math.sqrt(sum(float(x)*x for x in values)/32)
    row=dict(stage=stage,block=count,source_gains=floats(0x1a04,12),source_count=words(0x1a34,5),
             scene_mix=floats(0x9324,6),scene_controls=words(0x92f4,5),scene_state=words(0x9308,3),
             scene_direct=floats(0x9240,3),direct_remaining=words(0x924c,1),direct_first=floats(0x9260,1)[0],direct_last=floats(0x92dc,1)[0],
             ramp_constants=floats(0x2bd4,3),effect_startup=floats(0xc270,2),filter_coefficients=floats(0x990c,10),feedback_coefficients=floats(0x9934,6),resonance=floats(0x994c,2),effect_levels=floats(0xa4a4,6),
             return_gain=floats(0xa4c0,1)[0],return_counters=list(struct.unpack('<4I',read(process,BASE+0xa4c4,16))))
    row['crush_hold']=floats(0xbbe0,3);row['processed_main']=words(0x9344,1)[0];row['effect_input_gain']=floats(0xe854,1)[0]
    if stage=='return_input':
        channels=[struct.unpack('<32f',read(process,frame.FindRegister(name).GetValueAsUnsigned(),128)) for name in ('rsi','rdx')]
        row['return_input_rms']=[math.sqrt(sum(float(x)*x for x in values)/32) for values in channels]
        row['unfiltered_feed_rms']=[rms(BASE+offset) for offset in (0x9abc,0x9b3c)]
        step,progress=row['effect_startup'];gains=[]
        def f(value):return struct.unpack('<f',struct.pack('<f',value))[0]
        for _ in range(32):progress=f(progress+step);gains.append(progress)
        row['return_weighted_rms']={str(power):[math.sqrt(sum((float(x)*(g**power))**2 for x,g in zip(values,gains))/32) for values in channels] for power in (1,2,3,4)}
    with OUTPUT.open('a') as stream:stream.write(json.dumps(row)+'\n')
    if COUNTS[stage]>=64:location.GetBreakpoint().SetEnabled(False)
    return False


def setup(frame,location,internal):
    global BASE,MODULE
    MODULE=frame.GetModule();binary=Path(str(MODULE.GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original binary')
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();target=frame.GetThread().GetProcess().GetTarget()
    for stage,address in POINTS.items():
        point=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(address).GetLoadAddress(target));point.SetScriptCallbackFunction(__name__+'.observe')
    location.GetBreakpoint().SetEnabled(False)
    # The first source entry is this setup stop; explicitly record its scalars.
    observe(frame,location,internal)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_SCENE_FILTER_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::source_select()');point.SetScriptCallbackFunction(__name__+'.setup')
