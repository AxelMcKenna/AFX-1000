"""Observe bounded XML field names and limits; no writes or audio-buffer reads."""
import hashlib
import json
import os
from pathlib import Path
import struct

import lldb


def observe(frame, location, internal):
    process = frame.GetThread().GetProcess(); target = process.GetTarget(); module = frame.GetModule()
    binary = Path(str(module.GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest() != 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':
        raise RuntimeError('Wrong Original binary')
    def read(address, size):
        error = lldb.SBError(); data = process.ReadMemory(address, size, error)
        if not error.Success() or len(data) != size:
            raise RuntimeError('Schema scalar read failed')
        return data
    def address(value):
        return module.ResolveFileAddress(value).GetLoadAddress(target)
    def names(base, count):
        result = []
        for i in range(count):
            pointer = struct.unpack('<Q', read(address(base) + i * 8, 8))[0]
            error = lldb.SBError(); text = process.ReadCStringFromMemory(pointer, 128, error) if pointer else ''
            if not error.Success():
                raise RuntimeError('Schema field name read failed')
            result.append(text)
        return result
    record = dict(kind='original-scene-settings-xml-schema', original_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  xml_groups=names(0xc11bc0, 10), scene_fields=names(0xc11cf0, 110),
                  scene_limits=list(struct.unpack('<110i', read(address(0x26fdc0), 440))))
    output = Path(os.environ['RMX_SCENE_SETTINGS_SCHEMA'])
    with output.open('x') as f:
        json.dump(record, f, indent=2); f.write('\n')
    location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger, internal):
    point = debugger.GetSelectedTarget().BreakpointCreateByName('CustomizeFile::InitCustomizeData()')
    point.SetScriptCallbackFunction(__name__ + '.observe')
