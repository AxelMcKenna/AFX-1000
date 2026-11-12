"""Extract actual TBP61/signal board geometry. Coordinates and exports are mm."""
import hashlib, json, math, re
from pathlib import Path
from hardware.fabrication.assembly_layout import outline
from hardware.electronics.common.sexpr import children, first
from hardware.electronics.output_stage.check_placement import courtyard, transform

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
CAP=REPO/'hardware/fabrication/staging/two-board-placement-04/capture.json'
PATHS={
 'signal':REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb',
 'power':REPO/'hardware/fabrication/staging/two-board-power-control-corridors-native-02/power_protection.kicad_pcb'}

def main():
 old=json.loads(CAP.read_text()); known={p['id']:p for p in old['parts']}
 sources=[CAP,*PATHS.values(),Path(__file__)]
 boards=[];mounts=[];bodies=[];tails=[];assumptions=[]
 for name,path in PATHS.items():
  tree,poly=outline(path); z=old[name+'_Z'];holes=[]
  for fp in children(tree,'footprint'):
   ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
   pads=children(fp,'pad');side=first(fp,'layer')[1][0]
   if pads and all(p[2]=='np_thru_hole' for p in pads):
    for p in pads:
     xy=transform(fp,first(p,'at')[1:3]);d=float(first(p,'drill')[1]);holes.append([*xy,d])
     if d<3:mounts.append([ref,*xy,z,d])
    continue
   p=known.get(ref)
   h=float(p['height_mm']) if p else (3 if 'D_SMA' in fp[1] else 2.5)
   if not p: assumptions.append(dict(ref=ref,footprint=fp[1],height_mm=h,basis='Conservative provisional allocation; inspect selected part before assembly'))
   try: xy=list(courtyard(fp,side+'.CrtYd'))
   except AssertionError:
    pts=[transform(fp,first(pad,'at')[1:3]) for pad in pads]
    xy=[min(x[0] for x in pts)-1,min(x[1] for x in pts)-1,max(x[0] for x in pts)+1,max(x[1] for x in pts)+1]
   # Retain body overhang beyond courtyard, rotating the captured global box
   # by any change in footprint angle. This is conservative, not exact STEP.
   if p:
    a=math.radians((float(first(fp,'at')[3]) if len(first(fp,'at'))>3 else 0)-p['angle'])
    bb=p['body_relative_xy'];pos=first(fp,'at');corners=[(u*math.cos(a)+v*math.sin(a),-u*math.sin(a)+v*math.cos(a)) for u in (bb[0],bb[2]) for v in (bb[1],bb[3])]
    xy=[min(xy[0],float(pos[1])+min(t[0] for t in corners)),min(xy[1],float(pos[2])+min(t[1] for t in corners)),max(xy[2],float(pos[1])+max(t[0] for t in corners)),max(xy[3],float(pos[2])+max(t[1] for t in corners))]
   zz=[z-.2-h,z+.2] if side=='B' else [z-.2+1.44,z+.2+1.76+h]
   bodies.append([ref,xy,zz])
   for pad in pads:
    if pad[2]!='thru_hole':continue
    px,py=transform(fp,first(pad,'at')[1:3]);size=list(map(float,first(pad,'size')[1:3]));r=max(size)/2
    tails.append([ref,[px-r,py-r,px+r,py+r],[z-.2-3.2,z+.2]])
  boards.append(dict(id=name,outline=list(poly.exterior.coords)[:-1],z=z,thickness=1.6,holes=holes))
 data=dict(units='mm',outer=[338,192.4,45.6],boards=boards,mounts=mounts,
  touch_mounts=[[130.0871,168.922,20],[93.0871,168.9352,20]],
  lid_fasteners=[[x,y] for x in (3.9,334.1) for y in (8,96,188.5)]+[[169,188.5]],
  component_envelopes=bodies,tail_envelopes=tails,
  context=[c for c in old['context'] if not c['id'].startswith(('inlet_','touch_post_')) and c['id']!='release_bracket_and_motion_XY_keepout'],
  new_height_assumptions=assumptions,heights_supplier_approved=False,complete_harness=False,operational_thermal_qualification=False)
 rear=REPO/'hardware/cad/a12/enclosure_growth/rear-ports/analysis.json';sources.append(rear)
 data['rear_ports']=json.loads(rear.read_text())['candidate_rear_ports']
 # Keep the DC mating datum while adding 0.4 mm vertical opening allowance.
 for p in data['rear_ports']:
  if p[0]=='dc_input':p[5]=14.2
 data['rear_opening_change']='DC rectangle height 13.4 to 14.2, same X/Z centre and Y=-1.6 face; switch body backside counterbore Y>=0.30'
 data['rear_body_envelopes']=[[c['id'],[c['xy'][0]-.2,c['xy'][1]-.2,c['xy'][2]+.2,c['xy'][3]+.2],[c['z'][0]-.36,c['z'][1]+.36]] for c in old['context'] if c['id'] in ('inlet_J1','inlet_S1','inlet_S1_actuator')]
 defs=[]
 for f,keys in [('layout.scad',['openings','caps']),('controls.scad',['buttons','knobs'])]:
  path=REPO/'hardware/cad/a11/generated'/f;sources.append(path)
  for k in keys:
   value=json.loads(re.search(r'^'+k+r' = (.*);',path.read_text(),re.M)[1]);data[k]=value;defs.append(k+' = '+json.dumps(value)+';')
 data['source_sha256']={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
 (ROOT/'capture.json').write_text(json.dumps(data,indent=2)+'\n')
 defs += [k+' = '+json.dumps(data[k])+';' for k in ['mounts','touch_mounts','lid_fasteners','rear_ports']]
 defs += ['board_profiles = '+json.dumps([[b['outline'],b['z'],b['holes']] for b in boards])+';',
          'component_boxes = '+json.dumps([[b[1],b[2]] for b in bodies+tails])+';',
          'context_boxes = '+json.dumps([[c['xy'],c['z']] for c in data['context']])+';']
 defs += ['rear_component_boxes = '+json.dumps([[b[1],b[2]] for b in bodies if b[0] not in ('I_J1','I_S1')]+[[b[1],b[2]] for b in tails]+[[b[1],b[2]] for b in data['rear_body_envelopes']])+';']
 (ROOT/'captured.scad').write_text('// Generated by capture.py; actual current PCB geometry.\n'+'\n'.join(defs)+'\n')
 print(json.dumps(dict(boards=len(boards),mounts=len(mounts),bodies=len(bodies),tails=len(tails),new_height_assumptions=len(assumptions))))
if __name__=='__main__':main()
