"""Read-only first-kick ending scalars; no original buffers or instructions emitted."""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

COUNT=-1
BASE=0
ENVELOPE=0
POINTS={}
PENDING=None
OUTPUT=None


def memory(process,address,n):
    error=lldb.SBError();data=process.ReadMemory(address,n,error)
    if not error.Success() or len(data)!=n:raise RuntimeError('Scalar read failed: '+str(error))
    return data


def before(frame,location,internal):
    global COUNT,PENDING
    COUNT+=1
    process=frame.GetThread().GetProcess();envelope=memory(process,ENVELOPE,20)
    value=struct.unpack_from('<f',envelope,12)[0];rising=struct.unpack_from('<H',envelope,8)[0]
    if value!=0 or rising:return False
    error=lldb.SBError();sample=frame.FindRegister('xmm0').GetData().GetFloat(error,0)
    if not error.Success():raise RuntimeError('Cannot read last output scalar')
    PENDING=dict(active_block=COUNT,state_before=struct.unpack('<H',memory(process,BASE+0x8c54,2))[0],tone_value=value,tone_rising=rising,last_output=sample)
    POINTS['after'].SetEnabled(True)
    return False


def after(frame,location,internal):
    global PENDING
    if PENDING is None:return False
    process=frame.GetThread().GetProcess();PENDING['state_after']=struct.unpack('<H',memory(process,BASE+0x8c54,2))[0]
    with OUTPUT.open('a') as f:f.write(json.dumps(PENDING)+'\n')
    done=PENDING['state_after']==0 or COUNT>=1100;PENDING=None;location.GetBreakpoint().SetEnabled(False)
    if done:POINTS['before'].SetEnabled(False)
    return False


def setup(frame,location,internal):
    global BASE,ENVELOPE
    if frame.FindRegister('rsi').GetValueAsUnsigned()!=1:return False
    module=frame.GetModule();binary=Path(str(module.GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original binary')
    target=frame.GetThread().GetProcess().GetTarget();BASE=frame.FindRegister('rdi').GetValueAsUnsigned();ENVELOPE=module.ResolveFileAddress(0xc05654).GetLoadAddress(target)
    for name,address in [('before',0x136bb),('after',0x13703)]:
        point=target.BreakpointCreateByAddress(module.ResolveFileAddress(address).GetLoadAddress(target));point.SetScriptCallbackFunction(__name__+'.'+name);POINTS[name]=point
    POINTS['after'].SetEnabled(False);location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_VOICE_END_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::init_rndseed(int, int, int)');point.SetScriptCallbackFunction(__name__+'.setup')
