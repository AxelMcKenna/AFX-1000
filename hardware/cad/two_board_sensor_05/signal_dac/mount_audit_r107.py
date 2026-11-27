"""Fail-closed exact authored delta, all-group preservation and physical mount copper audit."""
import hashlib,json,math
from pathlib import Path
from shapely.geometry import Point,Polygon,shape as geo_shape
from hardware.fabrication.route_nf_surface import shape
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=read(R/'capture-r98/capture.json');c=read(R/'capture-r107/capture.json');r=read(R/'candidate-r107/routing.json');ids={v['uuid']for v in r['declared_removed']}
assert ids=={'ddc4f060-acad-5cdf-b2c5-eacdce6eecf9','f9f46967-df4b-52ce-b081-6c81851d0ff4','ecea17e2-69ed-5621-9e63-7ff6ca085a4f','31bc344d-b4e1-51bf-8de8-d76f7082df5b','bf298509-8042-5fe0-a905-34ead3d3e6a9'}
def objects(p):
 t=read_sexpr(p.read_text());out={}
 for tag in ['footprint','segment','via','zone','gr_line','gr_rect','gr_arc','gr_circle','gr_poly']:
  for row in children(t,tag):
   u=first(row,'uuid')
   if not u:continue
   out[u[1]]=sexpr([x for x in row if not(isinstance(x,list)and x and x[0]=='filled_polygon')])
 return t,out
bt,bo=objects(R/'native-r98/signal_main.kicad_pcb');nt,no=objects(R/'native-r107/signal_main.kicad_pcb')
assert {u for u,x in bo.items()if no.get(u)!=x}==ids
assert all(x['uuid']not in no and bo[x['uuid']]==x['before_sexpr']for x in r['declared_removed'])
for tag in ['general','layers','setup']:assert [sexpr(x)for x in children(bt,tag)]==[sexpr(x)for x in children(nt,tag)]
# Every old native electrical partition retains exactly its surviving membership; no merge or split.
after={u:g for g,vs in c['all_groups'].items()for u in vs};seen=set()
for gid,vs in b['all_groups'].items():
 dest={after[u]for u in vs if u not in ids};assert len(dest)==1,(gid,dest);newgid=next(iter(dest));assert newgid not in seen;seen.add(newgid)
assert len(seen)==len(c['all_groups'])
newobjects={x['uuid']:x for x in c['objects']};oldobjects={x['uuid']:x for x in b['objects']}
# Exact replacement net/layer/width/endpoints, including the two centered inner-layer tracks.
expected=[('LINK_SDA','F.Cu',[190.5,85.1],[191.394049,84.558567]),('LINK_SDA','F.Cu',[191.394049,84.558567],[188.5,68.9]),('/D_LED/LED_39','In3.Cu',[191.3,79.9],[189.2,77.5]),('/D_LED/LED_39','In5.Cu',[189.2,77.5],[189.2,67.6])]
tracks=[x for u,x in newobjects.items()if u not in oldobjects and x['kind']=='PCB_TRACK'];assert len(tracks)==4
for net,layer,p,q in expected:assert sum(x['net']==net and list(x['layers'])==[layer]and x['width_mm']==.2 and x['position_mm']==p and x['end_mm']==q for x in tracks)==1
kpath=REPO/'hardware/cad/assembly_workflow/verification/main-fasteners-r1/contact-keepouts.json';k=read(kpath);zs={x['uuid']:x for x in c['zones']};checks=[]
for f in k['features']:
 if f['properties']['board']!='signal':continue
 prop=f['properties'];name=prop['mount'];z=zs[r['keepout_uuids'][name]];p=shape(z['authored_outline']);source=geo_shape(f['geometry']);assert p.covers(source)
 assert z['keepout']and z['prohibit_tracks']and z['prohibit_vias']and z['layer']=='F.Cu'
 assert p.boundary.distance(Point(prop['center_mm']))>=2.4
 hits=[]
 for o in c['objects']:
  if not o['layers'].get('F.Cu'):continue
  if o.get('npth'):
   # The existing mount apertures are circular, with no copper outside their exact drill.
   pad=next(pad for fp in children(nt,'footprint')for pad in children(fp,'pad')if first(pad,'uuid')[1]==o['uuid'])
   if pad[2]=='np_thru_hole'and pad[3]=='circle' and tuple(map(float,first(pad,'size')[1:]))==tuple(o['drill_mm']):continue
  g=shape(o['layers']['F.Cu']);area=g.intersection(source).area
  if area>1e-9:hits.append({'uuid':o['uuid'],'area_mm2':area})
 for zone in c['zones']:
  if zone['layer']=='F.Cu'and not zone['keepout']and shape(zone['polygons']).intersection(source).area>1e-9:hits.append({'zone':zone['uuid']})
 assert not hits,(name,hits);checks.append({'mount':name,'native_rule_uuid':z['uuid'],'native_minimum_radius_mm':p.boundary.distance(Point(prop['center_mm'])),'full_source_receiving_region_covered':True,'conductive_copper_hits':hits})
