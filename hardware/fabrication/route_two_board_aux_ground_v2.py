"""Add separate AUX surface returns, feedback ground copper and thermal stitching."""
import json
import shutil
import uuid
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-aux-local-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2447-aux-local/capture.json'
OUT=STAGING/'two-board-power-aux-ground-02'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    new=cap['objects']
    geometries=[(o,l,routing.shape(ps)) for o in new for l,ps in o['layers'].items() if ps]
    trees={l:([(o,g) for o,k,g in geometries if k==l],STRtree([g for o,k,g in geometries if k==l])) for l in cap['copper_layers']}
    outline=routing.shape(cap['outline']).buffer(-.5)
    mounts=[(o['position_mm'],max(3.6,max(o['drill_mm'])/2+.5)) for o in new if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    codes={str(n[2]):int(n[1]) for n in children(board,'net')};routes=[];added=[];vias=[]
    def pad(ref,pin):return next(o for o in new if o.get('ref')==ref and o.get('pin')==pin)
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPAUXGROUND02:'+sha(CAP)+':'+label))
    def legal(net,layer,points,width):
        line=LineString(points)
        # Existing planes are on inner layers. Surface tracks do not change
        # their fill; an inner route must clear any foreign authored zone.
        if any(z['layer']==layer and z['net']!=net and line.distance(routing.shape(z['authored_outline']))<width/2+.21 for z in cap['zones']):return False
        if not outline.buffer(-width/2-.01).covers(line):return False
        rows,tree=trees[layer]
        for i in tree.query(line.buffer(width/2+.211)):
            o,g=rows[int(i)]
            if o['net']!=net and line.distance(g)<width/2+.21-1e-7:return False
        if any(n!=net and l==layer and line.distance(g)<width/2+w/2+.21-1e-7 for n,l,w,g in added):return False
        if any(line.distance(Point(p))<r+width/2+.01 for p,r in mounts):return False
        return True
    def connect(label,net,layer,start,end,width,limit,forced=None):
        candidates=[forced] if forced else routing.candidate_paths(start,end)
        good=[]
        for points in candidates:
            points=[p for i,p in enumerate(points) if not i or list(p)!=list(points[i-1])]
            if len(points)<2:continue
            length=LineString(points).length
            if length<=limit and legal(net,layer,points,width):good.append((length,points))
        assert good,(label,'no bounded route')
        length,points=min(good,key=lambda v:v[0]);ids=[]
        for i,(p,q) in enumerate(zip(points,points[1:])):
            u=uid(label+':'+str(i));ids.append(u)
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),u]])
        added.append((net,layer,width,LineString(points)))
        routes.append(dict(label=label,net=net,layer=layer,width_mm=width,path_mm=points,length_mm=length,maximum_length_mm=limit,segment_uuids=ids))
        print(label,round(length,3),'mm',flush=True)
    def via(net,xy,label):
        # Via radius plus fill clearance is .5mm; .61mm keeps every existing
        # plane unchanged. A fresh native refill independently verifies this.
        assert all(Point(xy).distance(routing.shape(z['authored_outline']))>.61 for z in cap['zones'])
        routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2;screen=ViaScreen(dict(cap,zones=[]))
        screen.vias=[(v['net'],v['position_mm']) for v in vias]
        assert screen.via_legal(net,xy),(label,xy,'via')
        assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21 for n,l,w,g in added)
        u=uid(label);board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        vias.append(dict(uuid=u,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for l in cap['copper_layers']:added.append((net,l,.6,Point(xy)))
    gnd=pad('P_U102','4')['net']
    for label,xy in [('left-outer',[188.4,130.8]),('left-inner',[189.1,130.8]),
                     ('right-inner',[192.4,129.2]),('right-outer',[193.2,129.2])]:
        via(gnd,xy,'thermal-'+label)
    connect('EP-left-front',gnd,'F.Cu',pad('P_U102','9')['position_mm'],[189.1,130.8],.6,2)
    connect('left-thermal-bus',gnd,'F.Cu',[189.1,130.8],[188.4,130.8],.6,1)
    connect('EP-right-front',gnd,'F.Cu',pad('P_U102','9')['position_mm'],[192.4,129.2],.6,2.5)
    connect('right-thermal-bus',gnd,'F.Cu',[192.4,129.2],[193.2,129.2],.6,1)
    changed='c10eec5d-cf1f-58da-8d6d-48ce5d70e70d'
    node=next(z for z in children(board,'zone') if str(first(z,'uuid')[1])==changed)
    assert first(node,'layer')[1]=='In1.Cu'
    old_u20_ring=[[169.3,115],[187,115],[187,143],[182.2,143],[182.2,138.5],
        [174.6,138.5],[174.6,147],[172,147],[172,138.5],[169.3,138.5]]
    assert [list(map(float,p[1:3])) for p in children(first(first(node,'polygon'),'pts'),'xy')]==old_u20_ring
    u20_ring=[[169.3,115],[187,115],[187,134.3],[186.4,134.3],[186.4,136.9],
        [187,136.9],[187,143],[182.2,143],[182.2,138.5],
        [174.6,138.5],[174.6,147],[172,147],[172,138.5],[169.3,138.5]]
    first(first(node,'polygon'),'pts')[:]=[a('pts'),*[[a('xy'),*p] for p in u20_ring]]
    node[:]=[v for v in node if not(isinstance(v,list) and v and v[0]=='filled_polygon')]
    removed=Polygon(old_u20_ring).difference(Polygon(u20_ring))
    assert abs(removed.area-1.56)<1e-8
    assert all(not removed.buffer(.3).intersects(routing.shape(o['layers']['In1.Cu']))
        for o in new if o['layers'].get('In1.Cu'))
    definitions=[
        ('AUX-input-return','F.Cu',[
            [186.8,122.2],[193.15,122.2],[193.15,130.8],[191.8,130.8],
            [191.8,132],[191.2,132],[191.2,131.1],[188,131.1],
            [188,133.6],[186,133.6],[186,132.4],[187.7,132.4],
            [187.7,126],[186.8,126]]),
        ('AUX-output-return','F.Cu',[
            [191.15,132.4],[193.1,132.4],[193.1,134.6],[196.95,138.2],
            [197.2,138.2],[197.2,139.6],[195.7,139.6],[195.7,138.8],
            [192.8,136.05],[192.8,136.95],[191.15,136.95]]),
        ('AUX-feedback-guard','B.Cu',[
            [186.5,128.3],[194.8,128.3],[194.8,133.2],[191.6,133.2],
            [191.6,136.6],[187.3,136.6],[187.3,131.2],[186.5,131.2]]),
        ('AUX-thermal-reference','In1.Cu',[
            [187.7,128.3],[194.8,128.3],[194.8,133.2],[191.6,133.2],
            [191.6,136.6],[186.7,136.6],[186.7,134.6],[187.7,134.6]])]
    zones=[]
    for label,layer,ring in definitions:
        ident=uid(label);g=Polygon(ring)
        assert g.is_valid and outline.covers(g),label
        assert all(g.distance(Point(p))>=r+.3 for p,r in mounts),label
        assert all(z['layer']!=layer or g.distance(Polygon(u20_ring) if z['uuid']==changed else routing.shape(z['authored_outline']))>.299 for z in cap['zones']),label
        board.append([a('zone'),[a('net'),codes[gnd]],[a('net_name'),gnd],[a('layer'),layer],[a('uuid'),ident],
            [a('hatch'),a('edge'),.5],[a('connect_pads'),a('yes'),[a('clearance'),.2]],
            [a('min_thickness'),.25],[a('filled_areas_thickness'),a('no')],
            [a('fill'),a('yes'),[a('thermal_gap'),.25],[a('thermal_bridge_width'),.5],[a('island_removal_mode'),0]],
            [a('polygon'),[a('pts'),*[[a('xy'),*p] for p in ring]]]])
        zones.append(dict(uuid=ident,label=label,net=gnd,layer=layer,outline_mm=ring,
                          clearance_mm=.2,minimum_thickness_mm=.25,solid_pad_connections=True))
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP25';p.write_text(sexpr(root)+'\n')
    inputs=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'aux-local-audit.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_power_layer_detours.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        moves=[],routes=routes,vias=vias,zones=zones,
        changed_U20_ground_zone_uuid=changed,old_U20_ground_outline_mm=old_u20_ring,
        new_U20_ground_outline_mm=u20_ring,U20_authored_recess_area_mm2=removed.area,
        added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        existing_tracks_vias_pads_and_components_unchanged=True,three_old_zones_unchanged=True,schematic_pin_net_map_unchanged=True,
        native_plane_fill_pending=True,whole_board_planes_complete=False,
        manufacturer_layout_source='https://www.ti.com/lit/ds/symlink/tps7a16.pdf',
        manufacturer_layout_sections='10.1 through 10.4, SBVS171F',
        input_output_ground_join_target='U102 GND pin 4; exposed pad connected by existing local trace',
        thermal_via_process='0.60mm copper / 0.30mm drill outside all SMD lands; no via-in-pad',
        actual_thermal_resistance_and_load_margin_qualified=False,
        native_validation_pending=True,fabrication_released=False)
    (OUT/'aux-ground-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(tracks=result['added_segments'],vias=len(vias),new_zones=len(zones))))

if __name__=='__main__':run()
