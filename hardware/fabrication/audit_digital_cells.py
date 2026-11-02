"""Independent DC02 placement, drilled-land and source-bound routing review."""
import json
from pathlib import Path
from shapely.geometry import Point,Polygon,box
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.common.netlists import netlist
from hardware.electronics.output_stage.check_placement import courtyard,transform
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.audit_candidate import sha,native_evidence_errors
from hardware.fabrication.audit_digital_core import verify_export
from hardware.fabrication.route_nf_surface import shape

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'hardware/fabrication'
OUT=ROOT/'staging/digital-local-cell-native-01'

def check():
    pcb=OUT/'digital_core.kicad_pcb';rp=OUT/'review.json';r=json.loads(rp.read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'),r)
    assert r['status']['counts']==dict(violations=0,unconnected_items=427,schematic_parity=0,erc=0)
    assert r['uncapped_open_connections']==427
    for name,h in r['captured_hierarchy_sha256'].items():assert sha(OUT/name)==h
    parts,pins=netlist(OUT/'netlist.xml');verify_export(parts,pins)
    receipts=[OUT/'independent-geometry-audit.json',OUT/'local-connectivity-review.json',
        ROOT/'staging/digital-power-cell-native-01/placement-change-audit.json',
        ROOT/'staging/digital-power-cell-placement-01/conditional-receiving-review.json']
    for path in receipts:
        data=json.loads(path.read_text())
        assert all(sha(Path(p))==h for p,h in data['source_sha256'].items())
    tree=read_sexpr(pcb.read_text());fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(tree,'footprint')}
    profile=Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
    courts={ref:box(*courtyard(f,first(f,'layer')[1][0]+'.CrtYd')) for ref,f in fps.items()}
    sides={ref:first(f,'layer')[1][0] for ref,f in fps.items()}
    through={ref:[box(*pad_box(f,p,.5)) for p in children(f,'pad') if p[2]=='thru_hole'] for ref,f in fps.items()}
    for ref in parts:
        assert profile.covers(courts[ref]) and courts[ref].distance(profile.boundary)>=.5-1e-8
        for other in parts:
            if ref==other:continue
            if sides[ref]==sides[other]:assert courts[ref].distance(courts[other])>=.3-1e-8,(ref,other)
            else:assert not any(courts[ref].intersection(p).area>1e-10 for p in through[other]),(ref,other)
        for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]:assert courts[ref].distance(box(x-3.6,y-3.6,x+3.6,y+3.6))>=.15-1e-8
    cp=ROOT/'staging/digital-local-cell-inputs-427/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    smd=[shape(ps) for o in c['objects'] if o['kind']=='PAD' and not any(o['drill_mm']) for l,ps in o['layers'].items() if l in ['F.Cu','B.Cu'] and ps]
    drills=[]
    for via in children(tree,'via'):
        xy=list(map(float,first(via,'at')[1:3]));drill=float(first(via,'drill')[1]);assert drill==.3 and float(first(via,'size')[1])==.6
        gap=min(Point(xy).distance(g)-drill/2 for g in smd);assert gap>=.15-1e-6
        drills.append(dict(uuid=first(via,'uuid')[1],xy_mm=xy,drill_mm=drill,minimum_hole_edge_to_SMD_copper_mm=gap))
    assert len(drills)==8 and len(children(tree,'segment'))==59 and not children(tree,'zone')
    assert all(first(n,'layer')[1] in ['F.Cu','B.Cu'] for n in children(tree,'segment'))
    inputs=[pcb,rp,OUT/'netlist.xml',cp,Path(__file__),*receipts]+[OUT/n for n in r['captured_hierarchy_sha256']]
    return dict(revision='DC02',source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},electrical_parts=138,exported_physical_terminals=sum(map(len,pins.values())),
        mounting_holes=5,PCB_area_mm2=6630,parts_by_side={s:sum(sides[ref]==s for ref in parts) for s in ['F','B']},
        uncapped_open_connections=427,native_geometry_findings=0,native_schematic_parity_findings=0,native_ERC_findings=0,
        all_native_categories_enabled=True,local_connections_native_verified=39,local_segments=59,conventional_vias=drills,
        all_source_values_lands_and_pin_nets_preserved=True,conditional_courtyard_THT_and_mount_clearances_pass=True,
        board_power_ground_returns_thermal_paths_and_remaining_signals_unfinished=True,
        complete_mechanical_receiving_qualified=False,routed=False,fabrication_released=False)

if __name__=='__main__':
    result=check();p=OUT/'handoff.json'
    with p.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('DC02: 39 verified local connections; 427 opens; eight vias clear of SMD lands')
