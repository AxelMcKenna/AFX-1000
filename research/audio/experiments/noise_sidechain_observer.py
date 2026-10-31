"""Write bounded temporary Sidechain driver/control records for live replay."""
import hashlib
import os
from pathlib import Path
import struct

import lldb

OUTPUT = None
COUNT = 0


def sample(frame, location, internal):
    global COUNT
    process = frame.GetThread().GetProcess()
    address = frame.FindRegister('r14').GetValueAsUnsigned()
    def read(offset, size):
        error = lldb.SBError()
        data = process.ReadMemory(address + offset, size, error)
        if not error.Success() or len(data) != size:
            raise RuntimeError('Sidechain control read failed')
        return data
    OUTPUT.write(read(0x70e4, 4) + read(0x74e8, 128) + read(0xa610, 128))
    COUNT += 1
    if COUNT > 15000:
        raise RuntimeError('Sidechain control observation exceeded bound')
    return False


def enter(frame, location, internal):
    binary = Path(str(frame.GetModule().GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest() != 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':
        raise RuntimeError('Wrong Original')
    point = frame.GetThread().GetProcess().GetTarget().BreakpointCreateByAddress(frame.GetPC() + 1182)
    point.SetScriptCallbackFunction(__name__ + '.sample')
    location.GetBreakpoint().SetEnabled(False)
    return False


def finish():
    OUTPUT.close()
    if not COUNT:
        raise RuntimeError('No Sidechain controls observed')


def __lldb_init_module(debugger, internal):
    global OUTPUT
    OUTPUT = Path(os.environ['RMX_NOISE_SIDECHAIN_TRACE']).open('xb')
    point = debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
    point.SetScriptCallbackFunction(__name__ + '.enter')
