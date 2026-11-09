"""Replay the eight-layer evidence chain from 71 to 56 to 52 opens."""
import json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_digital_eight_layer import check as layer_check
from hardware.fabrication.audit_digital_eight_comparison import check as comparison_check
from hardware.fabrication.audit_digital_eight_routes import check as route_check
from hardware.fabrication.audit_digital_eight_led import check as led_check
from hardware.electronics.common.sexpr import children,read_sexpr
ROOT=Path(__file__).resolve().parent
LABEL='digital-eight-led-clean-native-01'

def check():
    base=ROOT/'staging/digital-eight-routed-native-01';final=ROOT/'staging'/LABEL
    paths=[Path(__file__)]
    checks=[(base/'eight-layer-comparison.json',comparison_check(base.name)),
            (base/'additive-route-review.json',route_check('digital-eight-layer-native-01',base.name,'digital-eight-layer-routes-01')),
            (base/'corridor-audit.json',layer_check(base.name,'digital-eight-routed-inputs-56')),
            (final/'additive-route-review.json',led_check(base.name,final.name,'digital-eight-led-clean-01')),
            (final/'corridor-audit.json',layer_check(final.name,'digital-eight-led-clean-inputs-52'))]
    for path,result in checks:
        assert result==json.loads(path.read_text()),path
        paths.append(path)
    for name in ['visual-review.json','conditional-assembly-review.json','stage-connectivity-review.json']:
        path=final/name;record=json.loads(path.read_text())
        assert all(sha(Path(p))==h for p,h in record['source_sha256'].items())
        paths.append(path)
    visual=json.loads((final/'visual-review.json').read_text())
    assert visual['native_PDF_rendered_and_visually_inspected'] and len(visual['reviewed_layers'])==8
    old,new=[json.loads((p/'stage-connectivity-review.json').read_text()) for p in (base,final)]
    before,after=[{r['net']:r for r in c['nets']} for c in (old,new)]
    assert before['LED_SCK']==after['LED_SCK']
    assert new['uncapped_open_connections']==52 and new['open_nets']==51
    led=[r['net'] for r in new['nets'] if r['net'].startswith('/LED/LED_') and not r['all_pads_connected']]
    assert len(led)==35
    pcb=final/'digital_core.kicad_pcb';board=read_sexpr(pcb.read_text());paths.append(pcb)
    assert len(children(board,'segment'))==2530 and len(children(board,'via'))==461
    return dict(source_sha256={str(p):sha(p) for p in paths},independent_receipts_replay_exact=True,
                retained_six_layer_opens=71,first_eight_layer_opens=56,final_opens=52,final_open_nets=51,
                remaining_LED_output_nets=led,clock_unchanged_since_shortened_two_via_route=True,
                clock_planar_mm=after['LED_SCK']['planar_copper_length_mm'],clock_vias=2,
                tracks=2530,vias=461,eight_copper_plots_visually_reviewed=True,
                selected_DC04_unchanged=True,physical_stack_and_process_accepted=False,
                complete_unit_qualified=False,fabrication_released=False)
if __name__=='__main__':
    result=check()
    with (ROOT/'staging'/LABEL/'checkpoint-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Evidence chain replayed: 71 -> 56 -> 52 opens; zero native geometry/parity/ERC; all earlier pad groups retained')
