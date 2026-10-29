"""Read-only sparse Release-control/state scalars; no original audio or instructions."""
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
SAMPLES=[0,1,2,3,4,5,6,*range(2998,3016),*range(3748,3765),*range(4498,4515),*range(7498,7520)]
if os.environ.get('RMX_RELEASE_SAMPLES'):SAMPLES=[int(v) for v in os.environ['RMX_RELEASE_SAMPLES'].split(',')]


def read(process,address,n):
    error=lldb.SBError();b=process.ReadMemory(address,n,error)
    if not error.Success() or len(b)!=n:raise RuntimeError('Scalar read failed: '+str(error))
    return b


def state(frame):
    process=frame.GetThread().GetProcess()
    def values(offset,fmt):return list(struct.unpack('<'+fmt,read(process,BASE+offset,struct.calcsize('<'+fmt))))
    return dict(release_header=values(0xc294,'7H'),master=values(0xc284,'2f'),ramps=values(0x2bd4,'4f'),echo_mix=values(0xc8fc,'3f'),echo_state=values(0xc908,'2HI'),echo_ages=values(0x9318,'I'),echo_control=values(0xcc10,'5f'),echo_periods=values(0xcc24,'3I'),echo_gates=values(0xcc30,'5f'),echo_delay=values(0xcc44,'I'),echo_map=values(0xcc48,'11f'),custom_slots=values(0xcf8c,'7H'),brake=values(0xc3f8,'6f'),brake_ticks=values(0xc410,'IH'),brake_gain=values(0xc2c8,'f'),brake_write_frame=[(values(0xc2e8,'Q')[0]-values(0xc2d0,'Q')[0])//8],brake_read_frame=[(values(0xc2f0,'Q')[0]-values(0xc2d0,'Q')[0])//8],spin_motion=values(0xcdd0,'4f'),spin_shape=values(0xcde8,'3f'),spin_fade=values(0xce04,'f'),spin_copy_flag=values(0xcde0,'H'),spin_read_frames=[(values(0xccb8,'Q')[0]-values(0xcc80,'Q')[0])//8])


def after(frame,location,internal):
    global PENDING
    PENDING['after']=state(frame)
    with OUTPUT.open('a') as f:f.write(json.dumps(PENDING)+'\n')
    PENDING=None;location.GetBreakpoint().SetEnabled(False);return False


def before(frame,location,internal):
    global BASE,MODULE,AFTER,NEXT,PENDING
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();MODULE=frame.GetModule()
    if NEXT==0:
        path=Path(str(MODULE.GetFileSpec()))
        if hashlib.sha256(path.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original binary')
    index=SAMPLES[NEXT];NEXT+=1;PENDING=dict(block=index,before=state(frame),observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if AFTER is None:
        target=frame.GetThread().GetProcess().GetTarget();AFTER=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(0x17b28).GetLoadAddress(target));AFTER.SetScriptCallbackFunction(__name__+'.after')
    AFTER.SetEnabled(True)
    if NEXT==len(SAMPLES):location.GetBreakpoint().SetEnabled(False)
    else:location.GetBreakpoint().SetIgnoreCount(SAMPLES[NEXT]-index-1)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_RELEASE_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::relfx_subproc()');point.SetScriptCallbackFunction(__name__+'.before')
