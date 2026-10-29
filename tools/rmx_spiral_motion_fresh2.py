#!/usr/bin/env python3
"""Second independent prospective Spiral gesture campaign after return-gate fix."""
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_prospective as campaign
from tools.reference_audio import sha256

base_bindings = campaign.bindings


def bindings():
    return base_bindings() | {'tools/rmx_spiral_motion_fresh2.py': sha256(Path(__file__))}


def source():
    rng = np.random.default_rng(0x53504d4633)
    x = np.zeros((624000, 2), dtype='<f4'); t = np.arange(168000)/48000
    x[48000:216000] = rng.normal(0, .007, (len(t), 2)) + np.column_stack((
        .029*np.sin(2*np.pi*(73*t+337*t*t)), .021*np.cos(2*np.pi*(191*t+157*t*t))))
    x[72113:85117] *= .013; x[173013:180019] = 0
    for f in [48031, 73117, 96193, 145129, 192031, 217109, 264173]: x[f] += rng.uniform(-.19, .19, 2)
    return x


def recipe():
    rng = np.random.default_rng(0x53504d4634)
    boundary = [0, 1, 3, 4, 5, 8, 9, 16, 28, 29, 63, 64, 65, 66, 127, 128, 129, 130, 131, 192, 254, 255]
    rows = []
    for i in range(64):
        changes = []
        for j, frame in enumerate([60113, 85127, 109019, 135311, 159193, 184277, 211419, 237607, 293113, 351319]):
            for control in ['main', 'time', 'pitch', 'enabled']:
                raw = int(j % 2 == 1) if control == 'enabled' else int(rng.choice(boundary)) if j < 7 else int(rng.integers(256))
                changes.append(dict(frame=frame, control=control, raw=raw))
        rows.append(dict(name=f'spiral-motion-fresh2-{i:03d}', direction=['down', 'up'][i % 2],
              main=boundary[(i*7) % len(boundary)] if i < 44 else int(rng.integers(256)),
              time=int(rng.integers(256)), pitch=int(rng.integers(256)), source='program',
              block=[4096, 4093, 1021, 263, 127, 79, 32, 31, 17, 8][i % 10], changes=changes))
    return rows


if __name__ == '__main__':
    campaign.bindings = bindings; campaign.source = source; campaign.recipe = recipe
    raise SystemExit(campaign.main())
