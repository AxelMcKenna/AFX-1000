"""Recess U23's force plane so the quiet return enters near BP5."""
import json
import shutil
import uuid
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE = STAGING / 'two-board-power-u20-input-native-01'
CAP = STAGING / 'two-board-power-routing-inputs-2462-u20-input/capture.json'
OUT = STAGING / 'two-board-power-u23-quiet-01'
RING = [[289,109],[303.2,109],[303.2,134.5],[298.6,134.5],
        [298.6,129.2],[292.2,129.2],[292.2,132.5],[293.8,132.5],
        [293.8,134.5],[289,134.5]]


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text())
    for n,h in cap['source_sha256'].items():assert sha(Path(n)) == h,n
    board = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    zone = next(z for z in cap['zones'] if z['layer']=='In1.Cu' and routing.shape(z['authored_outline']).contains(Point(295,127)))
    assert zone['net']=='PWR_AGND' and len(cap['zones'])==4
    node = next(z for z in children(board,'zone') if first(z,'uuid')[1]==zone['uuid'])
    old_ring = [list(map(float,p[1:3])) for p in children(first(first(node,'polygon'),'pts'),'xy')]
    assert old_ring==[[289,109],[303.2,109],[303.2,134.5],[289,134.5]]
    ring = Polygon(RING)
    assert ring.is_valid and Polygon(old_ring).covers(ring)
    first(first(node,'polygon'),'pts')[:] = [a('pts'),*[[a('xy'),*p] for p in RING]]
    removed_fill = len(children(node,'filled_polygon'));assert removed_fill==1
    node[:] = [n for n in node if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    points = [[299.25,132.2],[300.05,132.2]]
    net = zone['net']; width=.4
    line = LineString(points)
    # Existing foreign zones are remote; only the selected same-net zone is
    # changed. This justifies screening ordinary copper without filled zones.
    for z in cap['zones']:
        if z['uuid']!=zone['uuid']:
            assert line.distance(routing.shape(z['authored_outline']))>2
    routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=width
    screen=ViaScreen(dict(cap,zones=[]))
    assert screen.via_legal(net,points[1])
    assert screen.legal(net,'F.Cu',points)
    def ident(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:U23QUIET01:'+sha(CAP)+':'+label))
    code = next(int(n[1]) for n in children(board,'net') if n[2]==net)
    vu,tu=ident('quiet-via'),ident('quiet-bus')
    board.append([a('via'),[a('at'),*points[1]],[a('size'),.6],[a('drill'),.3],
                  [a('layers'),'F.Cu','B.Cu'],[a('net'),code],[a('uuid'),vu]])
    board.append([a('segment'),[a('start'),*points[0]],[a('end'),*points[1]],
                  [a('width'),width],[a('layer'),'F.Cu'],[a('net'),code],[a('uuid'),tu]])
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json',
        'plots','*-audit.json','rejected-source-net-status.json','README.md','local-plane-fill.json','native-zone-export.*'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    path=OUT/'power_protection.kicad_sch';sch=read_sexpr(path.read_text())
    first(first(sch,'title_block'),'rev')[1]='TBP23';path.write_text(sexpr(sch)+'\n')
    paths=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'u20-input-audit.json',
           BASE/'buck-control-routing.json',BASE/'buck-enable-routing.json',
           REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',
           REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        changed_zone_uuid=zone['uuid'],old_outline_mm=old_ring,new_outline_mm=RING,
        removed_stale_filled_polygons=removed_fill,
        routes=[dict(label='quiet-via-bus',net=net,layer='F.Cu',width_mm=width,path_mm=points,
                     length_mm=line.length,maximum_length_mm=1,segment_uuids=[tu])],
        vias=[dict(uuid=vu,net=net,position_mm=points[1],size_mm=.6,drill_mm=.3)],
        added_segments=1,added_vias=1,moves=[],
        deliberately_removed_direct_plane_contact_xy=[292.8,129.8],
        remote_configuration_return_preserved_via_existing_trace=True,
        native_fill_and_connectivity_validation_pending=True,
        whole_field_return_noise_and_impedance_qualified=False,fabrication_released=False)
    (OUT/'u23-quiet-routing.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Recessed U23 ground outline; added one quiet-return via and 0.8mm bus')


if __name__=='__main__':run()
