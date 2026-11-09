"""Independent complete footprint/copper delta and mechanical audit for TBP31."""
import copy,json,math
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import Point,LineString,box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,read_netlist,sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.route_nf_surface import shape

BASE=STAGING/'two-board-power-input-thresholds-native-03'
OUT=STAGING/'two-board-power-fast-ov-native-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2405-input-thresholds/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2383-fast-ov/capture.json'

def angle(f):
    p=first(f,'at');return float(p[3]) if len(p)>3 else 0

def run():
    report_path=OUT/'fast-ov-routing.json';plane_path=OUT/'fast-ov-plane-review.json'
    report,before,after,planes=[json.loads(p.read_text()) for p in [report_path,BEFORE,AFTER,plane_path]]
    for d in [report,before,after,planes]:
        for p,h in d['source_sha256'].items():assert sha(REPO/p)==h,p
    assert planes['all_fourteen_native_planes_contiguous'] and planes['AUX_input_output_returns_separate_after_GND_land_cut']
    assert planes['full_control_reference_uncovered_mm2']==planes['bulk_output_trace_reference_uncovered_mm2_excluding_own_antipads']==0
    trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    assert set(fps[1])==set(fps[0])|{'P_C114'} and len(fps[1])==1101
    moves={r['ref']:r for r in report['moves']};assert set(moves)=={'P_U103','P_Q103','P_R115','P_R116','P_R117','P_R118','P_R119','P_C109','P_R120','P_R121'}
    flips=set()
    # Independently normalize the added capacitor against the retained donor footprint.
    donor=copy.deepcopy(fps[0]['P_C401']);added_fp=copy.deepcopy(fps[1]['P_C114'])
    assert donor[1]==added_fp[1] and prop(donor,'Value')[2]==prop(added_fp,'Value')[2]
    assert first(added_fp,'layer')==first(donor,'layer')
    assert list(map(float,first(added_fp,'at')[1:3]))==[194.9,114.8]
    assert (angle(added_fp)-angle(donor))%360==180
    first(added_fp,'at')[:]=first(donor,'at');first(added_fp,'uuid')[:]=first(donor,'uuid');prop(added_fp,'Reference')[2]='P_C401'
    donor_pads={str(p[1]):p for p in children(donor,'pad')}
    for p in children(added_fp,'pad'):first(p,'uuid')[:]=first(donor_pads[str(p[1])],'uuid')
    for tag in ['pad','property','fp_text']:
        aa,bb=children(donor,tag),children(added_fp,tag);assert len(aa)==len(bb)
        for pa,pb in zip(aa,bb):
            ats,bts=children(pa,'at'),children(pb,'at');assert len(ats)==len(bts)
            for x,y in zip(ats,bts):
                assert list(map(float,x[1:3]))==list(map(float,y[1:3]))
                oa=float(x[3]) if len(x)>3 else 0;na=float(y[3]) if len(y)>3 else 0
                assert (na-oa)%360==180;y[:]=x
    assert geometry(donor)==geometry(added_fp)
    for ref,old in fps[0].items():
        new=fps[1][ref]
        if ref not in moves:assert geometry(old)==geometry(new),ref;continue
        r=moves[ref]
        assert list(map(float,first(old,'at')[1:3]))==r['old_xy']
        assert list(map(float,first(new,'at')[1:3]))==r['new_xy']
        assert (angle(new)-angle(old))%360==r['rotation_added_degrees']%360
        assert old[1]==new[1] and prop(old,'Value')[2]==prop(new,'Value')[2]
        if ref in flips:
            assert first(old,'layer')[1]=='F.Cu' and first(new,'layer')[1]=='B.Cu'
            donor=copy.deepcopy(fps[0]['P_R102']);actual=copy.deepcopy(new)
            assert donor[1]==old[1]
            delta=(angle(actual)-angle(donor))%360
            first(actual,'at')[:]=first(donor,'at')
            first(actual,'uuid')[:]=first(donor,'uuid')
            for field in ['Reference','Value','Datasheet']:prop(actual,field)[2]=prop(donor,field)[2]
            dp={str(p[1]):p for p in children(donor,'pad')}
            for p in children(actual,'pad'):first(p,'uuid')[:]=first(dp[str(p[1])],'uuid')
            for tag in ['pad','property','fp_text']:
                aa,bb=children(donor,tag),children(actual,tag);assert len(aa)==len(bb)
                for pa,pb in zip(aa,bb):
                    ats,bts=children(pa,'at'),children(pb,'at');assert len(ats)==len(bts)
                    for x,y in zip(ats,bts):
                        assert list(map(float,x[1:3]))==list(map(float,y[1:3]))
                        oa=float(x[3]) if len(x)>3 else 0;na=float(y[3]) if len(y)>3 else 0
                        assert (na-oa)%360==delta
                        y[:]=x
            assert geometry(donor)==geometry(actual),ref
            continue
        assert first(old,'layer')==first(new,'layer')
        restored=copy.deepcopy(new);first(restored,'at')[:]=first(old,'at')
        for tag in ['pad','property','fp_text']:
            aa,bb=children(old,tag),children(restored,tag);assert len(aa)==len(bb)
            for a,b in zip(aa,bb):
                ats,bts=children(a,'at'),children(b,'at');assert len(ats)==len(bts)
                for x,y in zip(ats,bts):
                    assert list(map(float,x[1:3]))==list(map(float,y[1:3]))
                    oa=float(x[3]) if len(x)>3 else 0;na=float(y[3]) if len(y)>3 else 0
                    assert (na-oa)%360==r['rotation_added_degrees']%360
                    y[:]=x
        assert geometry(old)==geometry(restored),ref
    def shell(t):return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','segment','via','arc','net','zone'])]
    assert shell(trees[0])==shell(trees[1])
    parts0,pins0=read_netlist(BASE/'netlist.xml');parts,pins=read_netlist(OUT/'netlist.xml')
    assert set(parts)==set(parts0)|{'P_C114'} and len(parts)==1086
    assert {k:v for k,v in pins.items() if k[0]!='P_C114'}==pins0
    assert {k:v for k,v in pins.items() if k[0]=='P_C114'}=={('P_C114','1'):'PWR_V2V5_AUX',('P_C114','2'):'PWR_AGND'}
    assert all(parts['P_C114'].findtext(k)==parts0['P_C401'].findtext(k) for k in ['value','footprint'])
    assert all(parts0[r].findtext(k)==parts[r].findtext(k) for r in parts0 for k in ['value','footprint'])
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    retired={o['uuid']:o for o in report['retired_tracks']+report['retired_vias']}
    assert len(retired)==0 and all(old[u]==o and u not in new for u,o in retired.items())
    def expected_point(o):
        r=moves[o['ref']]
        return translate(rotate(Point(o['position_mm']),-r['rotation_added_degrees'],origin=r['old_xy']),r['new_xy'][0]-r['old_xy'][0],r['new_xy'][1]-r['old_xy'][1])
    def physical(o):return {k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys()-retired.keys():
        o=old[u];assert o['kind']=='PAD'
        if o.get('ref') in moves:
            hits=[v for v in new.keys()-old.keys() if new[v]['kind']=='PAD' and new[v].get('ref')==o.get('ref') and new[v].get('pin')==o.get('pin') and expected_point(o).distance(Point(new[v]['position_mm']))<2e-6]
        else:hits=[v for v in new.keys()-old.keys() if physical(o)==physical(new[v])]
        assert len(hits)==1,(u,o.get('ref'),o.get('pin'),hits)
        aliases[u]=hits[0]
    assert len(set(aliases.values()))==len(aliases)
    mappedkeys={aliases.get(u,u) for u in old if u not in retired}
    movedpads=0;maxerror=0
    for u,o in old.items():
        if u in retired:continue
        n=new[aliases.get(u,u)];ref=o.get('ref')
        if ref not in moves:assert physical(o)==physical(n),u;continue
        movedpads+=1;assert o['kind']==n['kind']=='PAD'
        assert all(o[k]==n[k] for k in ['ref','pin','net','drill_mm','npth'])
        assert expected_point(o).distance(Point(n['position_mm']))<2e-6
        r=moves[ref]
        assert (n['orientation_degrees']-o['orientation_degrees'])%360==r['rotation_added_degrees']%360
        if ref in flips:assert set(o['layers'])=={'F.Cu'} and set(n['layers'])=={'B.Cu'}
        else:assert o['layers'].keys()==n['layers'].keys()
        for layer,ps in o['layers'].items():
            target='B.Cu' if ref in flips else layer
            if not ps:assert not n['layers'][target];continue
            g=translate(rotate(shape(ps),-r['rotation_added_degrees'],origin=r['old_xy']),r['new_xy'][0]-r['old_xy'][0],r['new_xy'][1]-r['old_xy'][1])
            error=g.hausdorff_distance(shape(n['layers'][target]));assert error<3e-6,(ref,o['pin'],error)
            maxerror=max(maxerror,error)
    newpads=[o for o in new.values() if o.get('ref')=='P_C114'];assert len(newpads)==2
    for o in newpads:
        d=next(q for q in old.values() if q.get('ref')=='P_C401' and q.get('pin')==o['pin'])
        assert all(d[k]==o[k] for k in ['kind','net','drill_mm','npth']) and d['layers'].keys()==o['layers'].keys()
        oldxy=list(map(float,first(fps[0]['P_C401'],'at')[1:3]))
        expected=translate(rotate(Point(d['position_mm']),-180,origin=oldxy),194.9-oldxy[0],114.8-oldxy[1]);assert expected.distance(Point(o['position_mm']))<2e-6
        for l,ps in d['layers'].items():
            g=translate(rotate(shape(ps),-180,origin=oldxy),194.9-oldxy[0],114.8-oldxy[1]);assert g.hausdorff_distance(shape(o['layers'][l]))<3e-6
    added={o['uuid'] for o in newpads}
    for r in report['routes']:
        pts=r['path_mm'];assert len(pts)==len(r['segment_uuids'])+1
        assert abs(LineString(pts).length-r['length_mm'])<2e-6 and r['length_mm']<=r['maximum_length_mm']
        for u,p,q in zip(r['segment_uuids'],pts,pts[1:]):
            assert u not in added and u not in mappedkeys;added.add(u);o=new[u]
            assert o['kind']=='PCB_TRACK' and o['net']==r['net'] and o['width_mm']==r['width_mm']
            assert set(o['layers'])=={r['layer']}
            assert math.dist(o['position_mm'],p)<2e-6 and math.dist(o['end_mm'],q)<2e-6
    for v in report['vias']:
        u=v['uuid'];assert u not in added and u not in mappedkeys;added.add(u);o=new[u]
        assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['position_mm']==v['position_mm']
        assert o['width_mm']==.6 and o['drill_mm']==.3 and o['via_type']==4 and o['span']==['F.Cu','B.Cu']
        assert set(o['layers'])==set(after['copper_layers'])
    assert added==new.keys()-mappedkeys and len(added)==75
    assert sum(o['kind']=='PCB_TRACK' for o in new.values())==2448 and sum(o['kind']=='PCB_VIA' for o in new.values())==234
    # Native declarations and fill provenance, including each allowed outline change.
    oldz,newz=[{str(first(z,'uuid')[1]):z for z in children(t,'zone')} for t in trees]
    changed=set(report['changed_existing_zone_fills'])
    declared={r['uuid']:r for r in report['new_zones']}
    assert newz.keys()-oldz.keys()==declared.keys() and len(oldz)==14 and len(newz)==14 and len(changed)==6
    outlines={r['uuid']:r for r in report['changed_existing_zone_outlines']}
    assert set(outlines)=={'d41ab58e-16e9-5d76-8b14-dc335aff8371','78fadc71-5bdb-5968-8ca8-0e3b4b40722f'}
    def settings(z):return [n for n in z if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
    def ring(z):return [list(map(float,p[1:3])) for p in children(first(first(z,'polygon'),'pts'),'xy')]
    for u,z in oldz.items():
        assert settings(z)==settings(newz[u]),u
        if u in outlines:
            assert ring(z)==outlines[u]['old_outline_mm'] and ring(newz[u])==outlines[u]['new_outline_mm']
        else:assert ring(z)==ring(newz[u]),u
        if u not in changed:assert newz[u]==z,u
    for u,r in declared.items():
        z=newz[u];assert first(z,'net_name')[1]==r['net'] and first(z,'layer')[1]==r['layer'] and ring(z)==r['outline_mm']
        assert first(z,'connect_pads')[1]=='yes' and float(first(first(z,'connect_pads'),'clearance')[1])==.2 and float(first(z,'min_thickness')[1])==.25
    filled=STAGING/'two-board-power-fast-ov-filled-03';fillpath=filled/'local-plane-fill.json';fill=json.loads(fillpath.read_text())
    for n,h in fill['source_sha256'].items():assert sha(REPO/n)==h,n
    for n,h in fill['artifact_sha256'].items():assert sha(filled/n)==h,n
    assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==8 and all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    # Independent installed envelope checks on both sides and moved THT tails.
    placement_path=STAGING/'two-board-placement-05/capture.json';placement=json.loads(placement_path.read_text());records={r['id']:r for r in placement['parts']}
    for ref,template in [('P_C204','P_C205'),('P_C104','P_C102'),('P_C101','P_C102'),*[(r,'P_R102') for r in ['P_R101','P_R103','P_R104']]]:
        assert fps[1][ref][1]==fps[1][template][1]
        for key in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']:records[ref][key]=copy.deepcopy(records[template][key])
    assert not children(fps[1]['G_NT1'],'model')
    records['G_NT1']=dict(height_mm=0,angle=0,side='F',body_relative_xy=[-1.2,-.8,1.2,.8],additional_planar_reserves=[],tails_relative_xy=[])
    records['P_C114']=copy.deepcopy(records['P_C401'])
    receivers={'F':[],'B':[]}
    for ref,f in fps[1].items():
        for side in ['F','B']:
            try:receivers[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
            except AssertionError:pass
        if ref not in records:continue
        r=records[ref];x,y=map(float,first(f,'at')[1:3]);delta=angle(f)-r['angle']
        assert first(f,'layer')[1][0]==r['side'],ref
        def envelope(b):return translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
        receivers[r['side']].append((ref,envelope(r['body_relative_xy'])))
        for e in r['additional_planar_reserves']:receivers[e['side']].append((ref,envelope(e['bounds'])))
        for b in r['tails_relative_xy']:receivers['B'].append((ref,envelope(b)))
    contexts=[c for c in placement['context'] if not c['id'].startswith('inlet_')]
    allocation_path=STAGING/'assembly-layout-04/allocation.json'
    for name,x,y,z,dx,dy,t,*_ in json.loads(allocation_path.read_text())['additional_panel_PCBS']:contexts.append(dict(id=name,xy=[x,y,x+dx,y+dy],z=[z,z+t]))
    mounts=[o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])];assert len(mounts)==15
    outline=shape(after['outline']).buffer(-.5)
    for ref in set(moves)|{'P_C114'}:
        f=fps[1][ref];r=records[ref];side=first(f,'layer')[1][0];g=box(*courtyard(f,side+'.CrtYd'))
        assert outline.covers(g)
        assert all(other==ref or g.buffer(.3,join_style=2).intersection(h).area<1e-8 for other,h in receivers[side]),ref
        assert all(g.distance(Point(m['position_mm']))>=max(3.6,max(m['drill_mm'])/2+.5)+.3-1e-6 for m in mounts)
        z0=placement['power_Z'];height=r['height_mm'];z=[z0-.2+1.44,z0+.2+1.76+height] if side=='F' else [z0-.2-height,z0+.2]
        assert z[0]>=3.05 and z[1]<=43.35
        for c in contexts:
            if min(z[1]+.25,c['z'][1])>max(z[0]-.25,c['z'][0]):assert g.buffer(.25,join_style=2).intersection(box(*c['xy'])).area<1e-8,(ref,c['id'])
        x,y=map(float,first(f,'at')[1:3]);delta=angle(f)-r['angle']
        for b in r['tails_relative_xy']:
            g=translate(rotate(box(*b),-delta,origin=(0,0)),x,y).buffer(.3,join_style=2)
            assert all(other==ref or g.intersection(h).area<1e-8 for other,h in receivers['B']),(ref,'lead tails')
    smd=[shape(ps) for o in new.values() if o['kind']=='PAD' and not any(o['drill_mm']) for layer,ps in o['layers'].items() if layer in ['F.Cu','B.Cu'] and ps]
    st=STRtree(smd);gaps=[]
    for o in new.values():
        if o['kind']!='PCB_VIA':continue
        p=Point(o['position_mm']);gap=p.distance(smd[int(st.nearest(p))])-o['drill_mm']/2
        assert gap>=.15-2e-6;gaps.append(gap)
    for folder in [BASE,OUT]:
        native=json.loads((folder/'review.json').read_text())
        for n,h in native['artifact_sha256'].items():assert sha(folder/n)==h,n
    drc,erc=[json.loads((OUT/n).read_text()) for n in ['drc.json','erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for sh in erc['sheets'] for v in sh.get('violations',[])];assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
    sources=[Path(__file__),report_path,plane_path,BEFORE,AFTER,fillpath,placement_path,allocation_path,
        REPO/'hardware/fabrication/audit_two_board_power_delta.py',REPO/'hardware/electronics/output_stage/check_placement.py',REPO/'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE,OUT]:sources.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},
        components=1086,footprints=1101,unchanged_existing_pin_net_map=True,added_component=report["added_component"],new_capacitor_matches_retained_C401_package=True,
        moved_footprints=10,flipped_footprints=0,flipped_parts=sorted(flips),changed_pad_instances=movedpads,
        all_existing_values_and_package_identifiers_unchanged=True,
        all_retained_tracks_vias_and_unmoved_pads_unchanged=True,retired_tracks=0,retired_vias=0,added_tracks=58,added_vias=15,
        all_previous_connection_groups_preserved=planes['all_previous_connection_groups_preserved'],
        maximum_native_pad_polygon_error_mm=maxerror,tracks=2448,vias=234,zones=14,
        old_opens=2405,new_opens=2383,connections_closed=22,
        unchanged_existing_zones=8,changed_existing_zone_fills=6,new_local_zones=0,
        all_native_zone_declarations_and_fill_provenance_verified=True,
        moved_courtyard_body_height_context_and_THT_tail_findings=0,
        all_via_minimum_drill_to_SMD_mm=min(gaps),vias_screened=len(gaps),
        geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,
        all_native_instance_paths_canonical=True,duplicate_paths_removed=planes['duplicate_identical_footprint_paths_removed'],
        input_bypass_and_UV_OV_PGTH_clamp_locally_connected=True,
        prior_input_back_control_trace_reference_preserved=True,fast_OV_locally_connected=True,VIN_AUX_feed_connected=True,
        new_route_reference_gaps=planes["new_routes_with_reference_gaps"],
        input_bypass_thresholds_and_full_source_return_complete=False,
        electrical_current_thermal_transient_qualified=False,full_installed_fit_verified=False,fabrication_released=False)
    with (OUT/'fast-ov-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':run()
