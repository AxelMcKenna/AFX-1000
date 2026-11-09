"""Locate the spatial extent and copper classes enclosing SERIAL_1.

Power/ground omissions in this diagnostic never authorize their deletion.
"""
import copy,json
from pathlib import Path
from shapely.geometry import box
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-joint-repair-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    base=set(recipe['removed_uuids']);surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    results=[]
    for bounds,omit_power in [((70,17,77,23),True),((65,10,83,29),False),((65,10,83,29),True),((0,0,114,60),False)]:
        region=box(*bounds);removed=base.copy()
        for o in cap['objects']:
            if o['kind'] not in ('PCB_TRACK','PCB_VIA') or o['net']==SERIAL:continue
            if not omit_power and o['net'] in ('AGND','5V_DIG','3V3_DIG'):continue
            if any(surface.shape(ps).intersects(region) for ps in o['layers'].values()):removed.add(o['uuid'])
        work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        r=reachability(screen,SERIAL,[('F.Cu',(75.25,20.075))],[('F.Cu',(42.75,14.075))],FACES)
        results.append(dict(bounds_mm=bounds,omitted_power_ground=omit_power,removed_uuids=sorted(removed),region_report=r))
        print(bounds,'power omitted',omit_power,'objects',len(removed),'connected',r['connected'],'components',len(r['visited_components']),flush=True)
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_reachability.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-obstruction-extent-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},results=results,diagnostic_only=True,restoration_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':run()
