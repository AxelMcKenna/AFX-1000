"""Exact two-stub/one-footprint delta, native partitions and cumulative physical pose capture."""
import hashlib,json,math,collections
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon,box
from shapely.ops import unary_union,polygonize
from shapely.affinity import rotate,translate
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def authored(path):
 t=read_sexpr(path.read_text());objects={}
 for row in t:
  if isinstance(row,list)and children(row,'uuid'):objects[first(row,'uuid')[1]]=sexpr([x for x in row if not(isinstance(x,list)and x and x[0]=='filled_polygon')])
 return t,objects
oldtree,old=authored(R/'native-r107/signal_main.kicad_pcb');newtree,new=authored(R/'native-r123/signal_main.kicad_pcb');r=read(R/'candidate-r123/routing.json');pose=r['declared_pose_change'];removed={x['uuid']for x in r['declared_removed']}
assert removed=={'718b29e7-1ba2-58be-8881-8126cfeebf60','f684c170-6e78-5642-9206-0e97f42c9885'};assert pose['uuid']=='8faa53e9-5e58-5636-a554-f778027070b5'
assert {u for u,v in old.items()if new.get(u)!=v}==removed|{pose['uuid']}
assert old[pose['uuid']]==pose['before_sexpr']and new[pose['uuid']]==pose['after_sexpr'];assert all(x['uuid']not in new and old[x['uuid']]==x['before_sexpr']for x in r['declared_removed'])
assert sha(R/'native-r107/signal_main.kicad_dru')==sha(R/'native-r123/signal_main.kicad_dru')
for tag in ['general','layers','setup']:assert [sexpr(x)for x in children(oldtree,tag)]==[sexpr(x)for x in children(newtree,tag)]
b=read(R/'capture-r107/capture.json');c=read(R/'capture-r123/capture.json');obj={x['uuid']:x for x in b['objects']};after={u:g for g,vs in c['all_groups'].items()for u in vs};merge=collections.defaultdict(list)
for gid,vs in b['all_groups'].items():
 targets={after[u]for u in vs if u not in removed};assert len(targets)==1,(gid,targets);merge[next(iter(targets))].append(gid)
assert len(merge)==len(c['all_groups']);joins=[{'after_group':k,'before_groups':v,'net':obj[b['all_groups'][v[0]][0]]['net']}for k,v in merge.items()if len(v)>1];assert len(joins)==1 and joins[0]['net']=='/A_ADC/PD_L'and len(joins[0]['before_groups'])==2
assert c['native_uncapped_opens']==c['independent_sum_of_pad_cluster_gaps']==166
before_objects={x['uuid']:x for x in b['objects']};added=[x for x in c['objects']if x['uuid']not in before_objects];assert collections.Counter(x['kind']for x in added)=={'PCB_TRACK':5,'PCB_VIA':1}
for route in r['routes']:
 for p,q in zip(route['path_mm'],route['path_mm'][1:]):assert sum(x['kind']=='PCB_TRACK'and x['net']==route['net']and list(x['layers'])==[route['layer']]and x['position_mm']==[round(v,6)for v in p] and x['end_mm']==[round(v,6)for v in q] and x['width_mm']==route['width_mm']for x in added)==1
native_pose=read(R/'pose-r122/review.json');pads=[x for x in c['objects']if x.get('ref')=='A_D101'];assert len(pads)==3
for p in native_pose['exact_pad_world_coordinates']:assert sum(x['pin']==p['number']and x['net']==p['net']and x['position_mm']==p['after_mm']and x['orientation_degrees']==p['orientation_degrees']for x in pads)==1

def footprints(tree):
 out={}
 for f in children(tree,'footprint'):
  props={x[1]:x[2]for x in children(f,'property')};at=list(map(float,first(f,'at')[1:]));out[props['Reference']]={'uuid':first(f,'uuid')[1],'reference':props['Reference'],'value':props['Value'],'footprint':f[1],'position_mm':at[:2],'orientation_degrees':at[2]if len(at)>2 else 0,'side':first(f,'layer')[1],'authored_sha256':hashlib.sha256(sexpr(f).encode()).hexdigest()}
 return out
initial=footprints(read_sexpr((R.parent/'signal_input/native-r7/signal_main.kicad_pcb').read_text()));prior=footprints(oldtree);current=footprints(newtree);assert len(current)==477 and set(initial)==set(prior)==set(current)
moves=[{'reference':ref,'before':initial[ref],'after':row}for ref,row in current.items()if any(row[k]!=initial[ref][k]for k in ['position_mm','orientation_degrees','side'])];assert {x['reference']for x in moves}=={'A_R303','A_R308','A_D101'}
assert [ref for ref in current if current[ref]!=prior[ref]]==['A_D101'];assert current['A_D101']['position_mm']==[75.8,65.2]and current['A_D101']['orientation_degrees']==90 and current['A_D101']['side']=='B.Cu'
def courtyard(tree):
 f=next(f for f in children(tree,'footprint')if any(p[1]=='Reference'and p[2]=='A_D101'for p in children(f,'property')));segments=[LineString([list(map(float,first(x,k)[1:]))for k in ['start','end']])for x in children(f,'fp_line')if first(x,'layer')[1]=='B.CrtYd'];g=unary_union(list(polygonize(unary_union(segments))));at=list(map(float,first(f,'at')[1:]));g=translate(rotate(g,-(at[2]if len(at)>2 else 0),origin=(0,0)),xoff=at[0],yoff=at[1]);return {'bounds_mm':list(g.bounds),'polygon':list(g.exterior.coords)}
paths=[Path(__file__),R/'native-r107/signal_main.kicad_pcb',R/'native-r123/signal_main.kicad_pcb',R/'native-r107/signal_main.kicad_dru',R/'native-r123/signal_main.kicad_dru',R/'candidate-r123/routing.json',R/'capture-r107/capture.json',R/'capture-r123/capture.json',R/'pose-r122/review.json',R.parent/'signal_input/native-r7/signal_main.kicad_pcb']
result={'source_sha256':{str(p.relative_to(REPO)):sha(p)for p in paths},'exact_original_stub_replacements':r['declared_removed'],'exact_pose_change':pose,'all_other_authored_objects_unchanged':True,'all_r107_hardware_keepouts_and_native_rules_unchanged':True,'all_native_partitions_preserved_except_one_PD_L_join':joins,'old_footprints_unchanged':476,'cumulative_moves_from_input_r7':moves,'all_post_change_physical_poses':list(current.values()),'D101_courtyard_before':courtyard(oldtree),'D101_courtyard_after':courtyard(newtree),'new_signal_length_mm':r['new_signal_length_mm'],'native_opens':166,'fresh_cumulative_CAD_capture_required':True,'noise_qualified':False,'fabrication_released':False}
(R/'replacement-audit-r123.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS exact two stubs / one pose / one PD_L join; captured477 physical poses; cumulative moves R303,R308,D101')
