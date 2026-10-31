"""Read bounded Noise modulation controls; never copy audio or PRNG state."""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

ROWS = []
COUNT = 0
DIGEST = hashlib.sha256()
BINARY = 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced'


def motion(frame, location, internal):
    global COUNT
    process = frame.GetThread().GetProcess()
    address = frame.FindRegister('r14').GetValueAsUnsigned()
    def read(offset, fmt):
        error = lldb.SBError()
        data = process.ReadMemory(address+offset, struct.calcsize(fmt), error)
        if not error.Success() or len(data) != struct.calcsize(fmt):
            raise RuntimeError('Bounded Noise control read failed')
        return data, list(struct.unpack(fmt, data))
    data, wave = read(0xa610, '<32f')
    DIGEST.update(data)
    if COUNT < 8 or COUNT % 137 == 0:
        ROWS.append(dict(block=COUNT, lfo=wave, raw_sub2=read(0x92fc,'<H')[1][0],
            main=read(0x9344,'<H')[1][0], smoothed_sub2=read(0xa7f8,'<H')[1][0],
            period=read(0xa69c,'<f')[1][0], depth=read(0xa698,'<f')[1][0],
            phase=read(0xa6b8,'<f')[1][0], descending=read(0xa694,'<H')[1][0],
            counter=read(0xa6c4,'<I')[1][0], wave=read(0xc264,'<H')[1][0],
            envelope=read(0xa6e8,'<2f')[1]))
    COUNT += 1
    if COUNT > 15000: raise RuntimeError('Control trace exceeded bound')
    return False


def enter(frame, location, internal):
    binary = Path(str(frame.GetModule().GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest() != BINARY:
        raise RuntimeError('Wrong Original')
    target = frame.GetThread().GetProcess().GetTarget()
    point = target.BreakpointCreateByAddress(frame.GetPC()+1182)
    point.SetScriptCallbackFunction(__name__+'.motion')
    location.GetBreakpoint().SetEnabled(False)
    return False


def finish():
    if not COUNT: raise RuntimeError('No Noise control calls observed')
    with Path(os.environ['RMX_NOISE_MOTION']).open('x') as file:
        json.dump(dict(kind='bounded-noise-motion-controls', binary_sha256=BINARY,
                       blocks=COUNT, lfo_f32le_sha256=DIGEST.hexdigest(), rows=ROWS), file, indent=2)
        file.write('\n')


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
    point.SetScriptCallbackFunction(__name__+'.enter')
