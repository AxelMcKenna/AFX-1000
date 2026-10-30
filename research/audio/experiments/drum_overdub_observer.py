"""Read sparse beat/sequence-position metadata for our generated drum program."""
import hashlib
import json
import os
from pathlib import Path
import lldb

OUTPUT = None
INDEX = -1
NEXT = 0
SAMPLES = list(range(17)) + list(range(2995,3011)) + list(range(3900,3921))
PENDING = None
AFTER = None


def emit(row):
    with OUTPUT.open('a') as f: f.write(json.dumps(row) + '\n')


def number(frame):
    error = lldb.SBError(); value = frame.FindRegister('xmm0').GetData().GetDouble(error, 0)
    if not error.Success(): raise RuntimeError('Cannot read position scalar')
    return value


def after_read(frame, location, internal):
    global PENDING
    PENDING['slot'] = frame.FindRegister('rax').GetValueAsUnsigned() & 0xffffffff
    emit(PENDING); PENDING = None; location.GetBreakpoint().SetEnabled(False)
    return False


def read_point(frame, location, internal):
    global INDEX, NEXT, PENDING, AFTER
    INDEX = SAMPLES[NEXT]; NEXT += 1
    PENDING = dict(kind='read-point', index=INDEX, position=number(frame))
    if AFTER is None:
        target = frame.GetThread().GetProcess().GetTarget()
        AFTER = target.BreakpointCreateByAddress(frame.GetModule().ResolveFileAddress(0x5929).GetLoadAddress(target))
        AFTER.SetScriptCallbackFunction(__name__ + '.after_read')
    AFTER.SetEnabled(True)
    if NEXT == len(SAMPLES): location.GetBreakpoint().SetEnabled(False)
    else: location.GetBreakpoint().SetIgnoreCount(SAMPLES[NEXT] - INDEX - 1)
    return False


def write_point(frame, location, internal):
    emit(dict(kind='write-point', position=number(frame), command=frame.FindRegister('rsi').GetValueAsUnsigned() & 65535,
              quantize=frame.FindRegister('rdx').GetValueAsUnsigned() & 0xffffffff))
    return False


def bootstrap(frame, location, internal):
    global OUTPUT
    if hashlib.sha256(Path(str(frame.GetModule().GetFileSpec())).read_bytes()).hexdigest() != 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':
        raise RuntimeError('Wrong Original binary')
    OUTPUT = Path(os.environ['RMX_DRUM_OVERDUB_TRACE'])
    with OUTPUT.open('x'): pass
    target = frame.GetThread().GetProcess().GetTarget()
    for name, callback in [('BeatOverDubFunction::CalcReadPoint(double, BeatManager*)', 'read_point'),
                           ('BeatOverDubFunction::CalcWritePoint(double, unsigned short, int, BeatManager*)', 'write_point')]:
        point = target.BreakpointCreateByName(name); point.SetScriptCallbackFunction(__name__ + '.' + callback)
    location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('CustomizeFile::InitCustomizeData()')
    point.SetScriptCallbackFunction(__name__ + '.bootstrap')
