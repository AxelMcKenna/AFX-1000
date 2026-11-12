"""Verify the single TBP73 AUX join without changing planes or other connectivity."""
import json,math
from pathlib import Path
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,read_netlist
from hardware.fabrication.plan_two_board_aux_local_distribution_v6 import anchored_fields,newly_added_copper_referenced
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
from hardware.cad.two_board_installation_06.workflow_adapter.pcb_freshness import snapshot,compare

BASE=STAGING/'two-board-power-aux-ground-reuse-native-01'
OUT=STAGING/'two-board-power-aux-local-distribution-native-03'
BEFORE=STAGING/'two-board-power-routing-inputs-aux-ground-reuse-01/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-aux-local-distribution-03/capture.json'

def run():
    paths=[BEFORE,AFTER,OUT/'aux-local-distribution-routing.json',OUT/'review.json']
    before,after,routing,native=[json.loads(p.read_text()) for p in paths]
    for path,data in zip(paths,[before,after,routing,native]):
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/p
                assert sha(p)==h,(path,name)
    fidelity=verify_capture(after)
    assert len(routing['routes'])==1 and routing['added_tracks']==2
    assert not routing['vias'] and not routing['refilled_existing_zones']
    assert native['opens']==after['native_uncapped_opens']==1936
    assert before['native_uncapped_opens']==1937
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    assert not compare(snapshot(BASE/'power_protection.kicad_pcb'),snapshot(OUT/'power_protection.kicad_pcb'))
    tracks={u for r in routing['routes'] for u in r['segment_uuids']}
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys():
        assert old[u]['kind']=='PAD'
        matches=[v for v in new.keys()-old.keys()-tracks if physical(old[u])==physical(new[v])]
        assert len(matches)==1,u
        aliases[matches[0]]=u
    assert set(aliases)==new.keys()-old.keys()-tracks
    for o in after['objects']:
        o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
    after['all_groups']={aliases.get(g,g):[aliases.get(u,u) for u in members] for g,members in after['all_groups'].items()}
    new={o['uuid']:o for o in after['objects']}
    assert new.keys()-old.keys()==tracks and not old.keys()-new.keys()
    assert all(physical(old[u])==physical(new[u]) for u in old)
    assert before['zones']==after['zones'] and len(after['zones'])==47
    route=routing['routes'][0];groups=route['source_groups'];expected={frozenset(g) for g in before['all_groups'].values()};merged=set()
    for gid in groups:
        members=before['all_groups'][gid];assert all(old[u]['net']=='PWR_V2V5_AUX' for u in members)
        expected.remove(frozenset(members));merged.update(members)
    expected.add(frozenset(merged));actual={frozenset(set(g)-tracks) for g in after['all_groups'].values()}-{frozenset()}
    assert expected==actual
    assert {new[u]['group'] for u in merged|tracks}.__len__()==1
    endpoints={f"{old[u]['ref']}:{old[u]['pin']}" for u in merged if old[u]['kind']=='PAD'}
    assert endpoints=={'N_U35:14','N_U15:3'},endpoints
    for uid,(a,b) in zip(route['segment_uuids'],zip(route['path_mm'],route['path_mm'][1:])):
        o=new[uid];assert o['kind']=='PCB_TRACK' and o['net']=='PWR_V2V5_AUX' and list(o['layers'])==['F.Cu'] and o['width_mm']==.3
        assert math.dist(a,o['position_mm'])<1e-6 and math.dist(b,o['end_mm'])<1e-6
    fields,_=anchored_fields(after)
    main=next(o['group'] for o in after['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    old_aux=unary_union([shape(o['layers']['F.Cu']) for o in old.values() if o['net']=='PWR_V2V5_AUX' and o['layers'].get('F.Cu')])
    added=unary_union([shape(new[u]['layers']['F.Cu']) for u in tracks]).difference(old_aux)
    assert fields['In1.Cu',main].covers(added),'New native track copper lacks main-ground reference'
    assert newly_added_copper_referenced(route['path_mm'],fields['In1.Cu',main],old_aux)
    main_contacts=unary_union([shape(o['layers']['In1.Cu']) for o in after['objects'] if o['net']=='PWR_AGND' and o['group']==main and o['layers'].get('In1.Cu')])
    strict_polys=[Polygon(p['outer'],p['holes']) for z in after['zones'] if z['layer']=='In1.Cu' and z['net']=='PWR_AGND' for p in z['polygons'] if Polygon(p['outer'],p['holes']).intersection(main_contacts).area>1e-9]
    assert unary_union(strict_polys).covers(added),'Reference needs direct unbuffered main-ground contact'

    assert read_netlist(BASE/'netlist.xml')[1]==read_netlist(OUT/'netlist.xml')[1]
    erc=json.loads((OUT/'erc.json').read_text());issues=[v for s in erc['sheets'] for v in s.get('violations',[])];assert len(issues)==2 and all(v['severity']=='warning' for v in issues) and not erc['ignored_checks']
    sources=[Path(__file__),*paths,BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',BASE/'netlist.xml',OUT/'netlist.xml',OUT/'erc.json',REPO/'hardware/fabrication/plan_two_board_aux_local_distribution_v6.py',REPO/'hardware/fabrication/verify_native_zone_unfracture.py',REPO/'hardware/cad/two_board_installation_06/workflow_adapter/pcb_freshness.py']
    result={'source_sha256':{str(p.relative_to(REPO)):sha(p) for p in sources},'opens':1936,'closed_connections':1,'added_tracks':2,'added_vias':0,'unchanged_plane_fills':47,'all_original_copper_and_poses_preserved':True,'only_declared_group_merge':True,'joined_terminals':sorted(endpoints),'new_native_copper_reference_gap_mm2':added.difference(fields['In1.Cu',main]).area,'direct_unbuffered_main_ground_anchor_verified':True,'fidelity':fidelity,'source_feed_or_decoupling_qualified':False,'fabrication_released':False}
    (OUT/'final-review.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['source_sha256','fidelity']})
if __name__=='__main__':run()
