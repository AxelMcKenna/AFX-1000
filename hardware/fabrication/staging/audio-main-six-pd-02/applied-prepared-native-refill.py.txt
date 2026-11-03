"""Compare a dedicated inner control layer and adjacent ground plane on the audio PCB."""
import argparse
import copy
import json
import math
import shutil
import sys
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'staging/audio-main-controls-08'
OUT = ROOT/'staging/audio-main-six-control-01'
DRIVER = '/CODEC/DRIVER_SETTLE_READY'
TIMER = '/BYPASS/TIMER_INPUT_OK'
CHIP = 'CHIP_EN'
LAYERS = ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']
RETIRED = {'599b0ae6-95dc-50a6-a335-b074c9211b30','60600f0c-7d4e-50f7-9b97-4857f341a340',
 '35949e89-f6d6-53ff-a0d0-69708dd03479','0aeece30-5475-5eaf-b4a8-6645ea676060',
 '1e17c3c2-6813-56e0-821b-10e35b4395e6','894e9e9a-912b-5ed3-8be0-aa26c53d9a07',
 'ef532391-1051-58fe-bb4c-bacc32aad73a','439b9d3a-821c-5600-b400-5736ca8985fa','babb28b5-6841-5b39-8f03-60ede5a24549'}
GROUND_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:audio-six-layer:In4-reference'))


def snapshot(label):
    p=OUT/('applied-'+label+'.py.txt')
    assert not p.exists()
    shutil.copyfile(Path(__file__),p)
    return p


def prepare():
    assert not OUT.exists()
    parent=json.loads((SOURCE/'routing-handoff.json').read_text())
    verify_hashes(parent['source_sha256'])
    assert parent['uncapped_open_connections']==203 and not parent['fabrication_released']
    refill=json.loads((SOURCE/'native-refill.json').read_text())
    verify_hashes(refill['source_sha256'])
    assert sha(SOURCE/'audio_core.kicad_pcb')==refill['filled_PCB_sha256']
    board=read_sexpr((SOURCE/'audio_core.kicad_pcb').read_text())
    names={n[1]:str(n[2]) for n in children(board,'net')}
    removed=[n for n in children(board,'segment') if str(first(n,'uuid')[1]) in RETIRED]
    assert len(removed)==9 and all(names[first(n,'net')[1]]==DRIVER and first(n,'layer')[1]=='F.Cu' and float(first(n,'width')[1])==.2 for n in removed)
    board=[n for n in board if n not in removed]
    layer_table=first(board,'layers')
    assert [n[1] for n in layer_table[1:] if n[1].endswith('.Cu')]==['F.Cu','In1.Cu','In2.Cu','B.Cu']
    index=next(i for i,n in enumerate(layer_table) if isinstance(n,list) and n[1]=='B.Cu')
    layer_table[index:index]=[[a(3),'In3.Cu',a('signal')],[a(4),'In4.Cu',a('power')]]
    extended=[]
    for i,zone in enumerate(children(board,'zone')):
        if not children(zone,'keepout'):
            continue
        rows=children(zone,'layers')
        assert len(rows)==1
        before=list(rows[0][1:])
        assert set(before)<=set(LAYERS)-{'In3.Cu','In4.Cu'}
        rows[0].extend(['In3.Cu','In4.Cu'])
        extended.append(dict(zone_index=i,old_layers=before,new_layers=list(rows[0][1:])))
    ground=next(z for z in children(board,'zone') if not children(z,'keepout'))
    assert first(ground,'layer')[1]=='In1.Cu' and names[first(ground,'net')[1]]=='AGND'
    added_ground=copy.deepcopy(ground)
    first(added_ground,'layer')[1]='In4.Cu'
    first(added_ground,'uuid')[1]=GROUND_UUID
    added_ground[:]=[n for n in added_ground if not isinstance(n,list) or not n or n[0]!='filled_polygon']
    board.append(added_ground)
    OUT.mkdir()
    applied=snapshot('six-layer-preparation')
    for p in SOURCE.iterdir():
        if p.suffix in ('.kicad_sch','.kicad_pro','.kicad_sym','.kicad_dru') or p.name in ('plan.json','fp-lib-table','sym-lib-table'):
            shutil.copyfile(p,OUT/p.name)
    shutil.copytree(SOURCE/'libraries',OUT/'libraries')
    dest=OUT/'prepared-input.kicad_pcb'
    dest.write_text(sexpr(board)+'\n')
    inputs=[applied,SOURCE/'audio_core.kicad_pcb',SOURCE/'routing-handoff.json',SOURCE/'native-refill.json']
    record=dict(source_sha256=relative_hashes(inputs),authored_PCB_sha256=sha(dest),
        retired_copper_uuids=sorted(RETIRED),retired_nodes=removed,extended_rule_area_layers=extended,
        additional_copper_layers=['In3.Cu','In4.Cu'],added_ground_zone_uuid=GROUND_UUID,
        additional_layer_purpose={'In3.Cu':'dedicated control routing','In4.Cu':'adjacent AGND reference'},
        nominal_board_thickness_mm=1.6,physical_stack_material_cost_and_process_accepted=False,
        all_component_poses_solder_lands_mounts_and_unretired_copper_exact=True,
        native_checks_pending=True,fabrication_released=False)
    (OUT/'preparation-record.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Prepared six-layer comparison; outline, component poses, mounts and nominal thickness unchanged')


