"""Current-board installation evidence; no inferred pin joins or thermal approval."""
import hashlib,json
from pathlib import Path
import numpy as np
from hardware.fabrication.assembly_layout import outline
from hardware.electronics.common.sexpr import children,first
from hardware.electronics.output_stage.check_placement import courtyard,transform
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parents[2]
CAP=REPO/'hardware/cad/two_board_print_01/capture.json'
BOARDS={'signal':REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb','power':REPO/'hardware/fabrication/staging/two-board-power-western-logic-returns-native-02/power_protection.kicad_pcb'}
def overlap(a,b):return all(a[i]<b[i+3] and a[i+3]>b[i] for i in range(3))
def box(xy,z):return [xy[0],xy[1],z[0],xy[2],xy[3],z[1]]
def main():
 d=json.loads(CAP.read_text()); bodies={r:box(xy,z) for r,xy,z in d['component_envelopes']}; obs=[(r,box(xy,z)) for r,xy,z in d['component_envelopes']+d['tail_envelopes']]
 obs += [(r['id'],box(r['xy'],r['z'])) for r in d['context']]
 for m in d['mounts']:obs.append((m[0]+'_post_head',[m[1]-3.2,m[2]-3.2,2.8,m[1]+3.2,m[2]+3.2,m[3]+4.1]))
 for x,y in d['lid_fasteners']:obs.append(('lid_post',[x-3.5,y-3.5,0,x+3.5,y+3.5,43.6]))
 # Conservatively exclude entire mechanism rather than claiming AABB free means motion-safe.
 obs.append(('lever_retention_and_motion_reserve',[298,65,2.8,335,107,43.6]))
 inventory=[]
 for name,path in BOARDS.items():
  tree,_=outline(path)
  for fp in children(tree,'footprint'):
   props={p[1]:p[2] for p in children(fp,'property')};ref=props['Reference']
   if not ('_J' in ref or ref.startswith('J')):continue
   if ref not in bodies:continue
   pads=[]
   for p in children(fp,'pad'):
    if not p[1]:continue
    n=children(p,'net');pads.append(dict(pin=p[1],xy=transform(fp,first(p,'at')[1:3]),net=n[0][-1] if n else None))
   b=bodies[ref];probe=[b[0]-.5,b[1]-.5,b[5]+.01,b[3]+.5,b[4]+.5,42.2]
   hits=[r for r,o in obs if r!=ref and overlap(probe,o)] if probe[2]<probe[5] else ['above_guide_plane']
   # Height to nearest obstacle above existing body in the same footprint projection.
   heights=[(o[2]-b[5],r) for r,o in obs if r!=ref and o[2]>=b[5] and overlap([*probe[:2],b[5],*probe[3:5],100],o)]
   heights.append((42.2-b[5],'guide_plane_conservative'))
   inventory.append(dict(board=name,ref=ref,value=props.get('Value'),footprint=fp[1],pose=first(fp,'at')[1:],side=first(fp,'layer')[1],pads=pads,body_box=b,extra_vertical_room_mm=min(heights)[0],limiting_obstacle=min(heights)[1],vertical_service_probe=probe,vertical_service_obstacles=sorted(set(hits)),mating_part_qualified=False))
 # Conservative housing fan-body search. No ducts, fasteners or pressure claim.
 # Full footprint board bounding rectangles deliberately overexclude concave regions.
 fanobs=obs.copy()
 for b in d['boards']:
  xy=b['outline'];fanobs.append((b['id']+'_pcb_bounding_box',[min(p[0] for p in xy),min(p[1] for p in xy),b['z'],max(p[0] for p in xy),max(p[1] for p in xy),b['z']+1.6]))
 candidates=[];a=np.array([b for _,b in fanobs]); counts={}
 for orient,sz in [('horizontal',[41.5,41.5,11.5]),('side_x',[11.5,41.5,41.5]),('side_y',[41.5,11.5,41.5])]:
  tested=0;free=[]
  for z in np.arange(3.3,42.7-sz[2],2):
   for y in np.arange(7.5,189.1-sz[1],2):
    for x in np.arange(3.3,334.7-sz[0],2):
     lo=np.array([x,y,z]);hi=lo+sz;tested+=1
     if not np.any(np.all((a[:,:3]<hi)&(a[:,3:]>lo),axis=1)):free.append([*lo,*hi])
  counts[orient]=dict(grid_candidates_tested=tested,free_body_boxes=len(free),inflated_body_size_mm=sz)
  candidates += [dict(orientation=orient,box=b) for b in free[:20]]
 paths=[CAP,*BOARDS.values(),Path(__file__),REPO/'hardware/cad/two_board_print_02/latest-physical-compatibility-TBP66-candidate.json',REPO/'hardware/cad/a12/thermal/whole_unit/generated/ledger.json',REPO/'hardware/cad/a12/thermal/forced_air_sunon/analysis.json']
 result=dict(scope='Current-source installation constraints; service probes and conservative fan-body search, not installed-fit approval',source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},connector_count=len(inventory),connectors=inventory,fan_search=counts,fan_candidates=candidates,fan_search_limits=['2 mm grid cannot prove absence of every possible placement','Board bounding boxes conservatively overexclude concave regions','Fan body inflated 0.5 mm each side; no guard, duct or fastener allowance','Vertical orientation exceeds interior height before scan','Exact supplier component heights and connector mates remain unreceived'],complete_harness=False,thermal_qualified=False)
 (ROOT/'installation-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 scad=['// Diagnostic volumes only. Not printable parts or approved cable mates.','part="service";','module box(b){translate([b[0],b[1],b[2]])cube([b[3]-b[0],b[4]-b[1],b[5]-b[2]]);}', 'service_boxes='+json.dumps([c['vertical_service_probe'] for c in inventory if c['vertical_service_probe'][2]<42.2])+';', 'fan_boxes='+json.dumps([c['box'] for c in candidates])+';','if(part=="service")for(b=service_boxes)box(b);','if(part=="fan_candidates")for(b=fan_boxes)box(b);']
 (ROOT/'installation.scad').write_text('\n'.join(scad)+'\n')
 print(json.dumps(dict(connectors=len(inventory),restricted_vertical_probes=sum(bool(c['vertical_service_obstacles']) for c in inventory),fan_search=counts,fan_candidates=candidates[:3]),indent=2))
if __name__=='__main__':main()
