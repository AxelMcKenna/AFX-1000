"""Read one steady Noise control/coefficient record; no audio/state writes."""
import hashlib
import json
import os
from pathlib import Path
import struct
import lldb


def observe(frame, location, internal):
    process = frame.GetThread().GetProcess()
    binary = Path(str(frame.GetModule().GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest() != 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':
        raise RuntimeError('Wrong Original binary')
    base = frame.FindRegister('rdi').GetValueAsUnsigned()
    def values(offset, fmt):
        error = lldb.SBError(); size = struct.calcsize(fmt); data = process.ReadMemory(base+offset, size, error)
        if not error.Success() or len(data) != size: raise RuntimeError('Bounded Noise scalar read failed')
        return list(struct.unpack(fmt, data))
    result = dict(kind='steady-noise-control-coefficients', binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        main=values(0x92f8, '<H')[0], amount=values(0x92fa, '<H')[0], smoothed_main=values(0x9344, '<H')[0],
        customization={name: values(offset, '<H')[0] for name, offset in [('width',0xcfb4), ('minimum',0xcfc4), ('maximum',0xcfc6), ('wave',0xcfc8), ('resonance',0xcfca), ('mode',0xcfd0)]},
        sweep=values(0x9a9c, '<4f'), biquads=values(0x990c, '<10f'), feedback=values(0x994c, '<2f'),
        level=values(0x98fc, '<f')[0], activation=values(0xa4ac, '<f')[0])
    with Path(os.environ['RMX_NOISE_SCALARS']).open('x') as file: json.dump(result, file, indent=2); file.write('\n')
    location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
    point.SetScriptCallbackFunction(__name__+'.observe'); point.SetIgnoreCount(1800)
