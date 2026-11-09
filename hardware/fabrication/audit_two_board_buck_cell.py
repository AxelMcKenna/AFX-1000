"""Independent native audit of connector retirement and rigid buck regrouping."""
import copy
import json
import math
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import Point, box
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape

BASE = STAGING/'two-board-power-routed-native-08'
OUT = STAGING/'two-board-power-buck-cell-native-01'
BEFORE = STAGING/'two-board-power-routing-inputs-2554-via-repair/capture.json'
AFTER = STAGING/'two-board-power-routing-inputs-2551-buck-cell/capture.json'


def run():
    record_path = OUT/'buck-cell-change.json'; record = json.loads(record_path.read_text())
    before, after = [json.loads(p.read_text()) for p in [BEFORE, AFTER]]
    for d in [record,before,after]:
        for p,h in d['source_sha256'].items(): assert sha(REPO/p)==h,p
    trees = [read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    fps = [{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    retired = set(record['retired_connector_refs']); assert retired=={'I_J2','P_J101'}
    moves = {r['ref']:r for r in record['poses']}; assert len(moves)==10
    assert fps[0].keys()-fps[1].keys()==retired and not fps[1].keys()-fps[0].keys()
    def angle(at): return float(at[3]) if len(at)>3 else 0
    for ref,f in fps[1].items():
        old=fps[0][ref]
        if ref not in moves:
            assert geometry(f)==geometry(old),ref
            continue
        r=moves[ref]; old_at=first(old,'at'); new_at=first(f,'at')
        assert list(map(float,old_at[1:3]))==r['old_xy'] and list(map(float,new_at[1:3]))==r['new_xy']
        assert (angle(new_at)-angle(old_at))%360==r['rotation_added_degrees']==90
        restored=copy.deepcopy(f); first(restored,'at')[:]=old_at
        for tag in ['pad','property','fp_text']:
            old_nodes=children(old,tag); new_nodes=children(restored,tag); assert len(old_nodes)==len(new_nodes)
            for a,b in zip(old_nodes,new_nodes):
                old_ats=children(a,'at');new_ats=children(b,'at');assert len(old_ats)==len(new_ats)
                for old_pos,new_pos in zip(old_ats,new_ats):
                    assert list(map(float,old_pos[1:3]))==list(map(float,new_pos[1:3]))
                    assert (angle(new_pos)-angle(old_pos))%360==90
                    new_pos[:]=old_pos
        assert geometry(restored)==geometry(old),ref
    def shell(t): return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','net','segment','via','arc'])]
    assert shell(trees[0])==shell(trees[1])
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');newparts,newpins=read_netlist(OUT/'netlist.xml')
    assert oldparts.keys()-newparts.keys()==retired and not newparts.keys()-oldparts.keys()
    assert newpins=={k:v for k,v in oldpins.items() if k[0] not in retired}
    assert all(p.findtext(f)==oldparts[r].findtext(f) for r,p in newparts.items() for f in ['value','footprint'])
    assert newpins['I_F1','2']==newpins['P_Q101','1']=='PWR_DC_IN'
    assert newpins['I_J1','1']!=newpins['I_F1','2']
    assert newpins['N_U19','4']!=newpins['N_U19','5'] and newpins['N_U24','4']!=newpins['N_U24','5']
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    pruned=set(record['retired_stub_segment_uuids']);assert len(pruned)==3
    removed={u for u,o in old.items() if o.get('ref') in retired}|pruned
    def physical(o): return {k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys()-removed:
        assert old[u]['kind']=='PAD' and old[u]['ref'] not in moves
        matches=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
        assert len(matches)==1; aliases[u]=matches[0]
    assert len(set(aliases.values()))==len(aliases)
    assert set(new)=={aliases.get(u,u) for u in old if u not in removed}
    maximum_polygon_error=0; moved_pads=0
    for u,o in old.items():
        if u in removed: continue
        n=new[aliases.get(u,u)]
        if o.get('ref') not in moves:
            assert physical(o)==physical(n),u
            continue
        moved_pads+=1; r=moves[o['ref']]; pivot=r['old_xy'];target=r['new_xy']
        assert o['kind']==n['kind']=='PAD' and o['net']==n['net'] and o['pin']==n['pin']
        assert o['drill_mm']==n['drill_mm']==[0,0] and o['npth']==n['npth']==False
        assert (n['orientation_degrees']-o['orientation_degrees'])%360==90
        p=o['position_mm'];expected=[target[0]+p[1]-pivot[1],target[1]-p[0]+pivot[0]]
        assert math.dist(n['position_mm'],expected)<2e-6
        assert o['layers'].keys()==n['layers'].keys()
        for layer,ps in o['layers'].items():
            if not ps: assert not n['layers'][layer];continue
            g=translate(rotate(shape(ps),-90,origin=pivot),target[0]-pivot[0],target[1]-pivot[1])
            error=g.hausdorff_distance(shape(n['layers'][layer]));maximum_polygon_error=max(maximum_polygon_error,error)
            assert error<3e-6,(o['ref'],o['pin'],error)
    memberships={u:set(g) for g in after['all_groups'].values() for u in g}
    preserved=0
    for group in before['all_groups'].values():
        remaining={aliases.get(u,u) for u in group if u not in removed}
        if remaining:
            assert remaining<=memberships[next(iter(remaining))];preserved+=1
    # Check the removed copper was exclusively the inlet connector's leaf.
    stub=next(g for g in before['all_groups'].values() if pruned<=set(g))
    assert {(old[u].get('ref'),old[u].get('pin')) for u in stub if old[u]['kind']=='PAD'}=={('I_J2','1'),('I_F1','2')}
    assert set(stub)==pruned|{u for u in stub if old[u]['kind']=='PAD'}
    # Independent mechanical check uses actual candidate courtyards, not the
    # search templates. Receiving heights/connector allowances remain provisional.
    placement_path=STAGING/'two-board-placement-05/capture.json'; placement=json.loads(placement_path.read_text())
    rec={r['id']:r for r in placement['parts']}; obstacles=[]
    for ref,f in fps[1].items():
        if ref in moves: continue
        try: obstacles.append((ref,box(*courtyard(f,'F.CrtYd'))))
        except AssertionError: pass
        x,y=map(float,first(f,'at')[1:3]);r=rec.get(ref)
        if r:
            assert angle(first(f,'at'))==r['angle']
            bounds=[]
            if r['side']=='F': bounds.append(r['body_relative_xy'])
            bounds.extend(e['bounds'] for e in r.get('additional_planar_reserves',[]) if e['side']=='F')
            for b in bounds: obstacles.append((ref,box(b[0]+x,b[1]+y,b[2]+x,b[3]+y)))
    for o in new.values():
        if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref']):
            obstacles.append((o['ref'],Point(o['position_mm']).buffer(max(3.6,max(o['drill_mm'])/2+.5))))
    contexts=[r for r in placement['context'] if not r['id'].startswith('inlet_')]
    allocation_path=STAGING/'assembly-layout-04/allocation.json'
    for name,x,y,z,dx,dy,t,*_ in json.loads(allocation_path.read_text())['additional_panel_PCBS']:
        contexts.append(dict(id=name,xy=[x,y,x+dx,y+dy],z=[z,z+t]))
    moved_courts=[]; outline=shape(after['outline']).buffer(-.5)
    for ref in moves:
        f=fps[1][ref];g=box(*courtyard(f,'F.CrtYd'));assert outline.covers(g)
        r=rec[ref];assert r['body_relative_xy']==r['courtyard_relative_xy'] and not r['tails_relative_xy'] and not r['additional_planar_reserves']
        assert all(g.buffer(.3,join_style=2).intersection(h).area<1e-8 for name,h in obstacles),ref
        assert all(g.buffer(.3,join_style=2).intersection(h).area<1e-8 for name,h in moved_courts),ref
        z=[placement['power_Z']-.2+1.44,placement['power_Z']+.2+1.76+r['height_mm']]
        assert z[0]>=3.05 and z[1]<=43.35
        for c in contexts:
            if min(z[1]+.25,c['z'][1])>max(z[0]-.25,c['z'][0]):
                assert g.buffer(.25,join_style=2).intersection(box(*c['xy'])).area<1e-8,(ref,c['id'])
        moved_courts.append((ref,g))
    smd=[shape(ps) for o in new.values() if o['kind']=='PAD' and not any(o['drill_mm'])
         for layer,ps in o['layers'].items() if layer in ['F.Cu','B.Cu'] and ps]
    smd_tree=STRtree(smd); gaps=[]
    for o in new.values():
        if o['kind']!='PCB_VIA':continue
        point=Point(o['position_mm']);idx=int(smd_tree.nearest(point))
        gap=point.distance(smd[idx])-o['drill_mm']/2;assert gap>=.15-2e-6
        gaps.append(gap)
    assert len(gaps)==124
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    assert before['native_uncapped_opens']==2554 and after['native_uncapped_opens']==2551
    paths=[Path(__file__),BEFORE,AFTER,record_path,placement_path,allocation_path,
           REPO/'hardware/electronics/output_stage/check_placement.py',REPO/'hardware/fabrication/audit_two_board_power_delta.py',
           REPO/'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE,OUT]: paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','drc.json','erc.json','review.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        retired_connectors=sorted(retired),retired_pads=len(removed)-len(pruned),retired_leaf_tracks=len(pruned),
        retained_components=len(newparts),retained_footprints=len(fps[1]),unchanged_remaining_pin_net_map=True,
        retained_native_connection_groups_preserved=preserved,all_retained_copper_objects_unchanged=True,
        moved_footprints=len(moves),moved_native_pad_instances=moved_pads,maximum_native_polygon_transform_error_mm=maximum_polygon_error,
        moved_courtyard_context_findings=0,moved_courtyard_gap_mm=.3,board_edge_gap_mm=.5,
        via_drill_SMD_checks=len(gaps),minimum_via_drill_to_SMD_mm=min(gaps),
        old_opens=2554,new_opens=2551,opens_removed_by_connector_retirement=3,new_routes=0,
        geometry_findings=0,schematic_parity_findings=0,erc_errors=0,retained_erc_warnings=2,
        remaining_switching_routing_and_other_critical_placement_required=True,
        full_installed_housing_fit_verified=False,power_layout_qualified=False,fabrication_released=False)
    with (OUT/'buck-cell-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':run()
