"""Verify local via relocation, every prior connection, and all via/SMD gaps."""
import json
import math
from collections import Counter
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.native_two_board_power import partition

BASE=STAGING/'two-board-power-routed-native-07'
OUT=STAGING/'two-board-power-routed-native-08'
BEFORE=STAGING/'two-board-power-routing-inputs-2554/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2554-via-repair/capture.json'


def run():
    before,after=[json.loads(p.read_text()) for p in [BEFORE,AFTER]]
    rp=OUT/'via-repair.json';record=json.loads(rp.read_text())
    for d in [before,after,record]:
        for p,h in d['source_sha256'].items():assert sha(REPO/p)==h,p
    for d,folder in [(before,BASE),(after,OUT)]:assert d['source_sha256'][str(folder/'power_protection.kicad_pcb')]==sha(folder/'power_protection.kicad_pcb')
    trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    assert fps[0].keys()==fps[1].keys() and all(geometry(f)==geometry(fps[1][r]) for r,f in fps[0].items())
    def shell(t):return [n for n in t if not (isinstance(n,list) and n and n[0] in ['footprint','net','segment','via','arc'])]
    assert shell(trees[0])==shell(trees[1])
    parts,pins=read_netlist(BASE/'netlist.xml');newparts,newpins=read_netlist(OUT/'netlist.xml')
    assert parts.keys()==newparts.keys() and partition(pins)==partition(newpins)
    assert all(p.findtext(f)==newparts[r].findtext(f) for r,p in parts.items() for f in ['value','footprint'])
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    def physical(o):return {k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys():
        assert old[u]['kind']=='PAD'
        hits=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
        assert len(hits)==1;aliases[u]=hits[0]
    assert len(set(aliases.values()))==len(aliases)
    old={aliases.get(u,u):dict(o,uuid=aliases.get(u,u)) for u,o in old.items()}
    moves={r['uuid']:r for r in record['relocations']};assert len(moves)==10 and not record['deferred']
    def shape(ps):return unary_union([Polygon(p['outer'],p['holes']) for p in ps])
    for u,o in old.items():
        assert u in new
        if u not in moves:assert physical(o)==physical(new[u]),u;continue
        r=moves[u];v=new[u]
        assert o['kind']==v['kind']=='PCB_VIA' and o['net']==v['net']==r['net']
        assert {k:x for k,x in physical(o).items() if k not in ['position_mm','layers']}=={k:x for k,x in physical(v).items() if k not in ['position_mm','layers']}
        assert math.dist(o['position_mm'],r['old_position_mm'])<2e-6 and math.dist(v['position_mm'],r['new_position_mm'])<2e-6
        assert math.dist(o['position_mm'],v['position_mm'])<=2.5
        dx,dy=[b-a for a,b in zip(o['position_mm'],v['position_mm'])]
        assert o['layers'].keys()==v['layers'].keys()
        for layer,ps in o['layers'].items():assert translate(shape(ps),dx,dy).hausdorff_distance(shape(v['layers'][layer]))<3e-6
    memberships={u:set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped={aliases.get(u,u) for u in g};assert mapped<=memberships[aliases.get(g[0],g[0])],g[0]
    added=set();bridge_lengths=[]
    mounts=[o for o in new.values() if o['kind']=='PAD' and o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts)==15
    for u,r in moves.items():
        v=new[u]
        assert all(c['uuid'] in memberships[u] for c in r['old_contact_objects'])
        for path in r['paths']:
            xy=path['path_mm'];ids=path['segment_uuids'];assert len(ids)==len(xy)-1
            assert path['layer'] in {c['layer'] for c in r['old_contact_objects']}
            length=0
            for sid,p,q in zip(ids,xy,xy[1:]):
                assert sid not in old and sid not in added;added.add(sid);s=new[sid]
                assert s['kind']=='PCB_TRACK' and s['net']==r['net'] and s['width_mm']==.2 and set(s['layers'])=={path['layer']}
                assert math.dist(s['position_mm'],p)<2e-6 and math.dist(s['end_mm'],q)<2e-6
                assert sid in memberships[u]
                line=LineString([s['position_mm'],s['end_mm']]);length+=line.length
                assert all(line.distance(Point(m['position_mm']))-max(3.6,max(m['drill_mm'])/2+.5)-.1>.01-2e-6 for m in mounts)
            assert length<=3.5+2e-6;bridge_lengths.append(length)
    assert set(new)-set(old)==added and len(added)==record['added_segments']
    smd=[];drills=[];copper=[]
    for u,o in new.items():
        for layer,ps in o['layers'].items():
            if not ps:continue
            g=shape(ps);copper.append((u,o['net'],layer,g))
            if o['kind']=='PAD' and not any(o['drill_mm']) and layer in ['F.Cu','B.Cu']:smd.append((u,g))
        d=o.get('drill_mm',0);radius=max(d)/2 if isinstance(d,list) else d/2
        if radius:drills.append((u,o['position_mm'],radius))
    via_rows=[]
    for u,v in new.items():
        if v['kind']!='PCB_VIA':continue
        pt=Point(v['position_mm']);rad=v['width_mm']/2;hole=v['drill_mm']/2
        sg=min((pt.distance(g)-hole,p) for p,g in smd)
        hg=min((math.dist(v['position_mm'],p)-hole-r,h) for h,p,r in drills if h!=u)
        cg=min((pt.distance(g)-rad,p,l) for p,net,l,g in copper if net!=v['net'])
        assert sg[0]>=.15-2e-6,(u,'SMD',sg)
        assert hg[0]>=.25-2e-6,(u,'hole',hg)
        # Foreign native polygons are conservative outside approximations of
        # <=.001mm error. Native DRC below must separately satisfy exact .20mm.
        assert cg[0]>=.199-2e-6,(u,'copper',cg)
        if u in moves:
            assert sg[0]>=.16-2e-6 and hg[0]>=.26-2e-6 and cg[0]>=.21-2e-6
            assert all(pt.distance(Point(m['position_mm']))-max(3.6,max(m['drill_mm'])/2+.5)-rad>.01-2e-6 for m in mounts)
        via_rows.append(dict(uuid=u,relocated=u in moves,drill_to_SMD_mm=sg[0],nearest_SMD_uuid=sg[1],
            hole_to_hole_mm=hg[0],nearest_hole_uuid=hg[1],via_to_foreign_copper_mm=cg[0],nearest_foreign_uuid=cg[1],nearest_foreign_layer=cg[2]))
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    review=json.loads((OUT/'review.json').read_text())
    assert before['native_uncapped_opens']==after['native_uncapped_opens']==review['opens']==2554
    paths=[Path(__file__),BEFORE,AFTER,rp,REPO/'hardware/fabrication/audit_two_board_power_delta.py',REPO/'hardware/fabrication/native_two_board_power.py']
    for folder in [BASE,OUT]:paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},unchanged_footprints=len(fps[0]),
        unchanged_electrical_parts=len(parts),unchanged_schematic_pin_partition=True,preserved_native_connection_groups=len(before['all_groups']),
        unchanged_native_objects_except_declared_vias=len(old)-len(moves),relocated_vias=len(moves),added_segments=len(added),
        copper_counts=dict(Counter(o['kind'] for o in new.values() if o['kind']!='PAD')),
        maximum_relocation_mm=max(r['displacement_mm'] for r in moves.values()),maximum_reconnect_path_mm=max(bridge_lengths),
        all_vias_screened=len(via_rows),minimum_drill_to_SMD_mm=min(r['drill_to_SMD_mm'] for r in via_rows),
        minimum_hole_to_hole_mm=min(r['hole_to_hole_mm'] for r in via_rows),minimum_via_to_foreign_polygon_mm=min(r['via_to_foreign_copper_mm'] for r in via_rows),
        foreign_polygon_outside_error_mm=.001,exact_native_clearance_rule_mm=.20,
        via_clearance_evidence=via_rows,remaining_via_drills_in_SMD_lands=0,
        old_opens=2554,new_opens=2554,geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        loaded_noise_timing_or_assembly_process_qualified=False,stack_approved=False,fabrication_released=False)
    with (OUT/'via-repair-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','via_clearance_evidence']},indent=2))


if __name__=='__main__':run()
