"""Read one bounded Noise control record; never change reference memory."""
import json
import os
from pathlib import Path

import noise_coefficients_observer as base


def observe(frame, location, internal):
    base.observe(frame, location, internal)
    import lldb
    import struct
    process = frame.GetThread().GetProcess()
    address = frame.FindRegister('rdi').GetValueAsUnsigned()
    def read(offset, fmt):
        error = lldb.SBError()
        data = process.ReadMemory(address+offset, struct.calcsize(fmt), error)
        if not error.Success() or len(data) != struct.calcsize(fmt):
            raise RuntimeError('Noise scalar read failed')
        return list(struct.unpack(fmt, data))
    path = Path(os.environ['RMX_NOISE_SCALARS'])
    record = json.loads(path.read_text())
    record.update(sub2=read(0x92fc, '<H')[0], smoothed_sub2=read(0xa7f8, '<H')[0],
                  base_feedback=read(0xa5ec, '<f')[0], lfo_edges=[read(0xa610, '<f')[0], read(0xa650, '<f')[0]],
                  lfo_period=read(0xa69c, '<f')[0], lfo_limits=read(0xa6a0, '<2f'), lfo_depth=read(0xa698, '<f')[0])
    path.write_text(json.dumps(record, indent=2)+'\n')
    return False


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
    point.SetScriptCallbackFunction(__name__+'.observe')
    point.SetIgnoreCount(1800)
