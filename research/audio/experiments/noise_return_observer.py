"""Temporarily sample the pre-return buffer for a bounded timing diagnostic.

The driver deletes this private intermediate with the ordinary/observed WAVs.
No manufacturer generator state is read or embedded in project DSP.
"""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

OUTPUT = None
COUNT = 0
SCALARS = []


def sample(frame, location, internal):
    global COUNT
    process=frame.GetThread().GetProcess()
    base=frame.FindRegister('r14').GetValueAsUnsigned()
    def read(address,size):
        error=lldb.SBError();data=process.ReadMemory(address,size,error)
        if not error.Success() or len(data)!=size:raise RuntimeError('Pre-return read failed')
        return data
    left=struct.unpack('<32f',read(base+0x997c,128))
    right=struct.unpack('<32f',read(base+0x99fc,128))
    OUTPUT.write(struct.pack('<64f',*[v for pair in zip(left,right) for v in pair]))
    if COUNT%137==0:
        target=struct.unpack('<2f',read(frame.FindRegister('rbp').GetValueAsUnsigned()-0x38,8))
        level=struct.unpack('<f',read(base+0x98fc,4))[0]
        SCALARS.append(dict(block=COUNT,main_level_targets=list(target),amount_level=level))
    COUNT+=1
    if COUNT>7000:raise RuntimeError('Diagnostic trace exceeded bound')
    return False


def enter(frame, location, internal):
    binary=Path(str(frame.GetModule().GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong Original')
    point=frame.GetThread().GetProcess().GetTarget().BreakpointCreateByAddress(frame.GetPC()+2250)
    point.SetScriptCallbackFunction(__name__+'.sample');location.GetBreakpoint().SetEnabled(False)
    return False


def finish():
    OUTPUT.close()
    with Path(os.environ['RMX_NOISE_RETURN_SCALARS']).open('x') as file:
        json.dump(dict(blocks=COUNT,scalars=SCALARS),file,indent=2);file.write('\n')


def __lldb_init_module(debugger, internal):
    global OUTPUT
    OUTPUT=Path(os.environ['RMX_NOISE_DIRECT']).open('xb')
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
    point.SetScriptCallbackFunction(__name__+'.enter')
