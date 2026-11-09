"""Find mutually compatible SERIAL_1 and restoration escapes before global routing."""
import copy,itertools,json,math,time
from pathlib import Path
from shapely.geometry import LineString,Point
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_continuous_escape_options_v5 import escape_options
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,PERMIT,CLOCK,LED
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def compatible(left,right):
    if any(math.dist(a,b)<=.801 for a in left['vias'] for b in right['vias']):return False
    if any(LineString(p).distance(LineString(q))<=.401 for f,p in left['runs'] for g,q in right['runs'] if f==g):return False
    if any(LineString(p).distance(Point(v))<=.601 for _,p in left['runs'] for v in right['vias']):return False
    if any(LineString(p).distance(Point(v))<=.601 for _,p in right['runs'] for v in left['vias']):return False
    return True

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';kp=ROOT/'staging/digital-serial1-target-cutset-02/diagnosis.json'
    cap,cut=[json.loads(p.read_text()) for p in (cp,kp)]
    for r in (cap,cut):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    removed=set(cut['base_removed_uuids'])|set(cut['selected_extra_uuids']);work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(work,signal_layers=FACES)
    sources=[('serial source',SERIAL,'F.Cu',(42.75,14.075)),('permit',PERMIT,'B.Cu',(41.5,16.9125)),('serial target',SERIAL,'F.Cu',(75.25,20.075)),('clock',CLOCK,'F.Cu',(75.25,19.425)),('led48',LED,'F.Cu',(74.15,20.725))]
    domains={}
    for name,net,face,point in sources:
        opts=escape_options(screen,net,{(face,point)},name,time.monotonic()+24,radius_mm=12.)
        domains[name]=dict(net=net,face=face,start=point,options=opts)
        print(name,len(opts),'screened escapes',flush=True)
    packs=[]
    for names in [('serial source','permit'),('serial target','clock','led48')]:
        choices=[]
        for indices in itertools.product(*(range(len(domains[n]['options'])) for n in names)):
            opts=[domains[n]['options'][i] for n,i in zip(names,indices)]
            if all(compatible(a,b) for a,b in itertools.combinations(opts,2)):
                choices.append(dict(indices=indices,cost=sum(o['cost'] for o in opts)))
        choices.sort(key=lambda r:r['cost'])
        # Replay every reported combination through the independent mutable screen.
        for choice in choices[:64]:
            check=CloseMarginViaScreen(work,signal_layers=FACES)
            for name,index in zip(names,choice['indices']):add(check,domains[name]['net'],domains[name]['options'][index])
        packs.append(dict(names=names,compatible_count=len(choices),screen_replayed_choices=choices[:64]))
        print(names,'compatible packs',len(choices),flush=True)
    paths=[cp,kp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_continuous_escape_options_v5.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_visibility_escape.py','digital_native_spacing_search_v2.py','nf_pin_escape_routes.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-joint-escape-survey-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),domains=domains,packs=packs,search_radius_mm=12.,global_restorations_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':run()
