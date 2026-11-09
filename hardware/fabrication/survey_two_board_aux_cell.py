"""Screen a compact AUX regulator cell against current native copper and mechanics."""
import copy
import json
from pathlib import Path
from shapely.geometry import Point,box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_two_board_buck_cell import position,angle,mechanical_check,transform_object
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_nf_surface import shape

BASE=STAGING/'two-board-power-u23-quiet-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2462-u23-quiet/capture.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
OUT=STAGING/'two-board-aux-cell-survey-01'
MOVES={'P_U102':([190.5,130],90),'P_C113':([187.8,124.1],-90),
       'P_C106':([190.5,135.5],0),'P_C107':([195.5,138.6],-90),
       'P_R109':([186.9,134],90),'P_R108':([189,134],0),
       'P_R130':([193,132],0),'P_C110':([190.175,125],180)}


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for p,h in cap['source_sha256'].items():assert sha(Path(p))==h,p
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    old={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(old)
    for o in cap['objects']:
        if o.get('ref') in MOVES and o.get('pin'):assert cap['all_groups'][o['group']]==[o['uuid']]
    for r,(xy,rot) in MOVES.items():fps[r]=rotate_footprint(old[r],xy,rot)
    placement=json.loads(PLACEMENT.read_text());records={r['id']:r for r in placement['parts']}
    # The old placement capture predates the independently checked C204 flip.
    # Its physical receiving envelope must use the identical back-side C205
    # template, rather than asserting that this historical side is still current.
    proof_path=STAGING/'two-board-power-u20-input-native-01/u20-input-audit.json'
    proof=json.loads(proof_path.read_text())
    for p,h in proof['source_sha256'].items():assert sha(REPO/p)==h,p
    assert proof['flipped_footprints']==1 and proof['changed_native_pad_instances']==2
    assert old['P_C204'][1]==old['P_C205'][1]
    assert prop(old['P_C204'],'Value')[2]==prop(old['P_C205'],'Value')[2]
    assert first(old['P_C204'],'layer')[1]=='B.Cu' and angle(old['P_C204'])==0
    assert records['P_C204']['value']==records['P_C205']['value']
    assert records['P_C204']['footprint']==records['P_C205']['footprint']
    assert records['P_C204']['height_mm']==records['P_C205']['height_mm']
    for k in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']:
        records['P_C204'][k]=copy.deepcopy(records['P_C205'][k])
    mechanical_check(fps,set(MOVES),placement)
    objects=[transform_object(o,position(old[o['ref']]),*MOVES[o['ref']]) if o.get('ref') in MOVES else o for o in cap['objects']]
    geoms=[(o,l,shape(ps)) for o in objects for l,ps in o['layers'].items() if ps]
    trees={l:([(o,g) for o,k,g in geoms if k==l],STRtree([g for o,k,g in geoms if k==l])) for l in cap['copper_layers']}
    outline=shape(cap['outline']).buffer(-.5)
    holes=[];mounts=[]
    for o in objects:
        d=o.get('drill_mm',0);radius=max(d)/2 if isinstance(d,list) else d/2
        if radius:holes.append((Point(o['position_mm']),radius))
        if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref']):mounts.append((Point(o['position_mm']),max(3.6,radius+.5)))
    min_drill=1e9
    for o,l,g in geoms:
        if o.get('ref') not in MOVES:continue
        assert outline.covers(g)
        rows,tree=trees[l]
        for i in tree.query(g.buffer(.211)):
            q,h=rows[int(i)]
            if q.get('ref')!=o['ref'] and q['net']!=o['net']:assert g.distance(h)>=.21-1e-7,(o['ref'],q.get('ref'))
        gap=min(g.distance(p)-r for p,r in holes);assert gap>=.15
        min_drill=min(min_drill,gap)
        assert all(g.distance(p)>=r+.01 for p,r in mounts)
    for r in MOVES:
        side=first(fps[r],'layer')[1][0];g=box(*courtyard(fps[r],side+'.CrtYd'))
        assert outline.covers(g)
        assert all(g.distance(p)>=radius+.3 for p,radius in mounts)
    def pad(r,p):return next(o for o in objects if o.get('ref')==r and o.get('pin')==p)
    distances=[]
    for left,right in [(('P_C113','1'),('P_U102','8')),(('P_C106','1'),('P_U102','1')),
                       (('P_C106','2'),('P_U102','4')),(('P_C110','1'),('P_U102','7'))]:
        distances.append(dict(terminals=[left,right],straight_pad_center_distance_mm=Point(pad(*left)['position_mm']).distance(Point(pad(*right)['position_mm']))))
    paths=[Path(__file__),CAP,PLACEMENT,proof_path,BASE/'power_protection.kicad_pcb',BASE/'expected-circuit.json',
           STAGING/'assembly-layout-04/allocation.json',*[REPO/'hardware/fabrication'/n for n in
           ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_nf_surface.py']],
           REPO/'hardware/electronics/output_stage/check_placement.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        cell_members=sorted(MOVES),moved_footprints=7,retained_local_footprint='P_R130',
        poses=[dict(ref=r,old_xy=position(old[r]),new_xy=xy,rotation_added_degrees=rot,
                    final_angle_degrees=angle(fps[r]),side=first(fps[r],'layer')[1]) for r,(xy,rot) in MOVES.items()],
        placement_context_correction='C204 receiving envelope from identical C205 back-side package, verified by TBP22 audit',
        copper_courtyard_body_support_height_screen_pass=True,
        minimum_moved_pad_to_existing_drill_edge_mm=min_drill,
        capacitor_pad_center_distances=distances,
        main_input_output_and_delay_capacitors_same_front_side_as_regulator=True,
        all_moved_numbered_terminal_groups_isolated=True,
        manufacturer_source='https://www.ti.com/lit/ds/symlink/tps7a16.pdf',
        manufacturer_source_sections='9 and 10, SBVS171F',
        constraints=['Keep IN/OUT ground regions distinct until the regulator GND connection',
                     'Connect output capacitor return directly to regulator GND',
                     'Keep input/output/delay capacitors on the regulator side; avoid long/via capacitor paths',
                     'Guard high-impedance FB; R108/R130 remain on the back and require a reviewed local connection',
                     'Qualify effective capacitance, AUX total load, thermal dissipation and partial-power/startup'],
        candidate_only=True,native_candidate_validation_pending=True,new_routes_created=False,
        physical_board_modified=False,electrical_qualified=False,fabrication_released=False)
    OUT.mkdir();(OUT/'survey.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(moved=7,local_members=8,mechanical_and_pad_screen=True,
                         capacitor_distances=distances,board_modified=False)))


if __name__=='__main__':run()
