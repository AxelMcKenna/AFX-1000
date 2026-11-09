"""Verify U20 regrouping, six retired internal terminals and retained connectivity."""
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

BASE=STAGING/'two-board-power-buck-enable-native-01'
OUT=STAGING/'two-board-power-u20-local-native-01'
BEFORE=STAGING/'two-board-power-routing-inputs-2508-buck-enable/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2486-u20-local/capture.json'


def orientation(n):
    p=first(n,'at');return float(p[3]) if len(p)>3 else 0


def no_identity(n):
    if not isinstance(n,list):return n
    if n and n[0] in ['net','uuid','path']:return None
    return [v for child in n if (v:=no_identity(child)) is not None]


def run():
    report_path=OUT/'u20-local-change.json';report=json.loads(report_path.read_text())
    before,after=[json.loads(p.read_text()) for p in [BEFORE,AFTER]]
    for d in [report,before,after]:
        for name,h in d['source_sha256'].items():assert sha(REPO/name)==h,name
    trees=[read_sexpr((folder/'power_protection.kicad_pcb').read_text()) for folder in [BASE,OUT]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    retired={'P_J20':{'1':'PWR_AGND'},'P_J21':{'1':'PWR_AGND'},'P_J106':{'1':'PWR_V2V5_AUX','2':'PWR_AGND','3':'PWR_RUN_BEFORE_FAN','4':'PWR_P03_SOURCES_READY'}}
    assert fps[0].keys()-retired.keys()==fps[1].keys() and len(fps[1])==1100
    assert report['retired_connector_pins']==retired
    moves={r['ref']:r for r in report['moves']};assert set(moves)=={'P_U20','P_L20',*[f'P_C{i}' for i in range(200,212)],'P_R200','P_R201','P_R202','P_R203','P_R205','P_R206'}
    substitution=report['bootstrap_replacement'];assert substitution['ref']=='P_C201'
    for ref,old in fps[0].items():
        if ref in retired:continue
        new=fps[1][ref]
        if ref=='P_C201':
            template=copy.deepcopy(fps[0]['P_C221']);first(template,'at')[:]=first(new,'at')
            prop(template,'Reference')[2]=ref
            assert no_identity(template)==no_identity(new),'Replacement differs from the native 0402 template'
            assert first(new,'uuid')==first(old,'uuid')
            assert [first(p,'uuid') for p in children(new,'pad')]==[first(p,'uuid') for p in children(old,'pad')]
            continue
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
                    old_angle=float(old_at[3]) if len(old_at)>3 else 0
                    new_angle=float(new_at[3]) if len(new_at)>3 else 0
                    assert (new_angle-old_angle)%360==r['rotation_added_degrees']%360
                    new_at[:]=old_at
        assert geometry(old)==geometry(restored),ref
    def shell(t):return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','segment','via','arc','net'])]
    assert shell(trees[0])==shell(trees[1])
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');newparts,newpins=read_netlist(OUT/'netlist.xml')
    assert {k:v for k,v in oldpins.items() if k[0] not in retired}==newpins
    assert oldparts.keys()-retired.keys()==newparts.keys() and len(newparts)==1085
    for ref,pins in retired.items():
        assert {pin:net for (r,pin),net in oldpins.items() if r==ref}==pins
    assert len(oldpins)-len(newpins)==6
    assert newpins['G_NT1','1']!=newpins['G_NT1','2'] and newpins['N_J1','2']!=newpins['N_J6','2']
    for node,net in [(('F_U15','4'),'PWR_RUN_BEFORE_FAN'),(('E_U28','11'),'PWR_P03_SOURCES_READY'),(('P_U25','12'),'PWR_P03_SOURCES_READY'),(('E_U1','1'),'PWR_V2V5_AUX'),(('E_J7','1'),'PWR_AGND'),(('F_J201','2'),'PWR_AGND')]:assert newpins[node]==net
    for ref,p in newparts.items():
        for field in ['value','footprint']:
            expected=oldparts['P_C221' if ref=='P_C201' else ref].findtext(field)
            assert p.findtext(field)==expected,(ref,field)
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    removed={u for u,o in old.items() if o.get('ref') in retired}
    for u in removed:
        o=old[u];assert o['kind']=='PAD' and u not in new
        if o.get('group'):assert before['all_groups'][o['group']]==[u]
    def physical(o):return {k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys()-removed:
        assert old[u]['kind']=='PAD' and old[u]['ref'] not in set(moves)|{'P_C201'}
        hits=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
        assert len(hits)==1;aliases[u]=hits[0]
    assert len(aliases)==len(set(aliases.values()))
    oldkeys={aliases.get(u,u) for u in old if u not in removed};assert oldkeys<=new.keys()
    maxerror=0;changed_pads=0
    for uid,o in old.items():
        if uid in removed:continue
        n=new[aliases.get(uid,uid)];ref=o.get('ref')
        if ref not in set(moves)|{'P_C201'}:assert physical(o)==physical(n),uid;continue
        changed_pads+=1
        assert o['kind']==n['kind']=='PAD' and o['ref']==n['ref'] and o['pin']==n['pin'] and o['net']==n['net']
        assert o['drill_mm']==n['drill_mm']==[0,0]
        if ref=='P_C201':
            source=next(v for v in old.values() if v.get('ref')=='P_C221' and v.get('pin')==o['pin'])
            oldxy=list(map(float,first(fps[0]['P_C221'],'at')[1:3]));newxy=moves['P_C201']['new_xy'];angle=0
        else:
            r=moves[ref];source=o;oldxy=r['old_xy'];newxy=r['new_xy'];angle=r['rotation_added_degrees']
        point=translate(rotate(Point(source['position_mm']),-angle,origin=oldxy),newxy[0]-oldxy[0],newxy[1]-oldxy[1])
        assert point.distance(Point(n['position_mm']))<2e-6
        assert (n['orientation_degrees']-source['orientation_degrees'])%360==angle%360
        assert source['layers'].keys()==n['layers'].keys()
        for layer,ps in source['layers'].items():
            if not ps:assert not n['layers'][layer];continue
            g=translate(rotate(shape(ps),-angle,origin=oldxy),newxy[0]-oldxy[0],newxy[1]-oldxy[1])
            error=g.hausdorff_distance(shape(n['layers'][layer]));maxerror=max(maxerror,error);assert error<3e-6
    groups={u:set(g) for g in after['all_groups'].values() for u in g}
    retired_groups=0;preserved_groups=0
    for group in before['all_groups'].values():
        if set(group)&removed:
            assert len(group)==1 and set(group)<=removed;retired_groups+=1;continue
        preserved_groups+=1
        mapped={aliases.get(u,u) for u in group};assert mapped<=groups[next(iter(mapped))]
    assert retired_groups==6
    assert before['zones']==after['zones'] and len(after['zones'])==2
    for o in [v for v in old.values() if v.get('ref') in set(moves)|set(retired)]+[v for v in new.values() if v.get('ref') in moves]:
        for zone in after['zones']:
            assert all(shape(ps).distance(shape(zone['authored_outline']))>2 for ps in o['layers'].values() if ps)
    added=set();lengths=[]
    def endpoint(pair):
        if pair==['_SW_ANCHOR','1']:return [177.5,134],None
        o=next(v for v in new.values() if v.get('ref')==pair[0] and v.get('pin')==pair[1] and v['layers'].get('F.Cu'))
        return o['position_mm'],o['uuid']
    mounts=[o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])];assert len(mounts)==15
    for r in report['routes']:
        path=r['path_mm'];ids=r['segment_uuids'];assert len(ids)==len(path)-1
        start,left=endpoint(r['left']);end,right=endpoint(r['right'])
        assert math.dist(start,path[0])<2e-6 and math.dist(end,path[-1])<2e-6
        line=LineString(path);assert abs(line.length-r['length_mm'])<2e-6 and line.length<=r['maximum_length_mm']
        lengths.append(line.length)
        for u,p,q in zip(ids,path,path[1:]):
            assert u not in oldkeys and u not in added;added.add(u);o=new[u]
            assert o['kind']=='PCB_TRACK' and o['net']==r['net'] and o['width_mm']==r['width_mm']
            assert set(o['layers'])=={'F.Cu'} and math.dist(p,o['position_mm'])<2e-6 and math.dist(q,o['end_mm'])<2e-6
            assert set(ids)<=groups[u]
            if left:assert left in groups[u]
            if right:assert right in groups[u]
            seg=LineString([p,q])
            assert all(seg.distance(Point(m['position_mm']))-max(3.6,max(m['drill_mm'])/2+.5)-r['width_mm']/2>.01-2e-6 for m in mounts)
    assert new.keys()-oldkeys==added and len(added)==22 and len(report['routes'])==17
    sw=next(o for o in new.values() if o.get('ref')=='P_U20' and o.get('pin')=='10')
    assert any(new[u].get('ref')=='P_L20' and new[u].get('pin')=='1' for u in groups[sw['uuid']])
    # Native courtyard envelopes, including actual rotations of the earlier cell.
    placement_path=STAGING/'two-board-placement-05/capture.json';placement=json.loads(placement_path.read_text())
    records={r['id']:r for r in placement['parts']};receivers={'F':[],'B':[]};changed=set(moves)|{'P_C201'}
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
        rec=records['P_C230' if ref=='P_C201' else ref];height=rec['height_mm'];z0=placement['power_Z']
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
    assert len(gaps)==151
    assert sum(o['kind']=='PCB_TRACK' for o in new.values())==2199
    assert sum(o['kind']=='PCB_VIA' for o in new.values())==151
    for folder in [BASE,OUT]:
        review=json.loads((folder/'review.json').read_text())
        for name,h in review['artifact_sha256'].items():assert sha(folder/name)==h
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    assert before['native_uncapped_opens']==2508 and after['native_uncapped_opens']==2486
    paths=[Path(__file__),report_path,BEFORE,AFTER,placement_path,allocation_path,
           REPO/'hardware/electronics/output_stage/check_placement.py',REPO/'hardware/fabrication/audit_two_board_power_delta.py',REPO/'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE,OUT]:paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        components=1085,footprints=1100,unchanged_remaining_pin_net_map=True,sole_part_substitution='P_C201: existing P_C221 100nF 50V 0402 MPN/footprint',
        moved_footprints=20,replaced_footprints=1,changed_native_pad_instances=changed_pads,maximum_native_pad_polygon_error_mm=maxerror,
        all_retained_tracks_vias_unchanged=True,preserved_native_connection_groups=preserved_groups,
        retired_connector_pins=retired,retired_terminal_groups=retired_groups,retired_pad_instances=len(removed),
        existing_local_U23_planes_unchanged=True,return_replacement_qualified=False,legacy_return_bars_require_updated_assembly_design=True,
        local_route_sections=17,added_segments=22,added_vias=0,old_opens=2508,new_opens=2486,connections_closed=16,
        minimum_all_via_drill_to_SMD_mm=min(gaps),vias_screened=151,moved_courtyard_context_findings=0,
        local_route_lengths_mm={r['label']:r['length_mm'] for r in report['routes']},
        geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        power_planes_output_network_and_other_critical_placement_complete=False,
        electrical_thermal_and_manufacturing_qualified=False,full_installed_fit_verified=False,fabrication_released=False)
    with (OUT/'u20-local-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','local_route_lengths_mm']},indent=2))


if __name__=='__main__':run()
