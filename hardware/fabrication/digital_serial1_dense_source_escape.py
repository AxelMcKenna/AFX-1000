"""Sample the source-side SERIAL_1 and MCU_PERMIT escapes with LED37 intact.

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
from hardware.fabrication.digital_serial1_joint_escape_survey import compatible
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,CLOCK,LED,PERMIT
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-joint-escape-survey-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in recipe['removed_uuids']]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(work,signal_layers=FACES);domains={}
    xx,yy=np.meshgrid(np.arange(40.,47.0001,.05),np.arange(12.,23.0001,.05))
    native_options={'permit':dict(point=[44.018,14.693041],runs=[('B.Cu',[[41.5,16.9125],[44.018,14.693041]])],vias=[[44.018,14.693041]])}
    for name in ('serial source','permit'):
        source=recipe['domains'][name];net=source['net'];face=source['face'];start=source['start']
        obstacles=[g.buffer(d+.0005,quad_segs=32) for n,g,d in screen.geometry[face] if n!=net]
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
    # Preserve every successful option. Pair compatibility is evaluated by the
    # subsequent full restoration search, not by a sparse nearest sample.
    assert '4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1' not in recipe['removed_uuids']
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_joint_escape_survey.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-dense-source-escape-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=recipe['removed_uuids'],domains=domains,original_led37_via_retained=True,grid_step_mm=.05,grid_bounds_mm=[40,12,47,23],global_restorations_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Source escape domains captured with original LED37 via retained',flush=True)
if __name__=='__main__':run()
