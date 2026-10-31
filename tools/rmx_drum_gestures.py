#!/usr/bin/env python3
"""Recorded strip gestures, custom divisions and explicit transport reference campaigns."""
import sys

import numpy as np

from tools import rmx_drum_combos as campaign
from tools.reference_audio import sha256
from pathlib import Path

base_bindings = campaign.bindings
base_schedule = campaign.schedule
base_plan = campaign.original_plan
base_checked = campaign.checked


def checked(directory, c, **kwargs):
    def expected(req, value):
        # The Original rejects Hold-on during overdub. Keep the attempted
        # write and require its observed zero readback instead of discarding it.
        if c['family'] == 'recorded' and req['name'] == 'HoldButton' and req['frame'] >= 0:
            return 0
        return value
    return base_checked(directory, c, readback_for=expected, **kwargs)


def bindings():
    return base_bindings() | {n: sha256(Path(n)) for n in ['tools/rmx_drum_gestures.py', 'tools/audio_plugin_render.cpp', 'tools/audio_plugin_host.h', 'tools/legacy_vst2_host.h']}


def recipe(stage):
    base = stage.split('-fresh')[0]; fresh = '-fresh' in stage; rows = []
    campaign.require(base in ['recorded', 'divisions', 'transport'], 'Unknown gesture stage')
    if base == 'recorded':
        for user in [0, 1]:
            for pad in range(4):
                for variant in range(4):
                    changes = [(1, 'X', 153), (31, 'O', 1)]
                    campaign.press(changes, 48079 + pad * 6, pad)
                    changes += [(96113, 'T', 1), (144239, 'T', 0), (432701, 'O', 0)]
                    if variant == 1: changes += [(108157, 'X', 51), (120191, 'X', 204)]
                    if variant == 2: changes += [(108157, 'F', 1), (240337, 'F', 0)]
                    if variant == 3:
                        campaign.press(changes, 111313, (pad + 1) % 4)
                        changes += [(120191, 'X', 102), (288419, 'D', 1), (288551, 'D', 0)]
                        campaign.press(changes, 288451, pad)
                    settings = {n: campaign.profile((i * 2 + 1) % 7, i % 3, (i + variant) % 2) for i, n in enumerate(campaign.NODES)} if user else {}
                    rows.append(campaign.make_case(base, len(rows), changes, user=user, settings=settings, quantize=variant % 2,
                        block=[8, 127, 509, 4093][variant], drum=list(campaign.DRUMS)[pad]))
    elif base == 'divisions':
        for choice in range(16):
            for quantize in [0, 1]:
                pad = choice % 4; changes = [(1, 'X', 153)]
                campaign.press(changes, 48079 + pad * 6, pad)
                changes += [(96113, 'T', 1), (168191, 'T', 0), (192241, 'X', 153), (192273, 'T', 1), (312437, 'T', 0)]
                if quantize: changes += [(120157, 'F', 1), (288373, 'F', 0)]
                settings = {'Xpad': {f'Position{i}': choice for i in range(5)}}
                settings[campaign.NODES[pad]] = campaign.profile(choice % 7, choice % 3, choice % 2)
                rows.append(campaign.make_case(base, len(rows), changes, user=1, settings=settings, quantize=quantize,
                    block=[8, 31, 127, 509, 1021, 4093][choice % 6], drum=list(campaign.DRUMS)[pad], division_choice=choice))
    else:
        for pad in range(4):
            for variant in range(4):
                changes = [(1, 'X', 102)]
                campaign.press(changes, 48079 + pad * 6, pad)
                changes += [(96113, 'T', 1), (432701, 'T', 0)]
                c = campaign.make_case(base, len(rows), changes, automatic=1, block=[31, 127, 509, 4093][variant], drum=list(campaign.DRUMS)[pad])
                transport = [(0, 120, 0, 0, True)]
                if variant == 0: transport += [(192000, 137, 8, 4, True), (336000, 91, 14.85, 7, True)]
                elif variant == 1: transport += [(192000, 120, 8, 4, False), (288000, 120, 8, 4, True)]
                elif variant == 2: transport += [(192000, 120, 24, 12, True)]
                else: transport += [(192000, 120, 2, 1, True)]
                c['changes'] += [dict(frame=f, type='Z', value=0, bpm=bpm, beat=beat, seconds=seconds, playing=playing) for f, bpm, beat, seconds, playing in transport]
                c['changes'].sort(key=lambda e: e['frame']); rows.append(c)
    if fresh:
        rng = np.random.default_rng({'recorded': 0x47524531, 'divisions': 0x47444931, 'transport': 0x47545231}[base] + int(stage.endswith('fresh2')))
        for index, c in enumerate(rows):
            c['name'] = c['name'].replace('combo-', 'gesture-fresh2-' if stage.endswith('fresh2') else 'gesture-fresh-')
            c['block'] = [11, 43, 131, 257, 1021, 4096][index % 6]; shift = int(rng.integers(17, 1700))
            c['pitch'] = int(rng.choice([39, 117, 121, 128, 135, 139, 191])); c['level'] = [17, 107, 173, 239][index % 4]
            for e in c['changes']:
                if e['frame'] > 1 and e['type'] != 'Z': e['frame'] += shift
            c['changes'].sort(key=lambda e: e['frame']); c['hits'] = [e['frame'] for e in c['changes'] if e['type'] == 'H']
    return rows


def original_plan(c, inventory, session):
    plan = base_plan(c | dict(changes=[e for e in c['changes'] if e['type'] != 'Z']), inventory, session)
    plan['events'] += [dict(frame=e['frame'], type='transport', bpm=e['bpm'], beat=e['beat'], seconds=e['seconds'], playing=e['playing']) for e in c['changes'] if e['type'] == 'Z']
    plan['events'].sort(key=lambda e: e['frame']); return plan


def schedule(c):
    text = base_schedule(c | dict(changes=[e for e in c['changes'] if e['type'] != 'Z'])).splitlines(); text[0] = 'RMX_DRUM_PERFORMANCE 3'
    choices = [2, 4, 6, 8, 10, 11, 13, 14]
    # RSD choices start at 1/2 beat, while the project's public parameter
    # choices start at 1/32 beat. Both tables contain the same 16 divisions.
    for i, position in enumerate([1, 2, 3, 5, 6]):
        original = c['settings'].get('Xpad', {}).get('Position' + str(i))
        if original is not None: choices[position] = (original + 8) % 16
    events = [(e['frame'], line) for e, line in zip([e for e in c['changes'] if e['type'] != 'Z'], text[4:], strict=True)]
    events += [(e['frame'], f"{e['frame']} Z {e['bpm']} {e['beat']} {e['seconds']} {int(e['playing'])}") for e in c['changes'] if e['type'] == 'Z']
    events.sort(key=lambda e: e[0]); return '\n'.join(text[:4] + [' '.join(map(str, choices))] + [line for _, line in events]) + '\n'


def activate():
    campaign.bindings = bindings; campaign.recipe = recipe; campaign.original_plan = original_plan; campaign.schedule = schedule; campaign.checked = checked


if __name__ == '__main__':
    activate()
    campaign.main()
