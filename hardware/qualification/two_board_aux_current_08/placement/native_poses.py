import json,sys,hashlib
from pathlib import Path
import pcbnew
h=Path(sys.argv[1]);out=Path(sys.argv[2]);p=json.loads((h/'placement/individual-placement.json').read_text());rows=[]; board=pcbnew.BOARD()
for group in p['groups'].values():
 for pose in group['chosen']['parts']:
  lib,name=pose['footprint'].split(':');lp=h/'placement/AUX_READY.pretty' if lib=='AUX_READY' else h/'held_rail/authored/libraries'/f'{lib}.pretty'
  f=pcbnew.FootprintLoad(str(lp),name);board.Add(f);f.SetReference(pose['ref'])
  if pose['layer']=='B.Cu':f.Flip(pcbnew.VECTOR2I(0,0),True)
  f.SetOrientationDegrees((pose['rotation_deg']+(180 if pose['layer']=='B.Cu' else 0))%360);f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in pose['at_mm']]))
  rows.append({'footprint_sha256':hashlib.sha256((lp/(name+'.kicad_mod')).read_bytes()).hexdigest(),'ref':pose['ref'],'layer':f.GetLayerName(),'orientation_degrees':f.GetOrientationDegrees(),'pads':{q.GetNumber():[pcbnew.ToMM(q.GetPosition().x),pcbnew.ToMM(q.GetPosition().y)] for q in f.Pads()}})
(out/'native-poses.json').write_text(json.dumps({'input_proposal_sha256':hashlib.sha256((h/'placement/individual-placement.json').read_bytes()).hexdigest(),'native_version':pcbnew.Version(),'pcb_written':False,'poses':rows},indent=2)+'\n')
