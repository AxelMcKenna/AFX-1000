"""Author screened startup bypass, main-ground return and local feedback joins."""
import json,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-startup-references-native-04'
CAP=STAGING/'two-board-power-routing-inputs-2210-startup-references-04/capture.json'
PLAN=STAGING/'two-board-startup-cells-plan-04/plan.json'
OUT=STAGING/'two-board-power-startup-cells-02'


def run():
 assert not OUT.exists()
 c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
 for data in [c,p]:
  for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 assert all(len(cell['ground_paths'])==2 for cell in p['cells'])
 assert {cell['chip'] for cell in p['cells']}=={'E_U21','E_U25','E_U28'}
 assert p['expected_closed_connections']==len(p['joins'])==11
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
 for i,f in enumerate(board):
  if not(isinstance(f,list) and f and f[0]=='footprint'):continue
  ref=prop(f,'Reference')[2]
  if ref in p['moves']:
   xy,rot,flip=p['moves'][ref];assert not flip
   board[i]=rotate_footprint(f,xy,rot)
 codes={str(n[2]):int(n[1]) for n in children(board,'net')}
 uid=lambda key:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPSTARTCELLS02:'+sha(CAP)+':'+key))
 for i,r in enumerate(p['routes']):
  r['segment_uuids']=[]
  for j,(start,end) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
   u=uid(f'track:{i}:{j}');r['segment_uuids'].append(u)
   board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),r['width_mm']],[a('layer'),r['layer']],[a('net'),codes[r['net']]],[a('uuid'),u]])
 for i,v in enumerate(p['vias']):
  v['uuid']=uid(f'via:{i}')
  board.append([a('via'),[a('at'),*v['position_mm']],[a('size'),v['size_mm']],[a('drill'),v['drill_mm']],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
 affected={l:[] for l in c['copper_layers']}
 for r in p['routes']:affected[r['layer']].append(LineString(r['path_mm']).buffer(.7))
 for v in p['vias']:
  for l in affected:affected[l].append(Point(v['position_mm']).buffer(1.))
 from hardware.fabrication.route_two_board_buck_cell import position,transform_object
 originalfps={prop(f,'Reference')[2]:f for f in children(read_sexpr((BASE/'power_protection.kicad_pcb').read_text()),'footprint')}
 for o in c['objects']:
  if o.get('ref') not in p['moves']:continue
  xy,rot,_=p['moves'][o['ref']];n=transform_object(o,position(originalfps[o['ref']]),xy,rot)
  for item in [o,n]:
   for l,ps in item['layers'].items():affected[l].append(shape(ps).buffer(.7))
 zmap={z['uuid']:z for z in c['zones']};refill=[]
 for z in children(board,'zone'):
  u=str(first(z,'uuid')[1]);g=shape(zmap[u]['authored_outline'])
  if any(g.intersects(h) for h in affected[zmap[u]['layer']]):
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refill.append(u)
 OUT.mkdir();sources=[]
 for src in BASE.rglob('*'):
  if not src.is_file():continue
  rel=src.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or len(rel.parts)==1 and (src.suffix=='.kicad_sch' or src.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json']):
   target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target);sources.append(src)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 path=OUT/'power_protection.kicad_sch';sch=read_sexpr(path.read_text());first(first(sch,'title_block'),'rev')[1]='TBP49-CANDIDATE';path.write_text(sexpr(sch)+'\n')
 sources += [Path(__file__),CAP,PLAN,REPO/'hardware/fabrication/repack_two_board_buck_input.py',REPO/'hardware/fabrication/route_two_board_buck_cell.py',REPO/'hardware/fabrication/route_nf_surface.py']
 result=dict(p,source_sha256={str(f.relative_to(REPO)):sha(f) for f in sources},refilled_existing_zones=refill,edited_zone_outlines=[],retired_objects=[],added_tracks=sum(len(r['segment_uuids']) for r in p['routes']),added_vias=len(p['vias']),all_aux_supply_distribution_complete=False,startup_functionally_verified=False,fabrication_released=False)
 (OUT/'startup-cell-routing.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['added_tracks','added_vias','expected_closed_connections','refilled_existing_zones']}))


if __name__=='__main__':run()
