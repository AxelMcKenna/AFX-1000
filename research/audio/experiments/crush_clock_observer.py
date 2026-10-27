"""Read-only long-run Crush scalar clock observation; no sample buffers.

Set RMX_CRUSH_CLOCK_TRACE to a new ignored JSONL path and import in LLDB.
The reviewed original binary is checked before installing a scene-end probe.
"""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

BASE=0
COUNT=0
OUTPUT=None


def observe(frame,location,internal):
    global COUNT
    process=frame.GetThread().GetProcess();error=lldb.SBError()
    data=process.ReadMemory(BASE+0xbbe0,12,error)
    if not error.Success() or len(data)!=12:raise RuntimeError('Clock scalar read failed')
    fraction,left,right=struct.unpack('<3f',data)
    with OUTPUT.open('a') as stream:
        stream.write(json.dumps(dict(block=COUNT,fraction=fraction,held=[left,right]))+'\n')
    COUNT+=1
    if COUNT>=9000:location.GetBreakpoint().SetEnabled(False)
    return False


def setup(frame,location,internal):
    global BASE
    module=frame.GetModule();binary=Path(str(module.GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original binary')
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();target=frame.GetThread().GetProcess().GetTarget()
    point=target.BreakpointCreateByAddress(module.ResolveFileAddress(0x24ae4).GetLoadAddress(target))
    point.SetScriptCallbackFunction(__name__+'.observe');location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_CRUSH_CLOCK_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::source_select()')
    point.SetScriptCallbackFunction(__name__+'.setup')