def fill_prepared():
    assert sys.platform=='linux','Mac CAD remains disabled'
    import pcbnew

    applied=snapshot('prepared-native-refill')
    src,dest=OUT/'prepared-input.kicad_pcb',OUT/'prepared-refilled.kicad_pcb'
    assert not dest.exists()
    before=relative_hashes([applied,src,OUT/'preparation-record.json'])
    board=pcbnew.LoadBoard(str(src))
    assert board.GetCopperLayerCount()==6
    assert pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    export=OUT/'prepared-native-export.kicad_pcb'
    pcbnew.SaveBoard(str(export),board)
    native=read_sexpr(export.read_text())
    zones={str(first(z,'uuid')[1]):z for z in children(native,'zone') if not children(z,'keepout')}
    authored=read_sexpr(src.read_text())
    for z in children(authored,'zone'):
        if children(z,'keepout'):
            continue
        z[:]=[n for n in z if not isinstance(n,list) or not n or n[0]!='filled_polygon']
        fills=children(zones[str(first(z,'uuid')[1])],'filled_polygon')
        assert fills
        z.extend(copy.deepcopy(fills))
    dest.write_text(sexpr(authored)+'\n')
    verify_hashes(before)
    report=dict(source_sha256=before,native_export_sha256=sha(export),filled_PCB_sha256=sha(dest),
                native_version=pcbnew.GetBuildVersion(),native_copper_layer_count=6,fabrication_released=False)
    (OUT/'prepared-refill.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native six-layer load and two-plane refill complete')


def capture():
    assert sys.platform=='linux','Mac CAD remains disabled'
    from hardware.fabrication.capture_audio_layer_trial import capture as actual_capture
    applied=snapshot('prepared-layer-capture')
    actual_capture(OUT,OUT/'prepared-refilled.kicad_pcb',OUT/'prepared-refill.json','prepared-native-inputs.json',applied)


