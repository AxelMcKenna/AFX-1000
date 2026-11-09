"""Independently verify AUX PG routing, feedback rework and unchanged returns."""
import copy
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE=STAGING/'two-board-power-aux-ground-native-02'
OUT=STAGING/'two-board-power-aux-pg-native-01'
BEFORE=STAGING/'two-board-power-routing-inputs-2447-aux-ground-02/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2445-aux-pg/capture.json'


def run():
    report_path=OUT/'aux-pg-routing.json'
    report,before,after=[json.loads(p.read_text()) for p in [report_path,BEFORE,AFTER]]
    fidelity=verify_capture(after)
    for d in [report,before,after]:
        for name,h in d['source_sha256'].items():assert sha(REPO/name)==h,name
    for folder in [BASE,OUT]:
        for name,h in json.loads((folder/'review.json').read_text())['artifact_sha256'].items():assert sha(folder/name)==h,name
    trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    assert fps[0].keys()==fps[1].keys() and len(fps[1])==1100
    correct='https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf'
    for ref,old in fps[0].items():
        new=copy.deepcopy(fps[1][ref])
        if ref=='E_U42':
            assert prop(new,'Value')[2]=='SN74LVC3G17DCUR'
            assert prop(new,'Datasheet')[2]==correct
            prop(new,'Datasheet')[2]=prop(old,'Datasheet')[2]
        assert geometry(old)==geometry(new),ref
    def shell(t):return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','segment','via','arc','net','zone'])]
    assert shell(trees[0])==shell(trees[1])
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');parts,pins=read_netlist(OUT/'netlist.xml')
    assert oldpins==pins and parts.keys()==oldparts.keys() and len(parts)==1085
    for ref in parts:
        for field in ['value','footprint']:assert parts[ref].findtext(field)==oldparts[ref].findtext(field),(ref,field)
        if ref=='E_U42':assert parts[ref].findtext('datasheet')==correct
        else:assert parts[ref].findtext('datasheet')==oldparts[ref].findtext('datasheet')
    # Prove only the declared datasheet properties and root revision changed
    # in all schematics and their local symbol libraries.
    schfiles=list(BASE.glob('*.kicad_sch'))+list((BASE/'symbols').glob('*.kicad_sym'))
    metadata_changes=[]
    for path in schfiles:
        rel=path.relative_to(BASE);old=read_sexpr(path.read_text());new=read_sexpr((OUT/rel).read_text())
        def undo(a,b):
            if not isinstance(a,list) or not isinstance(b,list):return
            if a and b and a[0]==b[0]=='property' and a[1]==b[1]=='Datasheet' and a[2]!=b[2]:
                assert 'aup3g17' in a[2] and b[2]==correct
                b[2]=a[2];metadata_changes.append(str(rel));return
            # The embedded/library symbol previously had no Datasheet field.
            if a and b and a[0]==b[0]=='symbol' and len(a)>1 and isinstance(a[1],str) and a[1].endswith('E17_U42'):
                extra=[v for v in children(b,'property') if v[1]=='Datasheet']
                if not any(v[1]=='Datasheet' for v in children(a,'property')):
                    assert len(extra)==1 and extra[0][2]==correct
                    b.remove(extra[0]);metadata_changes.append(str(rel))
            if a and b and a[0]==b[0]=='rev' and rel.name=='power_protection.kicad_sch':
                assert a[1]=='TBP25' and b[1]=='TBP26';b[1]=a[1]
            assert len(a)==len(b),rel
            for x,y in zip(a,b):undo(x,y)
        undo(old,new);assert old==new,rel
    assert len(metadata_changes)==3
    assert (BASE/'expected-circuit.json').read_bytes()==(OUT/'expected-circuit.json').read_bytes()
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    retired={o['uuid']:o for o in report['retired_objects']}
    assert len(retired)==4 and all(old[u]==o for u,o in retired.items())
    assert all(o['net']=='/P_power_supply/AUX_FB' for o in retired.values())
    assert sum(o['kind']=='PCB_TRACK' for o in retired.values())==3
    assert set(retired).isdisjoint(new)
    def physical(o):return {k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys()-retired.keys():
        assert old[u]['kind']=='PAD'
        hits=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
        assert len(hits)==1;aliases[u]=hits[0]
    assert len(aliases)==len(set(aliases.values()))
    retained={aliases.get(u,u) for u in old if u not in retired}
    for u,o in old.items():
        if u not in retired:assert physical(o)==physical(new[aliases.get(u,u)]),u
    groups={u:set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped={aliases.get(u,u) for u in g if u not in retired}
        assert mapped and mapped<=groups[next(iter(mapped))]
    def pad(ref,pin):return next(o for o in new.values() if o.get('ref')==ref and o.get('pin')==pin)
    joins=[(('P_C102','1'),('P_U102','8')),(('P_U102','3'),('P_U101','12'))]
    for a,b in joins:assert pad(*b)['uuid'] in groups[pad(*a)['uuid']]
    added=set()
    for r in report['routes']:
        path=r['path_mm'];assert len(path)==len(r['segment_uuids'])+1
        assert abs(LineString(path).length-r['length_mm'])<2e-6 and r['length_mm']<=r['maximum_length_mm']
        for u,p,q in zip(r['segment_uuids'],path,path[1:]):
            assert u not in added and u not in retained;added.add(u);o=new[u]
            assert o['kind']=='PCB_TRACK' and o['net']==r['net'] and set(o['layers'])=={r['layer']}
            assert o['width_mm']==r['width_mm'] and math.dist(p,o['position_mm'])<2e-6 and math.dist(q,o['end_mm'])<2e-6
    for v in report['vias']:
        u=v['uuid'];assert u not in added and u not in retained;added.add(u);o=new[u]
        assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['position_mm']==v['position_mm']
        assert o['width_mm']==.6 and o['drill_mm']==.3 and o['span']==['F.Cu','B.Cu'] and o['via_type']==4
        assert set(o['layers'])==set(after['copper_layers'])
    assert added==new.keys()-retained and len(report['routes'])==7
    assert sum(len(r['segment_uuids']) for r in report['routes'])==10 and len(report['vias'])==3
    # Every through drill, including the new and relocated ones, clears SMD lands.
    smd=[shape(ps) for o in new.values() if o['kind']=='PAD' and not any(o['drill_mm'])
         for l,ps in o['layers'].items() if l in ['F.Cu','B.Cu'] and ps]
    tree=STRtree(smd);gaps=[]
    for o in new.values():
        if o['kind']=='PCB_VIA':
            p=Point(o['position_mm']);gap=p.distance(smd[int(tree.nearest(p))])-o['drill_mm']/2
            assert gap>=.15-2e-6;gaps.append(gap)
    assert len(gaps)==192
    zones=[{z['uuid']:z for z in c['zones']} for c in [before,after]]
    authored=[{str(first(z,'uuid')[1]):z for z in children(t,'zone')} for t in trees]
    assert zones[0].keys()==zones[1].keys() and len(zones[1])==8
    refilled=set(report['refilled_zone_uuids'])
    for u in zones[0]:
        def settings(z):return [n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
        assert settings(authored[0][u])==settings(authored[1][u])
        if u not in refilled:assert authored[0][u]==authored[1][u] and zones[0][u]==zones[1][u]
    labelmap={z['uuid']:z['label'] for z in json.loads((BASE/'aux-ground-routing.json').read_text())['zones']}
    ground=groups[pad('P_U102','9')['uuid']]
    expected={('P_U102','4'),('P_U102','9'),('P_C113','2'),('P_C110','2'),('P_R109','2'),('P_C106','2'),('P_C107','2')}
    assert {(new[u].get('ref'),new[u].get('pin')) for u in ground if new[u]['kind']=='PAD'}==expected
    plane_checks=[]
    for u,label in labelmap.items():
        z=zones[1][u];g=shape(z['polygons']);assert g.is_valid and g.geom_type=='Polygon' and len(z['polygons'])==1
        def contacts(objects,zone):
            poly=shape(zone['polygons']);layer=zone['layer']
            return {u for u,o in objects.items() if o['net']=='PWR_AGND' and o['layers'].get(layer)
                    and o['kind'] in ['PAD','PCB_VIA'] and poly.distance(shape(o['layers'][layer]))<.0015}
        assert contacts(old,zones[0][u])==contacts(new,z)
        copper=[o for o in new.values() if o['layers'].get(z['layer']) and o['net']!='PWR_AGND']
        gap=min(g.distance(shape(o['layers'][z['layer']])) for o in copper);assert gap>=.1985,(label,gap)
        plane_checks.append(dict(label=label,layer=z['layer'],area_mm2=g.area,unchanged_direct_ground_contacts=True,
                                 single_contiguous_polygon=True,minimum_foreign_copper_gap_mm=gap))
    # Independent multilayer GND-land cut preserves input/output return separation.
    cut=shape(pad('P_U102','4')['layers']['F.Cu']).buffer(.002);nodes=[]
    for layer in after['copper_layers']:
        polys=[shape(new[u]['layers'][layer]) for u in ground if new[u]['layers'].get(layer)]
        polys += [shape(z['polygons']) for u,z in zones[1].items() if u in labelmap and z['layer']==layer]
        if not polys:continue
        merged=unary_union([g.buffer(.000002) for g in polys])
        if layer=='F.Cu':merged=merged.difference(cut)
        nodes.extend((layer,p) for p in ([merged] if merged.geom_type=='Polygon' else list(merged.geoms)) if p.area>1e-10)
    parent=list(range(len(nodes)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for u in ground:
        o=new[u]
        if o['kind']!='PCB_VIA':continue
        hits=[i for i,(l,g) in enumerate(nodes) if o['layers'].get(l) and g.intersection(shape(o['layers'][l])).area>1e-8]
        assert len(hits)==len(after['copper_layers'])
        for i in hits[1:]:parent[root(i)]=root(hits[0])
    def node_for(ref,pin):
        o=pad(ref,pin);hits=[i for i,(l,g) in enumerate(nodes) if o['layers'].get(l) and g.intersection(shape(o['layers'][l])).area>1e-8]
        assert len(hits)==1;return root(hits[0])
    left=node_for('P_U102','9');right=node_for('P_C106','2');assert left!=right
    assert all(node_for(*p)==left for p in [('P_C113','2'),('P_C110','2'),('P_R109','2')])
    assert node_for('P_C107','2')==right
    fb=pad('P_U102','2')['net'];tracks=[o for o in new.values() if o['kind']=='PCB_TRACK' and o['net']==fb]
    fbvias=[o for o in new.values() if o['kind']=='PCB_VIA' and o['net']==fb];assert len(tracks)==5 and len(fbvias)==2
    projection=unary_union([LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2) for o in tracks])
    for o in fbvias:projection=projection.difference(Point(o['position_mm']).buffer(.515))
    thermal=shape(zones[1][next(u for u,l in labelmap.items() if l=='AUX-thermal-reference')]['polygons'])
    uncovered=projection.difference(thermal.buffer(.0015)).area;assert uncovered<1e-6,uncovered
    fillpath=STAGING/'two-board-power-aux-pg-filled-01/local-plane-fill.json';fill=json.loads(fillpath.read_text())
    assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==5 and all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    for name,h in fill['source_sha256'].items():assert sha(REPO/name)==h,name
    for name,h in fill['artifact_sha256'].items():assert sha(fillpath.parent/name)==h,name
    drc,erc=[json.loads((OUT/n).read_text()) for n in ['drc.json','erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
    assert before['native_uncapped_opens']==2447 and after['native_uncapped_opens']==2445
    assert sum(o['kind']=='PCB_TRACK' for o in new.values())==2300
    paths=[Path(__file__),report_path,BEFORE,AFTER,fillpath,BASE/'aux-ground-audit.json',
           REPO/'hardware/fabrication/verify_native_zone_unfracture.py',REPO/'hardware/fabrication/audit_two_board_power_delta.py']
    for folder in [BASE,OUT]:paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        old_opens=2447,new_opens=2445,connections_closed=2,declared_new_terminal_joins=joins,
        unchanged_complete_pin_net_map=True,all_component_poses_values_and_lands_unchanged=True,
        E_U42_datasheet_corrected_in_PCB_schematic_embedded_and_local_library=True,
        all_retained_ordinary_copper_unchanged=True,retired_FB_tracks=3,retired_FB_vias=1,
        added_tracks=10,added_vias=3,tracks=2300,vias=192,zones=8,
        all_previous_connection_groups_preserved=len(before['all_groups']),
        all_authored_zone_settings_and_outlines_unchanged=True,unchanged_native_zone_fills=5,
        U20_and_U23_zones_and_contacts_unchanged=True,local_plane_checks=plane_checks,
        input_output_returns_separate_after_multilayer_GND_land_cut=True,
        AUX_ground_group_has_only_original_seven_pads=True,
        full_FB_trace_projection_uncovered_mm2=uncovered,zone_unfracture_fidelity=fidelity,
        all_via_minimum_drill_to_SMD_mm=min(gaps),geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,
        upstream_VIN_source_and_full_AUX_distribution_complete=False,
        full_RUN_net_complete=False,actual_current_startup_thermal_qualified=False,fabrication_released=False)
    with (OUT/'aux-pg-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['new_opens','connections_closed','all_previous_connection_groups_preserved','all_via_minimum_drill_to_SMD_mm','full_FB_trace_projection_uncovered_mm2']}))

if __name__=='__main__':run()
