"""Sparse read-only Isolator control/envelope scalars, never sample buffers."""
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
SAMPLES=[0,1,2,3,4,5,6,7,8,9,10,1499,1500,2998,2999,3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3011,3012,3013,3014,3100,3375,3750,4500,7498,7499,7500,7501,7502,7503,7504,7505,7506,7507,7508,7509,7510]
if os.environ.get('RMX_ISOLATE_SAMPLES'):SAMPLES=[int(v) for v in os.environ['RMX_ISOLATE_SAMPLES'].split(',')]


def read(process,address,n):
    error=lldb.SBError();value=process.ReadMemory(address,n,error)
    if not error.Success() or len(value)!=n:raise RuntimeError('Isolator scalar read failed '+str(error))
    return value


def state(frame):
    process=frame.GetThread().GetProcess()
    def values(offset,fmt):return list(struct.unpack('<'+fmt,read(process,BASE+offset,struct.calcsize('<'+fmt))))
    return dict(master=values(0x2bfc,'2f'),header=values(0x2c04,'4H'),gate_settings=values(0x2c0c,'3H'),drive_settings=values(0x2c12,'3H'),knobs=values(0x2c18,'3H'),block_peak=values(0x6eec,'3f'),history_position=values(0x6ee6,'3H'),level_peak=values(0x7020,'3f'),level_held=values(0x702c,'3f'),level_step=values(0x7038,'3f'),level_smoothed=values(0x7044,'3f'),level_ramp=values(0x7050,'3H'),level_wait=values(0x7018,'3H'),level_target=values(0x70dc,'3f'),side=values(0x36b6,'3h'),side_pending=values(0x36bc,'3H'),neutral_ramp=values(0x36c2,'3H'),neutral_mix=values(0x36cc,'3f'),neutral_step=values(0x36d8,'3f'),drive_mix=values(0x6ed4,'3f'),drive_step=values(0x6ec8,'3f'),gate_gain=values(0x7568,'3f'),gate_envelope=values(0x7580,'3f'),gate_level=values(0x758c,'3f'),gate_target=values(0x7598,'3f'),gate_step=values(0x75a4,'3f'),gate_blocks=values(0x75b0,'3f'),drive_gain_previous=values(0x76ac,'3f'),drive_gain=values(0x76b8,'3f'))


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
    OUTPUT=Path(os.environ['RMX_ISOLATE_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::isofx_subproc()');point.SetScriptCallbackFunction(__name__+'.before');point.SetIgnoreCount(SAMPLES[0])
