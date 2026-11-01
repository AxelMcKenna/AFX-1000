"""Source-bound input harness screening, preserving unresolved physical gates."""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
INLET = REPO / "hardware/electronics/input_protection/inlet_revision2/rear_inlet.kicad_pcb"
POWER = REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"


def pad_centers(path, reference, datum):
    tree = read_sexpr(path.read_text())
    footprint = next(
        fp
        for fp in children(tree, "footprint")
        if any(p[1:3] == ["Reference", reference] for p in children(fp, "property"))
    )
    assert "JST_VH_B2PS-VH_1x02_P3.96mm_Horizontal" in footprint[1]
    result = {}
    for pad in children(footprint, "pad"):
        if pad[1] not in {"1", "2"}:
            continue
        xy = transform(footprint, first(pad, "at")[1:3])
        net = str(first(pad, "net")[-1]).lstrip("/")
        result[pad[1]] = dict(
            net=net,
            center_housing_xy_mm=[round(xy[index] - 100 + datum[index], 6) for index in range(2)],
        )
    assert set(result) == {"1", "2"}
    assert result["1"]["net"] == "DC_IN" and result["2"]["net"] == "AGND", result
    return result


def analyze():
    source_paths = [
        ROOT / "input-feed.json",
        ROOT / "analyze.py",
        INLET,
        POWER,
        ROOT.parent / "interface.json",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(path.relative_to(REPO)): sha(path) for path in source_paths}
    spec = json.loads((ROOT / "input-feed.json").read_text())
    a, w, c, j, project = (spec[key] for key in ("adapter", "wire", "internal_connectors", "jack", "project"))
    low, high = project["adapter_ambient_c"]
    assert (
        a["temperature_coefficient_applicable_range_c"][0]
        <= low
        <= high
        <= a["temperature_coefficient_applicable_range_c"][1]
    )
    temperature_error = (
        a["nominal_v"]
        * a["temperature_coefficient_fraction_per_c"]
        * max(abs(low - a["reference_temperature_c"]), abs(high - a["reference_temperature_c"]))
    )
    # Use the entire peak-to-peak ripple as an adverse displacement at either
    # end; the static reference level within that ripple is not specified here.
    error = (
        a["nominal_v"] * a["voltage_tolerance_fraction"]
        + temperature_error
        + a["ripple_maximum_peak_to_peak_v"]
    )
    diameter = [(w["diameter_inch"] + sign * w["diameter_tolerance_inch"]) * 25.4 for sign in (-1, 1)]
    assert (
        c["allowed_insulation_diameter_mm"][0]
        <= diameter[0]
        <= diameter[1]
        <= c["allowed_insulation_diameter_mm"][1]
    )
    assert not c["retainer_mountable_housing_selected"]
    hot_wire_pair = (
        2
        * w["maximum_candidate_cut_length_each_mm"]
        / 1000
        * w["dcr_nominal_ohm_per_1000ft_at_20c"]
        / 304.8
        * (
            1
            + w["copper_temperature_coefficient_assumed_per_c"] * (project["wire_screen_temperature_c"] - 20)
        )
    )
    interface = json.loads((ROOT.parent / "interface.json").read_text())
    inlet = pad_centers(INLET, "J2", [248, 1.4, 7.9])
    power = pad_centers(POWER, "J101", interface["power_candidate"]["datum"])
    order_product = (inlet["1"]["center_housing_xy_mm"][0] - inlet["2"]["center_housing_xy_mm"][0]) * (
        power["1"]["center_housing_xy_mm"][0] - power["2"]["center_housing_xy_mm"][0]
    )
    contact_loop = c["contact_environmental_maximum_ohm_catalog"] * c["series_contacts_in_complete_loop"]
    jack_loop = j["contact_maximum_ohm_catalog"] * j["series_contacts"]
    report = dict(
        revision=spec["revision"],
        adapter_static_plus_temperature_plus_adverse_ripple_interval_v=[
            a["nominal_v"] - error,
            a["nominal_v"] + error,
        ],
        adapter_cable_drop_counted_again=False,
        adapter_startup_and_load_step_qualified=False,
        wire_diameter_interval_mm=diameter,
        minimum_candidate_wire_bend_radius_mm=w["bend_radius_in_diameters"] * diameter[1],
        conservative_wire_centerline_bend_radius_allocation_mm=(w["bend_radius_in_diameters"] + 0.5)
        * diameter[1],
        bend_radius_basis="Manufacturer does not identify inner surface versus centerline here; CAD allocation adds one wire radius",
        nonretainer_housing_insulation_range_fits=True,
        retainer_housing_insulation_range_fits=diameter[1]
        <= c["retainer_mountable_housing_insulation_maximum_mm"],
        nominal_wire_pair_resistance_at_screen_temperature_ohm=hot_wire_pair,
        wire_resistance_guaranteed_by_catalog=False,
        catalog_four_internal_contacts_loop_ohm=contact_loop,
        catalog_jack_contact_loop_ohm=jack_loop,
        catalog_values_are_hot_lifetime_assembly_bounds=False,
        source_connector_pad_centers=inlet,
        destination_connector_pad_centers=power,
        connector_pin_order_reversed=order_product < 0,
        crossing_3d_route_and_retention_verified=False,
        wire_center_separation_allocation_mm=diameter[1] + project["wire_to_wire_clearance_allocation_mm"],
        complete_feed_scenario_ohm=project["complete_feed_scenario_ohm"],
        complete_feed_hot_bound_verified=False,
        source_sha256=hashes,
        physical_tests_performed=0,
        build_ready=False,
        fabrication_released=False,
    )
    assert all(sha(REPO / name) == value for name, value in hashes.items()), "Source changed during screening"
    OUT.mkdir(exist_ok=True)
    (OUT / "input-feed-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "A12 input feed: real component candidates screened; route, crimps, hot resistance and startup remain unqualified"
    )
    return report


if __name__ == "__main__":
    analyze()
