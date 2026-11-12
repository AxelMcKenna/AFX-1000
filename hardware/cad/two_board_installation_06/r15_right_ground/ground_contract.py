"""Join verified left/right ground routes into one explicit electrical contract."""
from pathlib import Path
import json,hashlib,collections,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
leftpath=HERE.parent/'r14_left_ground/left-routes.json';rightpath=HERE/'right-routes.json'
l=json.loads(leftpath.read_text());r=json.loads(rightpath.read_text());cpath=HERE.parent/'r11_distribution/reference/panel-contract.json';c=json.loads(cpath.read_text())
expected={row['id'] for row in c['front_inputs'] if row['receiver_kind']=='B3F-1000 momentary'}
order=l['order']+r['order'];assert len(order)==29 and {row['button'] for row in order}==expected
edges=[{k:e[k] for k in ('id','from','to','wire')} for e in l['edges']+r['edges']]
assert len(edges)==32 and set(collections.Counter(p for e in edges for p in (e['from'],e['to'])).values())=={1}
graph=collections.defaultdict(set)
def link(a,b):graph[a].add(b);graph[b].add(a)
for e in edges:link(e['from'],e['to'])
for row in order:link('button_'+row['button']+':3','button_'+row['button']+':4')
for port in ('OUT_A','OUT_B'):link('GROUND_SCENE:IN','GROUND_SCENE:'+port)
roots=['D_J2002:15','D_J2002:16'];components={}
for root in roots:
 seen=set();todo=[root]
 while todo:
  p=todo.pop()
  if p in seen:continue
  seen.add(p);todo.extend(graph[p]-seen)
 assert set(roots)&seen=={root}
 components[root]=sorted(seen)
assert set(components[roots[0]])|set(components[roots[1]])==set(graph)
assert sum(map(len,graph.values()))//2==len(graph)-2 # two trees, no unintended cycles
netpath=HERE.parent/'r11_distribution/reference/signal-netlist.xml';nets={(n.get('ref'),n.get('pin')):net.get('name')for net in ET.parse(netpath).findall('./nets/net')for n in net.findall('node')}
assert all(nets[tuple(p.split(':'))]=='LINK_AGND' for p in roots)
files=[Path(__file__),leftpath,rightpath,cpath,netpath,HERE/'verification.json',HERE.parent/'r14_left_ground/verification.json',HERE.parent/'r10_interfaces/button-contact-contract.json']
out={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'net':'LINK_AGND','used_main_contacts':roots,'unused_ground_contacts':['D_J2001:15','D_J2001:16','D_J2003:1'],'unused_ground_contacts_note':'No external ground wire in these female cavities. Main PCB nets remain unchanged. D_J2003 signal contacts still require their unselected mating solution.','button_order_and_contact_directions':order,'external_wires':edges,'internal_button_pair':[3,4],'splice_internal_links':[['GROUND_SCENE:IN','GROUND_SCENE:OUT_A'],['GROUND_SCENE:IN','GROUND_SCENE:OUT_B']],'unused_button_contact':'button_hold:4','splice':r['splices'][0],'source_components':components,'wire_count':32,'splice_count':1,'button_count':29,'selector_commons':2,'fixed_while_plugged':['D_J2002:15','D_J2002:16'],'lid_mounted_receivers':'All button terminals and both selector wire pads','splice_mount':'Unimplemented; proposed lid-carried to avoid adding moving-boundary wires.','fixed_to_lid_wires':['L01','R01'],'opening_assumption':'No hinge or articulation is qualified. Existing lid is removable. Installed curves are not service slack; lift/tilt and connector-unplug sequence must be defined and verified.','supports_qualified':False,'opening_slack_qualified':False,'fabrication_released':False}
(HERE/'ground-contract.json').write_text(json.dumps(out,indent=2)+'\n');print('Full ground graph:2nativefeeds29buttons2selectorcommons32wires1splice;2trees verified')
