"""Rank complete U20 cell placements against actual two-board envelopes.

Include front/back input and output banks, feedback/trim, configuration and
pull-down. R204 retains its existing upstream connection. This survey does not
approve the circuit or automatically displace the ranked blocking components.
"""
import copy,json,math
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import Point,box
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position,angle
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-buck-enable-native-01';CAP=STAGING/'two-board-power-routing-inputs-2508-buck-enable/capture.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json';OUT=STAGING/'two-board-u20-cell-survey-04'
# Desired relative centre and absolute angle, for U20 pointing toward the top.
POSES={
 'P_U20':([0,0],90),'P_L20':([0,-9.1],90),
 'P_C200':([4.25,3],270),'P_C201':([-2.65,1.4],90),
 'P_C202':([4.4,-1],90),'P_C203':([-4.4,-1],90),
 'P_C210':([2.5,-.75],90),'P_C211':([-2.5,-.75],90),
 'P_C204':([7.5,-4.5],90),'P_C205':([6.8,.15],0),
 'P_C208':([0,-15.65],0),'P_C209':([0,-19.15],0),
 'P_C206':([0,-15.65],0),'P_C207':([0,-12.15],0),
 'P_R200':([-.93,7.5],90),'P_R201':([1.27,4],270),'P_R206':([-.93,4],90),
 'P_R202':([-1.2,4.2],0),'P_R203':([-1.5,-1],180),'P_R205':([4.8,6],0)}

