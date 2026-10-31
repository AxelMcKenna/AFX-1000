"""Read two computed Noise main-level targets after the scalar observation."""
import json
import os
from pathlib import Path
import struct

import lldb
import noise_advanced_observer as advanced


def gain(frame, location, internal):
    error = lldb.SBError()
    address = frame.FindRegister('rbp').GetValueAsUnsigned()-0x38
    data = frame.GetThread().GetProcess().ReadMemory(address, 8, error)
    if not error.Success() or len(data) != 8: raise RuntimeError('Noise gain read failed')
    path = Path(os.environ['RMX_NOISE_SCALARS'])
    record = json.loads(path.read_text())
    record['main_level_targets'] = list(struct.unpack('<2f', data))
    path.write_text(json.dumps(record, indent=2)+'\n')
    location.GetBreakpoint().SetEnabled(False)
    return False


def observe(frame, location, internal):
    advanced.observe(frame, location, internal)
    point = frame.GetThread().GetProcess().GetTarget().BreakpointCreateByAddress(frame.GetPC()+2250)
    point.SetScriptCallbackFunction(__name__+'.gain')
    return False


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
    point.SetScriptCallbackFunction(__name__+'.observe')
    point.SetIgnoreCount(1800)
