import sys,json,hashlib,collections,copy
from pathlib import Path
from shapely.geometry import Polygon,GeometryCollection
from shapely import make_valid
from shapely.ops import unary_union
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
from hardware.electronics.common.netlists import netlist
R=Path('/private/tmp/afx-e28-p12-layerhop');screen=json.loads((R/'screen.json').read_text());S=Path(screen['source'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S/'rail_disconnect.kicad_pcb')==screen['source_pcb_sha256']
base=read_sexpr((R/'baseline-paired/rail_disconnect.kicad_pcb').read_text());trial=read_sexpr((R/'candidate-paired/rail_disconnect.kicad_pcb').read_text())
def uid(n):return str(first(n,'uuid')[1])
def strip_uuid(n):
 if isinstance(n,list):return [strip_uuid(c) for c in n if not(isinstance(c,list) and c and c[0]=='uuid')]
 return n
def objects(t,kind):
 return {(next(p[2] for p in children(n,'property') if p[1]=='Reference') if kind=='footprint' else hashlib.sha256(sexpr(strip_uuid(n)).encode()).hexdigest() if kind in ['gr_line','gr_arc'] else uid(n)):sexpr(strip_uuid(n) if kind in ['footprint','gr_line','gr_arc'] else n) for n in children(t,kind)}
obj={}
for kind in ['footprint','via','segment','gr_line','gr_arc']:
 b=objects(base,kind);c=objects(trial,kind)
 obj[kind]=dict(before=len(b),after=len(c),removed=[k for k in b if k not in c],added=[k for k in c if k not in b],changed=[k for k in b if k in c and b[k]!=c[k]])
 assert not obj[kind]['changed'],kind
assert obj['footprint']['removed']==obj['footprint']['added']==[]
assert not obj['via']['removed'] and len(obj['via']['added'])==1
assert set(obj['segment']['removed'])=={x['uuid'] for x in screen['blockers']}
assert len(obj['segment']['added'])==16
for k in ['setup','layers','general']:
 assert sexpr(first(base,k))==sexpr(first(trial,k)),k
for kind in ['gr_line','gr_arc']:assert not obj[kind]['removed'] and not obj[kind]['added']
def zonecontract(t):
 zs=[]
 for z in children(t,'zone'):
  z=copy.deepcopy(z);z[:]=[n for n in z if not(isinstance(n,list) and n and n[0] in ['filled_polygon','fill_segments'])];zs.append(sexpr(z))
 return zs
assert zonecontract(base)==zonecontract(trial)
for f in ['components.json','rail_disconnect.kicad_sch','rail_disconnect.kicad_pro']:
 assert (S/f).read_bytes()==(R/'candidate-paired'/f).read_bytes(),f

def shapes(t):
 result=collections.defaultdict(list);invalid=0
 for z in children(t,'zone'):
  name=str(first(z,'net_name')[1]) if children(z,'net_name') else str(first(z,'net')[1]) if children(z,'net') else ''
  if not name:continue
  for fp in children(z,'filled_polygon'):
   xy=[tuple(map(float,p[1:3])) for p in first(fp,'pts')[1:]]
   if len(xy)<3:continue
   p=Polygon(xy)
   if not p.is_valid:invalid+=1;p=make_valid(p)
   result[name,str(first(fp,'layer')[1])].append(p)
 return {k:unary_union(v) for k,v in result.items()},invalid
b,bi=shapes(base);c,ci=shapes(trial);areas=[]
for net,layer in sorted(set(b)|set(c)):
 p=b.get((net,layer),GeometryCollection());q=c.get((net,layer),GeometryCollection());removed=p.difference(q);added=q.difference(p)
 if removed.area+added.area>1e-7:areas.append(dict(net=net,layer=layer,before_area_mm2=p.area,after_area_mm2=q.area,withdrawn_area_mm2=removed.area,added_area_mm2=added.area))

def counts(p):
 d=json.loads(p.read_text());return dict(hard=sum(x['severity']=='error' for x in d['violations']),warnings=sum(x['severity']=='warning' for x in d['violations']),opens=len(d['unconnected_items']),parity=len(d['schematic_parity']),ignored_checks=d['ignored_checks'])
bn=counts(R/'baseline-drc.json');cn=counts(R/'candidate-drc.json');assert bn['hard']==cn['hard']==cn['parity']==0 and not cn['ignored_checks']
parts,pins=netlist(R/'candidate-netlist.xml');components=json.loads((R/'candidate-paired/components.json').read_text());mismatch=[]
for x in components:
 ref=x['ref']
 if parts[ref].findtext('value')!=x['part']:mismatch.append([ref,'value'])
 for p in x['pins']:
  num=str(p['number']);want=p['net'];actual=pins.get(ref,{}).get(num)
  if p.get('kind')=='no_connect' or want in ['UNASSIGNED_NC','NC']:continue
  if want is None and actual and actual.startswith('unconnected-'):continue
  if actual!=want:mismatch.append([ref,num,want,actual])
assert not mismatch,mismatch
native=json.loads((R/'native-connectivity.json').read_text());assert native['uncapped_unconnected_count']==31
for n in ['P12_OV_OK','E28_MASTER_ENABLE','P19_OV_OK_SCHMITT']:assert native['targets'][n]['all_actual_pads_connected']
assert not native['targets']['V5_REG_OV_OK_SCHMITT']['all_actual_pads_connected']
segments=objects(trial,'segment');vias=objects(trial,'via')
report=dict(status='PARTIAL_RECEIVER_REPAIR_SOURCE_SPECIFIC_NOT_FULL_ROUTING',source_pcb_sha256=screen['source_pcb_sha256'],candidate_pcb_sha256=sha(R/'candidate-paired/rail_disconnect.kicad_pcb'),baseline_refilled_sha256=sha(R/'baseline-paired/rail_disconnect.kicad_pcb'),before_native=bn,after_native=cn,uncapped_opens=native['uncapped_unconnected_count'],object_preservation=obj,
 removed_source_segments=screen['blockers'],added_segments=[dict(uuid=u,source_object=segments[u]) for u in obj['segment']['added']],added_vias=[dict(uuid=u,source_object=vias[u]) for u in obj['via']['added']],
 original_physical_FP_semantics_ignoring_regenerated_UUIDs_all_vias_all_remaining_tracks_setup_layers_outline_zone_contracts_exact=True,original_schematic_components_project_bytes_exact=True,
 native_component_count=len(parts),native_pin_value_mismatches=mismatch,native_ERC_violations=0,ERC_ignored_checks=json.loads((R/'candidate-erc.json').read_text())['ignored_checks'],
 native_actual_pad_connectivity=native['targets'],P12_MASTER_P19_source_pad_components_closed=True,V5_buffered_debt_remains=True,
 actual_saved_fill_delta=areas,polygon_repairs_before_after=[bi,ci],saved_fill_delta_not_resistance_or_noise_bound=True,
 receiving_via_process='Geometry .6/.3 only; resin filling/capping/flatness are receiving requirements, not manufacturing proof.',
 source_specific_merge_requires_fresh_native_and_fill_PDN=True,full_routing_closed=False,physical_qualified=False,adoption=False)
assert all(not x['violations'] for x in json.loads((R/'candidate-erc.json').read_text())['sheets'])
(R/'final-delta-proof.json').write_text(json.dumps(report,indent=2)+'\n')
print('baseline',bn,'candidate',cn,'parts',len(parts),'segments removed/added',len(obj['segment']['removed']),len(obj['segment']['added']))
for a in areas:print(a['net'],a['layer'],'withdrawn',a['withdrawn_area_mm2'],'added',a['added_area_mm2'])
