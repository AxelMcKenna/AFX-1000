"""Read-only scalar startup/source-gain observation of the reviewed local original.

Set RMX_SCENE_ROUTE_TRACE to a new ignored JSONL path, import in LLDB, then
run the Intel host. No original sample buffers or instructions are recorded.
"""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

POINTS={'source':0x8854,'scene':0x24574,'scene_end':0x24ae4}
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
    row=dict(stage=stage,block=count,source_gains=floats(0x1a04,12),source_count=words(0x1a34,5),
             scene_mix=floats(0x9324,6),scene_controls=words(0x92f4,5),scene_state=words(0x9308,3),
             scene_direct=floats(0x9240,3),direct_remaining=words(0x924c,1),direct_first=floats(0x9260,1)[0],direct_last=floats(0x92dc,1)[0],
             ramp_constants=floats(0x2bd4,3))
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
    OUTPUT=Path(os.environ['RMX_SCENE_ROUTE_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::source_select()');point.SetScriptCallbackFunction(__name__+'.setup')
