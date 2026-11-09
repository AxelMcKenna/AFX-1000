"""Place digital source on In4 and provide adjacent quiet references on In1/In6.

Native fill, connectivity and reference-preservation audits are required before
selection. This is not a current/thermal or parasitic qualification.
"""
import copy,json,shutil,uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-digital-cells-native-03'
CAP=STAGING/'two-board-power-routing-inputs-2320-digital-cells-03/capture.json'
OUT=STAGING/'two-board-power-digital-reference-01'


def run():
 assert not OUT.exists()
 cap=json.loads(CAP.read_text());routing=json.loads((BASE/'digital-cell-routing.json').read_text())
 for p,h in cap['source_sha256'].items():assert sha(REPO/p)==h,p
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());zones={str(first(z,'uuid')[1]):z for z in children(board,'zone')}
 codes={str(n[2]):int(n[1]) for n in children(board,'net')}
 uid=lambda label:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPDIGREF01:'+sha(CAP)+':'+label))
 cells=dict(zip(['E_U15','E_U16','E_U17','E_U33'],[['E_R105','E_R106','E_C43'],['E_R109','E_R110','E_C45'],['E_R113','E_R114','E_C47'],['E_R121','E_R122','E_C51']]))
 regions={};required={};old={};owners={};stars={};qids={}
 for q in routing['quiet_ground_islands']:
  ref=q['ref'];stars[ref]=q['star_via'];qids[ref]=q['zone_uuid']
  owned={v['uuid'] for v in [q['star_via'],*q['control_vias']]};owners[ref]=owned
  old[ref]=shape(next(z['authored_outline'] for z in cap['zones'] if z['uuid']==q['zone_uuid']))
  for layer,surface in [('In1.Cu','F.Cu'),('In6.Cu','B.Cu')]:
   rr=[r for r in routing['routes'] if r.get('chip',r.get('ref'))==ref and r['layer']==surface]
   pads=[shape(o['layers'][surface]) for o in cap['objects'] if o.get('ref') in cells[ref] and o['layers'].get(surface)]
   targets=[LineString(r['path_mm']).buffer(r['width_mm']/2+.4) for r in rr]+[p.buffer(.4) for p in pads]
   required[(ref,layer)]=unary_union([LineString(r['path_mm']).buffer(r['width_mm']/2+.04) for r in rr]+[p.buffer(.04) for p in pads])
   g=unary_union([Point(q['star_via']['position_mm']).buffer(.65),*targets]).convex_hull
   if layer=='In1.Cu':g=unary_union([g,old[ref]])
   for o in cap['objects']:
    if o['uuid'] not in owned and o['net']=='PWR_AGND' and o['layers'].get(layer):g=g.difference(shape(o['layers'][layer]).buffer(.21,quad_segs=64))
    if o.get('npth'):g=g.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51,quad_segs=64))
   for z in cap['zones']:
    if z['layer']!=layer or z['uuid']==q['zone_uuid'] or (z['net']=='PWR_5V_DIG_SRC' and layer=='In6.Cu'):continue
    g=g.difference(shape(z['authored_outline']).buffer(.215))
   regions[(ref,layer)]=g
 for layer in ['In1.Cu','In6.Cu']:
  for ref in cells:
   for other in cells:
    if other==ref:continue
    reserved=required[(other,layer)].buffer(.215)
    if layer=='In1.Cu':reserved=reserved.difference(old[ref].buffer(.215))
    regions[(ref,layer)]=regions[(ref,layer)].difference(reserved)
  refs=list(cells)
  for i,ref in enumerate(refs):
   for other in refs[i+1:]:regions[(other,layer)]=regions[(other,layer)].difference(regions[(ref,layer)].buffer(.215))
  for ref in cells:
   g=regions[(ref,layer)];ps=list(g.geoms) if hasattr(g,'geoms') else [g]
   regions[(ref,layer)]=next(p for p in ps if p.covers(Point(stars[ref]['position_mm'])))
 def setpoly(z,g):
  g=g.simplify(.00001,preserve_topology=True);assert g.geom_type=='Polygon' and g.is_valid
  z[:]=[n for n in z if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
  z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
  return dict(outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(h.coords)[:-1] for h in g.interiors])
 edits=[];new=[]
 for ref in cells:
  u=qids[ref];edits.append(dict(uuid=u,layer='In1.Cu',**setpoly(zones[u],regions[(ref,'In1.Cu')])))
  z=copy.deepcopy(zones[u]);first(z,'layer')[1]='In6.Cu';u=uid(ref+'-back-quiet');first(z,'uuid')[1]=u
  region=setpoly(z,regions[(ref,'In6.Cu')]);board.append(z);new.append(dict(uuid=u,layer='In6.Cu',net='PWR_AGND',ref=ref,allowed_ground_objects=sorted(owners[ref]),**region))
 src=next(z for z in cap['zones'] if z['net']=='PWR_5V_DIG_SRC' and z['layer']=='In6.Cu');source=shape(src['authored_outline'])
 first(zones[src['uuid']],'layer')[1]='In4.Cu';edits.append(dict(uuid=src['uuid'],old_layer='In6.Cu',layer='In4.Cu',**setpoly(zones[src['uuid']],source)))
 for z in cap['zones']:
  if z['layer']=='In4.Cu' and shape(z['authored_outline']).intersects(source.buffer(.215)):
   g=shape(z['authored_outline']).difference(source.buffer(.215));edits.append(dict(uuid=z['uuid'],layer='In4.Cu',**setpoly(zones[z['uuid']],g)))
 # Main ground beside the quiet islands references local input-capacitor escapes.
 main=next(o['group'] for o in cap['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
 ground=next(z for z in cap['zones'] if z['uuid']=='2fff880c-5da4-5609-a6d1-dfc1d5b3e287')
 g=shape(ground['authored_outline'])
 for ref in cells:g=g.difference(regions[(ref,'In6.Cu')].buffer(.215))
 for o in cap['objects']:
  if o['net']=='PWR_AGND' and o.get('group')!=main and o['layers'].get('In6.Cu'):g=g.difference(shape(o['layers']['In6.Cu']).buffer(.21))
 parts=list(g.geoms) if hasattr(g,'geoms') else [g];discarded=[]
 for i,g in enumerate(sorted(parts,key=lambda p:-p.area)):
  contacts=[o['uuid'] for o in cap['objects'] if o['net']=='PWR_AGND' and o.get('group')==main and o['layers'].get('In6.Cu') and g.intersects(shape(o['layers']['In6.Cu']))]
  if not contacts:discarded.append(dict(area_mm2=g.area,reason='No existing main-ground contact'));continue
  z=copy.deepcopy(zones[ground['uuid']]);u=uid('back-force-return-'+str(i));first(z,'uuid')[1]=u;first(z,'layer')[1]='In6.Cu'
  region=setpoly(z,g);board.append(z);new.append(dict(uuid=u,layer='In6.Cu',net='PWR_AGND',ref='main',existing_main_contacts=contacts,**region))
 OUT.mkdir();sources=[]
 for p in BASE.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (p.suffix=='.kicad_sch' or p.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst);sources.append(p)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 p=OUT/'power_protection.kicad_sch';s=read_sexpr(p.read_text());first(first(s,'title_block'),'rev')[1]='TBP39';p.write_text(sexpr(s)+'\n')
 sources=[Path(__file__),CAP,BASE/'digital-cell-routing.json',REPO/'hardware/fabrication/route_nf_surface.py',*sources]
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},edited_zones=edits,new_zones=new,discarded_unconnected_main_regions=discarded,quiet_ground_islands=routing['quiet_ground_islands'],moved_footprints=[],circuit_changes=[],added_tracks=0,added_vias=0,source_layer_change=['In6.Cu','In4.Cu'],native_validation_pending=True,complete_current_thermal_parasitic_qualification=False,fabrication_released=False)
 (OUT/'digital-reference-routing.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(edited_zones=len(edits),new_zones=len(new))))
if __name__=='__main__':run()