def run():
 assert not OUT.exists()
 cap=json.loads(CAP.read_text());placement=json.loads(PLACEMENT.read_text())
 for n,h in cap['source_sha256'].items():assert sha(REPO/n)==h,n
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(board,'footprint')};records={r['id']:r for r in placement['parts']};objects={o['uuid']:o for o in cap['objects']};moving=set(POSES)
 for o in objects.values():
  if o.get('ref') in moving and o.get('group'):assert all(objects[u].get('ref')==o['ref'] for u in cap['all_groups'][o['group']]),(o['ref'],o.get('pin'))
 envelopes=[]
 for ref,f in fps.items():
  if ref in moving:continue
  for side in ['F','B']:
   try:envelopes.append((ref,side,list(courtyard(f,side+'.CrtYd'))))
   except AssertionError:pass
  r=records.get(ref)
  if r:
   delta=angle(f)-r['angle'];x,y=position(f)
   def env(b):return list(translate(rotate(box(*b),-delta,origin=(0,0)),x,y).bounds)
   envelopes.append((ref,r['side'],env(r['body_relative_xy'])))
   envelopes.extend((ref,e['side'],env(e['bounds'])) for e in r['additional_planar_reserves'])
   envelopes.extend((ref,'B',env(b)) for b in r['tails_relative_xy'])
 mounts=[(o['ref'],o['position_mm'],max(3.6,max(o['drill_mm'])/2+.5)) for o in objects.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])];assert len(mounts)==15
 contexts=[q for q in placement['context'] if not q['id'].startswith('inlet_')]
 allocation=STAGING/'assembly-layout-04/allocation.json'
 for name,x,y,z,dx,dy,t,*_ in json.loads(allocation.read_text())['additional_panel_PCBS']:contexts.append(dict(id=name,xy=[x,y,x+dx,y+dy],z=[z,z+t]))
 outline=shape(cap['outline']).buffer(-.5);xx,yy=[q.ravel() for q in np.meshgrid(np.arange(8,328.01,.5),np.arange(108.5,182.51,.5))];results=[]
 for rot in [0,90,180,270]:
  members=[]
  for ref,(xy,ang) in POSES.items():
   prototype=fps['P_C221'] if ref=='P_C201' else fps[ref]
   rel=rotate(Point(xy),-rot,origin=(0,0));target=list(rel.coords[0]);f=rotate_footprint(prototype,target,ang+rot-angle(prototype));side=first(f,'layer')[1][0];r=records['P_C221' if ref=='P_C201' else ref]
   members.append(dict(ref=ref,side=side,delta_mm=target,angle_degrees=(ang+rot)%360,courtyard_relative_mm=list(courtyard(f,side+'.CrtYd')),height_mm=r['height_mm']))
  for i,m in enumerate(members):
   for n in members[:i]:
    if m['side']==n['side']:assert box(*m['courtyard_relative_mm']).buffer(.3,join_style=2).intersection(box(*n['courtyard_relative_mm'])).area<1e-8,(m['ref'],n['ref'])
  owners={}
  for ref,side,b in envelopes:owners.setdefault(ref,[]).append((side,b))
  counts=np.zeros(len(xx),dtype=np.int32);fixed=np.zeros(len(xx),dtype=bool)
  movable=set()
  for ref in owners:
   pads=[o for o in objects.values() if o.get('ref')==ref]
   if not pads or not ref.split('_',1)[-1].startswith(('R','C','U','Q')):continue
   if any(any(o.get('drill_mm',[0,0])) for o in pads):continue
   if any(o.get('group') and any(objects[u].get('ref')!=ref for u in cap['all_groups'][o['group']]) for o in pads):continue
   bounds=[g.bounds for side,g in [(side,box(*b)) for side,b in owners[ref]]]
   if any(max(b[2]-b[0],b[3]-b[1])>20 for b in bounds):continue
   movable.add(ref)
  for ref,rows in owners.items():
   hit=np.zeros(len(xx),dtype=bool)
   for m in members:
    b=m['courtyard_relative_mm']
    for side,q in rows:
     if side==m['side']:hit|=((xx+b[0]<q[2]+.3-1e-8)&(xx+b[2]>q[0]-.3+1e-8)&(yy+b[1]<q[3]+.3-1e-8)&(yy+b[3]>q[1]-.3+1e-8))
   counts+=hit
   if ref not in movable:fixed|=hit
  valid=~fixed
  for m in members:
   b=m['courtyard_relative_mm'];z0=placement['power_Z'];h=m['height_mm'];z=[z0-.2+1.44,z0+.2+1.76+h] if m['side']=='F' else [z0-.2-h,z0+.2];assert z[0]>=3.05 and z[1]<=43.35
   for q in contexts:
    if min(z[1]+.25,q['z'][1])>max(z[0]-.25,q['z'][0]):
     c=q['xy'];valid&=~((xx+b[0]<c[2]+.25)&(xx+b[2]>c[0]-.25)&(yy+b[1]<c[3]+.25)&(yy+b[3]>c[1]-.25))
   for ref,p,r in mounts:
    # Bounding boxes conservatively reject mounts before exact inspection.
    valid&=~((xx+b[0]<p[0]+r+.3)&(xx+b[2]>p[0]-r-.3)&(yy+b[1]<p[1]+r+.3)&(yy+b[3]>p[1]-r-.3))
  distance=(xx-255)**2+(yy-113.5)**2;candidates=[]
  for idx in np.lexsort((distance,counts)):
   if not valid[idx]:continue
   anchor=[float(xx[idx]),float(yy[idx])]
   shapes={m['ref']:translate(box(*m['courtyard_relative_mm']),*anchor) for m in members}
   if not all(outline.covers(g) for g in shapes.values()):continue
   blocking=sorted(ref for ref,rows in owners.items() if any(m['side']==side and shapes[m['ref']].buffer(.3,join_style=2).intersection(box(*q)).area>=1e-8 for m in members for side,q in rows));assert len(blocking)==counts[idx]
   attached={}
   for ref in blocking:
    others={objects[u].get('ref',objects[u]['kind']) for o in objects.values() if o.get('ref')==ref and o.get('group') for u in cap['all_groups'][o['group']] if objects[u].get('ref')!=ref}
    if others:attached[ref]=sorted(others)
   candidates.append(dict(anchor_mm=anchor,blocking_owners=blocking,blockers_with_external_copper=attached,regulator_displacement_mm=float(math.sqrt(distance[idx]))))
   if len(candidates)>=12:break
  print('rotation',rot,'best',candidates[:2],flush=True)
  results.append(dict(rotation_degrees=rot,members=members,candidates=candidates))
 paths=[Path(__file__),CAP,PLACEMENT,allocation,BASE/'power_protection.kicad_pcb',BASE/'buck-enable-audit.json']
 OUT.mkdir();(OUT/'survey.json').write_text(json.dumps(dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},cells=results,all_moved_part_pad_groups_isolated=True,proposed_boot_substitution='P_C201 uses existing P_C221 0402 100nF 50V footprint/part',blocked_owners_limited_to_unrouted_SMD_parts_under_20mm=True,copper_receiving_and_displaced_parts_not_yet_checked=True,candidate_board_written=False,fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':run()
