"""Check one-via CONTROL13 restorations with the complete LED10 route retained."""
import copy,json,time
from pathlib import Path
from shapely.geometry import Point,box,LineString
from shapely.ops import unary_union,nearest_points
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_region_reachability import polygon_parts
from hardware.fabrication.digital_polygon_path import route
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
    net='/CONTROLS/CONTROL_13';frozen=PlannedRegionScreen(screen,net)
    start=(6.7,22.2);end=(10.7,22.3)
    free={f:frozen.outline.difference(unary_union([g.buffer(d+.0005,quad_segs=32) for n,g,d in frozen.geometry[f] if n!=net])) for f in ('F.Cu','B.Cu')}
    via_free=frozen.via_outline.difference(frozen.obstacles(net));results=[]
    for bounds in [(4,19,12,25),(2,16,15,28),(.61,10,20,32)]:
        parts=[next((p for p in polygon_parts(free[f].intersection(box(*bounds))) if p.covers(Point(pt))),None) for f,pt in [('F.Cu',start),('B.Cu',end)]]
        shared=parts[0].intersection(parts[1]).intersection(via_free) if all(p is not None for p in parts) else box(0,0,0,0)
        areas=polygon_parts(shared);candidates=[]
        for area in areas:
            safe=area.buffer(-.002)
            points=[area.representative_point()]
            if not safe.is_empty:points += [nearest_points(safe,Point(p))[0] for p in (start,end,(8.7,22.25))]
            for p in points:
                xy=(round(p.x,6),round(p.y,6))
                if not screen.via_legal(net,xy):continue
                paths=[route(frozen,net,f,a,b,region,time.monotonic()+12) for f,a,b,region in [('F.Cu',start,xy,parts[0]),('B.Cu',xy,end,parts[1])]]
                if all(paths):candidates.append(dict(via=xy,runs=list(zip(('F.Cu','B.Cu'),paths)),length_mm=sum(LineString(p).length for p in paths)))
        candidates.sort(key=lambda r:r['length_mm'])
        results.append(dict(bounds_mm=bounds,one_via_region_count=len(areas),one_via_area_mm2=shared.area,complete_proposals=candidates))
        print('Local box',bounds,'shared via regions',len(areas),'best mm',candidates[0]['length_mm'] if candidates else None,flush=True)
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_planned_region_screen.py','digital_region_reachability.py','digital_polygon_path.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-control13-local-via-survey-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},results=results,candidate_emitted=False,
        retained_complete_LED10=True,one_via_only=True,global_infeasibility_proven=False,native_rules_relaxed=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
