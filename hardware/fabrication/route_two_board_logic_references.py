"""Add main-ground reference fields around the routed startup logic.

Do not merge quiet returns or isolated existing ground groups. Native fill,
partition preservation and route-reference coverage still require review.
"""
import copy,json,shutil,uuid
from pathlib import Path
from shapely.geometry import Point
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-startup-logic-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2294-startup-logic-02/capture.json'
PLAN=STAGING/'two-board-logic-reference-plan-01'
OUT=STAGING/'two-board-power-logic-references-01'

def run():
 assert not OUT.exists()
 for p in [CAP,PLAN/'manifest.json']:
  for name,h in json.loads(p.read_text())['source_sha256'].items():
   path=Path(name);assert sha(path if path.is_absolute() else REPO/path)==h,name
 c=json.loads(CAP.read_text());p=json.loads((PLAN/'regions.json').read_text())
 b=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());zones={str(first(z,'uuid')[1]):z for z in children(b,'zone')};zc={z['uuid']:z for z in c['zones']}
 main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2');assert main==p['main_group']
 quiet=set(p['quiet_vias_excluded']);template=zones['2fff880c-5da4-5609-a6d1-dfc1d5b3e287']
 uid=lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPLOGICREF01:'+sha(CAP)+':'+name))
 added=[];edited=[];discarded=[];refill=[]
 def setpoly(z,g):
  g=g.simplify(.00001,preserve_topology=True);assert g.geom_type=='Polygon' and g.is_valid
  z[:]=[n for n in z if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
  z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
  return dict(outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(h.coords)[:-1] for h in g.interiors])
 for layer,record in p['regions'].items():
  parts=sorted([shape([poly]) for poly in record['polygons']],key=lambda g:-g.area);existing=record['existing_zone_uuid'];retained_original=False
  for i,g in enumerate(parts):
   contacts=[o for o in c['objects'] if o['net']=='PWR_AGND' and o['layers'].get(layer) and g.intersects(shape(o['layers'][layer]))]
   if not contacts:
    discarded.append(dict(layer=layer,area_mm2=g.area,reason='No existing ground contact'));continue
   assert {o['group'] for o in contacts}=={main} and not {o['uuid'] for o in contacts}&quiet
   contains_original=existing and shape(zc[existing]['authored_outline']).difference(g.buffer(.000002)).area<1e-6
   if contains_original:
    assert not retained_original;retained_original=True
    if shape(zc[existing]['authored_outline']).symmetric_difference(g).area<1e-6:continue
    z=zones[existing];region=setpoly(z,g);edited.append(dict(uuid=existing,layer=layer,**region));refill.append(existing)
   else:
    z=copy.deepcopy(template);u=uid(layer+'-'+str(i));first(z,'uuid')[1]=u;first(z,'layer')[1]=layer
    region=setpoly(z,g);b.append(z);added.append(dict(uuid=u,layer=layer,net='PWR_AGND',existing_main_contacts=sorted(o['uuid'] for o in contacts),**region))
  if existing:assert retained_original,(layer,'Original field removed')
 OUT.mkdir();sources=[]
 for src in BASE.rglob('*'):
  if not src.is_file():continue
  rel=src.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (src.suffix=='.kicad_sch' or src.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);sources.append(src)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(b)+'\n')
 path=OUT/'power_protection.kicad_sch';s=read_sexpr(path.read_text());first(first(s,'title_block'),'rev')[1]='TBP42-CANDIDATE';path.write_text(sexpr(s)+'\n')
 sources=[Path(__file__),CAP,*PLAN.iterdir(),REPO/'hardware/fabrication/route_nf_surface.py',*sources]
 r=dict(source_sha256={str(src.relative_to(REPO)):sha(src) for src in sources},added_zones=added,edited_zone_outlines=edited,refilled_existing_zones=refill,discarded_unconnected_regions=discarded,existing_main_group=main,excluded_quiet_vias=sorted(quiet),moved_footprints=[],circuit_changes=[],added_tracks=0,added_vias=0,expected_native_opens=2294,native_validation_pending=True,reference_review_pending=True,fabrication_released=False)
 (OUT/'logic-reference-routing.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(added_zones=len(added),edited_zones=len(edited),discarded_regions=len(discarded),total_zones=len(children(b,'zone')))))

if __name__=='__main__':run()
