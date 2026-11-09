"""Probe equivalent spare translator channels; emit no PCB or schematic.

Any viable proposal still requires paired schematic/PCB edits, an explicit
channel-equivalence audit, native checks and fresh ground witnesses.
"""
import copy,itertools,json,math,time
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import nearest_points
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.digital_xlat_escape_repair import route,add
from hardware.fabrication.digital_latch_supply_repack import with_routes
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent
SIGNAL='LED_XLAT';OUTPUT='/LED/LATCH_5V_SRC'
GROUND_SPURS={
 '7':'953a00b8-2576-5a84-9e01-a1f5e2c4b58e',
 '8':'7dd735fd-37ee-539b-aa93-1b1cfb1e67fe',
 '9':'1a123c19-9776-51ae-8e1c-5372fbed6123',
 '10':'0f8d7bd8-2460-5a09-b2ae-1516c558455c'}

GROUND_VIAS={'7':'07656cf2-c27d-5856-aadf-1922a2d93506','8':'c11d2a67-43da-56a1-80d8-94f948607503','9':'c4fd4f50-1511-52eb-bd96-3e92dd2c2edb','10':'38372be8-4406-5275-8087-438385836f40'}

def run():
 cp=ROOT/'staging/digital-control26-inputs-38/capture.json';cap=json.loads(cp.read_text())
 assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
 surface.SIGNAL_LAYERS=search.LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');surface.MARGIN=.01
 results=[];deadline=time.monotonic()+540
 for inp,outp in [('9','15'),('10','14'),('8','16'),('7','17')]:
  base=copy.deepcopy(cap);pads={o['pin']:o for o in base['objects'] if o.get('ref')=='U3005'}
  assert pads['5']['net']==SIGNAL and pads['19']['net']==OUTPUT and pads[inp]['net']=='AGND' and pads[outp]['net'].startswith('unconnected-')
  mapping={'5':'AGND','19':'unconnected-(U3005-B3-Pad19)',inp:SIGNAL,outp:OUTPUT}
  for pin,net in mapping.items():pads[pin]['net']=net
  via=next(o for o in base['objects'] if o['uuid']==GROUND_VIAS[inp]);assert via['net']=='AGND'
  attached=[o['uuid'] for o in base['objects'] if o['kind']=='PCB_TRACK' and o['net']=='AGND' and any(f in via['layers'] and shape(gs).distance(shape(via['layers'][f]))<1e-6 for f,gs in o['layers'].items())]
  assert attached==[GROUND_SPURS[inp]],attached
  removed=[o for o in base['objects'] if o['kind'] in ('PCB_TRACK','PCB_VIA') and
           (o['net']==OUTPUT or o['uuid'] in (GROUND_SPURS[inp],GROUND_VIAS[inp],'0a7fb763-319e-4f8e-a109-407396f2f0bf'))]
  ids={o['uuid'] for o in removed};base['objects']=[o for o in base['objects'] if o['uuid'] not in ids]
  signal_targets={('B.Cu',tuple(o['position_mm'])) for o in base['objects'] if o.get('ref') in ('R3021','R1010') and o['net']==SIGNAL}
  output_targets={('B.Cu',tuple(o['position_mm'])) for o in base['objects'] if o.get('ref')=='R3017' and o['net']==OUTPUT}
  assert len(signal_targets)==2 and len(output_targets)==1
  ground_start=pads['5']['position_mm'];ground_targets=set()
  for o in base['objects']:
   if o['net']!='AGND' or o['uuid']==pads['5']['uuid']:continue
   points=[o['position_mm']]
   if o['kind']=='PCB_TRACK':points += [o['end_mm'],tuple(nearest_points(Point(ground_start),LineString([o['position_mm'],o['end_mm']]))[1].coords)[0]]
   ground_targets.update((f,tuple(p)) for f in search.LAYERS if o['layers'].get(f) for p in points if math.dist(p,ground_start)<10)
  tasks={'ground':('AGND',pads['5'],ground_targets,.25,15),
         'output':(OUTPUT,pads[outp],output_targets,.2,20),
         'input':(SIGNAL,pads[inp],signal_targets,.2,90)}
  for order in [('ground','output','input'),('input','output','ground')]:
   if time.monotonic()>deadline:break
   routes=[];attempt=dict(input_pin=inp,output_pin=outp,proposed_pin_nets=mapping,removed_uuids=sorted(ids),order=order,tasks=[]);results.append(attempt)
   for task in order:
    net,pad,targets,width,maxlen=tasks[task]
    surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=width
    screen=DigitalViaScreen(with_routes(base,routes),signal_layers=search.LAYERS)
    r=route(screen,net,'F.Cu',pad['position_mm'],targets,min(deadline,time.monotonic()+50))
    length=sum(LineString(p).length for f,p in r['runs']) if r else None
    attempt['tasks'].append(dict(task=task,net=net,found=bool(r),planar_length_mm=length));print({k:attempt[k] for k in ('input_pin','output_pin','order','tasks')},flush=True)
    if r is None or length>maxlen:break
    rr=add(screen,net,r);rr['width_mm']=width;routes.append(rr)
   attempt['all_three_restored_in_geometric_proposal']=len(routes)==3
   if len(routes)==3:attempt['routes']=routes;break
  if time.monotonic()>deadline or any(r['all_three_restored_in_geometric_proposal'] for r in results):break
 out=ROOT/'staging/digital-buffer-channel-probe-02';out.mkdir(exist_ok=False)
 source=ROOT.parent/'cad/a12/thermal/power_budget_audit/sources/primary/SN74LVC8T245-RevD.pdf'
 paths=[cp,pcb,Path(__file__),source]+[ROOT/n for n in ('digital_xlat_escape_repair.py','digital_latch_supply_repack.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v4.py','digital_visibility_escape.py','digital_multilayer_escape_routes_v4.py','digital_native_spacing_search_v3.py','digital_native_spacing_search_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_pin_escape_routes.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
 result=dict(source_sha256={str(p):sha(p) for p in paths},datasheet_url='https://www.ti.com/lit/ds/symlink/sn74lvc8t245.pdf',datasheet_revision='SCES584D, May 2026',datasheet_pin_function_pages=[4,5],proposed_change='Move latch A3/B3 to an unused matched A/B channel; ground the freed A3 and leave freed B3 unused.',trials=results,PCB_or_schematic_emitted=False,native_channel_equivalence_and_ground_review_pending=True,physical_or_electrical_qualified=False,fabrication_released=False)
 (out/'probe.json').write_text(json.dumps(result,indent=2)+'\n');print('Probe completed; full geometric proposals',sum(r['all_three_restored_in_geometric_proposal'] for r in results),flush=True)
if __name__=='__main__':run()
