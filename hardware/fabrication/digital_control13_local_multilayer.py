"""Search local multilayer CONTROL13 restorations with complete LED10 retained."""
import copy,json,time
from pathlib import Path
from shapely.geometry import Point,box,LineString
from shapely.ops import unary_union,nearest_points
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_region_reachability import polygon_parts
from hardware.fabrication.digital_costed_region_route_v3 import route
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    cp=ROOT/'staging/digital-led09-shortened-inputs-29-02/capture.json'
    rp=ROOT/'staging/digital-led10-refined-02/construction.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in recipe['removed_uuids']]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(work,signal_layers=FACES)
    for r in recipe['routes']:
        if r['net']=='/LED/LED_10':add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    net='/CONTROLS/CONTROL_13';start=(6.7,22.2);end=(10.7,22.3);results=[]
    for bounds in [(4,19,12,25),(2,16,15,28),(.61,10,20,32)]:
        local=branch(screen)
        local.outline=local.outline.intersection(box(*bounds))
        local.via_outline=local.via_outline.intersection(box(*bounds))
        result=route(local,net,[('F.Cu',start)],[('B.Cu',end)],time.monotonic()+45,max_refinements=80)
        proposal=result['route']
        if proposal:
            assert all(screen.legal(net,f,p) for f,p in proposal['runs'])
            assert all(screen.via_legal(net,p) for p in proposal['vias'])
        results.append(dict(bounds_mm=bounds,search=result))
        print('Local box',bounds,'complete',bool(proposal),flush=True)
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_planned_region_screen.py','digital_region_reachability.py','digital_polygon_path.py','digital_costed_region_route.py','digital_costed_region_route_v2.py','digital_costed_region_route_v3.py','digital_screen_branch.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-control13-local-multilayer-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},results=results,candidate_emitted=False,
        retained_complete_LED10=True,one_via_only=False,global_infeasibility_proven=False,native_rules_relaxed=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
