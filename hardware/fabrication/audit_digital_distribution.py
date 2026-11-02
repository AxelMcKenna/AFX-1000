"""Independent DC03 additive geometry, native power and drill-location audit."""
import json,math
from pathlib import Path
from collections import Counter
from shapely.geometry import Point,Polygon,box,LineString
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import sha,native_evidence_errors,geometry_delta
from hardware.fabrication.audit_digital_cells import check as previous_check,OUT as PREVIOUS
from hardware.fabrication.audit_digital_core import verify_export
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.rail_monitor_dc_paths import resistivity,track_ohm,barrel_ohm
REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'hardware/fabrication'
OUT=ROOT/'staging/digital-distribution-native-02'

def check():
    old=previous_check();assert old==json.loads((PREVIOUS/'handoff.json').read_text())
    pcb=OUT/'digital_core.kicad_pcb';rp=OUT/'review.json';review=json.loads(rp.read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'),review)
    assert review['status']['counts']==dict(violations=0,unconnected_items=255,schematic_parity=0,erc=0)
    assert review['uncapped_open_connections']==255
    for name,h in review['captured_hierarchy_sha256'].items():assert sha(OUT/name)==h
    parts,pins=netlist(OUT/'netlist.xml');verify_export(parts,pins)
    before=read_sexpr((PREVIOUS/'digital_core.kicad_pcb').read_text());after=read_sexpr(pcb.read_text())
    delta=geometry_delta(before,after);assert delta['other_root_geometry_exact']
    for tag,n in [('footprint',0),('segment',186),('via',128),('zone',2)]:
        assert len(delta[tag]['added'])==n and not delta[tag]['removed'] and not delta[tag]['changed'],tag
    receipts=[ROOT/'staging'/stage/'construction.json' for stage in ['digital-planes-01','digital-plane-escapes-01','digital-power-finish-01','digital-seed-supply-01','digital-3v3-routes-01','digital-thermal-vias-01']]
    cp=ROOT/'staging/digital-distribution-inputs-255-v2/capture.json'
    nr=OUT/'distribution-connectivity-review.json';receipts += [cp,nr]
    inputs=[pcb,pcb.with_suffix('.kicad_pro'),rp,OUT/'netlist.xml',PREVIOUS/'handoff.json',PREVIOUS/'digital_core.kicad_pcb',Path(__file__),ROOT/'rail_monitor_dc_paths.py',ROOT/'digital_core_layout.py']
    hashes=dict(old['source_sha256'])
    for p in receipts:
        d=json.loads(p.read_text())
        assert all(sha(Path(k))==v for k,v in d['source_sha256'].items())
        if 'candidate_PCB_sha256' in d:assert sha(p.parent/'digital_core.kicad_pcb')==d['candidate_PCB_sha256']
        hashes.update({str(Path(k).relative_to(REPO)):v for k,v in d['source_sha256'].items()})
    c=json.loads(cp.read_text());native=json.loads(nr.read_text())
    assert native['uncapped_open_connections']==255 and native['preserved_local_pad_pairs']==39
    assert len(native['power_nets'])==5 and all(r['all_native_connected'] for r in native['power_nets'])
    assert sum(r['pad_count'] for r in native['power_nets'])==201
    assert len(native['thermal_branches'])==33
    for name,h in native['plots_sha256'].items():assert sha(OUT/'plots'/name)==h
    plane_summary=[]
    for z in native['planes']:
        ps=[Polygon(p['outer'],p['holes']) for p in z['polygons']]
        assert len(ps)==1 and ps[0].is_valid and abs(ps[0].area-z['area_mm2'])<1e-6
        plane_summary.append({k:v for k,v in z.items() if k!='polygons'})
    assert {(z['net'],z['layer']) for z in native['planes']}=={('AGND','In1.Cu'),('5V_DIG','In2.Cu')}
    thermal=json.loads((ROOT/'staging/digital-thermal-vias-01/construction.json').read_text())
    special={r['via_uuid']:r for r in thermal['thermal_vias']}
    fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(after,'footprint')}
    smd=[(o,shape(ps)) for o in c['objects'] if o['kind']=='PAD' and not any(o['drill_mm']) for layer,ps in o['layers'].items() if layer in ['F.Cu','B.Cu'] and ps]
    drills=[]
    for v in children(after,'via'):
        ident=first(v,'uuid')[1];xy=list(map(float,first(v,'at')[1:3]));p=Point(xy)
        assert float(first(v,'drill')[1])==.3 and float(first(v,'size')[1])==.6
        permitted=special.get(ident);exempt=permitted['ref'] if permitted else None
        gap=min(p.distance(g)-.15 for o,g in smd if not (o.get('ref')==exempt and o.get('pin')=='33'))
        assert gap>=.15-1e-6,(ident,gap)
        aperture_gap=None
        if permitted:
            f=fps[exempt];ep=next(pad for pad in children(f,'pad') if pad[1]=='33')
            assert box(*pad_box(f,ep,0)).covers(p.buffer(.3))
            apertures=[box(*pad_box(f,pad,0)) for pad in children(f,'pad') if any(layer in first(pad,'layers')[1:] for layer in ['F.Mask','F.Paste'])]
            aperture_gap=min(p.distance(g)-.15 for g in apertures);assert aperture_gap>=.15
            assert math.isclose(aperture_gap,permitted['hole_edge_to_nearest_package_mask_or_paste_mm'],abs_tol=1e-8)
            assert first(v,'net')[1]=='AGND'
            assert first(first(v,'tenting'),'front')[1]==first(first(v,'tenting'),'back')[1]=='yes'
        drills.append(dict(uuid=ident,xy_mm=xy,drill_mm=.3,mask_covered_EP_ref=exempt,
            minimum_hole_edge_to_other_SMD_copper_mm=gap,minimum_hole_edge_to_package_mask_or_paste_mm=aperture_gap))
    assert len(drills)==136 and len(special)==21
    assert len(children(after,'segment'))==245
    assert all(first(s,'layer')[1] in ['F.Cu','B.Cu'] for s in children(after,'segment'))
    seed=json.loads((ROOT/'staging/digital-seed-supply-01/construction.json').read_text())
    feed=next(r for r in json.loads((ROOT/'staging/digital-plane-escapes-01/construction.json').read_text())['routes'] if r['owner']['ref']=='R1001')
    length=seed['length_mm']+LineString(feed['points_mm']).length
    sensitivities=[]
    for name,temp,copper,plating,thickness in [('illustrative_20C',20,35,25,1.6),('thin_hot_sensitivity',85,25,15,1.76)]:
        rho=resistivity(temp,1.)
        copper_r=track_ohm(length,1.,copper,rho)+2*barrel_ohm(thickness,.3,plating,rho)
        sensitivities.append(dict(name=name,temperature_C=temp,outer_copper_um=copper,plating_um=plating,board_mm=thickness,
            modeled_one_mm_tracks_length_mm=length,modeled_tracks_and_two_full_barrels_ohm=copper_r,
            allocated_input_current_A=1.,drop_V_including_initial_1pct_047ohm=copper_r+.4747,
            resistor_power_W_at_1A_initial_high_tolerance=.4747,
            excludes_plane_return_harness_source_TCR_and_self_heating=True,qualification_pass_inferred=False))
    inputs += receipts+[OUT/n for n in review['captured_hierarchy_sha256']]
    hashes.update({str(p.relative_to(REPO)):sha(p) for p in inputs})
    return dict(revision='DC03',source_sha256=hashes,electrical_parts=138,exported_physical_terminals=sum(map(len,pins.values())),
        uncapped_open_connections=255,native_geometry_findings=0,native_schematic_parity_findings=0,native_ERC_findings=0,
        geometry_delta=delta,all_previous_footprints_copper_and_root_geometry_exact=True,
        conditional_courtyard_THT_and_mount_clearances_pass=True,local_connections_native_verified=39,
        power_nets=native['power_nets'],planes=plane_summary,total_tracks=245,total_vias=136,
        drill_location_review=drills,thermal_vias_by_driver=dict(Counter(r['ref'] for r in native['thermal_branches'])),
        ordinary_vias_outside_SMD_copper=115,thermal_vias_in_mask_covered_EP_copper=21,
        Seed_feed_sensitivity=sensitivities,complete_mechanical_receiving_qualified=False,
        current_capacity_voltage_noise_signal_return_and_thermal_performance_qualified=False,
        mask_registration_tenting_plating_and_stack_accepted=False,routed=False,fabrication_released=False)

if __name__=='__main__':
    result=check()
    with (OUT/'handoff.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('DC03: 201 power/ground pads native-connected; 255 opens; 136 drills mapped')
