"""Private temporary excitation samples for a numerical whiteness diagnostic."""
import os
import hashlib
import json
from pathlib import Path
import struct

import lldb
import noise_return_observer as parent

BASE_SAMPLE = parent.sample
WHITE = None
COEFFICIENTS = None
CONTROL = hashlib.sha256()
SWEEP = None


def sample(frame, location, internal):
    global SWEEP
    BASE_SAMPLE(frame,location,internal)
    process=frame.GetThread().GetProcess();base=frame.FindRegister('r14').GetValueAsUnsigned();channels=[]
    for offset in [0x9abc,0x9b3c]:
        error=lldb.SBError();data=process.ReadMemory(base+offset,128,error)
        if not error.Success() or len(data)!=128:raise RuntimeError('Excitation read failed')
        channels.append(struct.unpack('<32f',data))
    WHITE.write(struct.pack('<64f',*[v for pair in zip(*channels) for v in pair]))
    def read(offset,size):
        error=lldb.SBError();data=process.ReadMemory(base+offset,size,error)
        if not error.Success() or len(data)!=size:raise RuntimeError('Coefficient read failed')
        return data
    controls=read(0xa610,128);CONTROL.update(controls);values=struct.unpack('<32f',controls)
    coefficients=struct.unpack('<10f',read(0x990c,40));feedback=struct.unpack('<2f',read(0x994c,8))
    main=struct.unpack('<H',read(0x9344,2))[0]
    COEFFICIENTS.write(struct.pack('<15f',*coefficients,*feedback,float(main),values[0],values[16]))
    if SWEEP is None:SWEEP=list(struct.unpack('<4f',read(0x9a9c,16)))
    return False


def finish():
    WHITE.close();COEFFICIENTS.close();parent.finish()
    path=Path(os.environ['RMX_NOISE_RETURN_SCALARS']);record=json.loads(path.read_text())
    record.update(control_sha256=CONTROL.hexdigest(),sweep=SWEEP)
    path.write_text(json.dumps(record,indent=2)+'\n')


def enter(frame, location, internal):
    binary=Path(str(frame.GetModule().GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong Original')
    point=frame.GetThread().GetProcess().GetTarget().BreakpointCreateByAddress(frame.GetPC()+2250)
    point.SetScriptCallbackFunction(__name__+'.sample');location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger, internal):
    global WHITE, COEFFICIENTS
    WHITE=Path(os.environ['RMX_NOISE_WHITE']).open('xb')
    COEFFICIENTS=Path(os.environ['RMX_NOISE_COEFFICIENTS']).open('xb')
    parent.OUTPUT=Path(os.environ['RMX_NOISE_DIRECT']).open('xb')
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
    point.SetScriptCallbackFunction(__name__+'.enter')
