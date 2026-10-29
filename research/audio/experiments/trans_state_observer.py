"""Sparse read-only Trans/Roll clocks, pointer offsets and controls; never sample buffers."""
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
if os.environ.get('RMX_TRANS_SAMPLES'):SAMPLES=[int(v) for v in os.environ['RMX_TRANS_SAMPLES'].split(',')]


def read(process,address,n):
    error=lldb.SBError();value=process.ReadMemory(address,n,error)
    if not error.Success() or len(value)!=n:raise RuntimeError('Isolator scalar read failed '+str(error))
    return value


def state(frame):
    process=frame.GetThread().GetProcess()
    def values(offset,fmt):return list(struct.unpack('<'+fmt,read(process,BASE+offset,struct.calcsize('<'+fmt))))
    fields=dict(direct_current=(0x39d0,'3f'),ramp_constants=(0x2bd0,'5f'),ready_gain=(0x3988,'9f'),ready_step=(0x39ac,'9f'),voice_gain=(0x3e5c,'9f'),voice_step=(0x3e80,'9f'),grid_elapsed=(0x3ef4,'i'),grid_flag=(0x2c4e,'H'),mask_clock=(0x3660,'3i'),mask_duty=(0x3684,'3f'),mask_value=(0x36a8,'3f'),mask_step=(0x3690,'3f'),mask_countdown=(0x369c,'3i'),trans_elapsed=(0x3d8c,'3i'),trans_compensation=(0x3e30,'3h'),master=(0x2bfc,'2f'),header=(0x2c04,'4H'),patterns=(0x2c0c,'6H'),requested_knobs=(0x2c18,'3H'),current_knobs=(0x3052,'3H'),period=(0x3050,'H'),period_previous=(0x36b4,'H'),roll_init=(0x3d98,'3H'),trans_depth=(0x3d9e,'3H'),roll_depth=(0x3da4,'3H'),attack_age=(0x3daa,'3h'),recording=(0x3cdc,'3H'),capture_copy=(0x3ce2,'9H'),capture_level=(0x3de0,'9f'),roll_mix=(0x3ebc,'9f'),roll_direct=(0x3ee0,'3f'),roll_fade=(0x3dc8,'3f'),roll_step=(0x3dd4,'3f'),grid_counts=(0x3ef8,'9H'),grid_ticks=(0x3f0c,'3i'),grid_phase=(0x3f18,'3i'),input_attack=(0x7580,'3f'),level=(0x70dc,'3f'),level_current=(0x758c,'3f'),level_target=(0x7598,'3f'),level_step=(0x75a4,'3f'),level_countdown=(0x75b0,'3f'),trans_active=(0x3e04,'3H'),trans_start=(0x3f04,'3H'),trans_mix=(0x3970,'3f'),trans_gain=(0x3d54,'3f'),trans_target=(0x3d60,'3f'),trans_step=(0x3d6c,'3f'),trans_level=(0x3d78,'3i'),trans_countdown=(0x3d84,'3H'))
    result={name:values(offset,fmt) for name,(offset,fmt) in fields.items()}
    raw_base=values(0x3648,'3Q');roll_base=values(0x3868,'3Q')
    def offsets(offset,count,bases,voices=1):return [None if p==0 or bases[i//voices]==0 else (p-bases[i//voices])//8 for i,p in enumerate(values(offset,str(count)+'Q'))]
    result.update(raw_writer=offsets(0x3618,3,raw_base),raw_reader=offsets(0x3db0,3,raw_base),roll_writer=offsets(0x38b0,3,roll_base),roll_readers=offsets(0x38c8,9,roll_base,3),roll_end=offsets(0x3880,3,roll_base))
    return result


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
    OUTPUT=Path(os.environ['RMX_TRANS_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::isofx_subproc()');point.SetScriptCallbackFunction(__name__+'.before');point.SetIgnoreCount(SAMPLES[0])
