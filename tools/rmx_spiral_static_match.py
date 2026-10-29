#!/usr/bin/env python3
"""Score static Default48k/120BPM Spiral controls against pinned original captures."""
import argparse,json
from pathlib import Path
import numpy as np
from tools.rmx_drums import require
from tools.reference_audio import save_json,sha256
from tools.noise_statistics import float_wav
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_spiral_core import calibration
from tools.rmx_spiral_return import BUTTONS
from tools.rmx_drums_fx import source_hashes as core_hashes


def bindings():
 names=['tools/rmx_spiral_static_match.py','research/audio/experiments/spiral_static_probe.cpp','research/audio/experiments/IsolateNeutral.h','include/rmx/FactoryEchoReturn.h','include/rmx/Dsp.h','src/core/Wav.cpp','tools/rmx_spiral_programs.py']
 return core_hashes()|{n:sha256(Path(n)) for n in names}


def transport(clock,source,block):
 result=np.zeros_like(clock);result[:min(len(result),len(source))]=source[:len(result)];pending=np.zeros((32,2),dtype=clock.dtype);received=available=head=generated=0
 for start in range(0,len(clock),block):
  count=min(block,len(clock)-start);read=written=0
  while read<count:
   take=min(32-received,count-read);received+=take;read+=take;emit=min(available,count-written);result[start+written:start+written+emit]=pending[head:head+emit];written+=emit;available-=emit;head+=emit
   if received==32:
    pending[:]=0;n=min(32,len(clock)-generated);pending[:n]=clock[generated:generated+n];generated+=32;received=0;available=32;head=0
 return result


def original(folder,host):
 receipt=json.loads((folder/'receipt.json').read_text());require(receipt['complete'] and receipt['role']=='reference' and receipt['sample_rate']==48000 and receipt['host_sha256']==sha256(host) and all(receipt['plugin'][k]==v for k,v in IDENTITY.items()),'Wrong original identity/host')
 for name,key in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==receipt[key],'Original artifact changed: '+str(folder/name))
 require(sha256(Path(receipt['input_path']))==receipt['input_sha256'],'Original input changed')
 for b in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/b['path'])==b['sha256'],'Original binary changed')
 plan=json.loads((folder/'plan.json').read_text());controls={p['name']:p['value'] for p in plan['parameters']};require(plan['sample_rate']==48000 and plan['bpm']==120 and not plan.get('events'),'Requires static48k/120BPM')
 require(all(controls[k]==v for k,v in dict(AutoButton=1,QuantizeButton=0,InputButton=1,XpadButton=0,DefaultSwitch=1,UserSwitch=0).items()),'Outside original static factory route')
 requested=[p|dict(frame=-1) for p in plan['parameters']];actual=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(requested)==len(actual),'Control count differs')
 final={}
 for req,event in zip(requested,actual,strict=True):
  require(all(req[k]==event[k] for k in ['name','id','index','frame']) and np.float32(req['value'])==np.float32(event['requested_value']) and abs(event['immediate_readback']-float(np.float32(req['value'])))<=1e-6,'Original control delivery differs');final[req['name']]=float(np.float32(req['value']))
 after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<=1e-6 for k,v in final.items()),'Original final controls differ')
 selected=[k for k,v in BUTTONS.items() if controls.get(v)==1];require(len(selected)==1,'Requires one Spiral direction')
 rate,a=float_wav(folder/'audio.wav');require(rate==48000 and a.shape==(receipt['frames'],2),'Original audio extent differs')
 return receipt,plan,controls,selected[0],a


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,action='append',default=[]);p.add_argument('--session',type=Path,action='append',default=[])
 for k in ['host','renderer','calibration','output']:p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--transport',action='store_true')
 a=p.parse_args();calibration(a.calibration);bound=bindings();binary=sha256(a.renderer);folders=list(a.case)
 for session in a.session:folders.extend(sorted(p.parent for p in session.glob('*/receipt.json')))
 folders=list(dict.fromkeys(p.resolve() for p in folders));require(folders,'No cases');root=new_directory(a.output);rows=[]
 for i,folder in enumerate(folders):
  r,plan,c,direction,reference=original(folder,a.host);raw={k:round(c[k]*255) for k in ['SceneVolume','Sub1Volume','Sub2Volume']};out=root/f'{i:04d}-candidate.wav'
  run([a.renderer,r['input_path'],out,direction,raw['SceneVolume'],raw['Sub1Volume'],raw['Sub2Volume'],plan['tail_seconds']]+([r['maximum_block_size']] if a.transport else []));rate,candidate=float_wav(out);require(rate==48000 and len(candidate)>=len(reference)-32,'Candidate extent differs');reference=reference[32:];candidate=(candidate[32:] if a.transport else candidate[:len(reference)])
  _,x=float_wav(Path(r['input_path']));dry=np.zeros_like(reference)
  if a.transport:
   clock=np.zeros((len(reference)+32,2),dtype=x.dtype);clock[:min(len(clock),len(x))]=x[:len(clock)];dry[:]=transport(clock,clock,r['maximum_block_size'])[32:]
  else:dry[:min(len(x),len(dry))]=x[:len(dry)]
  whole=screen(reference,candidate);wet=screen(reference.astype(float)-dry,candidate.astype(float)-dry);passed=whole['passed'] and wet['passed'];rows.append(dict(session=folder.parent.name,case=folder.name,direction=direction,controls_raw=raw,receipt_sha256=sha256(folder/'receipt.json'),candidate_sha256=sha256(out),original_sha256=r['output_sha256'],whole=whole,wet=wet,passed=passed));print('PASS' if passed else 'FAIL',folder.name,flush=True)
 require(bound==bindings() and binary==sha256(a.renderer),'Candidate changed');save_json(root/'comparison.json',dict(kind='spiral-static-control-research',callback_transport=a.transport,candidate_offset_frames=32 if a.transport else 0,passed=all(r['passed'] for r in rows),cases=rows,source_sha256=bound,renderer_sha256=binary,host_sha256=sha256(a.host),calibration_sha256=sha256(a.calibration),scope='Existing static original factory48k/120BPM programs. Fixed32-frame reference boundary, no gain/alignment fit. No prospective, moving-control, live-wrapper or hardware qualification.'))
 return 0 if all(r['passed'] for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
