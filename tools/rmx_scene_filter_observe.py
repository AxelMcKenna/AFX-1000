#!/usr/bin/env python3
"""Replay the separately observed HPF startup gain and verify static coefficients."""
import argparse
import copy
import json
from pathlib import Path
import tempfile

import numpy as np

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_scene_route_observe import analyze as route_analysis
from tools.rmx_drums_fx import FRAMES,checked,recipe
from tools.drum_clock_diagnostics import clock_map,generated_view


def analyze(args):
    rows=[json.loads(line) for line in args.trace.read_text().splitlines()]
    route_rows=[r for r in rows if r['stage'] in ('source','scene','scene_end')]
    with tempfile.TemporaryDirectory(prefix='rmx-scene-route-audit-') as folder:
        call=copy.copy(args);call.report=Path(folder)/'route.json';call.trace=Path(folder)/'route-trace.jsonl'
        call.trace.write_text(''.join(json.dumps(r)+'\n' for r in route_rows));route_analysis(call);report=json.loads(call.report.read_text())
    projection_hash=report['trace_sha256'];report['trace_sha256']=sha256(args.trace)
    ends=[r for r in rows if r['stage']=='scene_end'];returns=[r for r in rows if r['stage']=='return_input']
    require(len(rows)==256 and [r['block'] for r in returns]==list(range(64)),'Incomplete return observation')
    f=np.float32;progress=f(0);step=f(0);exact=0;trajectory=[]
    for i,row in enumerate(ends):
        if i==1:step=f(.00625)
        if 1<=i<=5:
            for _ in range(32):progress=f(progress+step)
            if i==5:progress=f(1);step=f(0)
        expected=[float(step),float(progress)];exact+=row['effect_startup']==expected;trajectory.append(row['effect_startup'])
    require(exact==64,'Effect startup gain replay differs')
    coeff=ends[1]['filter_coefficients'];feedback=ends[1]['feedback_coefficients'];resonance=ends[1]['resonance']
    require(len(coeff)==10 and coeff[:5]==coeff[5:] and ends[0]['filter_coefficients']==[0.]*10,'Unexpected coefficient layout')
    require(all(row['filter_coefficients']==coeff and row['feedback_coefficients']==feedback and row['resonance']==resonance for row in ends[1:]),'Filter coefficients vary after activation')
    plan=json.loads((args.normal/'plan.json').read_text());main=next(p['value'] for p in plan['parameters'] if p['name']=='SceneVolume');raw=round(main*255)
    control=f(f(1)-f(f(raw-3)*f(1/63)));direct=f(control*control)
    require(all(row['effect_levels'][2]==float(control) for row in ends[1:]) and report['direct_mix']['observed_target']==float(direct),'Float32 control grouping differs')
    case=next(c for c in recipe('fresh') if c['name']==args.normal.name);call=copy.copy(args);call.session=args.normal.parent;call.stage='fresh'
    original,provenance=checked(call,case);baseline=next(c for c in recipe('fresh') if c['name']==case['baseline']);off,off_provenance=checked(call,baseline)
    logical,valid=generated_view((original-off).astype(np.float64),clock_map(case,FRAMES))
    quantization=(np.spacing(np.abs(original)).astype(np.float64)+np.spacing(np.abs(off)).astype(np.float64))*.5
    quantization,_=generated_view(quantization,clock_map(case,FRAMES))
    position=(case['amount']-3)/62.25;weight=3-position;factor=.7*weight;predictions={str(p):[] for p in (1,2,3,4)}
    for row in returns:
        start=12000+32+row['block']*32;require(bool(np.all(valid[start:start+32])),'Return RMS window has missing generated frames')
        actual=np.sqrt(np.mean(logical[start:start+32]**2,axis=0))
        bound=np.sqrt(np.mean(quantization[start:start+32]**2,axis=0))
        for power in (1,2,3,4):
            predicted=np.array(row['return_weighted_rms'][str(power)])*factor
            delta=np.abs(actual-predicted);relative=delta/np.maximum(actual,1e-30)
            predictions[str(power)].append(dict(block=row['block'],actual_rms=actual.tolist(),predicted_rms=predicted.tolist(),relative_error=relative.tolist(),
                float32_subtraction_rms_bound=bound.tolist(),passed=bool(np.all(delta<=bound+predicted*1e-5+1e-12))))
    require(all(r['passed'] for r in predictions['3']),'Cubic return gate RMS prediction differs')
    require(all(not all(r['passed'] for r in predictions[str(p)]) for p in (1,2,4)),'Alternative fade powers were not rejected')
    report.update(kind='rmx220-scene-filter-startup-scalar-replay',route_analyzer_sha256=report.pop('analyzer_sha256'),analyzer_sha256=sha256(Path(__file__)),
        route_projection_sha256=projection_hash,clock_helper_sha256=sha256(Path('tools/drum_clock_diagnostics.py')),
        effect_startup=dict(exact_blocks=exact,block_end_step_value=trajectory),
        activated_filter=dict(stable_blocks=63,left_right_coefficients_equal=True,coefficients=coeff[:5],feedback_coefficients=feedback,resonance=resonance),
        hpf_direct_control=dict(raw_main=raw,control=float(control),direct_target=float(direct),float32_grouping_verified=True),
        first_return_gate=dict(original_provenance=provenance,baseline_provenance=off_provenance,delay_frames=12000,coefficient=factor,coefficient_not_fitted=True,
            rms_relative_limit=1e-5,rms_absolute_limit=1e-12,float32_subtraction_bound='Per-sample sum of half ULP of the on/off float32 outputs, propagated as an RMS norm bound; this affects component measurement uncertainty, not waveform acceptance.',
            gate_power_predictions=predictions,scope='Scalar weighted RMS from original return input predicts64 two-channel blocks of the separately recorded first return; fixed causal callback mapping, no alignment/gain fit. Cubic passes within stated float32 measurement uncertainty; linear, squared and fourth-power alternatives fail. This aligned tap alone does not distinguish write-side and read-side factors.'),
        scope='Read-only component checks for one HPF/X-Pad cold case. Source, Scene wet/direct and separate effect-startup ramps replay64/64 exactly each; post-activation filter coefficients stay fixed63 blocks. Float32 direct-control grouping predicts the observed target. Original-only weighted RMS establishes a cubic effective first-return gate for the aligned12000-frame tap. Normal/debugger audio and auxiliary files are byte-identical. These checks do not establish the complete multi-tap return or waveform accuracy.')
    save_json(args.report,report);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('normal','observed','trace','observer','report','host'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(analyze(p.parse_args()))


if __name__=='__main__':main()
