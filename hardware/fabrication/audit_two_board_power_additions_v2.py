"""Independent additive routing audit, including KiCad 10 through vias.

Checks existing geometry, circuit and physical connection groups, then measures
declared new tracks/vias and the provisional mounting reserves. Native DRC/ERC
remain mandatory; this does not qualify loaded behavior or installed mechanics.
"""
import argparse
import json
import math
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.native_two_board_power import partition


def run():
    ap=argparse.ArgumentParser()
    for key in ['base','candidate','before_capture','after_capture','record']:
        ap.add_argument('--'+key.replace('_','-'),required=True)
    args=ap.parse_args()
    base,out=STAGING/args.base,STAGING/args.candidate
    cap_paths=[STAGING/n/'capture.json' for n in [args.before_capture,args.after_capture]]
    before,after=[json.loads(p.read_text()) for p in cap_paths]
    record_path=out/args.record;data=json.loads(record_path.read_text())
    paths=[Path(__file__),record_path,*cap_paths]
    for d in [before,after,data]:
        for name,h in d['source_sha256'].items():
            p=REPO/name;assert sha(p)==h,name
    for cap,directory in [(before,base),(after,out)]:
        p=directory/'power_protection.kicad_pcb'
        assert cap['source_sha256'][str(p)]==sha(p)
    oldtree,newtree=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [base,out]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in [oldtree,newtree]]
    assert fps[0].keys()==fps[1].keys()
    assert all(geometry(f)==geometry(fps[1][ref]) for ref,f in fps[0].items())
    def shell(tree):
        return [n for n in tree if not (isinstance(n,list) and n and n[0] in ['footprint','net','segment','via','arc'])]
    assert shell(oldtree)==shell(newtree)
    parts,pins=read_netlist(base/'netlist.xml');newparts,newpins=read_netlist(out/'netlist.xml')
    assert parts.keys()==newparts.keys() and partition(pins)==partition(newpins)
    assert all(p.findtext(f)==newparts[ref].findtext(f) for ref,p in parts.items() for f in ['value','footprint'])
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    # Some authored module lands have no UUID field. KiCad generates transient
    # IDs on load. The complete authored footprint equality above is required;
    # only uniquely matching native PAD geometry may receive an identity alias.
    def pad_shape(o):return {k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for uid in old.keys()-new.keys():
        o=old[uid];assert o['kind']=='PAD'
        matches=[u for u,p in new.items() if u not in old and pad_shape(p)==pad_shape(o)]
        assert len(matches)==1,(uid,matches);aliases[uid]=matches[0]
    assert len(set(aliases.values()))==len(aliases)
    old={aliases.get(uid,uid):dict(o,uuid=aliases.get(uid,uid)) for uid,o in old.items()}
    assert set(old)<=set(new)
    def physical(o):return {k:v for k,v in o.items() if k!='group'}
    for uid,o in old.items():assert physical(o)==physical(new[uid]),uid
    # Compare native full physical groups, not a capped DRC-item list.
    memberships={uid:set(group) for group in after['all_groups'].values() for uid in group}
    for group in before['all_groups'].values():
        translated={aliases.get(u,u) for u in group}
        assert translated<=memberships[aliases.get(group[0],group[0])],group[0]
    mounts=[o for o in old.values() if o['kind']=='PAD' and o.get('npth') and
            (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts)==15
    def reserve_margin(line,width):
        return min((line.distance(Point(m['position_mm']))-max(3.6,max(m['drill_mm'])/2+.5)-width/2,m['ref']) for m in mounts)
    declared=set();rows=[];via_count=0
    for route in data['routes']:
        net=route['net'];pu,qu=route['endpoint_pad_uuids']
        assert new[pu]['net']==new[qu]['net']==net
        assert [[new[u]['ref'],new[u]['pin']] for u in [pu,qu]]==route['endpoints']
        assert qu in memberships[pu],route['endpoints']
        assert qu not in before['all_groups'][old[pu]['group']]
        routepaths=route.get('paths') or [dict(layer=route['layer'],path_mm=route['path_mm'],segment_uuids=route['segment_uuids'])]
        length=0;minimum=(math.inf,'')
        for path in routepaths:
            layer=path['layer'];xy=path['path_mm'];ids=path['segment_uuids']
            assert layer in ['F.Cu','B.Cu'] and len(ids)==len(xy)-1
            for uid,p,q in zip(ids,xy,xy[1:]):
                assert uid not in declared and uid not in old;declared.add(uid)
                o=new[uid];assert o['kind']=='PCB_TRACK' and o['net']==net
                assert set(o['layers'])=={layer} and abs(o['width_mm']-.2)<1e-7
                assert math.dist(o['position_mm'],p)<2e-6 and math.dist(o['end_mm'],q)<2e-6
                length+=math.dist(o['position_mm'],o['end_mm'])
                minimum=min(minimum,reserve_margin(LineString([o['position_mm'],o['end_mm']]),o['width_mm']))
        if route.get('via'):
            v=route['via'];uid=v['uuid'];assert uid not in old and uid not in declared;declared.add(uid)
            o=new[uid];assert o['kind']=='PCB_VIA' and o['net']==net
            assert o['width_mm']==.6 and o['drill_mm']==.3 and o['span']==['F.Cu','B.Cu'] and o['via_type']==4
            assert math.dist(o['position_mm'],v['position_mm'])<2e-6
            minimum=min(minimum,reserve_margin(Point(o['position_mm']),o['width_mm']));via_count+=1
        assert minimum[0]>.01-2e-6,(route['endpoints'],minimum)
        assert abs(length-route['length_mm'])<2e-5
        rows.append(dict(net=net,endpoints=route['endpoints'],physical_endpoints_connected=True,length_mm=length,
            minimum_new_copper_to_mount_reserve_mm=minimum[0],nearest_mount=minimum[1]))
    assert set(new)-set(old)==declared
    drc=json.loads((out/'drc.json').read_text());erc=json.loads((out/'erc.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for sheet in erc['sheets'] for v in sheet.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    review=json.loads((out/'review.json').read_text());assert review['opens']==after['native_uncapped_opens']
    assert before['native_uncapped_opens']-after['native_uncapped_opens']>=len(rows)
    for d in [base,out]:paths.extend(d/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    paths.extend(REPO/'hardware/fabrication'/n for n in ['audit_two_board_power_delta.py','native_two_board_power.py','integrate_two_board_signal.py'])
    # Exhaustive native-geometry audit: no spatial index/search-radius reuse
    # from the router, and same-net drills/SMD lands remain obstacles here.
    smd=[];drills=[];copper=[]
    for uid,o in new.items():
        for layer,polys in o['layers'].items():
            if not polys:continue
            shape=unary_union([Polygon(p['outer'],p['holes']) for p in polys])
            copper.append((uid,o['net'],layer,shape))
            if o['kind']=='PAD' and not any(o['drill_mm']) and layer in ['F.Cu','B.Cu']:
                smd.append((uid,shape))
        d=o.get('drill_mm',0);radius=max(d)/2 if isinstance(d,list) else d/2
        if radius:drills.append((uid,o['position_mm'],radius))
    via_rows=[]
    for uid in declared:
        o=new[uid]
        if o['kind']!='PCB_VIA':continue
        assert set(o['layers'])==set(after['copper_layers'])
        pt=Point(o['position_mm']);radius=o['width_mm']/2;hole=o['drill_mm']/2
        smd_min=min((pt.distance(g)-radius,u) for u,g in smd)
        drill_min=min((math.dist(o['position_mm'],p)-hole-r,u) for u,p,r in drills if u!=uid)
        copper_min=min((pt.distance(g)-radius,u,l) for u,net,l,g in copper if net!=o['net'])
        assert smd_min[0]>=.01-2e-6,(uid,smd_min)
        assert drill_min[0]>=.26-2e-6,(uid,drill_min)
        assert copper_min[0]>=.21-2e-6,(uid,copper_min)
        via_rows.append(dict(uuid=uid,position_mm=o['position_mm'],net=o['net'],
            copper_edge_to_nearest_SMD_mm=smd_min[0],nearest_SMD_pad_uuid=smd_min[1],
            drill_edge_to_nearest_SMD_mm=smd_min[0]+radius-hole,
            drill_edge_to_nearest_drill_mm=drill_min[0],nearest_drill_uuid=drill_min[1],
            copper_edge_to_foreign_copper_mm=copper_min[0],nearest_foreign_copper_uuid=copper_min[1],
            nearest_foreign_copper_layer=copper_min[2]))
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        unchanged_footprints=len(fps[0]),unchanged_electrical_parts=len(parts),unchanged_schematic_pin_partition=True,
        unchanged_original_native_objects=len(old),native_generated_pad_IDs_matched_by_unique_geometry=len(aliases),
        preserved_native_connection_groups=len(before['all_groups']),
        added_segments=len(declared)-via_count,added_through_vias=via_count,verified_routes=len(rows),connection_evidence=rows,
        through_via_native_enum=4,exhaustive_via_clearance_evidence=via_rows,
        same_net_hole_and_SMD_clearance_included=True,
        provisional_mount_reserves_checked=len(mounts),old_opens=before['native_uncapped_opens'],new_opens=after['native_uncapped_opens'],
        geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        loaded_timing_noise_return_qualified=False,installed_fastener_geometry_qualified=False,stack_approved=False,fabrication_released=False)
    with (out/'additive-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','connection_evidence','exhaustive_via_clearance_evidence']},indent=2))


if __name__=='__main__':run()
