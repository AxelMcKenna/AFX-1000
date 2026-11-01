"""New J4GND129.5 connector model; no radius/allowance relaxation."""

import json
import math
from pathlib import Path

from hardware.cad.a12.harness.ear_connector_search.arcs import prefix
from hardware.cad.a12.harness.ear_connector_search.bezier import certificate, chord_contract, points
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
SEARCH=REPO/"hardware/cad/a12/harness/ear_connector_search"


def sha(p):
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,d):
    p.write_text(json.dumps(d,indent=2)+"\n")


def native_pad(path,ref,pin,xy_offset,z):
    tree=read_sexpr(path.read_text())
    fp=next(f for f in children(tree,"footprint") if next(p[2] for p in children(f,"property") if p[1]=="Reference")==ref)
    pad=next(p for p in children(fp,"pad") if p[1]==pin)
    xy=transform(fp,first(pad,"at")[1:3])
    return [xy[0]+xy_offset[0],xy[1]+xy_offset[1],z],float(first(pad,"drill")[1])


def build():
    import numpy as np

    out=ROOT/"generated/ground-route.json"
    if out.exists():
        raise RuntimeError("New route output required")
    source=ROOT/"inputs/E28/rail_disconnect.kicad_pcb"
    receiver=ROOT/"inputs/R1/processor_carrier.kicad_pcb"
    start,drill=native_pad(source,"J4","2",[-92,8.5],6.62)
    finish,rdrill=native_pad(receiver,"J13","2",[-70,-58],8.1)
    assert start==[161,129.5,6.62] and finish==[188,104,8.1] and drill==rdrill==2.2
    selected=SEARCH/"generated/selected-paths.json"
    old=json.loads(selected.read_text())
    r=old["routes"][1]
    assert r["source_face_mm"]==[161,126.5,6.62]
    profile=r["source_prefix_profile"]
    p0=np.array(profile["endpoint_mm"])+[0,3,0]
    heading=np.array([math.cos(math.radians(profile["angle_deg"])),math.sin(math.radians(profile["angle_deg"])),0])
    end=np.array([188,104,15.1])
    cp=np.array([p0,p0+10*heading,end+[0,0,9],end]).tolist()
    cert=certificate(cp,required_radius=9.6393,max_depth=12)
    assert cert["certified"] and cert["radius_lower_mm"]>9.7
    paths={}
    contracts={}
    indices={}
    for name,step in [("native",.25),("dense",.02)]:
        pre,pre_c=prefix(profile,step)
        pre += [0,3,0]
        n=max(1,math.ceil(chord_contract(cp,1)["maximum_parameter_speed_upper"]/step))
        free=points(cp,np.linspace(0,1,n+1))
        chord=chord_contract(cp,n)
        stub=end-np.linspace(0,7,math.ceil(7/step)+1)[:,None]*[0,0,1]
        path=np.vstack([pre,free[1:],stub[1:]])
        paths[name]=path.tolist()
        index=math.ceil(profile["initial_straight_mm"]/step)
        indices[name]=dict(source_face=0,source_initial_straight_end=index,
            source_prefix_end=len(pre)-1,destination_stub_start=len(pre)+len(free)-2,destination_face=len(path)-1)
        contracts[name]=dict(prefix=pre_c,cubic=chord,point_count=len(path),
            whole_chord_error_bound_mm=max(pre_c["chord_error_bound_mm"],chord["chord_error_bound_mm"])+1e-9,
            continuous_sample_cover_bound_mm=max(pre_c["continuous_nearest_sample_cover_mm"],chord["continuous_sample_cover_bound_mm"],step/2))
    join=np.array(cp[1])-np.array(cp[0]);join/=np.linalg.norm(join)
    final=np.array(cp[3])-np.array(cp[2]);final/=np.linalg.norm(final)
    assert np.linalg.norm(join-heading)<1e-12 and np.linalg.norm(final-[0,0,-1])<1e-12
    length=profile["curve_length_mm"]+cert["control_polygon_length_upper_mm"]+7+2*(1.76+1.5)
    native=paths["native"]
    idx=indices["native"]
    data=dict(revision="G129-private",source_face_mm=start,source_native_drill_mm=drill,
        receiver_face_mm=finish,receiver_native_drill_mm=rdrill,old_wrong_ground_source_mm=[161,126.5,6.62],
        old_source_misregistration_mm=3,old_unmatched_endpoint_is_retained_failure_control=True,
        prefix_translation_mm=[0,3,0],prefix_shape_congruent_to_old_R16=True,
        prefix_radius_mm=16,prefix_initial_straight_mm=profile["initial_straight_mm"],
        new_cubic_controls_mm=cp,continuous_radius_certificate=cert,
        whole_radius_lower_mm=min(16-1e-9,cert["radius_lower_mm"]),required_true_radius_mm=9.6393,
        all_unit_tangent_joins_C1=True,curvature_C2_not_required=True,
        source_bare_cut_z_mm=9.72,destination_bare_cut_z_mm=11.2,destination_stub_length_mm=7,
        above_face_strip_length_mm=3.1,remaining_receiver_straight_insulation_mm=3.9,
        wire_insulation_OD_max_mm=1.7526,core_receiving_OD_mm=1.4,
        independent_position_allowance_mm=.65,separate_clearance_mm=.25,separate_geometry_reserve_mm=.005,
        minimum_prospective_native_bore_mm=2.1,relative_bore_centering_mm=.3,
        paths_mm=paths,boundary_indices=indices,sample_contract=contracts,
        native_middle=native[idx["source_initial_straight_end"]:idx["destination_stub_start"]+1],
        length_upper_mm_including_max_boardtails=length,
        cutslack_strain_relief_and_fanout_extra_not_allocated=True,
        central_minimum_Z_mm=min(p[2] for p in native[idx["source_initial_straight_end"]:idx["destination_stub_start"]+1]),
        source_sha256={str(p):sha(p) for p in [source,receiver,selected,Path(__file__),SEARCH/"arcs.py",SEARCH/"bezier.py"]},
        previous_unbounded_probe_stopped=True,all_current_certificates_explicitly_depth_bounded=True,
        actual_source_escape_requires_new_ANA_return_bar=True,
        native_geometry_verified=False,physical_qualified=False,thermal_qualified=False,
        current_capacity_or_voltage_drop_qualified=False,fabrication_released=False)
    write(out,data)
    print(json.dumps(dict(continuous_radius_lower_mm=data["whole_radius_lower_mm"],length_upper_mm=length,
           native_points=len(native),dense_points=len(paths["dense"]),central_minimum_Z_mm=data["central_minimum_Z_mm"])))


if __name__=="__main__":
    build()
