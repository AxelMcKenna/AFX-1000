"""Check radius contract, curve sampling, feed nets and escape separation."""
from pathlib import Path
import json,math,hashlib,importlib.util,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
helper=HERE.parent/'r12_ground/verify.py'
spec=importlib.util.spec_from_file_location('ground_distance',helper);distance=importlib.util.module_from_spec(spec);spec.loader.exec_module(distance)
c=json.loads((HERE/'exit-contract.json').read_text());R=c['selected_centerline_radius_mm'];wire_r=c['modeled_wire_radius_mm']
assert R-wire_r>=c['supplier_radius_at_max_OD_mm']
# Conservative inscribed-sphere facet error in each angular direction, then
# the exact arc-to-chord sagitta. This bounds the ideal supplier-OD wire sweep.
represented_radius=wire_r*math.cos(math.pi/24)**2-c['maximum_chord_sagitta_mm']
assert represented_radius>c['supplier_max_wire_OD_mm']/2
paths=[]
for root,angle in c['selected_exit_azimuth_degrees'].items():
 p=c['root_start_mm'][root];az=math.radians(angle)
 paths.append([[p[0]+R*(1-math.cos(math.radians(t)))*math.cos(az),p[1]+R*(1-math.cos(math.radians(t)))*math.sin(az),p[2]+R*math.sin(math.radians(t))]for t in range(0,91,3)])
minimum=min(distance.distance(a,b,d,e)for a,b in zip(paths[0],paths[0][1:])for d,e in zip(paths[1],paths[1][1:]))
assert minimum>2*wire_r
netpath=HERE.parent/'r11_distribution/reference/signal-netlist.xml'
nets={(p.get('ref'),p.get('pin')):net.get('name')for net in ET.parse(netpath).findall('./nets/net')for p in net.findall('node')}
assert all(nets[tuple(root.split(':'))]=='LINK_AGND' for root in c['selected_exit_azimuth_degrees'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in c['source_sha256'].items():assert sha(REPO/p)==h
results={}
for part in ('structure','allocations'):
 p=HERE/'native'/(part+'-selected-final')/'result.json';v=json.loads(p.read_text())
 assert v['empty'] and not v['runtime_failure']
 assert all(sha(REPO/k)==h for k,h in v['source_sha256'].items())
 results[part]=str(p.relative_to(REPO))
files=[Path(__file__),helper,HERE/'exits.scad',HERE/'exit-contract.json',netpath]+[REPO/p for p in results.values()]
out={'source_sha256':{str(p.relative_to(REPO)):sha(p)for p in files},'selected_source_nets':'Both D_J2002 feeds independently verified LINK_AGND in native netlist','centerline_radius_mm':R,'inside_radius_mm':R-wire_r,'supplier_required_radius_mm':c['supplier_radius_at_max_OD_mm'],'conservative_represented_wire_radius_mm':represented_radius,'supplier_max_wire_radius_mm':c['supplier_max_wire_OD_mm']/2,'minimum_centerline_separation_mm':minimum,'minimum_modeled_surface_gap_mm':minimum-2*wire_r,'endpoints_mm':[p[-1]for p in paths],'local_native_clearance':results,'complete_routes':False,'full_assembly_verified':False,'fabrication_released':False}
(HERE/'verification.json').write_text(json.dumps(out,indent=2)+'\n')
print('Selected radius12 pair: local clearance and separation pass; full routes pending')
