#!/usr/bin/env python3
"""Verify read-only original kick traces and replay selected numeric state hypotheses."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_drums import checked, recipe, require


def audit(args):
    case=next(c for c in recipe() if c['name']=='drum-kick-base');_,provenance=checked(args.session,case)
    original=args.session/case['name'];a=json.loads((original/'receipt.json').read_text());b=json.loads((args.debugger/'receipt.json').read_text())
    require(b['complete'] and b['role']=='reference' and b['plugin']['binary_files']==a['plugin']['binary_files'],'Debugger reference identity differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),
                       ('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(args.debugger/name)==b[field]==a[field],'Debugger render differs from normal original: '+name)
    require(all(b[k]==a[k] for k in ('host_sha256','input_sha256','sample_rate','frames','maximum_block_size','bpm')),'Debugger recipe/host differs')
    rows=[json.loads(s) for s in args.log.read_text().splitlines()];stages={name:[r for r in rows if r['stage']==name] for name in ('pitch','source','noise','output')}
    require(len(rows)==256 and all([r['subblock'] for r in group]==list(range(64)) for group in stages.values()),'Incomplete kick scalar trace')
    for r in rows:
        require(r['custom']==[3,1,0] and r['pitch_controls']==[11,11,0] and r['pitch_raw']==128,'Unexpected original controls')
        require(all(r['envelopes'][key]['attack']==float(np.float32(.001)) for key in ('tone','pitch','noise')),'Unexpected attack time')
    f=np.float32
    def envelope(decay):
        position=value=f(0);rising=True;falling=False;values=[]
        for _ in range(64):
            if rising:
                value=position;position=f(position+f(f(16)*f(f(1)/f(f(.001)*f(48000)))))
                if position>1:position=f(0);value=f(1);rising=False;falling=True
            if falling:
                value=f(value+f(f(16)*f(-f(1)/f(f(decay)*f(48000)))))
                if value<0:value=f(0);rising=falling=False
            values.append(dict(value=float(value),position=float(position),flags=[int(rising),int(falling)]))
        return values
    envelope_checks={}
    for name,stage,decay in [('pitch','pitch',.343),('tone','source',.44),('noise','noise',.15859)]:
        predicted=envelope(decay);observed=[r['envelopes'][name] for r in stages[stage]]
        exact=[all(p[k]==o[k] for k in ('value','position','flags')) and o['decay']==float(f(decay)) for p,o in zip(predicted,observed)]
        envelope_checks[name]=dict(blocks=64,exact_blocks=sum(exact),maximum_value_error=max(abs(p['value']-o['value']) for p,o in zip(predicted,observed)))
    phases=[f(.25),f(.25)];phase_checks=[]
    for r in stages['source']:
        for channel,ratio in enumerate([f(1),f(.6)]):
            step=f(f(f(r['frequency'])*ratio)*f(f(1)/f(48000)))
            for _ in range(16):
                phases[channel]=f(phases[channel]+step)
                if phases[channel]>1:phases[channel]=f(phases[channel]-f(1))
        phase_checks.append([float(v) for v in phases]==r['phase'])
    save_json(args.report,dict(kind='rmx220-kick-read-only-state-replay',original=provenance,debugger_receipt_sha256=sha256(args.debugger/'receipt.json'),
              audio_and_auxiliary_files_byte_identical=True,trace_sha256=sha256(args.log),observer_source_sha256=sha256(args.observer),
              script_sha256=sha256(Path(__file__)),observations=dict(stages=4,subblocks_per_stage=64,frames_per_subblock=16),
              envelope_replay=envelope_checks,oscillator_phase_replay=dict(blocks=64,exact_blocks=sum(phase_checks)),
              observed_default_pitch_envelope_decay=float(f(.343)),static_file_pitch_envelope_decay=float(f(.21514)),
              source_frequency_range=[min(r['frequency'] for r in stages['source']),max(r['frequency'] for r in stages['source'])],
              scope='Component replay from read-only numeric observations; oscillator phase replay uses observed frequency, not autonomous source generation. No original code, raw internal audio/trace or binary is distributed. Complete waveform acceptance is separate.'))
    print('Verified original/debugger identity and replayed envelopes/oscillator phase')
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('session','debugger','log','observer','report'):parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(audit(parser.parse_args()))


if __name__=='__main__':main()
