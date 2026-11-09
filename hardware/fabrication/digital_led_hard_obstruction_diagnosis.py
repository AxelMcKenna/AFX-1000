"""Identify copper-only blockers while retaining all pads, holes and keepouts.

Diagnostic paths are deliberately not routed candidates. Every removed blocker
would need complete reconnection and native review before any adoption.
"""
import copy,json,math,time
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v4 import escape_options
import hardware.fabrication.route_nf_surface as surface
ROOT=Path(__file__).resolve().parent
ENDPOINTS=[('U3001',str(n)) for n in (15,22,23,24,25,26,27,28)]+[('U3002',str(n)) for n in (7,27,28)]
def run():
 cp=ROOT/'staging/digital-pot-filter-inputs-40/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 surface.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 soft=copy.deepcopy(cap);soft['objects']=[o for o in cap['objects'] if o['kind']=='PAD'];screen=DigitalViaScreen(soft,signal_layers=surface.SIGNAL_LAYERS)
 rows=[(o,{f:shape(ps) for f,ps in o['layers'].items() if ps}) for o in cap['objects'] if o['kind'] in ('PCB_TRACK','PCB_VIA')]
 results=[]
 for ref,pin in ENDPOINTS:
  pad=next(o for o in cap['objects'] if o.get('ref')==ref and o.get('pin')==pin);face=next(iter(pad['layers']));net=pad['net']
  options=escape_options(screen,net,{(face,tuple(pad['position_mm']))},ref+'.'+pin,time.monotonic()+8);ranked=[]
  for option in options:
   blockers=[]
   for o,gs in rows:
    hit=o['net']!=net and (any(LineString(path).distance(gs[f])<.3105 for f,path in option['runs'] if f in gs) or any(Point(p).distance(g)<.513 for p in option['vias'] for g in gs.values()))
    # Even a same-net drill can conflict with a proposed new hole.
    if o['kind']=='PCB_VIA' and any(math.dist(p,o['position_mm'])<.563 for p in option['vias']):hit=True
    if hit:blockers.append(dict(uuid=o['uuid'],net=o['net'],kind=o['kind'],position_mm=o['position_mm'],end_mm=o.get('end_mm'),layers=list(gs)))
   ranked.append(dict(runs=option['runs'],via_points=option['vias'],planar_length_mm=sum(LineString(p).length for _,p in option['runs']),blockers=blockers,blocker_nets=sorted({o['net'] for o in blockers})))
  ranked.sort(key=lambda r:(len(r['blocker_nets']),len(r['blockers']),r['planar_length_mm']))
  result=dict(ref=ref,pin=pin,net=net,side=face,options=ranked[:8]);results.append(result)
  print(ref,pin,'options',len(options),'best blocker nets',ranked[0]['blocker_nets'] if ranked else None,'objects',len(ranked[0]['blockers']) if ranked else None,flush=True)
 out=ROOT/'staging/digital-led-hard-obstruction-diagnosis-01';out.mkdir(exist_ok=False)
 paths=[cp,Path(__file__),ROOT/'digital_continuous_escape_options_v4.py',ROOT/'digital_via_spacing_v2.py',ROOT/'route_nf_surface.py',ROOT/'digital_visibility_escape.py',ROOT/'digital_native_spacing_search_v2.py',ROOT/'nf_pin_escape_routes.py',ROOT/'nf_softstart_joint_screen.py',ROOT/'nf_softstart_cell_routes.py',ROOT/'nf_minimum_logic.py']
 r=dict(source_sha256={str(p):sha(p) for p in paths},retained_all_pad_holes_and_keepouts=True,diagnostic_ignored_existing_tracks_and_vias=True,not_a_routed_candidate=True,results=results,physical_or_electrical_qualified=False,fabrication_released=False)
 (out/'diagnosis.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':run()
