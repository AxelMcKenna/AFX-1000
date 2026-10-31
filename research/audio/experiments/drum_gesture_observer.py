"""Read command words and timing scalars for our own synthetic strip program.

Never reads audio buffers or writes Original state. Raw traces remain private.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import lldb

OUTPUT = None
PENDING = None
AFTER = None


def number(frame):
    error = lldb.SBError(); value = frame.FindRegister('xmm0').GetData().GetDouble(error, 0)
    if not error.Success(): raise RuntimeError('Cannot read timing argument')
    return value


def scalar(frame, address, size):
    error = lldb.SBError(); data = frame.GetThread().GetProcess().ReadMemory(address, size, error)
    if not error.Success() or len(data) != size: raise RuntimeError('Cannot read command metadata')
    return data


def reg(frame, name): return frame.FindRegister(name).GetValueAsUnsigned()


def emit(row):
    with OUTPUT.open('a') as f: f.write(json.dumps(row) + '\n')


def write(frame, location, internal):
    emit(dict(kind='write-strip', slot=reg(frame, 'rsi') & 0xffffffff,
              command=reg(frame, 'rdx') & 65535, quantize=reg(frame, 'rcx') & 0xffffffff))
    return False


def offset(frame, location, internal):
    emit(dict(kind='strip-offset', position=number(frame), command=reg(frame, 'rsi') & 65535,
              quantize=reg(frame, 'rdx') & 0xffffffff))
    return False


def direction_after(frame, location, internal):
    global PENDING
    result = reg(frame, 'r14') & 65535
    if result: emit(PENDING | dict(output=result))
    PENDING = None; location.GetBreakpoint().SetEnabled(False)
    return False


def direction(frame, location, internal):
    global PENDING, AFTER
    sequence = reg(frame, 'rdi'); clock = reg(frame, 'rsi')
    PENDING = dict(kind='direction', division=reg(frame, 'rdx') & 0xffffffff,
        timeline=struct.unpack('<d', scalar(frame, clock + 0x198, 8))[0],
        offsets=list(struct.unpack('<5d', scalar(frame, sequence + 0x108, 40))),
        active=list(struct.unpack('<5i', scalar(frame, sequence + 0x138, 20))))
    if AFTER is None:
        target = frame.GetThread().GetProcess().GetTarget()
        AFTER = target.BreakpointCreateByAddress(frame.GetModule().ResolveFileAddress(0x658b).GetLoadAddress(target))
        AFTER.SetScriptCallbackFunction(__name__ + '.direction_after')
    AFTER.SetEnabled(True)
    return False


def bootstrap(frame, location, internal):
    global OUTPUT
    if hashlib.sha256(Path(str(frame.GetModule().GetFileSpec())).read_bytes()).hexdigest() != 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':
        raise RuntimeError('Wrong Original binary')
    OUTPUT = Path(os.environ['RMX_GESTURE_TRACE'])
    with OUTPUT.open('x'): pass
    target = frame.GetThread().GetProcess().GetTarget()
    for name, callback in [('BeatOverDubFunction::WriteCommandForXPad(int, unsigned short, int)', write),
                           ('BeatOverDubFunction::SetEachXPadOffset(unsigned short, double, int)', offset),
                           ('BeatOverDubFunction::CreateXPadDirectionBeatCommand(BeatManager*, int)', direction)]:
        point = target.BreakpointCreateByName(name); point.SetScriptCallbackFunction(__name__ + '.' + callback.__name__)
    location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('CustomizeFile::InitCustomizeData()')
    point.SetScriptCallbackFunction(__name__ + '.bootstrap')
