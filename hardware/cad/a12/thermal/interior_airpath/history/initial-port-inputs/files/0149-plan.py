"""AP02 exact area/pin/stack requirements, not an installed flow model."""

import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HT=ROOT.parents[1]/"pot_stack_high_temp"
FI=ROOT.parent/"enlarged_base_forced_air"


def plan():
    text=(FI/"generated/parts.scad").read_text()
    pins=json.loads(next(l for l in text.splitlines() if l.startswith("eb_part_pins=")).split("=",1)[1].rstrip(";"))
    bays=[[36,142,112,188.4],[229.5,142,278.5,188.4]]
    gates=[[69.75,136.5,90.25,144.25],[243.75,136.5,264.25,144.25]]
    def overlaps(p,b):
        return p[0]+1.75>b[0] and p[0]-1.75<b[2] and p[1]+1.75>b[1] and p[1]-1.75<b[3]
    removed=[p for p in pins if any(overlaps(p,b) for b in bays+gates)]
    kept=[p for p in pins if p not in removed]
    radius=6; d=164-168.9352
    F=lambda y:y*math.sqrt(radius*radius-y*y)+radius*radius*math.asin(y/radius)
    island=F(radius)-F(d)
    R=18.75
    G=lambda x:x*math.sqrt(R*R-x*x)+R*R*math.asin(x/R)
    guard=sum(G(c+2)-G(c-2) for c in range(-15,16,5))
    return dict(revision="AP02", targets=dict(total_m3h=10,interior_m3h=8.8,base_m3h=1.2,inlet_net_mm2=2500,exhaust_net_mm2=2500,guard_net_each_mm2=800),
        inlet=dict(left_rect=[38,164,110,183],right_rect=[231.5,154,276.5,183],corner_r_mm=1,island_centre=[93.0871,168.9352],island_r_mm=6,
            nominal_left_net_mm2=72*19-(4-math.pi)-island,nominal_right_net_mm2=45*29-(4-math.pi),
            nominal_total_net_mm2=72*19+45*29-2*(4-math.pi)-island,island_intact_join_width_mm=2*math.sqrt(radius*radius-d*d)),
        exhaust=dict(slot_count=18,width_mm=4,height_mm=36,radius_mm=1.5,pitch_mm=5.5,Y_extent=[40,137.5],Z_extent=[5,41],
            nominal_net_mm2=18*(4*36-(4-math.pi)*1.5**2),inter_slot_web_mm=1.5,nominal_lower_wall_web_mm=2.2,nominal_upper_wall_web_mm=2.6),
        guard=dict(slot_centres_x=list(range(-15,16,5)),slot_width_mm=4,clipped_disc_diameter_mm=37.5,nominal_net_each_mm2=guard,
            minimum_gross_slot_web_mm=1,protective_finger_strength_test_passed=False),
        plenum_bays_XY=bays,replaceable_meter_insert_keepouts_XY=gates,
        pins=dict(parent_count=len(pins),removed_centres=removed,removed_count=len(removed),kept_centres=kept,kept_count=len(kept),
            rule="Remove whole parent3mm pins whose footprint+.25 intersects actual pressure-bay or meter-fastener envelope; no partial pin stubs"),
        fan=dict(exact_part="Sunon MF40100V1-1000U-G99",centres=[[80,165.5],[254,165.5]],body_max=[40.5,40.5,10.5],nominal_CAD_thickness=10.4,
            thickness_interval=[10,10.5],matched_rigid_shim_interval=[2,2.5],nominal_CAD_matched_shim=2.1,combined_nominal_clamp_stack=12.5,
            lower_bearing_z=-24.7,upper_shim_z=-12.2,hole_min=4.0,
            shared_floating_bolt_error_each_XY=.275,guard_relative_error_each_XY=.375,nominal_shank_max=3.1,
            supplier_M4_recommendation_not_satisfied_by_prototype_M3_qualification=True),
        seals=dict(material_candidate="Rogers BISCO HT-800,0.79mm standard sheet",supplier_thickness_interval=[.688,1.171],compressed_gap_nominal_mm=.5,
            actual_compression_force_load_flatness_registration_and_leak_verified=False,
            frame_seal_and_shim_nominal_profiles_are_official_STEP_derived=True,uncompressed_die_cut_width_tolerance_quote_required=True),
        metering=dict(count=2,replaceable_plate_width=20,plate_height=17.5,plate_thickness=2,default_aperture_width=6.25,aperture_height=10,
            nominal_total_aperture_mm2=125,flow_ratio_calibrated=False,
            service="RemovefourM3x20footretainers andlowerentiretray;interchange2bolted/gasketedrearwallmeterplates; noPCB/wiremoves intended"),
        old_base_rear_outlet_mm2=3724,old_outlet_is_direct_fan_bypass=False,
        actual_flow_split_verified=False,fan_face_contact_and_rotor_dynamics_qualified=False,physical_qualified=False,thermal_qualified=False,
        structural_qualified=False,fabrication_released=False,newer_board_wire_candidates_adopted=False)
