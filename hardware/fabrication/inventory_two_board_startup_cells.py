"""Record startup bypass/return state and reference obstacles from native copper."""
import argparse,json
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape


def run():
 ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
 assert all(all(ch.isalnum() or ch in '-_' for ch in n) for n in [args.capture,args.output])
 source=STAGING/args.capture/'capture.json';out=STAGING/args.output;assert not out.exists()
 c=json.loads(source.read_text())
 for n,h in c['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 def pad(ref,pin):return next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin)
 main=pad('P_C103','2')['group'];aux=pad('P_U102','1')['group']
 zone=next(z for z in c['zones'] if z['uuid']=='4b63f119-2e71-5d61-96f6-8b78a1f5c6cb');field=shape(zone['polygons']);outline=shape(zone['authored_outline'])
 cells=[]
 for i in range(18,29):
  ref=f'E_U{i}';cap=f'E_C{i+39 if i<=20 else i+45}'
  vp='3' if i==18 else '4' if i in [19,20] else '14';gp='12' if i==18 else '2' if i in [19,20] else '7'
  v,g,cp,cg=[pad(r,p) for r,p in [(ref,vp),(ref,gp),(cap,'1'),(cap,'2')]]
  assert v['net']==cp['net']=='PWR_V2V5_AUX' and g['net']==cg['net']=='PWR_AGND'
  point=Point(v['position_mm']);projection=point.buffer(.1)
  obstacles=[]
  for o in c['objects']:
   if o['net']=='PWR_AGND' or not o['layers'].get('In6.Cu'):continue
   distance=point.distance(shape(o['layers']['In6.Cu']))
   if distance<.6:obstacles.append(dict(uuid=o['uuid'],net=o['net'],kind=o['kind'],start=o['position_mm'],end=o.get('end_mm'),distance_mm=distance))
  cells.append(dict(chip=ref,bypass=cap,supply_pin=vp,ground_pin=gp,supply_pin_xy_mm=v['position_mm'],bypass_supply_xy_mm=cp['position_mm'],local_bypass_connected=v['group']==cp['group'],chip_ground_to_main=g['group']==main,bypass_ground_to_main=cg['group']==main,IC_supply_connected_to_aux_regulator=v['group']==aux,bypass_supply_connected_to_aux_regulator=cp['group']==aux,straight_pad_separation_mm=point.distance(Point(cp['position_mm'])),supply_pad_0p2mm_projection_unreferenced_mm2=projection.difference(field.buffer(.0015)).area,main_In6_outline_distance_at_supply_mm=point.distance(outline),nearby_inner_signal_copper=obstacles))
 d=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),source,REPO/'hardware/fabrication/route_nf_surface.py']},native_board_opens=c['native_uncapped_opens'],cells=cells,local_bypass_and_both_returns_complete=[x['chip'] for x in cells if x['local_bypass_connected'] and x['chip_ground_to_main'] and x['bypass_ground_to_main']],scope='Exact native connectivity plus geometric supply-pin reference diagnostics. This is not a complete startup netlist, current/thermal/noise assessment or functional verification.',startup_functionally_verified=False,fabrication_released=False)
 out.mkdir();(out/'inventory.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(opens=d['native_board_opens'],local_cells=d['local_bypass_and_both_returns_complete'],ICs_connected_to_aux_source=[x['chip'] for x in cells if x['IC_supply_connected_to_aux_regulator']])))


if __name__=='__main__':run()
