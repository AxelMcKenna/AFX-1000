"""Resample receiving escapes after the native R3015 quarter-millimetre translation.

Sparse nearest/centroid samples miss legal original via positions. This bounded
grid retains independent copper, drill and pairwise route clearance screens.
"""
import copy,itertools,json,math,time
from pathlib import Path
import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_serial1_joint_escape_survey import compatible
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,CLOCK,LED
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-serial1-source-preparation-inputs-31-02/capture.json';rp=ROOT/'staging/digital-serial1-data-placement-first-02/diagnosis.json'
    cap,placement=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,placement):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    proposal=placement['placement_and_local_escapes'];assert proposal
    recipe=dict(removed_uuids=placement['removed_uuids'],domains=proposal['domains'])
    removed=set(recipe['removed_uuids']);work=copy.deepcopy(cap)
    work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed and o.get('ref')!='R3015']+copy.deepcopy(proposal['pose']['pads'])
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(work,signal_layers=FACES);domains={}
    for r in proposal['routes']:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    xx,yy=np.meshgrid(np.arange(70.,78.0001,.025),np.arange(16.,24.0001,.025))
    native_options={'clock':dict(point=[72.6,19.8],runs=[('F.Cu',[[75.25,19.425],[73.3,19.4],[72.6,19.8]])],vias=[[72.6,19.8]]),'led48':dict(point=[73.5,20.075],runs=[('F.Cu',[[74.15,20.725],[73.5,20.075]])],vias=[[73.5,20.075]])}
    for name in ('serial target','clock','led48'):
        source=recipe['domains'][name];net=source['net'];face=source['face'];start=source['start']
        frozen=PlannedRegionScreen(screen,net)
        obstacles=[g.buffer(d+.0005,quad_segs=32) for n,g,d in frozen.geometry[face] if n!=net]
        free=screen.outline.difference(unary_union(obstacles));via_free=screen.via_outline.difference(screen.obstacles(net))
        mask=contains_xy(free,xx,yy)&contains_xy(via_free,xx,yy)
        points=[(round(x,6),round(y,6)) for x,y in zip(xx[mask],yy[mask])]
        options=copy.deepcopy(source['options']);tested=0
        if name in native_options:
            option=native_options[name]
            if screen.via_legal(net,option['point']) and all(screen.legal(net,f,p) for f,p in option['runs']):
                option['cost']=sum(LineString(p).length for f,p in option['runs'])+2.5;options.append(option)
        for point in sorted(points,key=lambda p:math.dist(start,p)):
            if not screen.via_legal(net,point):continue
            tested+=1
            choices=[p for p in surface.candidate_paths(start,point) if screen.legal(net,face,p)]
            if not choices:continue
            path=min(choices,key=lambda p:LineString(p).length)
            options.append(dict(point=point,runs=[(face,path)],vias=[point],cost=LineString(path).length+2.5))
        # Keep every successful grid point, including longer escape candidates.
        domains[name]=dict(net=net,face=face,start=start,via_grid_points_tested=tested,options=options)
        print(name,'tested',tested,'screened routes',len(options),flush=True)
    # Keep the complete dense domains; solve their joint packing separately.
    for name,domain in domains.items():
        for option in domain['options']:
            assert all(screen.legal(domain['net'],face,path) for face,path in option['runs'])
            assert all(screen.via_legal(domain['net'],point) for point in option['vias'])
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_planned_region_screen.py','digital_serial1_joint_repair.py','digital_serial1_joint_escape_survey.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-shifted-target-escape-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=recipe['removed_uuids'],domains=domains,source_preparation_preserved=True,component_pose=proposal['pose'],data_routes=proposal['routes'],grid_step_mm=.025,grid_bounds_mm=[70,16,78,24],global_restorations_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Receiving escapes resampled after R3015 translation',flush=True)
if __name__=='__main__':run()
