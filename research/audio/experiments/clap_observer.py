"""LLDB scalar-only observer for the reviewed local original; writes no DSP state.

Import with `command script import ABSOLUTE_PATH` before `run` on the Intel
reference host. Set RMX_CLAP_TRACE to a new ignored .jsonl destination first.
No original buffers, instructions or executable are emitted by this observer.
"""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

POINTS={'source':0x12765,'filtered':0x127d8,'envelope':0x12868,'output':0x129a1}
COUNTS={}
MODULE=None
BASE=0
OUTPUT=None


def read(process,address,size):
    error=lldb.SBError();data=process.ReadMemory(address,size,error)
    if not error.Success() or len(data)!=size:raise RuntimeError('Scalar observation failed: '+str(error))
    return data


def observe(frame,location,internal):
    process=frame.GetThread().GetProcess();target=process.GetTarget()
    stage=next(k for k,v in POINTS.items() if MODULE.ResolveFileAddress(v).GetLoadAddress(target)==frame.GetPC())
    count=COUNTS.get(stage,0);COUNTS[stage]=count+1
    def floats(offset,n):return list(struct.unpack('<'+'f'*n,read(process,BASE+offset,4*n)))
    def envelope(address):
        address=MODULE.ResolveFileAddress(address).GetLoadAddress(target);data=read(process,address,20)
        return dict(attack=struct.unpack_from('<f',data)[0],decay=struct.unpack_from('<f',data,4)[0],
                    flags=list(struct.unpack_from('<HH',data,8)),value=struct.unpack_from('<f',data,12)[0],position=struct.unpack_from('<f',data,16)[0])
    row=dict(stage=stage,subblock=count,saw_phase=floats(0xe458,1)[0],
             elapsed_frames=struct.unpack('<i',read(process,BASE+0xe45c,4))[0],gain=floats(0xe2b4,1)[0],
             custom=list(struct.unpack('<HHH',read(process,BASE+0xe2c8,6))),
             pitch_controls=list(struct.unpack('<HHH',read(process,BASE+0xcfde,6))),
             pitch_raw=struct.unpack('<H',read(process,BASE+0x76d6,2))[0],
             envelopes={name:envelope(address) for name,address in [('noise',0xc056cc),('tail',0xc056e0)]},
             filters={name:dict(coefficients=floats(address+16,5),frequency=floats(address+36,1)[0],q=floats(address+40,1)[0])
                      for name,address in [('bandpass',0xe3d4),('highpass',0xe400),('lowpass1',0xe42c)]})
    with OUTPUT.open('a') as stream:stream.write(json.dumps(row)+'\n')
    if COUNTS[stage]>=128:location.GetBreakpoint().SetEnabled(False)
    return False


def setup(frame,location,internal):
    global BASE,MODULE
    if frame.FindRegister('rsi').GetValueAsUnsigned()!=3:return False
    MODULE=frame.GetModule();binary=Path(str(MODULE.GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':
        raise RuntimeError('Requires the reviewed original 2.2.0 Intel binary')
    target=frame.GetThread().GetProcess().GetTarget();BASE=frame.FindRegister('rdi').GetValueAsUnsigned()
    for address in POINTS.values():
        point=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(address).GetLoadAddress(target))
        point.SetScriptCallbackFunction(__name__+'.observe')
    location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_CLAP_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::init_rndseed(int, int, int)')
    point.SetScriptCallbackFunction(__name__+'.setup')
