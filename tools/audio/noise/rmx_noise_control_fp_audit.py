#!/usr/bin/env python3
"""Verify Original control hashes through the actual shared production core."""
from pathlib import Path
import json,subprocess,hashlib
import numpy as np
from tools.audio.noise.rmx_noise_sidechain_controls import stimulus
from tools.audio.common.reference_audio import sha256,save_json
import argparse
parser=argparse.ArgumentParser(description="Audit the shared contraction-disabled production Noise controls")
for name in ["motion-controls","sidechain-controls","sidechain-release","motion-probe","motion-sanitizer","sidechain-probe","sidechain-sanitizer","core-library","scene-object","model-object","output"]:parser.add_argument("--"+name,type=Path,required=True)
parser.add_argument("--baseline",default="c9ccbb6dd0862cfebe139e13b759b3b6cdae8d6b")
args=parser.parse_args()
R=Path.cwd();old_header=subprocess.check_output(['git','show',args.baseline+':include/rmx/NoiseModulator.h'],text=True);new_header=(R/'include/rmx/NoiseModulator.h').read_text();cpp=(R/'src/core/NoiseModulator.cpp').read_text();start=old_header.index('    const std::array<float,32>& sidechain');end=old_header.index('\nprivate:',start);functions=old_header[start:end];expected=functions.replace('    const std::array<float,32>& sidechain(', 'const std::array<float,32>& NoiseModulator::sidechain(').replace('    const std::array<float,32>& generate(', 'const std::array<float,32>& NoiseModulator::generate(').replace('bool resonance=false','bool resonance');assert expected in cpp
assert new_header==old_header[:start]+'    const std::array<float,32>& sidechain(int raw,const std::array<float,32>& detector,float target) noexcept;\n    const std::array<float,32>& generate(int raw,int wave,bool resonance=false) noexcept;'+old_header[end:]
assert '-ffp-contract=off' in (args.model_object.parents[2]/'flags.make').read_text().split('NoiseModulator.cpp.o_OPTIONS = ')[1].splitlines()[0]
assembly=subprocess.check_output(['otool','-tvV',str(args.model_object)],text=True);assert not any(op in assembly for op in ['fmadd','fmsub','fnmadd','fnmsub'])
scene_symbols=subprocess.check_output(['nm','-C',str(args.scene_object)],text=True);assert all(' U rmx::NoiseModulator::'+name in scene_symbols for name in ['generate','sidechain'])
rows=[]
for old in json.loads(args.motion_controls.read_text())['cases']:
 c=old['case'];arguments=[str(c['sub2']),str(c['wave']),'2849'];outputs=[]
 for build in ['core','asan']:
  r=subprocess.run([args.motion_probe if build=='core' else args.motion_sanitizer,*arguments],capture_output=True,check=True);assert not r.stderr;outputs.append(r.stdout)
 assert outputs[0]==outputs[1] and hashlib.sha256(outputs[0]).hexdigest()==old['control_sha256'];rows.append(dict(kind='deterministic',case=c['name'],prospective=old['prospective'],controls=old['controls'],complete_original_native_asan_identity=True,sha256=old['control_sha256']))
fresh=json.loads(args.sidechain_controls.read_text());release=json.loads(args.sidechain_release.read_text())
for old in fresh['cases']+[release]:
 c=old['case']
 if old is release:x=np.zeros((192000,2),dtype='<f4');x[:48000]=stimulus('low')
 else:x=stimulus(c['name'].removeprefix('sidechain-fresh-'))
 outputs=[]
 for build in ['core','asan']:
  r=subprocess.run([args.sidechain_probe if build=='core' else args.sidechain_sanitizer,'--chain',str(c['sub2'])],input=x.tobytes(),capture_output=True,check=True);assert not r.stderr;outputs.append(r.stdout)
 assert outputs[0]==outputs[1] and hashlib.sha256(outputs[0]).hexdigest()==old['prediction_sha256']==old['observed_trace_sha256'];rows.append(dict(kind='sidechain',case=c['name'],prospective=True,controls=old['blocks']*32,complete_original_native_asan_identity=True,sha256=old['observed_trace_sha256']))
baseline_stimulus=subprocess.check_output(['git','show',args.baseline+':tools/rmx_noise_sidechain_controls.py'],text=True)
current_stimulus=Path('tools/audio/noise/rmx_noise_sidechain_controls.py').read_text()
# Compare the historical source after reversing only the directory relocation.
for current, historical in [('from tools.audio.noise import', 'from tools import'), ('tools.audio.noise.', 'tools.'), ('tools.audio.common.', 'tools.'), ('tools/audio/noise/', 'tools/'), ('tools/audio/common/', 'tools/'), ('tools/probes/', 'tools/')]:
 current_stimulus=current_stimulus.replace(current,historical)
assert current_stimulus.replace("'include/rmx/NoiseModulator.h','src/core/NoiseModulator.cpp',","'include/rmx/NoiseModulator.h',")==baseline_stimulus
source_changes={n:dict(before_sha256=hashlib.sha256(subprocess.check_output(['git','show',args.baseline+':'+n.replace('tools/audio/noise/','tools/')])).hexdigest() if n!='src/core/NoiseModulator.cpp' else None,after_sha256=sha256(R/n)) for n in ['CMakeLists.txt','hardware/firmware/full_engine/CMakeLists.txt','include/rmx/NoiseModulator.h','src/core/NoiseModulator.cpp','tools/audio/noise/rmx_noise_sidechain_controls.py']}
binaries={name:sha256(getattr(args,name)) for name in ['motion_probe','motion_sanitizer','sidechain_probe','sidechain_sanitizer']}
save_json(args.output,dict(kind='shared-production-noise-control-fp-audit',passed=True,baseline_commit=args.baseline,input_report_sha256={str(p):sha256(p) for p in [args.motion_controls,args.sidechain_controls,args.sidechain_release]},auditor_sha256=sha256(Path(__file__)),functions_moved_without_source_body_changes=True,actual_scene_uses_shared_out_of_line_functions=True,shared_core_object_sha256=sha256(args.model_object),core_archive_sha256=sha256(args.core_library),no_fused_multiply_add_in_control_object=True,source_changes=source_changes,binary_sha256=binaries,cases=rows,raw_audio_retained=False,scope='All24 earlier deterministic and seven Sidechain complete Original control observations replay exactly through the same contraction-disabled core functions linked by the live Engine. Corrects the distinction between standalone probe arithmetic and compiler-contracted live arithmetic. Does not upgrade changed audio without a separate WAV bridge or fresh reference checks.'))
print('31 complete observed streams match actual shared production core; no contraction instructions')
