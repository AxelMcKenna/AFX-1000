import json,hashlib
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union,nearest_points
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[4]);args=ap.parse_args()
root=args.repo;p=root/'hardware/fabrication/staging/two-board-power-routing-inputs-aux-ground-reuse-01/capture.json';x=json.loads(p.read_text());objs=x['objects'];pads={(o.get('ref'),o.get('pin')):o for o in objs if o['kind']=='PAD'}
sg=pads['P_U102','1']['group'];gg=pads['P_C103','2']['group']
def shape(o,l):return unary_union([Polygon(q['outer'],q['holes']) for q in o['layers'][l]])
def short(o):return {k:v for k,v in o.items() if k!='layers'}
r=[]
for ref,pin in [('E_U19','4'),('E_C58','1'),('E_U35','8'),('E_C78','1'),('E_C78','2')]:
 target=pads[ref,pin];main=gg if target['net']=='PWR_AGND' else sg;near=[]
 for o in objs:
  if o['group']!=main or o['net']!=target['net']:continue
  for l in set(target['layers'])&set(o['layers']):
   a,b=shape(target,l),shape(o,l);pa,pb=nearest_points(a,b)
   near.append(dict(object=short(o),layer=l,gap_mm=a.distance(b),target_edge_mm=list(pa.coords[0]),candidate_edge_mm=list(pb.coords[0])))
 near.sort(key=lambda a:a['gap_mm'])
 r.append(dict(target=short(target),already_main_connected=target['group']==main,nearest_same_surface=near[:5]))
out=Path(__file__).with_name('startup-route-targets.json');out.write_text(json.dumps({'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'capture_source':str(p.relative_to(root)),'capture_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_group':sg,'ground_group':gg,'targets':r,'required_ground_contacts':[short(pads[k]) for k in [('E_U19','2'),('E_C58','2'),('E_U35','4'),('E_C78','2')]],'scope':'Nearest same-surface native object copper candidates only; filledzones excluded; obstacle/DRC/route access and return impedance not established'},indent=2)+'\n')
for a in r:
 print(a['target']['ref'],a['target']['pin'],[(n['object'].get('ref',n['object']['uuid']),n['object'].get('pin'),round(n['gap_mm'],3),n['candidate_edge_mm']) for n in a['nearest_same_surface'][:3]])
