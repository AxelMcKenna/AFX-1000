"""Move the clock series resistor off the TLC output exit, restoring its supply crossing."""
import copy,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
from shapely.affinity import translate
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.nf_multilayer_raster_directed as search
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent

def polygons(g):
    return [dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]

def run():
    cp=ROOT/'staging/digital-interface-clean-inputs-75/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text());original=copy.deepcopy(board)
    fp=next(f for f in children(board,'footprint') if any(p[1:3]==['Reference','R3016'] for p in children(f,'property')))
    assert list(map(float,first(fp,'at')[1:3]))==[75,21] and first(fp,'layer')[1]=='B.Cu'
    first(fp,'at')[1:3]=[69,23]
    removed_ids={'8c356d48-a8c2-5b4e-9490-333d5fd326d4','413b2d93-f3c0-4d2f-bd71-d759a5143351'}
    removed=[n for n in children(board,'segment') if first(n,'uuid')[1] in removed_ids];assert len(removed)==2
    for n in removed:board.remove(n)
    c['objects']=[o for o in c['objects'] if o['uuid'] not in removed_ids]
    for o in c['objects']:
        if o.get('ref')=='R3016':
            o['position_mm']=[o['position_mm'][0]-6,o['position_mm'][1]+2]
            o['layers']={l:polygons(translate(surface.shape(ps),-6,2)) for l,ps in o['layers'].items() if ps}
    records=[]
    def append(net,runs,vias,width):
        for layer,path in runs:
            for p,q in zip(path,path[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:clock-repack:{sha(cp)}:{net}:{layer}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
                c['objects'].append(dict(uuid=uid,net=net,kind='PCB_TRACK',position_mm=list(p),end_mm=list(q),width_mm=width,layers={layer:polygons(LineString([p,q]).buffer(width/2,quad_segs=32))}))
        for p in vias:
            from shapely.geometry import Point
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:clock-repack-via:{sha(cp)}:{net}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
            c['objects'].append(dict(uuid=uid,net=net,kind='PCB_VIA',position_mm=list(p),drill_mm=[.3,.3],layers={l:polygons(Point(p).buffer(.3,quad_segs=32)) for l in c['copper_layers']}))
        records.append(dict(net=net,runs=runs,vias=vias,width_mm=width))
    surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;search.LAYERS=('F.Cu','In3.Cu','B.Cu')
    for pin,net in [('1','/LED/CLOCK_5V_SRC'),('2','/LED/CLOCK_5V')]:
        s=ExistingViaScreen(c,signal_layers=search.LAYERS)
        pad=next(o for o in c['objects'] if o.get('ref')=='R3016' and o['pin']==pin)
        start=pad['position_mm'];targets=[o for o in c['objects'] if o['net']==net and o.get('ref')!='R3016']
        def portal(layer,p):return dict(point=p,layers=[layer],runs=[],vias=[],cost=0.,group='clock')
        ends={l:[portal(l,p) for o in targets if o['layers'].get(l) for p in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else [])] for l in search.LAYERS}
        found=search.route_multi(s,net,[portal('B.Cu',start)],ends,time.monotonic()+30,max_visits=500000)
        assert found,('No legal clock reconnection',net)
        fresh=[p for p in found['vias'] if not any(n==net and math.dist(p,q)<1e-7 for n,q in s.vias)]
        assert all(s.legal(net,l,p) for l,p in found['runs']) and all(s.via_legal(net,p) for p in fresh)
        append(net,found['runs'],fresh,.2);print('Connected',net,flush=True)
    surface.WIDTH=layers.WIDTH=.3
    s=ExistingViaScreen(c,signal_layers=('F.Cu','In3.Cu','B.Cu'))
    p,q=(70.4,25.2),(67.4,21.)
    choices=[v for v in surface.candidate_paths(p,q) if s.legal('V3V3_IO','B.Cu',v)]
    path=min(choices,key=lambda v:LineString(v).length) if choices else s.grid_path('V3V3_IO','B.Cu',p,q,budget=80000)
    assert path,'No legal restoration for the 0.30 mm supply branch'
    assert s.legal('V3V3_IO','B.Cu',path);append('V3V3_IO',[('B.Cu',path)],[],.3)
    print('Restored 3.3 V branch',LineString(path).length,flush=True)
    out=ROOT/'staging/digital-clock-series-repack-01';out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(board)+'\n')
    delta=geometry_delta(original,board);assert delta['other_root_geometry_exact'] and not delta['zone']['changed'] and not delta['zone']['added'] and not delta['zone']['removed']
    inputs=[source,cp,Path(__file__)]+[ROOT/n for n in ['nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','nf_minimum_logic.py','route_nf_surface.py','nf_pin_escape_routes.py','nf_multilayer_raster_directed.py']]
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),component_moves=[dict(ref='R3016',before_mm=[75,21],after_mm=[69,23])],removed_objects=removed,routes=records,geometry_delta=delta,native_checks_pending=True,physical_qualification=False,fabrication_released=False),indent=2)+'\n')
    print('Clock resistor repack emitted for native verification',flush=True)

if __name__=='__main__':run()
