"""Observe bounded customization-parser return codes without modifying state."""
import hashlib
import json
import os
from pathlib import Path
import lldb

OUTPUT = None


def value(frame, location, internal):
    row = dict(address=hex(frame.GetPCAddress().GetFileAddress()), code=frame.FindRegister('rax').GetValueAsUnsigned() & 0xffffffff)
    with OUTPUT.open('a') as f: f.write(json.dumps(row) + '\n')
    return False


def bootstrap(frame, location, internal):
    global OUTPUT
    target = frame.GetThread().GetProcess().GetTarget(); module = frame.GetModule()
    if hashlib.sha256(Path(str(module.GetFileSpec())).read_bytes()).hexdigest() != 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':
        raise RuntimeError('Wrong Original binary')
    OUTPUT = Path(os.environ['RMX_DRUM_SETTINGS_LOAD_TRACE'])
    with OUTPUT.open('x'): pass
    for address in [0x34a6f, 0x25712, 0x2573b, 0x25d71, 0x25d86, 0x25d9b, 0x25db0]:
        point = target.BreakpointCreateByAddress(module.ResolveFileAddress(address).GetLoadAddress(target))
        point.SetScriptCallbackFunction(__name__ + '.value')
    location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('CustomizeFile::InitCustomizeData()')
    point.SetScriptCallbackFunction(__name__ + '.bootstrap')