assert len(checks)==9
rules=(R/'native-r107/signal_main.kicad_dru').read_text();oldrules=(R/'native-r98/signal_main.kicad_dru').read_text();assert rules.startswith(oldrules)
for v in checks:assert 'Main mount '+v['mount']+' conductive receiving disc r2.4 copper pads'in rules
assert "A.Pad_Type != 'NPTH, mechanical' || A.Pad_Shape != 'Circle' || A.Size_X > A.Hole_Size_X || A.Size_Y > A.Hole_Size_Y" in rules
previous_ref=read(R/'reference-review-r98.json');current_ref=read(R/'reference-review-r107.json')
prior={x['uuid']:x for x in previous_ref['retained_reference_cases']};retained={x['uuid']:x for x in current_ref['retained_reference_cases']};removed_tracks={u for u in ids if oldobjects[u]['kind']=='PCB_TRACK'}
assert set(prior)-set(retained)==removed_tracks and not(set(retained)-set(prior))and len(removed_tracks)==4
replacement_refs=[x for x in current_ref['new_reference_cases']if x['name']in ['LINK_SDA mount rework','/D_LED/LED_39 mount via recenter']]
assert len(replacement_refs)==3 and all(x['unexplained_uncovered_mm2']<1e-6 for x in replacement_refs)
removed_reference_cases=[{'uuid':u,'net':oldobjects[u]['net'],'layer':next(iter(oldobjects[u]['layers'])),'before_start_mm':oldobjects[u]['position_mm'],'before_end_mm':oldobjects[u]['end_mm'],'before_reference_case':prior[u],'replacement_reference_cases':[x for x in replacement_refs if x['name'].startswith(oldobjects[u]['net']+' ') and x['layer']==next(iter(oldobjects[u]['layers']))]}for u in sorted(removed_tracks)]
assert all(x['replacement_reference_cases']for x in removed_reference_cases)
paths=[R/'reference-review-r98.json',R/'reference-review-r107.json',Path(__file__),kpath,R/'capture-r98/capture.json',R/'capture-r107/capture.json',R/'candidate-r107/routing.json',R/'native-r98/signal_main.kicad_pcb',R/'native-r107/signal_main.kicad_pcb',R/'native-r98/signal_main.kicad_dru',R/'native-r107/signal_main.kicad_dru']
report={'source_sha256':{str(p.relative_to(REPO)):sha(p)for p in paths},'exact_removed_original_copper':sorted(ids),'exact_removed_retained_reference_cases':removed_reference_cases,'all_other_authored_objects_unchanged':True,'all_r98_native_partitions_preserved_without_merges_or_splits':True,'all_477_footprints_unchanged':True,'mounts':checks,'new_trace_length_mm':sum(math.dist(x['position_mm'],x['end_mm'])for x in tracks),'opens':c['native_uncapped_opens'],'noise_qualified':False}
(R/'mount-audit-r107.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS exact five-object repair, all partitions, nine complete copper keepouts')
