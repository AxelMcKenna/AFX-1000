"""Independent U20 input/ground-plane, capacitor relocation and return audit."""
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
BASE=STAGING/'two-board-power-u20-enable-native-01'
OUT=STAGING/'two-board-power-u20-input-native-01'
BEFORE=STAGING/'two-board-power-routing-inputs-2469-u20-enable/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2462-u20-input/capture.json'

def orientation(n):
    p=first(n,'at');return float(p[3]) if len(p)>3 else 0

def run():
    report_path=OUT/'u20-input-routing.json';report=json.loads(report_path.read_text())
    before,after=[json.loads(p.read_text()) for p in [BEFORE,AFTER]]
    for d in [report,before,after]:
        for name,h in d['source_sha256'].items():assert sha(REPO/name)==h,name
    trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    assert fps[0].keys()==fps[1].keys() and len(fps[1])==1100
    moves={r['ref']:r for r in report['moves']};assert set(moves)=={'P_C204'}
    assert report['back_side_template']=='P_C205'
    for ref,old in fps[0].items():
        new=fps[1][ref]
        if ref!='P_C204':assert geometry(old)==geometry(new),ref;continue
        assert list(map(float,first(old,'at')[1:3]))==[185,132]
        assert list(map(float,first(new,'at')[1:3]))==[173,132]
        assert first(old,'layer')[1]=='F.Cu' and first(new,'layer')[1]=='B.Cu'
        assert orientation(old)==90 and orientation(new)==0
        template=copy.deepcopy(fps[0]['P_C205'])
        first(template,'at')[:]=first(new,'at')
        prop(template,'Reference')[2]=ref
        first(template,'uuid')[:]=first(old,'uuid')
        oldpads={str(p[1]):p for p in children(old,'pad')}
        for p in children(template,'pad'):
            first(p,'uuid')[:]=first(oldpads[str(p[1])],'uuid')
        assert geometry(template)==geometry(new),ref
    def shell(t):return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','segment','via','arc','net','zone'])]
    assert shell(trees[0])==shell(trees[1])
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');parts,pins=read_netlist(OUT/'netlist.xml')
    assert oldpins==pins and oldparts.keys()==parts.keys() and len(parts)==1085
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
        source=next(q for q in old.values() if q.get('ref')=='P_C205' and q.get('pin')==o['pin'])
        origin=[184.3,136.65];target=[173,132]
        point=translate(Point(source['position_mm']),target[0]-origin[0],target[1]-origin[1])
        assert point.distance(Point(n['position_mm']))<2e-6
        assert n['orientation_degrees']==source['orientation_degrees']
        assert n['layers'].keys()==source['layers'].keys()
        for l,ps in source['layers'].items():
            if not ps:assert not n['layers'][l];continue
            g=translate(shape(ps),target[0]-origin[0],target[1]-origin[1])
            error=g.hausdorff_distance(shape(n['layers'][l]));assert error<3e-6;maxerror=max(error,maxerror)
    assert changed_pads==2
    groups={u:set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped={aliases.get(u,u) for u in g};assert mapped<=groups[next(iter(mapped))]
    def pads(r,p):return [o for o in new.values() if o.get('ref')==r and o.get('pin')==p]
    joins=[(('P_U20','8'),('P_U20','12')),(('P_U20','9'),('P_U20','11')),
        (('P_U20','9'),('P_U20','5')),(('P_C204','1'),('P_U20','8')),
        (('P_C204','2'),('P_U20','9')),(('P_C205','1'),('P_U20','8')),(('P_C205','2'),('P_U20','9'))]
    joined_groups=set()
    for left,right in joins:
        g=groups[pads(*left)[0]['uuid']];assert pads(*right)[0]['uuid'] in g
        joined_groups.update(g)
    for ref,pin in [('P_R202','2'),('P_R203','2'),('P_R205','2'),('P_C200','2'),('P_C203','2'),('P_C202','2')]:
        assert pads(ref,pin)[0]['uuid'] in groups[pads('P_U20','9')[0]['uuid']]
    assert groups[pads('P_U20','8')[0]['uuid']] != groups[pads('P_U20','9')[0]['uuid']]
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
    assert added==new.keys()-oldkeys and len(report['routes'])==16 and len(report['vias'])==13 and len(added)==29
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
    assert len(gaps)==180
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    assert before['native_uncapped_opens']==2469 and after['native_uncapped_opens']==2462
    # Filled copper must be the native output, not a drawn approximation.
    filled_source=STAGING/'two-board-power-u20-input-filled-01'
    fill_report=filled_source/'local-plane-fill.json';fill=json.loads(fill_report.read_text())
    for name,h in fill['source_sha256'].items():assert sha(REPO/name)==h,name
    for name,h in fill['artifact_sha256'].items():assert sha(filled_source/name)==h,name
    filled_tree=read_sexpr((filled_source/'power_protection.kicad_pcb').read_text())
    original_zones={str(first(z,'uuid')[1]):z for z in children(filled_tree,'zone')}
    actual_zones={str(first(z,'uuid')[1]):z for z in children(trees[1],'zone')}
    earlier_zones={str(first(z,'uuid')[1]):z for z in children(trees[0],'zone')}
    assert original_zones==actual_zones and len(actual_zones)==4 and len(earlier_zones)==2
    assert all(actual_zones[u]==z for u,z in earlier_zones.items())
    assert all(z in after['zones'] for z in before['zones'])
    assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==2
    assert all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    declared={r['uuid']:r for r in report['zones']};assert set(declared)==set(actual_zones)-set(earlier_zones)
    nets={int(n[1]):str(n[2]) for n in children(trees[1],'net')}
    zone_records=[];planes={}
    for z in after['zones']:
        if z['uuid'] not in declared:continue
        r=declared[z['uuid']];node=actual_zones[z['uuid']]
        assert not z['keepout'] and z['net']==r['net']==nets[int(first(node,'net')[1])]
        assert z['layer']==r['layer']==first(node,'layer')[1]
        ring=[list(map(float,p[1:3])) for p in children(first(first(node,'polygon'),'pts'),'xy')]
        assert ring==r['outline_mm']
        assert first(node,'connect_pads')[1]=='yes' and float(first(first(node,'connect_pads'),'clearance')[1])==.2
        assert float(first(node,'min_thickness')[1])==.25
        g=shape(z['polygons']);boundary=shape(z['authored_outline'])
        assert g.is_valid and g.geom_type=='Polygon' and len(z['polygons'])==1
        assert boundary.buffer(2e-6).covers(g) and outline.covers(boundary)
        assert math.isclose(g.area,z['native_area_after_unfracture_mm2'],rel_tol=1e-8,abs_tol=1e-6)
        assert all(g.distance(Point(m['position_mm']))>=max(3.6,max(m['drill_mm'])/2+.5)+.3-2e-6 for m in mounts)
        distances=[g.distance(shape(o['layers'][z['layer']])) for o in new.values() if o['net']!=z['net'] and o['layers'].get(z['layer'])]
        # Object polygons are expanded by at most .001 mm during native capture.
        assert min(distances)>=.1985,(z['layer'],min(distances))
        contacts=[]
        for v in report['vias']:
            if v['net']==z['net']:
                assert g.buffer(.0015).covers(shape(new[v['uuid']]['layers'][z['layer']]))
                contacts.append(v['uuid'])
        assert len(contacts)==(7 if z['layer']=='In1.Cu' else 6)
        planes[z['layer']]=g
        zone_records.append(dict(layer=z['layer'],net=z['net'],area_mm2=g.area,holes=sum(len(p['holes']) for p in z['polygons']),
            connected_new_vias=len(contacts),minimum_captured_foreign_copper_gap_mm=min(distances),single_contiguous_filled_polygon=True))
    # New ground must cover the previously reviewed sense trace on the next
    # layer, apart from its two intentional signal-via antipads.
    control_path=BASE/'u20-control-routing.json';control=json.loads(control_path.read_text())
    sense=next(r for r in control['routes'] if r['label']=='output-sense-In2')
    corridor=LineString(sense['path_mm']).buffer(sense['width_mm']/2)
    for v in control['vias']:
        if v['net']=='PWR_5V_DIG_SRC':corridor=corridor.difference(Point(v['position_mm']).buffer(.515))
    uncovered=corridor.difference(planes['In1.Cu'].buffer(.0015)).area
    assert uncovered<1e-6,uncovered
    # The new force plane does not directly engulf the remote MODE return via
    # or the configuration link. Their only plane entry is near BP5's ground.
    mode_return=Point(175.3,139.3).buffer(.3)
    assert planes['In1.Cu'].distance(mode_return)>=.2
    quiet_link=next(r for r in control['routes'] if r['label']=='configuration-return-In1')
    remote_link=LineString(quiet_link['path_mm']).buffer(.125).intersection(box(0,0,181.9,500))
    assert planes['In1.Cu'].distance(remote_link)>=.2
    old_quiet=next(v for v in control['vias'] if v['position_mm']==[182.8,141.1])
    assert planes['In1.Cu'].buffer(.0015).covers(shape(new[old_quiet['uuid']]['layers']['In1.Cu']))

    paths=[Path(__file__),report_path,BEFORE,AFTER,placement_path,allocation_path,fill_report,control_path,
        REPO/'hardware/electronics/output_stage/check_placement.py',REPO/'hardware/fabrication/audit_two_board_power_delta.py',REPO/'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE,OUT]:paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        components=1085,footprints=1100,unchanged_complete_pin_net_map=True,
        moved_footprints=1,flipped_footprints=1,replaced_footprints=0,changed_native_pad_instances=2,maximum_native_pad_polygon_error_mm=maxerror,
        all_old_tracks_vias_unchanged=True,all_other_copper_objects_unchanged=True,all_previous_native_connection_groups_preserved=len(before['all_groups']),
        local_route_sections=16,added_segments=16,added_vias=13,old_opens=2469,new_opens=2462,connections_closed=7,
        verified_endpoint_joins=joins,local_plane_checks=zone_records,
        sense_trace_projection_covered_by_In1_except_own_via_antipads=True,sense_projection_uncovered_area_mm2=uncovered,
        reference_corridor_checked_width_mm=.2,whole_field_return_noise_and_impedance_qualification=False,
        minimum_all_via_drill_to_SMD_mm=min(gaps),vias_screened=180,moved_courtyard_context_findings=0,
        existing_U23_zones_and_fill_unchanged=True,
        configuration_return_enters_force_plane_only_near_BP5=True,
        quiet_return_to_PGND_connected=True,
        enable_reference_plane_complete=False, effective_input_capacitance_qualified=False,
        geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        electrical_thermal_and_manufacturing_qualified=False,full_installed_fit_verified=False,fabrication_released=False)
    with (OUT/'u20-input-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':run()
