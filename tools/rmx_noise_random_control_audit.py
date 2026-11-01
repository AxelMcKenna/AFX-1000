#!/usr/bin/env python3
"""Audit conditional Random controls, provider invariance and prior control streams."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
import numpy as np
from tools.reference_audio import save_json,sha256
from tools.rmx_noise_sidechain_controls import stimulus
from tools.rmx_noise_random_controls import verify_targets


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['discovery','fresh','motion-report','sidechain-report','sidechain-release','random-probe','random-sanitizer','motion-probe','motion-sanitizer','sidechain-probe','sidechain-sanitizer','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();discovery=json.loads(a.discovery.read_text());fresh=json.loads(a.fresh.read_text());rows=[];preserved=[]
    if not fresh['verification_passed'] or not fresh['all_conditional_controls_matched']:raise ValueError('Fresh controls failed')
    for name,digest in fresh['source_sha256'].items():
        if sha256(Path(name))!=digest:raise ValueError('Fresh model source changed: '+name)
    with tempfile.TemporaryDirectory(prefix='rmx-random-control-audit-',dir='/private/tmp') as directory:
        path=Path(directory)/'targets.txt'
        for old in discovery['cases']:
            trace=old['trace']
            serialized=json.dumps(trace,indent=2)+'\n'
            if hashlib.sha256(serialized.encode()).hexdigest()!=old['trace_sha256']:raise ValueError('Discovery trace changed')
            if not trace['blocks']:continue
            row=old|dict(blocks=trace['blocks'],observed_targets=trace['targets'],observed_control_sha256=trace['full_control_sha256'],prospective_reference_target_driven_prediction=False)
            rows.append(row)
        rows+=fresh['cases'];out=[]
        for row in rows:
            c=row['case'];trace=dict(targets=row['observed_targets']);verify_targets(trace,c['sub2'],row['blocks']*32)
            path.write_text('\n'.join(format(r['target'],'.17g') for r in row['observed_targets'])+'\n');buffers=[]
            for probe in [a.random_probe,a.random_sanitizer]:
                r=subprocess.run([probe,str(c['sub2']),str(row['blocks']),str(path),'controls'],capture_output=True,check=True)
                if r.stderr:raise ValueError('Random probe diagnostics')
                buffers.append(r.stdout)
            digest=hashlib.sha256(buffers[0]).hexdigest()
            if buffers[0]!=buffers[1] or digest!=row['observed_control_sha256']:raise ValueError('Conditional Random stream differs')
            wrong=list(reversed([r['target'] for r in row['observed_targets']]));path.write_text('\n'.join(format(v,'.17g') for v in wrong)+'\n')
            negative=subprocess.run([a.random_probe,str(c['sub2']),str(row['blocks']),str(path),'controls'],capture_output=True,check=True)
            if hashlib.sha256(negative.stdout).hexdigest()==digest:raise ValueError('Wrong-target negative passed')
            own=subprocess.run([a.random_probe,str(c['sub2']),str(row['blocks']),'own','controls'],capture_output=True,check=True)
            own_targets=subprocess.run([a.random_probe,str(c['sub2']),str(row['blocks']),'own','targets'],capture_output=True,check=True)
            targets=np.frombuffer(own_targets.stdout,dtype='<f4');path.write_text('\n'.join(format(v,'.17g') for v in targets)+'\n')
            supplied=subprocess.run([a.random_probe,str(c['sub2']),str(row['blocks']),str(path),'controls'],capture_output=True,check=True)
            if own.stdout!=supplied.stdout:raise ValueError('Target provider changes production arithmetic')
            out.append(dict(case=c,controls=row['blocks']*32,conditional_original_native_asan_f32_identity=True,observed_control_sha256=digest,prospective_reference_target_driven_prediction=row['prospective_reference_target_driven_prediction'],wrong_target_sequence_rejected=True,own_target_provider_invariance=True,default_own_sequence_is_original=own.stdout==buffers[0]))
        for old in json.loads(a.motion_report.read_text())['cases']:
            c=old['case'];buffers=[]
            for probe in [a.motion_probe,a.motion_sanitizer]:
                r=subprocess.run([probe,str(c['sub2']),str(c['wave']),'2849'],capture_output=True,check=True)
                if r.stderr:raise ValueError('Motion probe diagnostics')
                buffers.append(r.stdout)
            if buffers[0]!=buffers[1] or hashlib.sha256(buffers[0]).hexdigest()!=old['control_sha256']:raise ValueError('Prior deterministic controls changed')
            preserved.append(dict(kind='deterministic',case=c['name'],controls=old['controls'],complete_original_native_asan_f32_identity=True))
        release=json.loads(a.sidechain_release.read_text())
        for old in json.loads(a.sidechain_report.read_text())['cases']+[release]:
            c=old['case'];x=np.zeros((192000,2),dtype='<f4') if old is release else stimulus(c['name'].removeprefix('sidechain-fresh-'))
            if old is release:x[:48000]=stimulus('low')
            buffers=[]
            for probe in [a.sidechain_probe,a.sidechain_sanitizer]:
                r=subprocess.run([probe,'--chain',str(c['sub2'])],input=x.tobytes(),capture_output=True,check=True)
                if r.stderr:raise ValueError('Sidechain probe diagnostics')
                buffers.append(r.stdout)
            if buffers[0]!=buffers[1] or hashlib.sha256(buffers[0]).hexdigest()!=old['observed_trace_sha256']:raise ValueError('Prior Sidechain controls changed')
            preserved.append(dict(kind='sidechain',case=c['name'],controls=old['blocks']*32,complete_original_native_asan_f32_identity=True))
    save_json(a.output,dict(kind='random-noise-control-and-regression-audit',verification_passed=True,conditional_random_cases=out,preserved_control_cases=preserved,input_report_sha256={str(path):sha256(path) for path in [a.discovery,a.fresh,a.motion_report,a.sidechain_report,a.sidechain_release]},binary_sha256={name:sha256(getattr(a,name)) for name in ['random_probe','random_sanitizer','motion_probe','motion_sanitizer','sidechain_probe','sidechain_sanitizer']},auditor_sha256=sha256(Path(__file__)),model_sha256=sha256(Path('src/core/NoiseModulator.cpp')),raw_audio_retained=False,scope='Six complete conditional Random control streams and31 preserved deterministic/Sidechain streams through shared production core. Random identity is conditional on the observed target input. Default production targets remain independent; their full controls differ from Original. Includes wrong-target negatives and own-source provider invariance.'))


if __name__=='__main__':main()
