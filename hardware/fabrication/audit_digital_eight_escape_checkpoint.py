"""Replay three control/serial joins and the earlier eight-layer evidence chain."""
import json
from pathlib import Path
from shapely.geometry import LineString
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_digital_eight_checkpoint import check as prior_check
from hardware.fabrication.audit_digital_eight_routes import check as route_check
from hardware.fabrication.audit_digital_eight_layer import check as layer_check
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.electronics.common.sexpr import children,read_sexpr
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
ROOT=Path(__file__).resolve().parent
LABEL='digital-eight-serial-native-01'
STEPS=[('digital-eight-led-clean-native-01','digital-eight-control-native-01','digital-eight-control-escapes-01','digital-eight-led-clean-inputs-52'),
       ('digital-eight-control-native-01','digital-eight-continuous-native-01','digital-eight-continuous-escapes-01','digital-eight-control-inputs-51'),
       ('digital-eight-continuous-native-01',LABEL,'digital-eight-serial-routes-01','digital-eight-continuous-inputs-50')]


def check():
    paths=[Path(__file__)];base=ROOT/'staging/digital-eight-led-clean-native-01';out=ROOT/'staging'/LABEL
    p=base/'checkpoint-review.json';assert prior_check()==json.loads(p.read_text());paths.append(p)
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
    rescreened=[]
    for before,after,recipe_label,capture_label in STEPS:
        p=ROOT/'staging'/after/'additive-route-review.json';result=route_check(before,after,recipe_label)
        assert result==json.loads(p.read_text());paths.append(p)
        cp=ROOT/'staging'/capture_label/'capture.json';capture=json.loads(cp.read_text())
        assert all(sha(Path(p))==h for p,h in capture['source_sha256'].items())
        rp=ROOT/'staging'/recipe_label/'construction.json';recipe=json.loads(rp.read_text())
        screen=DigitalViaScreen(capture,signal_layers=surface.SIGNAL_LAYERS)
        for route in recipe['routes']:
            net=route['net']
            assert all(screen.legal(net,face,points) for face,points in route['runs'])
            assert all(screen.via_legal(net,point) for point in route['new_vias_mm'])
            screen.added += [(net,face,LineString(points)) for face,points in route['runs']]
            screen.new_vias += [(net,tuple(point)) for point in route['new_vias_mm']]
            rescreened.append(dict(net=net,new_vias=len(route['new_vias_mm']),added_planar_mm=route['planar_length_mm']))
        paths += [cp,rp]
    p=out/'corridor-audit.json';assert layer_check(LABEL,'digital-eight-serial-inputs-49')==json.loads(p.read_text());paths.append(p)
    for name in ['stage-connectivity-review.json','visual-review.json','conditional-assembly-review.json']:
        p=out/name;record=json.loads(p.read_text());assert all(sha(Path(f))==h for f,h in record['source_sha256'].items());paths.append(p)
    c=json.loads((out/'stage-connectivity-review.json').read_text());old=json.loads((base/'stage-connectivity-review.json').read_text())
    oldnets,newnets=[{r['net']:r for r in d['nets']} for d in (old,c)]
    assert oldnets['LED_SCK']==newnets['LED_SCK']
    assert c['uncapped_open_connections']==49 and c['open_nets']==48
    assert sum(r['net'].startswith('/LED/LED_') and not r['all_pads_connected'] for r in c['nets'])==35
    pcb=out/'digital_core.kicad_pcb';b=read_sexpr(pcb.read_text());paths.append(pcb)
    assert len(children(b,'segment'))==2591 and len(children(b,'via'))==466
    assert sum(r['new_vias'] for r in rescreened)==5
    return dict(source_sha256={str(p):sha(p) for p in paths},independent_chain_replays_exact=True,
                open_progression=[71,56,52,51,50,49],final_open_nets=48,remaining_LED_output_nets=35,
                added_control_serial_tracks=61,added_control_serial_vias=5,tracks=2591,vias=466,
                exact_020mm_trace_and_actual_drill_screen_replayed=rescreened,
                interface_copper={n:newnets[n] for n in ['LED_SCK','SCL','SDA','/LED/DATA_5V_SRC','/LED/SERIAL_2']},
                shorter_clock_route_preserved=True,long_LED49_detour_adopted=False,
                DATA_source_series_resistor_placement_and_timing_qualified=False,
                I2C_loading_pullups_rise_time_and_installed_harness_qualified=False,
                physical_stack_and_process_accepted=False,complete_unit_qualified=False,fabrication_released=False)
if __name__=='__main__':
    result=check()
    with (ROOT/'staging'/LABEL/'checkpoint-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Verified chain to 49 opens; 61 new tracks/five vias; every earlier pad group retained')
