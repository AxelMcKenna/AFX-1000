"""Emit source-bound workflow metadata; this does not change physical geometry."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent; REPO=R.parents[3]
source='hardware/cad/two_board_sensor_05/workflow_adapter/sensor.scad';sources={}
def bind(p):
 p=p.resolve();key=str(p.relative_to(REPO))
 if key in sources:return
 sources[key]=hashlib.sha256(p.read_bytes()).hexdigest()
 for rel in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/rel)
bind(REPO/source)
roles=[
 ('sensor_fixture','installed','sensor_mount','Carrier, magnet guard, cap and mounting/cap hardware','Printed receiving tolerances and actual fastener stack remain physical checks'),
 ('sensor_substrate','installed','pcb','20x18x1.6mm sensor board substrate','Selected sensor PCB source bound; fabrication/receiving remains open'),
 ('sensor_population','receiving','electronic_population','Actual selected component placement plus solder and local wire reservations','Mixed component/reserve envelope, not supplier-certified complete assembly CAD'),
 ('sensor_harness','receiving','harness','Current ribbon, main mate, clamp and replacement screw-head envelope','Conditional mating, cable forming, clamp strength and12pF branch ceiling require receiving'),
 ('sensor_lever_bracket','installed','lever_mount','Current fixed spring anchor/bracket','Printed strength and actual spring/clevis receiving remain open'),
 ('sensor_lever_guard','installed','lever_guard','Retained lever guard','Source preserved; physical tolerances remain open'),
 ('sensor_lever_motion','motion','lever','Continuous0..35degree lever sweep with0.5mm axial allowance','Motion reservation, not stationary hardware'),
 ('sensor_spring_motion','motion','spring','Fixed pin, moving pin sweep and attached spring corridor','Spring return force and physical hook retention require qualification')]
components=[dict(id=n,source=source,module=n,role=role,category=category,description=desc,uncertainty=uncertainty)for n,role,category,desc,uncertainty in roles]
contacts=[
 dict(components=['sensor_fixture','sensor_substrate'],reason='PCB edge-capture seating; retain strict non-seat clearance checks',evidence='hardware/cad/two_board_sensor_05/verified-r3/carrier_board_clearance/result.json',mode='seating_boundary_only'),
 dict(components=['sensor_population','sensor_substrate'],reason='Component/solder termination envelopes intentionally meet the PCB substrate',evidence='hardware/cad/two_board_sensor_05/population-contract.json',mode='electronic_attachment'),
 dict(components=['sensor_harness','sensor_population'],reason='Sensor-end wire fanout meets local wire/solder receiving region',evidence='hardware/cad/two_board_sensor_05/harness_mate_clearance/contract.json',mode='termination_region_only',region_mm={'min':[293,73.1,22.7],'max':[301.9,90.9,38.5]}),
 dict(components=['sensor_spring_motion','sensor_lever_motion'],reason='Moving spring pin is attached to lever; body-versus-lever clearance has a separate verified check',evidence='hardware/cad/two_board_sensor_05/spring-verified-r2/spring_body_lever_clearance/result.json',mode='attachment_only'),
 dict(components=['sensor_spring_motion','sensor_lever_bracket'],reason='Fixed pin attaches spring to bracket; this does not waive spring body interference',evidence='hardware/cad/two_board_sensor_05/spring-verified-r2/spring_body_lever_clearance/result.json',mode='attachment_only')]
meta=dict(schema_version=1,components=components,sources_sha256=sources,intentional_contacts=contacts,
 replacement_hardware=[dict(ref='D_H2',world_xy_mm=[250,57],remove='Original board screw head/washer at board seat',replacement='Included in sensor_harness: M2x25 head/washer seatZ23.35; clamp foot atZ8.35',source_module='mount_heads'),dict(ref='D_H5',world_xy_mm=[294,88],remove='Original board screw head/washer at board seat',replacement='Included in sensor_harness: M2x20 head/washer seatZ18.35; clamp foot atZ8.35',source_module='mount_heads')],
 assembly_rules=['Instantiate each atomic component once; do not also include carrier tbh05_installed or a second harness complete module.','Keep native main-board components except replace original D_H2/D_H5 screw heads; main mate intentionally occupies D_J1010 interface.','Do not substitute inherited generic sensor_package() for actual_population().','Motion and receiving roles are collision reservations; they are not all simultaneously printable physical solids.'],
 selected_pcb={'main_signal':'hardware/cad/two_board_sensor_05/signal_input/native-r7/signal_main.kicad_pcb','sensor':'hardware/cad/two_board_sensor_05/pcb/native-r3/sensor.kicad_pcb'},
 evidence=['hardware/cad/two_board_sensor_05/harness_mate_clearance/review.json','hardware/cad/two_board_sensor_05/signal_input/final-review.json'],
 complete_installed_fit=False,fabrication_released=False)
for key,path in meta['selected_pcb'].items():meta.setdefault('selected_pcb_sha256',{})[key]=hashlib.sha256((REPO/path).read_bytes()).hexdigest()
for c in contacts:assert (REPO/c['evidence']).is_file(),c['evidence']
(R/'components.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Bound',len(components),'atomic roles and',len(sources),'recursive SCAD sources')
if __name__=='__main__':pass
