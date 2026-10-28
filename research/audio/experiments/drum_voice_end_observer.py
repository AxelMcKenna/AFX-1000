"""Read-only controller scalars and block peaks; never exports original audio buffers."""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

COUNT=0
PENDING=None
RETURN=None
OUTPUT=None


def memory(process,address,n):
    error=lldb.SBError();data=process.ReadMemory(address,n,error)
    if not error.Success() or len(data)!=n:raise RuntimeError('Cannot read reviewed controller scalars: '+str(error))
    return data


def scalars(process,base,buffer):
    samples=struct.unpack('<32f',memory(process,buffer,128))
    return dict(controller_words=list(struct.unpack('<24H',memory(process,base+0xe290,48))),
      gain_values=list(struct.unpack('<4f',memory(process,base+0xe2ac,16))),
      peak=max(abs(v) for v in samples),last=samples[-1])


def returned(frame,location,internal):
    global PENDING
    if PENDING is None:return False
    process=frame.GetThread().GetProcess();row,base,buffer=PENDING;row['after']=scalars(process,base,buffer);PENDING=None
    with OUTPUT.open('a') as f:f.write(json.dumps(row)+'\n')
    return False


def enter(frame,location,internal):
    global COUNT,PENDING,RETURN
    pad=frame.FindRegister('rsi').GetValueAsUnsigned()&0xffff
    if pad!=0:return False
    index=COUNT;COUNT+=1
    if index>=1700:location.GetBreakpoint().SetEnabled(False);return False
    if index<280:return False
    process=frame.GetThread().GetProcess();base=frame.FindRegister('rdi').GetValueAsUnsigned();buffer=frame.FindRegister('rdx').GetValueAsUnsigned()
    if RETURN is None:
        binary=Path(str(frame.GetModule().GetFileSpec()))
        if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original binary')
        address=struct.unpack('<Q',memory(process,frame.FindRegister('rsp').GetValueAsUnsigned(),8))[0]
        RETURN=process.GetTarget().BreakpointCreateByAddress(address);RETURN.SetScriptCallbackFunction(__name__+'.returned')
    PENDING=(dict(block=index,before=scalars(process,base,buffer)),base,buffer)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_VOICE_END_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::control_1shot_osc(short, float*)')
    point.SetScriptCallbackFunction(__name__+'.enter')
