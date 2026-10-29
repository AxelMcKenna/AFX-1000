"""Sparse read-only Cut/Add controls and filter coefficients; never sample buffers."""
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
SAMPLES=[0,4,5,6,2999,3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3011,3012,3013,3014,3015,3016,3017,3018,3020,3050,3100,3125,3180,3250,3375,3750,4000,4500,6000,7499,7500,7510]
if os.environ.get('RMX_CUT_SAMPLES'):SAMPLES=[int(v) for v in os.environ['RMX_CUT_SAMPLES'].split(',')]


def read(process,address,n):
    error=lldb.SBError();value=process.ReadMemory(address,n,error)
    if not error.Success() or len(value)!=n:raise RuntimeError('Isolator scalar read failed '+str(error))
    return value


def state(frame):
    process=frame.GetThread().GetProcess()
    def values(offset,fmt):return list(struct.unpack('<'+fmt,read(process,BASE+offset,struct.calcsize('<'+fmt))))
    fields=dict(master=(0x2bfc,'2f'),header=(0x2c04,'4H'),settings=(0x2c0c,'6H'),requested=(0x2c18,'3H'),current=(0x3052,'3H'),ramp_constants=(0x2bd0,'7f'),kick_filter_coefficients=(0x45a8,'30f'),kick_output_filter=(0x4820,'5f'),high_coefficients=(0x4ee8,'10f'),mid_coefficients=(0x4f10,'10f'),mid_feedback_coefficients=(0x6e70,'6f'),high_feedback_coefficients=(0x6e88,'6f'),low_gain=(0x4ae4,'f'),low_target=(0x6ea8,'f'),filter_settings=(0x6eac,'6H'),resonance_levels=(0x6eb8,'2f'),setting_ramp=(0x6ec0,'2H'),filter_feedback=(0x548c,'4f'),kick_depth=(0x54a8,'f'),manual_smoothing=(0x537c,'3f'))
    return {name:values(offset,fmt) for name,(offset,fmt) in fields.items()}



def after(frame,location,internal):
    global PENDING
    PENDING['after']=state(frame)
    with OUTPUT.open('a') as f:f.write(json.dumps(PENDING)+'\n')
    PENDING=None;location.GetBreakpoint().SetEnabled(False);return False


def before(frame,location,internal):
    global BASE,MODULE,AFTER,NEXT,PENDING
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();MODULE=frame.GetModule();process=frame.GetThread().GetProcess();target=process.GetTarget()
    if NEXT==0:
        path=Path(str(MODULE.GetFileSpec()))
        if hashlib.sha256(path.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong original DSP')
        coefficients={name:list(struct.unpack('<6f',read(process,MODULE.ResolveFileAddress(address).GetLoadAddress(target),24))) for name,address in [('lp284',0xc050d0),('hp284',0xc050f0),('lp4649',0xc05110),('hp4649',0xc05130)]}
        with OUTPUT.open('a') as f:f.write(json.dumps(dict(kind='coefficient_scalars',values=coefficients))+'\n')
    index=SAMPLES[NEXT];NEXT+=1;PENDING=dict(kind='state',block=index,before=state(frame),observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if AFTER is None:
        AFTER=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(0xfee7).GetLoadAddress(target));AFTER.SetScriptCallbackFunction(__name__+'.after')
    AFTER.SetEnabled(True)
    if NEXT==len(SAMPLES):location.GetBreakpoint().SetEnabled(False)
    else:location.GetBreakpoint().SetIgnoreCount(SAMPLES[NEXT]-index-1)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_CUT_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::isofx_subproc()');point.SetScriptCallbackFunction(__name__+'.before');point.SetIgnoreCount(SAMPLES[0])
