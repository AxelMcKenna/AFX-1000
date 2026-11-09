"""Restore main-return copper where retired quiet-control vias left clearance holes."""
import copy,json,shutil
from pathlib import Path
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape

def run():
 source=STAGING/'two-board-power-digital-startup-02';native=STAGING/'two-board-power-digital-startup-native-01';out=STAGING/'two-board-power-digital-startup-04';assert not out.exists()
 oldcp=STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json';cp=STAGING/'two-board-power-routing-inputs-2310-digital-startup-01/capture.json'
 old,current=[json.loads(p.read_text()) for p in [oldcp,cp]]
 for p in [oldcp,cp,native/'digital-startup-review.json',native/'digital-startup-reference-review.json']:
  for n,h in json.loads(p.read_text())['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h
 r=json.loads((source/'digital-startup-routing.json').read_text());retired=[o for o in old['objects'] if o['uuid'] in r['retired_objects'] and o['kind']=='PCB_VIA' and o['net']=='PWR_AGND'];assert len(retired)==9
 main=next(o['group'] for o in current['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
 protected=[v for q in r['quiet_ground_islands'] for v in q['control_vias']+q['extra_quiet_vias']]
 board=read_sexpr((source/'power_protection.kicad_pcb').read_text());zones={str(first(z,'uuid')[1]):z for z in children(board,'zone')};changed=[]
 for z in current['zones']:
  if z['layer']!='In5.Cu' or z['net']!='PWR_AGND':continue
  original=shape(z['authored_outline']);assert original.geom_type=='Polygon';outer=Polygon(original.exterior)
  addition=unary_union([Point(o['position_mm']).buffer(.51002,quad_segs=64).intersection(outer) for o in retired]).difference(original)
  for v in protected:addition=addition.difference(Point(v['position_mm']).buffer(.51,quad_segs=64))
  for o in current['objects']:
   if o['net']=='PWR_AGND' and o.get('group')!=main and o['layers'].get('In5.Cu'):addition=addition.difference(shape(o['layers']['In5.Cu']).buffer(.21,quad_segs=64))
   if o.get('npth'):addition=addition.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51,quad_segs=64))
  g=unary_union([original,addition])
  if original.symmetric_difference(g).area<1e-7:continue
  g=g.simplify(.00001,preserve_topology=True);assert g.geom_type=='Polygon' and g.is_valid
  u=z['uuid'];node=zones[u];node[:]=[n for n in node if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
  node.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
  record=dict(uuid=u,layer='In5.Cu',outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(h.coords)[:-1] for h in g.interiors])
  r['edited_zone_outlines']=[x for x in r['edited_zone_outlines'] if x['uuid']!=u]+[record]
  if u not in r['refilled_existing_zones']:r['refilled_existing_zones'].append(u)
  changed.append(dict(uuid=u,restored_authored_copper_mm2=g.difference(original).area,removed_authored_copper_mm2=original.difference(g).area))
 assert changed
 sources=[Path(__file__),oldcp,cp,native/'digital-startup-review.json',native/'digital-startup-reference-review.json',REPO/'hardware/fabrication/route_nf_surface.py',*[p for p in source.rglob('*') if p.is_file()]]
 shutil.copytree(source,out);(out/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 r['source_sha256'].update({str(p.relative_to(REPO)):sha(p) for p in sources})
 r['retired_quiet_clearance_restoration']=dict(retired_ground_vias=[o['uuid'] for o in retired],edited_planes=changed,current_control_and_extra_quiet_via_exclusions_preserved=True,other_separate_ground_and_NPTH_exclusions_preserved=True)
 (out/'digital-startup-routing.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(changed))
if __name__=='__main__':run()
