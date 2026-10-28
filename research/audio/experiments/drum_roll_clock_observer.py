"""Observe sparse original beat-clock scalars without writing DSP state."""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

OUTPUT=None
MODULE=None
BASE=0
INDEX=-1
NEXT=0
PENDING=None
AFTER=None
SAMPLES=[0,1,2,3,4,5,6,7,8,9,10,11,12,15,20,100,186,187,188,189,374,375,376,750,1500,1501,3000]
if os.environ.get('RMX_ROLL_CLOCK_SAMPLES'):SAMPLES=[int(v) for v in os.environ['RMX_ROLL_CLOCK_SAMPLES'].split(',')]


def read(process,address,n):
    error=lldb.SBError();b=process.ReadMemory(address,n,error)
    if not error.Success() or len(b)!=n:raise RuntimeError('Clock scalar read failed: '+str(error))
    return b


def state(frame):
    process=frame.GetThread().GetProcess();b=read(process,BASE+0x198,64)
    return dict(phase=struct.unpack('<d',read(process,BASE,8))[0],timeline=struct.unpack_from('<d',b,0)[0],
      correction=struct.unpack_from('<d',b,8)[0],initial_frames=struct.unpack_from('<i',b,16)[0],tap_offset=struct.unpack_from('<d',b,24)[0],
      last_increment=struct.unpack_from('<d',b,48)[0],roll_offset=struct.unpack_from('<d',b,56)[0])


def emit(row):
    with OUTPUT.open('a') as f:f.write(json.dumps(row)+'\n')


def initialize(frame):
    global BASE,MODULE
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();MODULE=frame.GetModule();p=Path(str(MODULE.GetFileSpec()))
    if hashlib.sha256(p.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original binary')


def tick_after(frame,location,internal):
    global PENDING
    if PENDING is not None:PENDING['after']=state(frame);emit(PENDING);PENDING=None
    location.GetBreakpoint().SetEnabled(False);return False


def tick(frame,location,internal):
    global INDEX,NEXT,PENDING,AFTER
    initialize(frame);INDEX=SAMPLES[NEXT];NEXT+=1
    error=lldb.SBError();increment=frame.FindRegister('xmm0').GetData().GetDouble(error,0)
    if not error.Success():raise RuntimeError('Cannot read clock increment')
    PENDING=dict(kind='tick',index=INDEX,increment=increment,before=state(frame))
    if AFTER is None:
        target=frame.GetThread().GetProcess().GetTarget();AFTER=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(0x44df).GetLoadAddress(target));AFTER.SetScriptCallbackFunction(__name__+'.tick_after')
    AFTER.SetEnabled(True)
    if NEXT==len(SAMPLES):location.GetBreakpoint().SetEnabled(False)
    else:location.GetBreakpoint().SetIgnoreCount(SAMPLES[NEXT]-INDEX-1)
    return False


def offset(frame,location,internal):
    initialize(frame);emit(dict(kind='roll-offset-before',quantize=frame.FindRegister('rsi').GetValueAsUnsigned()&0xffffffff,state=state(frame)))
    target=frame.GetThread().GetProcess().GetTarget();point=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(0x4c7f).GetLoadAddress(target));point.SetScriptCallbackFunction(__name__+'.offset_after')
    return False


def offset_after(frame,location,internal):
    emit(dict(kind='roll-offset-after',state=state(frame)));location.GetBreakpoint().SetEnabled(False);return False


def tap(frame,location,internal):
    initialize(frame);emit(dict(kind='tap-offset-before',state=state(frame)))
    target=frame.GetThread().GetProcess().GetTarget();point=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(0x48ce).GetLoadAddress(target));point.SetScriptCallbackFunction(__name__+'.tap_after')
    return False


def tap_after(frame,location,internal):
    emit(dict(kind='tap-offset-after',state=state(frame)));location.GetBreakpoint().SetEnabled(False);return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_ROLL_CLOCK_TRACE'])
    with OUTPUT.open('x'):pass
    for name,callback in [('BeatManager::SetBaseBeatTime(double)',tick),('BeatManager::SetNormalRollOffset(int)',offset),('BeatManager::CalcOffsetNoQuantizeForTap(int*, int, int)',tap)]:
        point=debugger.GetSelectedTarget().BreakpointCreateByName(name);point.SetScriptCallbackFunction(__name__+'.'+callback.__name__)
