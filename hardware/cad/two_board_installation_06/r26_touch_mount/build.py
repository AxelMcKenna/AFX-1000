"""Conditional sourced touch fasteners and native host ownership; no frozen-source changes."""
import argparse, hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(pcb,netlist,host='D_J1009'):
 # Ownership is independent of bus-net equality: J10 belongs to AS5600.
 assert host=='D_J1009','Touch ownership must be D_J1009, not a net-identical bus header'
 spec=R/'hardware/electronics/processor_carrier/components.json'; comps=json.loads(spec.read_text())
 if isinstance(comps,dict):comps=comps['components']
 owner=next(x for x in comps if x['ref']=='J9');assert 'Trill Craft bus' in owner['note']
 tree=read_sexpr(pcb.read_text());fps={next(x[2] for x in children(f,'property') if x[1]=='Reference'):f for f in children(tree,'footprint')}
 f=fps[host];expected={'1':'LINK_AGND','2':'LINK_V3V3_IO','3':'LINK_SCL','4':'LINK_SDA'}
 actual={p[1]:first(p,'net')[-1] for p in children(f,'pad')};assert actual==expected
 xml=ET.parse(netlist).getroot();native={n.attrib['pin']:net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node') if n.attrib['ref']==host};assert native==expected
 capture=json.loads((R/'hardware/cad/two_board_print_01/capture.json').read_text())
 c3=json.loads((H.parent/'r25_touch_module/contract.json').read_text());c3pads={p['pin']:p for p in c3['communication_pads']};mapping={'1':'3','2':'4','3':'6','4':'5'}
 assert {k:c3pads[v]['net'] for k,v in mapping.items()}=={'1':'GND','2':'VCC','3':'/I2C_SCL','4':'/I2C_SDA'}
 wires=[dict(host=host,pin=p[1],net=actual[p[1]],native_xy_mm=transform(f,first(p,'at')[1:3]),trill_pin=mapping[p[1]],trill_xy_mm=c3pads[mapping[p[1]]]['world_xy_mm']) for p in children(f,'pad')]
 files=[pcb,netlist,spec,H.parent/'r25_touch_module/contract.json',R/'hardware/cad/two_board_print_01/housing.scad',Path(__file__)]+list((H/'sources').glob('*.pdf'))
 # PCB source may be parent integration's newer capture: bind repo-relative identity.
 def relative(p):
  try:return str(p.relative_to(R))
  except ValueError:return str(p)[str(p).index('hardware/'):]
 c=dict(source_sha256={relative(p):sha(p) for p in files},host=host,host_ownership=owner['note'],wires=wires,trill_unused_pins=['1 XRES','2 EVENT'],host_mate_selected=False,host_row_spacing_mm=4,host_d_j1010_reserved_for_AS5600=True,parts={'screw':'Accu SSC-M2-20-A2','nut':'Accu HPN-M2-A2','washer':'Accu HPW-M2-A2-BL'},supplier_mm=dict(screw_length_nominal=20,screw_head_diameter=[3.62,3.8],screw_head_height=[1.86,2],nut_AF=[3.82,4],nut_height=[1.35,1.6],washer_OD=[4.7,5],washer_ID=[2.2,2.34],washer_thickness=[.25,.35]),standard_derived_length_mm=[19.58,20.42],standard_basis='Unbrako primary Engineering Guide printed pages48/49: DIN912 lengthjs15,18..30mm±0.42; confirm delivered parts conform',receiving_requirements_mm=dict(post_seat_z=[19.9,20.1],board_thickness=[1.5,1.7],board_bore=[3.1,3.3],pocket_ceiling=[4.7,4.9],pocket_AF=[4.15,4.25],post_OD=[7.1,7.3],through_bore=[2.35,2.45],post_bore_registration_max=.1,washer_registration_max=.2,incomplete_screw_tip_max=.4),limits=['Printed/board/registration/incomplete-tip limits are project acceptance requirements, not manufacturer guarantees','Supplier nominal thread and sourced dimensional stack do not prove torque, strength, creep, retention, thread class, insulation, vibration or underside tool access','Washer finish not credited as electrical insulation; C3 mount pads are unconnected, metal washer to nearby copper still needs inspection','Host mate remains unselected; preserve D_J1010 sensor mating and four mm row separation'],physical_qualified=False,fabrication_released=False)
 c['stack_mm']=dict(tip_min=19.9+1.5+.25-20.42,tip_max=20.1+1.7+.35-19.58,nut_bottom_min=4.7-1.6,end_protrusion_min=4.7-1.6-(20.1+1.7+.35-19.58),full_thread_beyond_nut_min=4.7-1.6-(20.1+1.7+.35-19.58)-.4,head_top_max=20.1+1.7+.35+2,washer_receiving_diameter=5+2*.2,old_pocket_min_end_protrusion=1.7-1.6-(20.1+1.7+.35-19.58))
 assert c['stack_mm']['full_thread_beyond_nut_min']>.12 and c['stack_mm']['tip_min']>1.2
 (H/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--pcb',type=Path,required=True);a.add_argument('--netlist',type=Path,required=True);a.add_argument('--host',default='D_J1009');x=a.parse_args();build(x.pcb.resolve(),x.netlist.resolve(),x.host)
