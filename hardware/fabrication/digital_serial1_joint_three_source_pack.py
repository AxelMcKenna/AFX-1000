"""Pack SERIAL_1, MCU_PERMIT and LED37 escapes with independent replay."""
import copy,json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_joint_escape_packing import pack
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-three-source-escape-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in recipe['removed_uuids']]
    result=pack(recipe['domains']);print('Joint three-source packs',len(result['choices']),'pair counts',result['pair_compatible_counts'],flush=True)
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    for choice in result['choices']:
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        for name,index in zip(result['names'],choice['indices']):
            d=recipe['domains'][name];add(screen,d['net'],d['options'][index])
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_joint_escape_packing.py','digital_serial1_joint_escape_survey.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parents[1]/'tests/tooling/test_digital_joint_escape_packing.py']
    out=ROOT/'staging/digital-serial1-joint-three-source-pack-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=recipe['removed_uuids'],packing=result,all_reported_packs_screen_replayed=True,global_restorations_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':run()
