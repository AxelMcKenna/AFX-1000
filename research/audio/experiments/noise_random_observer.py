"""Observe bounded Random control targets and ramps; never read PRNG state."""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb

TARGETS = []
BLOCKS = 0
CONTROL = hashlib.sha256()
POINTS = {}
BINARY = 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced'


def read(process, address, offset, fmt):
    error = lldb.SBError()
    data = process.ReadMemory(address + offset, struct.calcsize(fmt), error)
    if not error.Success() or len(data) != struct.calcsize(fmt):
        raise RuntimeError('Random control read failed')
    return data, list(struct.unpack(fmt, data))


def target(frame, location, internal):
    process = frame.GetThread().GetProcess()
    address = frame.FindRegister('rdi').GetValueAsUnsigned()
    phase, value, step = read(process, address, 0xa6c8, '<3f')[1]
    half = POINTS[frame.GetPC()]
    if os.environ.get('RMX_RANDOM_COMPACT') == '1':
        TARGETS.append(value)
        if len(TARGETS) > 200000:
            raise RuntimeError('Random target observation exceeded bound')
        return False
    TARGETS.append(dict(event=len(TARGETS), half=half,
        control_frame=BLOCKS * 32 + half * 16 if os.environ.get('RMX_RANDOM_FULL') == '1' else None,
        previous=phase, target=value, step=step,
        counter=read(process, address, 0xa6c4, '<I')[1][0],
        period=read(process, address, 0xa69c, '<f')[1][0],
        depth=read(process, address, 0xa698, '<f')[1][0]))
    if len(TARGETS) > 200000:
        raise RuntimeError('Random target observation exceeded bound')
    return False


def controls(frame, location, internal):
    global BLOCKS
    process = frame.GetThread().GetProcess()
    address = frame.FindRegister('r14').GetValueAsUnsigned()
    CONTROL.update(read(process, address, 0xa610, '<32f')[0])
    BLOCKS += 1
    if BLOCKS > 15000:
        raise RuntimeError('Random full control observation exceeded bound')
    return False


def checked_base(frame):
    binary = Path(str(frame.GetModule().GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest() != BINARY:
        raise RuntimeError('Wrong Original')
    target = frame.GetThread().GetProcess().GetTarget()
    return target, frame.GetSymbol().GetStartAddress().GetLoadAddress(target)


def enter_lfo(frame, location, internal):
    context, base = checked_base(frame)
    for half, offset in [(0, 982), (1, 1213)]:
        point = context.BreakpointCreateByAddress(base + offset)
        point.SetScriptCallbackFunction(__name__ + '.target')
        POINTS[base + offset] = half
    location.GetBreakpoint().SetEnabled(False)
    return False


def enter_noise(frame, location, internal):
    context, base = checked_base(frame)
    point = context.BreakpointCreateByAddress(base + 1182)
    point.SetScriptCallbackFunction(__name__ + '.controls')
    location.GetBreakpoint().SetEnabled(False)
    return False


def finish():
    if not TARGETS:
        raise RuntimeError('No Random targets observed')
    if os.environ.get('RMX_RANDOM_COMPACT') == '1':
        with Path(os.environ['RMX_RANDOM_TRACE']).open('xb') as file:
            file.write(struct.pack('<' + str(len(TARGETS)) + 'f', *TARGETS))
        return
    with Path(os.environ['RMX_RANDOM_TRACE']).open('x') as file:
        json.dump(dict(kind='bounded-original-random-controls', binary_sha256=BINARY,
            blocks=BLOCKS, full_control_sha256=CONTROL.hexdigest() if BLOCKS else None,
            targets=TARGETS), file, separators=(',', ':'))
        file.write('\n')


def __lldb_init_module(debugger, internal):
    context = debugger.GetSelectedTarget()
    point = context.BreakpointCreateByName('PluginDSP::calc_mod_knob_lfo()')
    point.SetScriptCallbackFunction(__name__ + '.enter_lfo')
    if os.environ.get('RMX_RANDOM_FULL') == '1':
        point = context.BreakpointCreateByName('PluginDSP::scnfx_noise(float*, float*)')
        point.SetScriptCallbackFunction(__name__ + '.enter_noise')
