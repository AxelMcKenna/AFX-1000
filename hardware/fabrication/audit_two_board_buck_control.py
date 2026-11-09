"""Independent audit of regulator sensing/configuration and buffer bypass."""
import copy
import json
import math
from pathlib import Path
from shapely.affinity import rotate, translate
from shapely.geometry import Point, LineString, box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-buck-output-native-02'
OUT=STAGING/'two-board-power-buck-control-native-02'
BEFORE=STAGING/'two-board-power-routing-inputs-2525-buck-output/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2518-buck-control/capture.json'

def orientation(n):
    p=first(n,'at');return float(p[3]) if len(p)>3 else 0

def run():
    report_path=OUT/'buck-control-routing.json';report=json.loads(report_path.read_text())
    before,after=[json.loads(p.read_text()) for p in [BEFORE,AFTER]]
    for d in [report,before,after]:
        for name,h in d['source_sha256'].items():assert sha(REPO/name)==h,name
    trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    assert fps[0].keys()==fps[1].keys() and len(fps[1])==1103
    moves={r['ref']:r for r in report['moves']};assert set(moves)=={'P_R222','P_R223'}
    for ref,old in fps[0].items():
        new=fps[1][ref]
        if ref not in moves:assert geometry(old)==geometry(new),ref;continue
        r=moves[ref];assert list(map(float,first(old,'at')[1:3]))==r['old_xy']
        assert list(map(float,first(new,'at')[1:3]))==r['new_xy']
        assert (orientation(new)-orientation(old))%360==r['rotation_added_degrees']%360
        restored=copy.deepcopy(new);first(restored,'at')[:]=first(old,'at')
        for tag in ['pad','property','fp_text']:
            aa,bb=children(old,tag),children(restored,tag);assert len(aa)==len(bb)
            for a,b in zip(aa,bb):
                old_ats,new_ats=children(a,'at'),children(b,'at');assert len(old_ats)==len(new_ats)
                for old_at,new_at in zip(old_ats,new_ats):
                    assert list(map(float,old_at[1:3]))==list(map(float,new_at[1:3]))
                    assert (orientation(b)-orientation(a))%360==r['rotation_added_degrees']%360
                    new_at[:]=old_at
        assert geometry(old)==geometry(restored),ref
    def shell(t):return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','segment','via','arc','net'])]
    assert shell(trees[0])==shell(trees[1])
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');parts,pins=read_netlist(OUT/'netlist.xml')
    assert oldpins==pins and oldparts.keys()==parts.keys() and len(parts)==1088
    for ref in parts:
        for field in ['value','footprint']:assert oldparts[ref].findtext(field)==parts[ref].findtext(field)
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    def physical(o):return {k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys():
        assert old[u]['kind']=='PAD' and old[u]['ref'] not in moves
        hits=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
        assert len(hits)==1;aliases[u]=hits[0]
    assert len(aliases)==len(set(aliases.values()))
    oldkeys={aliases.get(u,u) for u in old};maxerror=0;changed_pads=0
    for uid,o in old.items():
        n=new[aliases.get(uid,uid)];ref=o.get('ref')
        if ref not in moves:assert physical(o)==physical(n),uid;continue
        changed_pads+=1;r=moves[ref]
        assert o['kind']==n['kind']=='PAD' and o['pin']==n['pin'] and o['net']==n['net'] and o['ref']==n['ref']
        assert o['drill_mm']==n['drill_mm']==[0,0]
        origin=r['old_xy'];target=r['new_xy'];rot=r['rotation_added_degrees']
        point=translate(rotate(Point(o['position_mm']),-rot,origin=origin),target[0]-origin[0],target[1]-origin[1])
        assert point.distance(Point(n['position_mm']))<2e-6
        assert (n['orientation_degrees']-o['orientation_degrees'])%360==rot%360
        assert o['layers'].keys()==n['layers'].keys()
        for l,ps in o['layers'].items():
            if not ps:assert not n['layers'][l];continue
            g=translate(rotate(shape(ps),-rot,origin=origin),target[0]-origin[0],target[1]-origin[1])
            error=g.hausdorff_distance(shape(n['layers'][l]));assert error<3e-6;maxerror=max(error,maxerror)
    assert changed_pads==4
    groups={u:set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped={aliases.get(u,u) for u in g};assert mapped<=groups[next(iter(mapped))]
    def pads(r,p):return [o for o in new.values() if o.get('ref')==r and o.get('pin')==p]
    joins=[(('P_R220','1'),('P_C228','1')),(('P_R222','1'),('P_U23','1')),
        (('P_R223','1'),('P_U23','2')),(('P_R222','2'),('P_C220','2')),
        (('P_R223','2'),('P_C220','2')),(('N_U28','5'),('N_C67','1')),(('N_U28','3'),('N_C67','2'))]
    joined_groups=set()
    for left,right in joins:
        g=groups[pads(*left)[0]['uuid']];assert pads(*right)[0]['uuid'] in g
        joined_groups.update(g)
    # Configuration returns must reach the existing BP5/AGND island, not
    # accidentally join the currently separate PGND or another bypass return.
    quiet=groups[pads('P_C220','2')[0]['uuid']]
    assert pads('P_U23','5')[0]['uuid'] in quiet and pads('P_U23','9')[0]['uuid'] not in quiet
    assert pads('N_U28','3')[0]['uuid'] not in quiet
    added=set();mounts=[o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])];assert len(mounts)==15
    for r in report['routes']:
        points=r['path_mm'];assert len(points)==len(r['segment_uuids'])+1
        assert abs(LineString(points).length-r['length_mm'])<2e-6 and r['length_mm']<=r['maximum_length_mm']
        for u,p,q in zip(r['segment_uuids'],points,points[1:]):
            assert u not in added and u not in oldkeys;added.add(u);o=new[u]
            assert o['kind']=='PCB_TRACK' and o['net']==r['net'] and o['width_mm']==r['width_mm']
            assert set(o['layers'])=={r['layer']} and math.dist(o['position_mm'],p)<2e-6 and math.dist(o['end_mm'],q)<2e-6
            assert u in joined_groups
            assert all(LineString([p,q]).distance(Point(m['position_mm']))-max(3.6,max(m['drill_mm'])/2+.5)-o['width_mm']/2>.01-2e-6 for m in mounts)
    for v in report['vias']:
        u=v['uuid'];assert u not in oldkeys and u not in added;added.add(u);o=new[u]
        assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['width_mm']==.6 and o['drill_mm']==.3 and o['via_type']==4
        assert o['position_mm']==v['position_mm'] and o['span']==['F.Cu','B.Cu']
        assert set(o['layers'])==set(after['copper_layers']) and u in joined_groups
    assert added==new.keys()-oldkeys and len(report['routes'])==15 and len(report['vias'])==8 and len(added)==29
    # Native courtyard envelopes, including actual rotations of the earlier cell.
    placement_path=STAGING/'two-board-placement-05/capture.json';placement=json.loads(placement_path.read_text())
    records={r['id']:r for r in placement['parts']};receivers={'F':[],'B':[]};changed=set(moves)
    for ref,f in fps[1].items():
        for side in ['F','B']:
            try:receivers[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
            except AssertionError:pass
        rec=records.get(ref)
        if rec and ref not in changed:
            x,y=map(float,first(f,'at')[1:3]);delta=orientation(f)-rec['angle']
            def envelope(b):return translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
            receivers[rec['side']].append((ref,envelope(rec['body_relative_xy'])))
            for e in rec['additional_planar_reserves']:receivers[e['side']].append((ref,envelope(e['bounds'])))
            for b in rec['tails_relative_xy']:
                assert rec['side']=='F';receivers['B'].append((ref,envelope(b)))
    contexts=[c for c in placement['context'] if not c['id'].startswith('inlet_')]
    allocation_path=STAGING/'assembly-layout-04/allocation.json'
    for name,x,y,z,dx,dy,t,*_ in json.loads(allocation_path.read_text())['additional_panel_PCBS']:
        contexts.append(dict(id=name,xy=[x,y,x+dx,y+dy],z=[z,z+t]))
    outline=shape(after['outline']).buffer(-.5)
    for ref in changed:
        f=fps[1][ref];side=first(f,'layer')[1][0];g=box(*courtyard(f,side+'.CrtYd'));assert outline.covers(g)
        assert all(g.buffer(.3,join_style=2).intersection(h).area<1e-8 for other,h in receivers[side] if other!=ref),ref
        assert all(g.distance(Point(m['position_mm']))>=max(3.6,max(m['drill_mm'])/2+.5)+.3-1e-6 for m in mounts),ref
        rec=records[ref];height=rec['height_mm'];z0=placement['power_Z']
        z=[z0-.2+1.44,z0+.2+1.76+height] if side=='F' else [z0-.2-height,z0+.2]
        assert z[0]>=3.05 and z[1]<=43.35
        for c in contexts:
            if min(z[1]+.25,c['z'][1])>max(z[0]-.25,c['z'][0]):assert g.buffer(.25,join_style=2).intersection(box(*c['xy'])).area<1e-8,(ref,c['id'])
    smd=[shape(ps) for o in new.values() if o['kind']=='PAD' and not any(o['drill_mm']) for l,ps in o['layers'].items() if l in ['F.Cu','B.Cu'] and ps]
    tree=STRtree(smd);gaps=[]
    for o in new.values():
        if o['kind']=='PCB_VIA':
            p=Point(o['position_mm']);gap=p.distance(smd[int(tree.nearest(p))])-o['drill_mm']/2
            assert gap>=.15-2e-6;gaps.append(gap)
    assert len(gaps)==138
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    assert before['native_uncapped_opens']==2525 and after['native_uncapped_opens']==2518
    # Cross-layer projection is deliberate: electrical DRC alone does not
    # flag a quiet sense trace beneath SW copper on another layer.
    noisy=[shape(ps) for o in new.values() if o['net'] in ['/P_power_supply/P03_A_SW',
        '/P_power_supply/P03_A_BOOT','/P_power_supply/P03_A_BOOT_RETURN'] for ps in o['layers'].values() if ps]
    sense_clearances=[]
    for r in report['routes']:
        if r['label'].startswith('output-sense'):
            line=LineString(r['path_mm']);sense_clearances.append(min(line.distance(g)-r['width_mm']/2 for g in noisy))
    for v in report['vias']:
        if v['net']=='/P_power_supply/P03_PRE6V':
            sense_clearances.append(min(Point(v['position_mm']).distance(g)-.3 for g in noisy))
    assert len(sense_clearances)==5 and min(sense_clearances)>=1-2e-6,sense_clearances
    paths=[Path(__file__),report_path,BEFORE,AFTER,placement_path,allocation_path,
        REPO/'hardware/electronics/output_stage/check_placement.py',REPO/'hardware/fabrication/audit_two_board_power_delta.py',REPO/'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE,OUT]:paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        components=1088,footprints=1103,unchanged_complete_pin_net_map=True,
        moved_footprints=2,replaced_footprints=0,changed_native_pad_instances=4,maximum_native_pad_polygon_error_mm=maxerror,
        all_old_copper_objects_unchanged=True,all_previous_native_connection_groups_preserved=len(before['all_groups']),
        local_route_sections=15,added_segments=21,added_vias=8,old_opens=2525,new_opens=2518,connections_closed=7,
        verified_endpoint_joins=joins,configuration_returns_use_existing_quiet_AGND_group=True,
        quiet_AGND_to_PGND_plane_connection_still_pending=True,
        minimum_projected_sense_to_SW_BOOT_copper_gap_mm=min(sense_clearances),
        sense_projection_policy_mm=1,projection_clearance_is_not_noise_qualification=True,
        minimum_all_via_drill_to_SMD_mm=min(gaps),vias_screened=138,moved_courtyard_context_findings=0,
        geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        electrical_thermal_and_manufacturing_qualified=False,full_installed_fit_verified=False,fabrication_released=False)
    with (OUT/'buck-control-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':run()
