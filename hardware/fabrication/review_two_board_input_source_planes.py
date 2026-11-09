"""Independent native connectivity, plane contacts and reference review of TBP28."""
import json,math,copy
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE=STAGING/'two-board-power-input-controls-native-02'
OUT=STAGING/'two-board-power-input-source-native-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2440-input-controls/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2427-input-source/capture.json'

def run():
    rp=OUT/'input-source-routing.json'
    before,after,report=[json.loads(p.read_text()) for p in [BEFORE,AFTER,rp]]
    for d in [before,after,report]:
        for p,h in d['source_sha256'].items():assert sha(REPO/p)==h,p
    fidelity=verify_capture(after)
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    aliases={}
    for uid in old.keys()-new.keys():
        o=old[uid]
        if o['kind']=='PCB_TRACK':
            assert uid in {r['uuid'] for r in report['retired_tracks']}
            continue
        assert o['kind']=='PAD'
        candidates=[q for v,q in new.items() if v not in old and q['kind']=='PAD' and q.get('ref')==o.get('ref') and q.get('pin')==o.get('pin')]
        # Unnumbered LFPAK paste apertures have no copper, and do not belong
        # to any electrical group. Numbered pins must map unambiguously.
        if not o.get('pin'):
            assert not o['group'] and not any(o['layers'].values())
            continue
        assert len(candidates)==1,(o.get('ref'),o.get('pin'))
        aliases[uid]=candidates[0]['uuid']
    groups={u:set(g) for g in after['all_groups'].values() for u in g}
    retired={r['uuid'] for r in report['retired_tracks']}
    for g in before['all_groups'].values():
        mapped={aliases.get(u,u) for u in g if u not in retired}
        assert mapped and mapped<=groups[next(iter(mapped))]
    def pad(r,p):return next(o for o in new.values() if o.get('ref')==r and o.get('pin')==p)
    intended={
        'gate':{('P_U101','3'),('P_Q101','4'),('P_Q102','3')},
        'driver':{('P_U101','4'),('P_Q102','1')},
        'source':{('P_Q101','1'),('P_Q101','2'),('P_Q101','3'),('P_Q102','2')},
        'input':{('P_Q101','5'),('P_U101','1'),('P_U101','2')},
        'output':{('P_U101','17'),('P_U101','18'),('P_C104','1'),('P_C103','1')},
        'ground':{('P_U101','8'),('P_U101','25'),('P_C105','2'),('P_R107','2'),('P_C103','2'),('P_C104','2')},
        'aux-ground':{('P_U102','4'),('P_U102','9'),('P_C106','2'),('P_C107','2'),('P_C113','2'),('P_C110','2'),('P_R109','2')},
    }
    verified={}
    for name,pins in intended.items():
        ref,pin=next(iter(pins));g=groups[pad(ref,pin)['uuid']]
        assert {(new[u].get('ref'),new[u].get('pin')) for u in g if new[u]['kind']=='PAD'}==pins,name
        verified[name]=g
    assert len({tuple(sorted(g)) for g in verified.values()})==len(verified)
    assert before['native_uncapped_opens']==2440 and after['native_uncapped_opens']==2427
    previous_zones={z['uuid']:z for z in before['zones']};zones={z['uuid']:z for z in after['zones']}
    changed={r['uuid'] for r in report['changed_existing_zones']}
    assert len(changed)==3 and len(zones)==13
    assert all(zones[u]==z for u,z in previous_zones.items() if u not in changed)
    plane_checks=[]
    for u,z in zones.items():
        g=shape(z['polygons'])
        assert g.is_valid and g.geom_type=='Polygon' and len(z['polygons'])==1,u
        direct=[o for o in new.values() if o['layers'].get(z['layer']) and o['net']==z['net'] and g.distance(shape(o['layers'][z['layer']]))<.0015]
        record=dict(uuid=u,layer=z['layer'],net=z['net'],area_mm2=g.area,
                    directly_contacted_pads=sorted([o['ref'],o['pin']] for o in direct if o['kind']=='PAD'),
                    directly_contacted_vias=sorted(o['uuid'] for o in direct if o['kind']=='PCB_VIA'))
        if u in changed or u not in previous_zones:
            gap=min(g.distance(shape(o['layers'][z['layer']])) for o in new.values() if o['net']!=z['net'] and o['layers'].get(z['layer']))
            assert gap>=.1985,(u,gap)
            record['minimum_captured_foreign_copper_gap_mm']=gap
        plane_checks.append(record)
    expected_new_pads={'source-pin-bank':{('P_Q101','1'),('P_Q101','2'),('P_Q101','3')},
        'blocking-FET-to-IN':intended['input'],'OUT-to-ceramic':{('P_U101','17'),('P_U101','18')}}
    for r in report['zones']:
        c=next(q for q in plane_checks if q['uuid']==r['uuid'])
        assert {tuple(p) for p in c['directly_contacted_pads']}==expected_new_pads[r['label']],r['label']
    # Original AUX group stays electrically separate, and the established
    # single GND-land joining topology must survive the small input-plane refill.
    aux=verified['aux-ground'];cut=shape(pad('P_U102','4')['layers']['F.Cu']).buffer(.002)
    auxzones={'d0572a8e-b95d-5c59-9a7c-1d3514a507b4','94ece1a2-cfec-59cf-ba79-c618ed566f57','bc76c316-2c04-5ecb-85b7-3e5f80b26bf1','dfd01f0a-edcf-55b7-aecb-2d44a419b9b3'}
    nodes=[]
    for layer in after['copper_layers']:
        polys=[shape(new[u]['layers'][layer]) for u in aux if new[u]['layers'].get(layer)]
        polys += [shape(z['polygons']) for u,z in zones.items() if u in auxzones and z['layer']==layer]
        if not polys:continue
        merged=unary_union([g.buffer(.000002) for g in polys])
        if layer=='F.Cu':merged=merged.difference(cut)
        pieces=[merged] if merged.geom_type=='Polygon' else list(merged.geoms)
        nodes.extend((layer,g) for g in pieces if g.area>1e-10)
    parent=list(range(len(nodes)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for u in aux:
        o=new[u]
        if o['kind']!='PCB_VIA':continue
        hits=[i for i,(l,g) in enumerate(nodes) if o['layers'].get(l) and g.intersection(shape(o['layers'][l])).area>1e-8]
        assert len(hits)==len(after['copper_layers'])
        for i in hits[1:]:parent[root(i)]=root(hits[0])
    def node_for(r,p):
        o=pad(r,p);hits=[i for i,(l,g) in enumerate(nodes) if o['layers'].get(l) and g.intersection(shape(o['layers'][l])).area>1e-8]
        assert len(hits)==1
        return root(hits[0])
    a,b=node_for('P_U102','9'),node_for('P_C106','2');assert a!=b
    assert all(node_for(r,p)==a for r,p in [('P_C113','2'),('P_C110','2'),('P_R109','2')])
    assert node_for('P_C107','2')==b
    ground=shape(zones['d41ab58e-16e9-5d76-8b14-dc335aff8371']['polygons'])
    controls=[o for o in new.values() if o['kind']=='PCB_TRACK' and o['net'] in ['/P_power_supply/INPUT_SLEW','/P_power_supply/INPUT_ILIM']]
    projection=unary_union([LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2) for o in controls])
    control_uncovered=projection.difference(ground.buffer(.0015)).area;assert control_uncovered<1e-6
    bus=next(r for r in report['routes'] if r['label']=='output-bulk-force')
    projection=LineString(bus['path_mm']).buffer(bus['width_mm']/2)
    projection=projection.difference(shape(pad('P_C103','1')['layers']['In1.Cu']).buffer(.215))
    for v in report['vias']:
        if v['net']=='PWR_MODULE_FEED_IN':projection=projection.difference(Point(v['position_mm']).buffer(.515))
    bus_uncovered=projection.difference(ground.buffer(.0015)).area;assert bus_uncovered<1e-6,bus_uncovered
    # Canonical path normalization is the entire filled-board/native-board delta.
    paths=[STAGING/'two-board-power-input-source-filled-03/power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb']
    trees=[read_sexpr(p.read_text()) for p in paths];removed=0
    fs=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    for ref,f in fs[0].items():
        pp=children(f,'path')
        if not pp:continue
        qq=children(fs[1][ref],'path');assert len(qq)==1 and all(p==qq[0] for p in pp)
        removed+=len(pp)-1
        for node in [f,fs[1][ref]]:node[:]=[n for n in node if not(isinstance(n,list) and n and n[0]=='path')]
    assert trees[0]==trees[1]
    sources=[Path(__file__),BEFORE,AFTER,rp,*paths,REPO/'hardware/fabrication/verify_native_zone_unfracture.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},
        old_opens=2440,new_opens=2427,connections_closed=13,
        all_previous_connection_groups_preserved=len(before['all_groups']),
        verified_terminal_groups={n:sorted(p) for n,p in intended.items()},
        all_thirteen_native_planes_contiguous=True,unchanged_existing_native_zones=7,
        plane_contacts=plane_checks,zone_unfracture_fidelity=fidelity,
        AUX_input_output_returns_separate_after_GND_land_cut=True,
        full_control_reference_uncovered_mm2=control_uncovered,
        bulk_output_trace_reference_uncovered_mm2_excluding_own_antipads=bus_uncovered,
        duplicate_identical_footprint_paths_removed=removed,native_path_normalization_only_board_delta=True,
        independent_placement_and_complete_copper_delta_audit_pending=True,
        electrical_current_thermal_transient_qualification=False,fabrication_released=False)
    with (OUT/'input-source-plane-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','verified_terminal_groups','plane_contacts','zone_unfracture_fidelity']},indent=2))

if __name__=='__main__':run()
