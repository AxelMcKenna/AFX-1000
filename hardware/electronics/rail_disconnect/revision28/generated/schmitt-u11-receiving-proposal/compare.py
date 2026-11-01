import sys,json,hashlib,collections
from pathlib import Path
from shapely.geometry import Polygon,GeometryCollection
from shapely import make_valid
from shapely.ops import unary_union
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
ROOT=Path('/private/tmp/afx-u11-independent')
base=read_sexpr((ROOT/'baseline/rail_disconnect.kicad_pcb').read_text());trial=read_sexpr((ROOT/'candidate0/rail_disconnect.kicad_pcb').read_text())

def uid(n):return str(first(n,'uuid')[1])
def objects(t,kind):return {uid(n):sexpr(n) for n in children(t,kind)}
proof={}
def clean(n):
 if isinstance(n,list):return [clean(c) for c in n if not(isinstance(c,list) and c and c[0]=='uuid')]
 return n
def fps(t):return {next(p[2] for p in children(n,'property') if p[1]=='Reference'):sexpr(clean(n)) for n in children(t,'footprint')}
bf=fps(base);cf=fps(trial)
fp_semantic_changes=[k for k in bf if k not in cf or bf[k]!=cf[k]]
for kind in ['footprint','via','segment']:
 b=objects(base,kind);c=objects(trial,kind)
 proof[kind]=dict(before=len(b),after=len(c),removed=[k for k in b if k not in c],added=[k for k in c if k not in b],changed=[k for k in b if k in c and b[k]!=c[k]])

def shapes(t):
 result=collections.defaultdict(list);invalid=0
 for z in children(t,'zone'):
  net=str(first(z,'net_name')[1]) if children(z,'net_name') else str(first(z,'net')[1]) if children(z,'net') else ''
  if not net:continue
  for fp in children(z,'filled_polygon'):
   layer=str(first(fp,'layer')[1]);xy=[tuple(map(float,p[1:3])) for p in first(fp,'pts')[1:]]
   if len(xy)<3:continue
   p=Polygon(xy)
   if not p.is_valid:invalid+=1;p=make_valid(p)
   result[net,layer].append(p)
 return {k:unary_union(v) for k,v in result.items()},invalid
b,bi=shapes(base);c,ci=shapes(trial);rows=[]
for net,layer in sorted(set(b)|set(c)):
 p=b.get((net,layer),GeometryCollection());q=c.get((net,layer),GeometryCollection())
 removed=p.difference(q);added=q.difference(p)
 if removed.area+added.area>1e-7:rows.append(dict(net=net,layer=layer,before_area_mm2=p.area,after_area_mm2=q.area,withdrawn_area_mm2=removed.area,added_area_mm2=added.area))
baseD=json.loads((ROOT/'baseline-drc.json').read_text());newD=json.loads((ROOT/'candidate0-drc.json').read_text())
def counts(d):return dict(hard=sum(v['severity']=='error' for v in d['violations']),warnings=sum(v['severity']=='warning' for v in d['violations']),opens=len(d['unconnected_items']),schematic_parity=len(d['schematic_parity']),ignored=d['ignored_checks'])
report=dict(source_pcb_sha256=json.loads((ROOT/'screen.json').read_text())['source_pcb_sha256'],
 baseline_refilled_sha256=hashlib.sha256((ROOT/'baseline/rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),candidate_refilled_sha256=hashlib.sha256((ROOT/'candidate0/rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),
 before_native=counts(baseD),after_native=counts(newD),original_object_UUID_comparison=proof,
 actual_filled_polygon_delta=rows,polygon_repairs_before_after=[bi,ci],
 polygon_delta_is_diagnostic_not_conduction_bound=True,
 actual_pour_void_changes_are_NOT_zero=True,force_resistance_or_current_acceptance=False,
 candidate_complete_routing=False,old_vias_or_FP_modified=False)
(ROOT/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['original_object_UUID_comparison','actual_filled_polygon_delta']},indent=2))
for row in rows:print(row['net'],row['layer'],'withdrawn',row['withdrawn_area_mm2'],'added',row['added_area_mm2'])
assert not fp_semantic_changes and set(bf)==set(cf)
assert not proof['via']['changed'] and not proof['via']['removed'] and len(proof['via']['added'])==1
assert not proof['segment']['changed'] and len(proof['segment']['removed'])==30