def controls():
    from shapely.geometry import LineString

    from hardware.fabrication.audio_main_continuous_path import route
    from hardware.fabrication.audio_main_joint_fanouts import choices
    from hardware.fabrication.audio_main_layer_screen import LayeredSignalScreen

    applied=snapshot('inner-control-routing')
    dest=OUT/'distribution-input.kicad_pcb'
    assert not dest.exists()
    capture_path=OUT/'prepared-native-inputs.json'
    captured=json.loads(capture_path.read_text())
    verify_hashes(captured['source_sha256'])
    assert captured['layer_count']==6 and captured['native_uncapped_opens']==204
    objects={o['uuid']:o for o in captured['objects']}
    members={i:k for k,ids in captured['groups'].items() for i in ids}
    pads={(o['ref'],o['pin']):o for o in objects.values() if o['kind']=='PAD' and o['pin']}
    screen=LayeredSignalScreen(captured)
    timer_point=[56.1,6.9]
    timer_neck=[pads['U607','6']['position_mm'],timer_point]
    assert screen.via_legal(TIMER,timer_point) and screen.legal(TIMER,'F.Cu',timer_neck)
    driver_screen=LayeredSignalScreen(captured)
    driver_screen.new_vias.append((TIMER,timer_point))
    driver_screen.added.append((TIMER,'F.Cu',LineString(timer_neck)))
    routes=[]
    source,target=[63.5,6.5],[57.2,14.4]
    contacts=[next(o for o in objects.values() if o['net']==DRIVER and o['kind']=='PCB_VIA' and math.dist(o['position_mm'],p)<1e-7) for p in (source,target)]
    groups=[members[o['uuid']] for o in contacts]
    assert groups[0]!=groups[1]
    middle=route(driver_screen,DRIVER,'In3.Cu',source,target,[45,0,85,25])
    assert middle
    length=middle['length_mm']
    limit=min(180,2.5*math.dist(source,target)+10)
    assert length<=limit
    routes.append(dict(net=DRIVER,runs=[('In3.Cu',middle['points_mm'])],vias=[],new_vias_mm=[],groups=groups,
        source_groups=[[k] for k in groups],portals=[source,target],terminal_points_mm=[source,target],
        planar_length_mm=length,maximum_planar_length_mm=limit,continuous_path_receipt=middle))
    screen.added.append((DRIVER,'In3.Cu',LineString(middle['points_mm'])))
    receiver=pads['U606','2']
    timer_routes=[]
    for end in choices(screen,receiver,members[receiver['uuid']],limit=64):
        if math.dist(timer_point,end['point'])<=.86:
            continue
        middle=route(screen,TIMER,'In3.Cu',timer_point,end['point'],[25,0,90,60])
        if not middle:
            continue
        runs=[('F.Cu',timer_neck),('In3.Cu',middle['points_mm'])]+[(face,list(reversed(ps))) for face,ps in reversed(end['runs'])]
        length=sum(LineString(ps).length for _,ps in runs)
        terminals=[pads['U607','6']['position_mm'],receiver['position_mm']]
        limit=min(180,2.5*math.dist(*terminals)+10)
        if length>limit:
            continue
        groups=[members[pads['U607','6']['uuid']],members[receiver['uuid']]]
        timer_routes.append(dict(net=TIMER,runs=runs,vias=[timer_point,end['point']],new_vias_mm=[timer_point,end['point']],groups=groups,
            source_groups=[[k] for k in groups],portals=[timer_point,end['point']],terminal_points_mm=terminals,
            planar_length_mm=length,maximum_planar_length_mm=limit,continuous_path_receipt=middle))
        break
    assert timer_routes,'Timer control did not complete on the dedicated layer'
    routes+=timer_routes
    for face,ps in routes[-1]['runs']:
        screen.added.append((TIMER,face,LineString(ps)))
    screen.new_vias.extend((TIMER,p) for p in routes[-1]['new_vias_mm'])
    start=pads['U207','12']
    root=next(o for o in objects.values() if o['net']==CHIP and o['kind']=='PCB_VIA' and math.dist(o['position_mm'],[66.7,8.3])<1e-7)
    chip_routes=[]
    for entry in choices(screen,start,members[start['uuid']],limit=64):
        middle=route(screen,CHIP,'In3.Cu',entry['point'],root['position_mm'],[55,0,90,20])
        if not middle:
            continue
        runs=entry['runs']+[('In3.Cu',middle['points_mm'])]
        terminals=[start['position_mm'],root['position_mm']]
        length=sum(LineString(ps).length for _,ps in runs)
        limit=min(180,2.5*math.dist(*terminals)+10)
        if length>limit:
            continue
        groups=[members[start['uuid']],members[root['uuid']]]
        chip_routes.append(dict(net=CHIP,runs=runs,vias=entry['vias'],new_vias_mm=entry['vias'],groups=groups,
            source_groups=[[k] for k in groups],portals=[entry['point'],root['position_mm']],terminal_points_mm=terminals,
            planar_length_mm=length,maximum_planar_length_mm=limit,continuous_path_receipt=middle))
        break
    assert chip_routes,'The remaining CHIP_EN input did not complete'
    routes+=chip_routes
    inputs=[applied,capture_path,ROOT/'audio_main_layer_screen.py',ROOT/'audio_main_continuous_path.py',
            ROOT/'audio_main_global_controls.py',ROOT/'audio_main_joint_fanouts.py']
    proposal=dict(source_sha256=relative_hashes(inputs),routes=routes,proposal_only=True,
                  ordinary_control_length_and_four_via_limits_preserved=True,native_checks_pending=True,fabrication_released=False)
    proposal_path=OUT/'control-routing-proposal.json'
    proposal_path.write_text(json.dumps(proposal,indent=2)+'\n')
    board=read_sexpr((OUT/'prepared-refilled.kicad_pcb').read_text())
    additions=[]
    for row in routes:
        for face,ps in row['runs']:
            add_geometry(board,additions,row['net'],face,ps,.2,'dedicated_inner_control')
        for point in row['new_vias_mm']:
            add_via(board,additions,row['net'],point,'dedicated_inner_control')
    dest.write_text(sexpr(board)+'\n')
    record=dict(source_sha256=relative_hashes([applied,proposal_path,OUT/'prepared-refilled.kicad_pcb',OUT/'preparation-record.json',
        OUT/'prepared-refill.json',ROOT/'audio_main_bypass_repack.py']),authored_PCB_sha256=sha(dest),routes=routes,
        added_segments=[r for r in additions if r['kind']=='segment'],added_vias=[r for r in additions if r['kind']=='via'],
        allowed_control_nets=sorted([DRIVER,TIMER,CHIP]),signal_layers=['F.Cu','In2.Cu','In3.Cu','B.Cu'],
        trace_width_mm=.2,clearance_mm=.2,planning_margin_mm=.01,repaired_existing_control_joins=1,new_global_control_joins=2,
        physical_stack_material_cost_and_process_accepted=False,native_checks_pending=True,fabrication_released=False)
    (OUT/'distribution-construction.json').write_text(json.dumps(record,indent=2)+'\n')
    for row in routes:
        print(row['net'],round(row['planar_length_mm'],3),'mm /',len(row['new_vias_mm']),'fresh vias')


def native(action):
    assert sys.platform=='linux','Mac CAD remains disabled'
    applied=snapshot(action+'-entry')
    if action=='fill':
        from hardware.fabrication import audio_main_power_routes as helper
        helper.OUT=OUT
        helper.fill()
        result=OUT/'native-refill.json'
    elif action=='review':
        from hardware.fabrication.audio_main_native_review import review
        review(OUT,SOURCE/'terminal-connectivity-review.json',OUT/'prepared-native-inputs.json',OUT/'distribution-construction.json',applied)
        result=OUT/'terminal-connectivity-review.json'
    else:
        from hardware.fabrication.review_audio_layer_retention import review
        review(SOURCE,OUT,64,applied)
        result=OUT/'additional-terminal-review.json'
    (OUT/(action+'-entry.json')).write_text(json.dumps(dict(source_sha256=relative_hashes([applied,result]),fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','fill-prepared','capture','controls','fill','review','retain'))
    args=parser.parse_args()
    {'prepare':prepare,'fill-prepared':fill_prepared,'capture':capture,'controls':controls,
     'fill':lambda:native('fill'),'review':lambda:native('review'),'retain':lambda:native('retain')}[args.action]()
