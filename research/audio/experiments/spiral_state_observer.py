"""Read-only sparse Spiral envelope/filter scalars; no original sample buffers."""
import hashlib
import json
import os
from pathlib import Path
import struct
import lldb

OUTPUT=None
BASE=0
MODULE=None
AFTER=None
NEXT=0
PENDING=None
SAMPLES=[0,1,2,3,4,5,*range(1495,1575),*range(1900,2130),*range(3000,3020)]
if os.environ.get('RMX_SPIRAL_SAMPLES'):SAMPLES=[int(v) for v in os.environ['RMX_SPIRAL_SAMPLES'].split(',')]


def read(process,address,n):
    error=lldb.SBError();b=process.ReadMemory(address,n,error)
    if not error.Success() or len(b)!=n:raise RuntimeError('Spiral scalar read failed: '+str(error))
    return b


def state(frame):
    process=frame.GetThread().GetProcess()
    fields={'sample_quiet':(0xe558,'I'),'block_average_count':(0xe560,'I'),'input_peak':(0xe564,'f'),'activity_peak':(0xe568,'f'),'average_peak':(0xe56c,'f'),'clip_threshold':(0xe574,'f'),'loop_delay':(0xe578,'d'),'held_peak':(0xe584,'f'),'feedback_gain':(0xa810,'3f'),'wet_gain':(0x98c8,'3f'),'input_gain':(0xe854,'f')}
    return {name:list(struct.unpack('<'+fmt,read(process,BASE+offset,struct.calcsize('<'+fmt)))) for name,(offset,fmt) in fields.items()}


def after(frame,location,internal):
    global PENDING
    PENDING['after']=state(frame)
    with OUTPUT.open('a') as f:f.write(json.dumps(PENDING)+'\n')
    PENDING=None;location.GetBreakpoint().SetEnabled(False);return False


def before(frame,location,internal):
    global BASE,MODULE,AFTER,NEXT,PENDING
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();MODULE=frame.GetModule();process=frame.GetThread().GetProcess();target=process.GetTarget()
    if NEXT==0:
        p=Path(str(MODULE.GetFileSpec()))
        if hashlib.sha256(p.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original binary')
        constants={name:list(struct.unpack('<6f',read(process,MODULE.ResolveFileAddress(address).GetLoadAddress(target),24))) for name,address in [('loop_highpass',0xc05270),('loop_lowpass',0xc05290),('source_filter',0xc052b0),('filter2',0xc052d0),('filter3',0xc052f0),('output_filter',0xc05310)]}
        with OUTPUT.open('a') as f:f.write(json.dumps(dict(kind='coefficient_scalars',values=constants))+'\n')
    index=SAMPLES[NEXT];NEXT+=1;PENDING=dict(kind='state',block=index,before=state(frame))
    if AFTER is None:
        AFTER=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(0x23ee0).GetLoadAddress(target));AFTER.SetScriptCallbackFunction(__name__+'.after')
    AFTER.SetEnabled(True)
    if NEXT==len(SAMPLES):location.GetBreakpoint().SetEnabled(False)
    else:location.GetBreakpoint().SetIgnoreCount(SAMPLES[NEXT]-index-1)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_SPIRAL_STATE_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_spiral(float*, float*)');point.SetScriptCallbackFunction(__name__+'.before')
