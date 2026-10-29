#!/usr/bin/env python3
"""Capture development-only Spiral control and button transitions."""
import argparse,concurrent.futures,json
from pathlib import Path
from tools import rmx_spiral_programs as programs
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_drums import require


def recipe():
 rows=[]
 for direction in ['up','down']:
  for i,kind in enumerate(['main','pitch','time','enabled']):
   values=dict(main=[192,64,248,4,128,96],pitch=[64,130,255,17,0,192],time=[64,130,255,11,128,0],enabled=[0,1,0,1,0,1])[kind];frames=[96113,144319,192193,240277,288419,336607];changes=[dict(frame=f,control=kind,raw=r) for f,r in zip(frames,values,strict=True)];rows.append(dict(name=f'spiral-motion-{direction}-{kind}',direction=direction,kind=kind,main=128,time=0,pitch=0,source='program',block=[127,263,1021,32][i],changes=changes))
 return rows


def plan_for(c,inventory):
 def setting(name,value):
  matches=[p for p in inventory['parameters'] if p['name']==name];require(len(matches)==1,'Original control differs '+name);return {k:matches[0][k] for k in ['id','index','name']}|dict(value=value)
 values=dict(AutoButton=1,QuantizeButton=0,InputButton=1,XpadButton=0,IsolatorButton=0,DefaultSwitch=1,UserSwitch=0,SceneVolume=c['main']/255,Sub1Volume=c['time']/255,Sub2Volume=c['pitch']/255);values[programs.BUTTONS[c['direction']]]=int(c.get('initial_enabled',True))
 names=dict(main='SceneVolume',pitch='Sub2Volume',time='Sub1Volume');events=[];direction=c['direction']
 for e in c['changes']:
  if e['control']=='direction':
   next_direction=['up','down'][e['raw']]
   if next_direction!=direction:events.append(setting(programs.BUTTONS[direction],0)|dict(frame=e['frame'],type='parameter'))
   events.append(setting(programs.BUTTONS[next_direction],1)|dict(frame=e['frame'],type='parameter'));direction=next_direction
  else:events.append(setting(programs.BUTTONS[direction] if e['control']=='enabled' else names[e['control']],e['raw'] if e['control']=='enabled' else e['raw']/255)|dict(frame=e['frame'],type='parameter'))
 return dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,sample_rate=48000,bpm=120,tail_seconds=0,parameters=[setting(k,v) for k,v in values.items()],events=events)


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['host','plugin','session']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();root=new_directory(a.session);script=sha256(Path(__file__));inventory=json.loads(run([a.host,'inventory',a.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original');save_json(root/'inventory.json',inventory);write_wav(root/'program.wav',48000,programs.sources('mixed')['program'].ravel())
 def capture(c):
  plan=root/(c['name']+'.json');save_json(plan,plan_for(c,inventory));run([a.host,'render',a.plugin,root/'program.wav',plan,root/c['name'],c['block']]);print('DISCOVERY',c['name'],flush=True);return c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json'))
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(capture,recipe()))
 require(script==sha256(Path(__file__)),'Discovery recipe changed');save_json(root/'matrix.json',dict(kind='spiral-control-motion-original-discovery',cases=rows,verifier_sha256=script,input_sha256=sha256(root/'program.wav'),scope='Development discovery without prospective model predictions. Input-only Default48k/120BPM. No live or hardware qualification.'))
if __name__=='__main__':main()
