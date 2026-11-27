"""Check independent left-chain ownership, radius bounds and wire separation."""
from pathlib import Path
import json,math,hashlib,importlib.util,xml.etree.ElementTree as ET
from collections import Counter
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
helper=HERE.parent/'r12_ground/verify.py';spec=importlib.util.spec_from_file_location('distance',helper);distance=importlib.util.module_from_spec(spec);spec.loader.exec_module(distance)
g=json.loads((HERE/'left-routes.json').read_text());contract=json.loads((HERE.parent/'r11_distribution/reference/panel-contract.json').read_text())
expected={r['id'] for r in contract['front_inputs'] if r['receiver_kind']=='B3F-1000 momentary' and not r['id'].startswith('scene_')}
assert len(expected)==19 and {r['button'] for r in g['order']}==expected
assert len(g['edges'])==19 and g['root']=='D_J2002:15'
counts=Counter(p for e in g['edges'] for p in (e['from'],e['to']));assert set(counts.values())=={1}
datums=json.loads((HERE.parent/'r12_ground/ground-routes.json').read_text())['endpoints_mm']
for edge in g['edges']:
 assert np.linalg.norm(np.array(edge['points_mm'][0])-datums[edge['from']])<1e-7
 assert np.linalg.norm(np.array(edge['points_mm'][-1])-datums[edge['to']])<1e-7
up=g['root']
for row,e in zip(g['order'],g['edges']):
 assert row['incoming_terminal'] in ('3','4')
 assert row['outgoing_terminal'] in (None,str(7-int(row['incoming_terminal'])))
 assert e['from']==up and e['to']=='button_'+row['button']+':'+row['incoming_terminal']
 up='button_'+row['button']+':'+str(row['outgoing_terminal'])
assert up=='button_hold:None' and g['unused_last_terminal']=='button_hold:4'
netpath=HERE.parent/'r11_distribution/reference/signal-netlist.xml';nets={(p.get('ref'),p.get('pin')):net.get('name') for net in ET.parse(netpath).findall('./nets/net')for p in net.findall('node')};assert nets[('D_J2002','15')]=='LINK_AGND'
minimum=999;collisions=[];minimum_sample_radius=999;curvature=[]
for i,a in enumerate(g['edges']):
 points=np.array(a['points_mm']);cursor=0;arcs=[]
 for primitive in a['primitives']:
  if primitive['kind']=='line':cursor+=1
  elif primitive['kind']=='arc':
   end=cursor+math.ceil(primitive['angle_degrees']/3);arcs.append((cursor,end,primitive['radius_mm']));cursor=end
   assert primitive['radius_mm']>=12
  elif primitive['kind']=='smooth_height_overlay':
   first,last=primitive['first_point'],primitive['last_point']
   included=[r for start,end,r in arcs if first<=start and end<=last]
   assert included
   R=min(included);L=primitive['planar_sample_length_mm'];dz=abs(primitive['delta_mm'])
   z1=1.875*dz/L;z2=(10/math.sqrt(3))*dz/(L*L)
   bound=1/math.sqrt((1+z1*z1)/(R*R)+z2*z2)
   assert bound>=12
   curvature.append({'wire':a['id'],'height_overlay_radius_lower_bound_mm':bound})
  else:raise AssertionError('Unknown curve type')
 assert cursor==len(points)-1
 for aa,bb,cc in zip(points,points[1:],points[2:]):
  u,v=bb-aa,cc-bb;cross=float(np.linalg.norm(np.cross(u,v)))
  if cross>1e-10:minimum_sample_radius=min(minimum_sample_radius,float(np.linalg.norm(u)*np.linalg.norm(v)*np.linalg.norm(cc-aa)/(2*cross)))
 for b in g['edges'][i+1:]:
  gap=min(distance.distance(aa,ab,ba,bb)for aa,ab in zip(a['points_mm'],a['points_mm'][1:])for ba,bb in zip(b['points_mm'],b['points_mm'][1:]))
  minimum=min(minimum,gap)
  if gap<1.2-1e-8:collisions.append({'wires':[a['id'],b['id']],'distance_mm':gap})
assert minimum_sample_radius>=12-1e-7
assert not collisions,collisions
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(REPO/p)==h for p,h in g['source_sha256'].items())
out={'source_sha256':{str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),helper,HERE/'left-routes.json',HERE/'left.scad',netpath]},'left_chain_endpoints_verified':19,'source_native_net':'LINK_AGND','all_contacts_one_wire':True,'minimum_sampled_centerline_radius_mm':minimum_sample_radius,'height_overlay_radius_bounds':curvature,'minimum_centerline_separation_mm':minimum,'minimum_modeled_surface_gap_mm':minimum-1.2,'wire_collisions':collisions,'receiving_curve_geometry_pass':True,'complete_harness':False,'support_retention_qualified':False,'service_slack_included':False,'fabrication_released':False}
(HERE/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('source_sha256','height_overlay_radius_bounds')}))
