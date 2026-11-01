"""Conservative continuous rear-gap area bounds; no installed pressure proof."""

import json
import math

from hardware.cad.a12.thermal.interior_airpath.polygon_contract import primitive_contracts
from hardware.cad.a12.thermal.interior_airpath.pressure_rejection import calculate

from .stage import OUT, ROOT, sha, write


def section_bound(gap, component_xy_allowance=0):
    """Uniform lower bound at EVERY height, subtracting full obstacle AABBs.

    AABBs intentionally overcount overlapping shank/nut regions and extend
    each part's maximum section over the full channel height. Left FIP is
    outside its fan-back strip; the right one is conservatively counted in
    full. These rectangles are conservative for the source-defined cylinders
    and hexagon, without depending on sampled Z sections.
    """
    e = component_xy_allowance
    gross = 40 * gap
    nuts = 2 * (4.7 / math.cos(math.pi / 6) + 2 * e) * (1.6 + 2 * e)
    shanks = 2 * (2.1 + 2 * e) * (3 + 2 * e)
    fip = (6 + 2 * e) * (.6 + 2 * e)
    return dict(gross_mm2=gross, two_nut_AABB_mm2=nuts, two_shank_AABB_mm2=shanks,
                right_feedthrough_AABB_mm2=fip,
                left_uniform_lower_bound_mm2=gross - nuts - shanks,
                right_uniform_lower_bound_mm2=gross - nuts - shanks - fip,
                overlapping_obstacle_bounds_are_not_subtracted_from_losses_twice=True)


def source_errors(source, data):
    required = [
        "ap_bays=[[36,137,112,188.4],[229.5,137,278.5,188.4]];",
        "translate([p[0]-20.55,p[1]-20.55,-24.7])cube([41.1,41.1,12.5])",
        "translate([p[0]+x,134,-8.9])", "cylinder(d=2.1,h=8,$fn=96)",
        "translate([0,0,5])difference(){cylinder(d=4.7/cos(30),h=1.6,$fn=6)",
        "translate([x,137,-10])", "translate([0,0,2])cylinder(d=6,h=.6,$fn=96)",
        "ap_fans=[[80,165.5],[254,165.5]];", "for(x=[46,235.5])",
        "module ap_meter_orifices(w=16)", "ap_round(w,10,1)",
    ]
    bad=["source-construction-missing:"+r for r in required if r not in source]
    if data["rear_wall_Y"] != [137,139] or data["approach_gap_min_requirement_mm"] != 5.95:
        bad.append("wrong-actual-rear-gap")
    if data["actual_flow_split_verified"] or data["physical_qualified"]:
        bad.append("unsupported-qualification")
    return bad


def report():
    source=(OUT/"checks.scad").read_text()
    data=json.loads((OUT/"analysis.json").read_text())
    bad=source_errors(source,data)
    if bad:
        raise ValueError(bad)
    rho=101325/(287.05*313.15)
    area=2*(160-(4-48*math.sin(2*math.pi/96)))
    guard=primitive_contracts()["guard_area_gauge"]["volume"]/.1
    guard_loss=calculate(guard,5,rho,.6)
    meter_loss=calculate(area,1.2,rho,.6)
    required=section_bound(5.95)
    smallest=required["right_uniform_lower_bound_mm2"]
    v=(.6/3600)/(smallest*1e-6)
    dynamic=rho*v*v/2
    return dict(revision="AP03-channel-bound",
        source_sha256={"channel_budget.py":sha(ROOT/"channel_budget.py"),
            "generated/analysis.json":sha(OUT/"analysis.json"),"generated/checks.scad":sha(OUT/"checks.scad")},
        absolute_Z_interval_mm=[-22,-6.7], rear_strip_width_mm=40,
        nominal_Y_gap_mm=6.25, fan_registered_Y_gap_requirement_mm=5.95,
        bounds=dict(nominal=section_bound(6.25), fan_registration=required,
                    extra_wall_plus02_component_XY_plus02_sensitivity=section_bound(5.75,.2)),
        continuous_bound_method="For every Z, remove the full projected XY AABB of every possible intrusion; intersections between nut/shank bounds deliberately overcount removal. No sampled section minimum or zero-loss assumption.",
        continuous_bound_scope="Source-defined rear approach strip only. Not fan rotor area, entire circuit, installed flow or manufacturing approval.",
        native_clear_lower_leg_core=dict(width_mm=31,Y=[139.01,144.94],Z=[-22,-12.2],area_mm2=31*5.93,
                    meaning="Native Boolean tests the whole volume, with explicit10um geometric reservation at eachYboundary. It does not repair/change any part.",
                    excludes_upper_bolt_row=True),
        meter_actual_faceted_total_mm2=area,
        nominal_meter_net_each_mm2=data["nominal_meter_net_each_mm2"],
        pressure_sensitivity=dict(rho_kg_m3=rho,Cd=.6,planning_speed_rpm=5300,
            total_m3_h=10,base_m3_h=1.2,each_fan_m3_h=5,parent_curve_head_Pa=9.046,
            common_guard_Pa=guard_loss,meter_Pa=meter_loss,
            remaining_for_ALL_base_approach_pins_turns_and_outlet_Pa=9.046-guard_loss-meter_loss,
            worst_rear_strip_dynamic_head_Pa=dynamic,
            extra_K_loss_Pa={str(k):dynamic*k for k in [1,2,4,8]},
            these_K_values_are_sensitivities_not_guaranteed_bounds=True),
        limitations=[
            "Area is not a fan duty point; coupled base/interior branch solution still required.",
            "Turns, pins, old outlet, fan system effect, feedthrough wires and leakage have no qualified loss bound.",
            "No Sunon installed fan curve/speed guarantee, rigid-position tolerance or gasket leak acceptance.",
            "The extra0.2mm wall/component scenario is a proposed receiving sensitivity, not a vendor tolerance.",
            "Current P03/E28/E19/control/wire source scope remains AP02 captured historical scene.",
        ],installed_flow_verified=False,thermal_qualified=False,physical_qualified=False,
        geometry_only=True)


def build():
    target=OUT/"channel-budget.json"
    if target.exists() or (ROOT/"handoff.json").exists():
        raise RuntimeError("Existing evidence cannot be overwritten")
    d=report()
    write(target,d)
    print(json.dumps({k:d[k] for k in ["bounds","meter_actual_faceted_total_mm2","pressure_sensitivity"]}))


if __name__=="__main__":
    build()
