"""Read-only computed Scene control values; no sample buffers or PRNG state."""
import hashlib,json,os,struct
from pathlib import Path
import lldb
BASE=0
BLOCK=0
OUTPUT=None


def observe(frame,location,internal):
    global BLOCK
    p=frame.GetThread().GetProcess();error=lldb.SBError()
    def read(offset,fmt):
        n=struct.calcsize(fmt);data=p.ReadMemory(BASE+offset,n,error)
        if not error.Success() or len(data)!=n:raise RuntimeError('Read-only Scene control observation failed')
        return list(struct.unpack(fmt,data))
    row=dict(block=BLOCK,scene_controls=read(0x92f4,'<5H'),processed_main=read(0x9344,'<H')[0],main_slewed=read(0x933e,'<H')[0],scene_direct=read(0x9240,'<3f'),return_controls=read(0xa4a4,'<6f'),return_weights_targets_steps=read(0x9c40,'<12f'),return_remaining=read(0x9c70,'<H')[0],source_gains=read(0x1a04,'<12f'),source_counts=read(0x1a34,'<5H'),scene_phase=read(0x930c,'<H')[0],scene_initializing=read(0x9308,'<H')[0],common_wet=read(0x9330,'<3f'))
    with OUTPUT.open('a') as f:f.write(json.dumps(row)+'\n')
    BLOCK+=1
    if BLOCK>=320:location.GetBreakpoint().SetEnabled(False)
    return False


def setup(frame,location,internal):
    global BASE
    module=frame.GetModule();binary=Path(str(module.GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong Original binary')
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();target=frame.GetThread().GetProcess().GetTarget();point=target.BreakpointCreateByAddress(module.ResolveFileAddress(0x24ae4).GetLoadAddress(target));point.SetScriptCallbackFunction(__name__+'.observe');location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_SCENE_MOTION_TRACE'])
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::source_select()');point.SetScriptCallbackFunction(__name__+'.setup')
