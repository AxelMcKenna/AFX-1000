#!/usr/bin/env python3
"""Compare an autonomous kick hypothesis with verified original discovery recordings."""
import argparse
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_drums import checked, recipe, require


def source_hashes():
    names = ['tools/rmx_kick.py','tools/rmx_drums.py','CMakeLists.txt','src/core/Wav.cpp','include/rmx/Wav.h','include/rmx/Dsp.h',
             'include/rmx/drums/Kick.h','src/core/drums/Kick.cpp',
             'include/rmx/drums/FrequencyCalibration.h','research/audio/experiments/kick_research_probe.cpp']
    names += ['include/rmx/drums/Controls.h','include/rmx/drums/ControlTables.h','include/rmx/drums/FrequencyCalibration.h']
    return {name:sha256(Path(name)) for name in names}


def compare(args):
    binding = source_hashes(); binary = sha256(args.renderer); root = new_directory(args.output); rows = []
    for c in recipe():
        if c['drum'] != 'kick': continue
        raw_a,provenance = checked(args.session,c); plan = root/(c['name']+'.tsv')
        plan.write_text('RMX_DRUM 1\n'+f'0 {c["level"]} {c["pitch"]} {c["block"]}\n'+''.join(f'{at}\n' for at in c['hits']))
        output = root/(c['name']+'.wav'); dry_path = root/(c['name']+'-dry.wav')
        run([args.renderer,args.session/'silence.wav',output,plan,dry_path])
        rate,raw_b = float_wav(output); dry_rate,dry = float_wav(dry_path)
        require(rate == dry_rate == 48000 and raw_b.shape == raw_a.shape == dry.shape and not np.any(dry),'Kick fixture extent/rate/dry differs')
        a,b = raw_a[32:].astype(float),raw_b[32:].astype(float)
        row = provenance | dict(variant=c['variant'],candidate_sha256=sha256(output),dry_trace_sha256=sha256(dry_path),
                  schedule_sha256=sha256(plan),whole=screen(a,b),windows=[])
        for at in c['hits']:
            for label,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                right = min(len(a),right)
                if right>left:row['windows'].append(dict(kind=label,frame=at,start=left,stop=right,score=screen(a[left:right],b[left:right])))
        row['passed'] = row['whole']['passed'] and all(w['score']['passed'] for w in row['windows'])
        rows.append(row);print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    require(source_hashes() == binding and sha256(args.renderer) == binary,'Kick candidate changed during comparison')
    save_json(root/'comparison.json',dict(kind='rmx220-kick-research-development',passed=all(r['passed'] for r in rows),
              source_sha256=binding,renderer_sha256=binary,cases=rows,
              acceptance=dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,
                              reference_offset_frames=32,candidate_offset_frames=32,gain_fit=False,alignment_search=False),
              scope='Autonomous factory neutral-kick research candidate at 48k/120BPM. Discovery regressions, not a prospective holdout or live Engine claim. The new fixture explicitly models the original nominal32 transport before comparison; the previous Engine baseline had candidate0 transport. No fitted waveform shift or comparison gain.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('session','renderer','output'):parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(compare(parser.parse_args()))


if __name__ == '__main__': main()
