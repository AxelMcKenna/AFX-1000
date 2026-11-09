"""Distinguish local escape access from global connectivity in SERIAL_1 repair."""
import copy
import json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_point_access import reachability
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,PERMIT,CLOCK,LED
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json'
    rp=ROOT/'staging/digital-serial1-joint-repair-01/diagnosis.json'
    dp=ROOT/'staging/digital-interface-hard-obstructions-32-01/diagnosis.json'
    cap,recipe,diag=[json.loads(p.read_text()) for p in (cp,rp,dp)]
    for r in (cap,recipe,diag):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in recipe['removed_uuids']]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    tasks=[('serial source',SERIAL,'F.Cu',(42.75,14.075)),('serial target',SERIAL,'F.Cu',(75.25,20.075)),('permit branch',PERMIT,'B.Cu',(41.5,16.9125)),('clock',CLOCK,'F.Cu',(75.25,19.425)),('led48',LED,'F.Cu',(74.15,20.725))]
    results=[]
    for fixed in (False,True):
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        if fixed:
            for r in diag['results']:
                if (r['ref'],r['pin']) in [('U3002','29'),('U3003','4')]:
                    e=r['options'][0];add(screen,SERIAL,dict(runs=e['runs'],vias=e['via_points']))
        for name,net,face,point in tasks:
            crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
            crossings += [(p,list(FACES)) for n,p in screen.new_vias if n==net]
            r=reachability(PlannedRegionScreen(screen,net),net,[(face,point)],[(face,point)],FACES,existing_crossings=crossings,probes=[(f,(110.,55.)) for f in FACES])
            r.update(task=name,fixed_serial_escapes=fixed,net=net)
            results.append(r)
            print(name,'fixed',fixed,'global probes',[p['connected_to_sources'] for p in r['probe_results']],'reachable components',len(r['visited_components']),flush=True)
    paths=[cp,rp,dp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_point_access.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_planned_region_screen.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-region-diagnosis-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},results=results,candidate_emitted=False,diagnostic_removed_copper_not_adopted=True,fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':run()
