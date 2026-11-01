"""Audit actual E12 copper and independent limits without claiming hardware tests."""

import argparse
import hashlib
import heapq
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import transform
from ..pcb.paths import graph, in_polygon, objects

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated"
SENSITIVE_PINS = [(u, str(p)) for u in ("U1", "U2") for p in (1, 4, 5, 8)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def footprints(tree):
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }


def pad(tree, ref, pin):
    fp = footprints(tree)[ref]
    terminal = next(p for p in children(fp, "pad") if str(p[1]) == str(pin))
    return terminal, tuple(map(float, transform(fp, first(terminal, "at")[1:3])))


def plane_coverage(tree):
    """Use actual saved fill polygons, including their bridged hole boundaries."""
    planes = {}
    for zone in children(tree, "zone"):
        if children(zone, "keepout"):
            continue
        layer = str(first(zone, "layer")[1])
        if layer not in ("In1.Cu", "In4.Cu"):
            continue
        planes[layer] = [
            [tuple(map(float, xy[1:3])) for xy in children(first(f, "pts"), "xy")]
            for f in children(zone, "filled_polygon")
        ]
    assert set(planes) == {"In1.Cu", "In4.Cu"}, "Missing actual reference-plane fills"
    return {
        ref + "." + pin: {
            layer: any(in_polygon(pad(tree, ref, pin)[1], polygon) for polygon in polygons)
            for layer, polygons in planes.items()
        }
        for ref, pin in SENSITIVE_PINS
    }


def path_witness(tree, net, start, end):
    """Connected real copper witness, not a straight-line placement estimate.

    Cost sums complete visited segment centre-lines and counts traversed vias.
    Pads/overlapping segment extents can shorten the physical shortest path, so
    this is a conservative route witness, not an extracted RF path impedance.
    """
    items = objects(tree, net)
    edges = graph(items)
    pads = {o["pad"]: i for i, o in enumerate(items) if "pad" in o}
    source, goal = pads[start], pads[end]
    queue, seen = [(0.0, source, ())], set()
    while queue:
        cost, index, route = heapq.heappop(queue)
        if index in seen:
            continue
        seen.add(index)
        route = (*route, index)
        if index == goal:
            lines = [items[i] for i in route if items[i]["kind"] == "line"]
            return dict(
                conservative_segment_sum_mm=round(sum(math.dist(o["p"], o["q"]) for o in lines), 6),
                vias=sum(bool(items[i].get("via")) for i in route),
                layers=sorted({layer for o in lines for layer in o["layers"]}),
                pad_center_distance_mm=round(math.dist(items[source]["p"], items[goal]["p"]), 6),
                minimum_trace_width_mm=min(o["r"] * 2 for o in lines),
                rf_impedance_extracted=False,
            )
        for target in edges[index] - seen:
            o = items[target]
            length = math.dist(o["p"], o["q"]) if o["kind"] == "line" else 0
            heapq.heappush(queue, (cost + length, target, route))
    raise AssertionError((net, start, end, "No actual copper witness"))


def surface_leakage(voltage_error_v, source_resistance_ohm=500000, aggressor_difference_v=10.35):
    assert voltage_error_v > 0 and source_resistance_ohm > 0 and aggressor_difference_v >= 0
    current = voltage_error_v / source_resistance_ohm
    return dict(
        illustrative_error_allocation_v=voltage_error_v,
        maximum_added_leakage_a=current,
        minimum_isolation_to_aggressor_ohm=aggressor_difference_v / current,
        qualification_acceptance_limit=False,
    )


def supply_screen(v5=(4.90, 5.10), nbias=(-0.256, -0.1838)):
    assert v5[0] <= v5[1] and nbias[0] <= nbias[1]
    total = (v5[0] - nbias[1], v5[1] - nbias[0])
    return dict(
        fda_total_supply_interval_v=list(total),
        recommended_fda_total_supply_v=[2.7, 5.4],
        fda_dc_supply_screen_passes=total[0] >= 2.7 and total[1] <= 5.4,
        maximum_fda_supply_reserve_v=5.4 - total[1],
        pump_positive_operating_range_v=[3.0, 5.25],
        pump_positive_dc_screen_passes=v5[0] >= 3.0 and v5[1] <= 5.25,
        transient_or_partial_power_verified=False,
    )


def bias_health_headroom(allocation, upper_health_v=-0.16):
    minimum = (
        allocation["minimum_driver_output_v"]
        - allocation["maximum_dc_common_mode_error_v"]
        - allocation["maximum_differential_dc_v"] / 2
    )
    needed = allocation["output_rail_headroom_allocation_v"]
    actual = minimum - upper_health_v
    return dict(
        conditional_minimum_driver_output_after_dc_errors_v=minimum,
        existing_health_window_upper_v=upper_health_v,
        project_output_headroom_allocation_v=needed,
        headroom_at_existing_window_upper_v=actual,
        reserve_to_project_allocation_v=actual - needed,
        required_upper_bias_for_this_screen_v=minimum - needed,
        existing_window_guarantees_its_own_headroom_allocation=actual >= needed,
        actual_clipping_or_thd_verified=False,
        threshold_tolerances_and_dynamic_margin_included=False,
    )


def analyze():
    source = PARENT / "pcb/adc_driver.kicad_pcb"
    native_record = OUT / "native-original/verification.json"
    saved = OUT / "native-original/filled.kicad_pcb"
    if not native_record.exists():
        native_record = PARENT / "pcb/generated/verification.json"
        saved = PARENT / "pcb/generated/filled.kicad_pcb"
    receipt = json.loads(native_record.read_text())
    assert receipt["source_sha256"][str(source.relative_to(REPO))] == sha(source), (
        "Native record belongs to another E12 source board"
    )
    assert receipt["source_sha256"][str(saved.relative_to(REPO))] == sha(saved), (
        "Changed native fill evidence"
    )
    tree, filled = read_sexpr(source.read_text()), read_sexpr(saved.read_text())
    coverage = plane_coverage(filled)
    paths = {}
    for ci, ch in enumerate(("L", "R")):
        for net, u, pin, c, cp in [
            ("V5_REG", "U" + str(ci + 1), "3", "C" + str(13 + 14 * ci), "1"),
            ("NBIAS_" + ch, "U" + str(ci + 1), "6", "C" + str(14 + 14 * ci), "1"),
            ("FLY_P_" + ch, "U" + str(ci + 5), "1", "C" + str(8 + 14 * ci), "1"),
            ("FLY_N_" + ch, "U" + str(ci + 5), "8", "C" + str(8 + 14 * ci), "2"),
            ("RES_" + ch, "U" + str(ci + 5), "7", "C" + str(9 + 14 * ci), "1"),
            ("NPUMP_" + ch, "U" + str(ci + 5), "6", "C" + str(10 + 14 * ci), "1"),
            ("V5_REG", "U" + str(ci + 5), "4", "C" + str(12 + 14 * ci), "1"),
        ]:
            paths[f"{u}.{pin}-{c}.{cp}"] = path_witness(tree, net, (u, pin), (c, cp))
        for offset, pol, resistor in [(0, "P", 5), (1, "N", 6)]:
            paths["force_" + ch + pol] = path_witness(
                tree,
                "ADC_" + ch + pol,
                ("R" + str(resistor + 16 * ci), "2"),
                ("J2", str(1 + 3 * ci + offset)),
            )
    lands = {}
    for ref in ("U1", "U2", "U5", "U6"):
        fp = footprints(tree)[ref]
        pads = children(fp, "pad")
        xs = sorted({float(first(p, "at")[1]) for p in pads})
        ys = sorted({float(first(p, "at")[2]) for p in pads})
        lands[ref] = dict(
            pin_count=len(pads),
            row_center_spacing_mm=xs[-1] - xs[0],
            pitch_mm=round(ys[1] - ys[0], 6),
            pad_length_width_mm=list(map(float, first(pads[0], "size")[1:3])),
            adjacent_pad_gap_mm=round(ys[1] - ys[0] - float(first(pads[0], "size")[2]), 6),
            fabrication_qualified=False,
        )
    allocation = json.loads((PARENT / "generated/circuit-analysis.json").read_text())[
        "voltage_current_screen"
    ]
    facts = json.loads((ROOT / "source-facts.json").read_text())
    model = dict(
        manufacturer_internal_feedback_capacitance_f=0.6e-12,
        nominal_external_feedback_capacitance_f=1e-12,
        nominal_parallel_feedback_capacitance_f=1.6e-12,
        illustrative_1210ohm_external_feedback_pole_hz=1 / (2 * math.pi * 1210 * 1e-12),
        illustrative_1210ohm_combined_feedback_pole_hz=1 / (2 * math.pi * 1210 * 1.6e-12),
        pole_values_are_not_loop_margin_results=True,
        manufacturer_loop_model_executed=False,
        actual_codec_switching_model_available=False,
    )
    return dict(
        revision="E12-Q01",
        native_geometry_record=str(native_record.relative_to(REPO)),
        actual_filled_geometry=str(saved.relative_to(REPO)),
        assessment="failed_design_review_and_unmeasured",
        original_native_drc_can_be_clean_while_design_review_fails=True,
        manufacturer_plane_opening_requirement_satisfied=not any(any(p.values()) for p in coverage.values()),
        original_sensitive_pin_plane_coverage=coverage,
        physical_stackup_present=bool(children(first(tree, "setup"), "stackup")),
        route_witnesses=paths,
        library_land_geometry=lands,
        ti_dgk_land_pattern_example_mm=dict(pitch=0.65, row_spacing=4.4, length=1.4, width=0.45),
        dgk_footprint_disposition="Actual KiCad lands are an IPC-style alternate, not the TI example. Assembly/process acceptance remains required; difference alone is not a demonstrated footprint failure.",
        supply_screen=supply_screen(),
        stage_noise_to_full_scale_screen_db=20 * math.log10(2 / 1.35e-6),
        stage_noise_screen_is_complete_weighted_snr=False,
        leakage_scenarios=[surface_leakage(v) for v in (0.0001, 0.001, 0.005)],
        existing_allocated_screen=allocation,
        bias_health_headroom_consistency=bias_health_headroom(allocation),
        fda_model_review=model,
        manufacturer_facts=facts,
        findings=[
            dict(
                id="ADC-01",
                state="failed",
                subject="Ground planes under FDA summing and output pads",
                basis="Measured actual fill coverage violates the manufacturer plane-opening layout requirement.",
                remedy="Separate bounded plane-opening trial; then extract all sensitive-node parasitics from a selected stackup and rerun the manufacturer model.",
            ),
            dict(
                id="ADC-02",
                state="blocked",
                subject="High-frequency supply and charge-pump loops",
                basis="Actual pad-to-capacitor copper witnesses traverse multiple millimetres and, for several nets, two vias. No loop ESL/ESR or switched pump simulation is established.",
                remedy="Place 0.1 uF bypass and pump capacitors at actual IC pins with short local loops; extract impedance, verify ripple and conductance under actual loading.",
            ),
            dict(
                id="ADC-03",
                state="failed",
                subject="Final converter force/sense interface",
                basis="Seven-pin J2 has one conductor per ADC polarity; feedback senses its header, not the codec pins.",
                remedy="Co-locate/consolidate the ADC driver and codec or revise the force/sense interface before claiming final-system feedback closure.",
            ),
            dict(
                id="ADC-04",
                state="blocked",
                subject="Stability and 1 pF compensation",
                basis="The manufacturer includes 0.6 pF internal feedback. Existing simplified low-frequency sensitivities and external 1 pF alone do not establish loop margin with actual planes, output capacitors and codec switching.",
                remedy="Use the manufacturer model with measured/extracted parasitics and actual converter load; verify gain/phase, step response, ringing and recovery physically.",
            ),
            dict(
                id="ADC-05",
                state="blocked",
                subject="Scale, noise, leakage and temperature",
                basis="The current screen has only 17.1 mV differential peak reserve to a typical 2 Vrms ADC full scale; no guaranteed minimum codec full scale, physical calibration, complete noise, contamination or thermal result is available.",
                remedy="Characterize calibrated gain/clipping, full audio noise/distortion, hot/humid leakage and enclosed temperatures using actual parts and a reviewed measurement budget.",
            ),
            dict(
                id="ADC-06",
                state="failed",
                subject="Negative-bias supervision",
                basis="Both LM7705 outputs require health windows before driver enable, but E12 integration declares their monitor unimplemented.",
                remedy="Implement both hardware windows in the selected system; verify loss, startup and asymmetric partial power before enabling the ADC driver.",
            ),
            dict(
                id="ADC-07",
                state="failed",
                subject="Bias health window does not guarantee the project's own headroom allocation",
                basis="The proposed -0.16 V upper health threshold permits only about 0.29388 V output headroom at the existing worst-case model, below the declared 0.30 V reserve.",
                remedy="Revise the hardware health-window specification using the final load/headroom model and threshold tolerances; the conditional calculation needs an upper bias bound no greater than about -0.16612 V before tolerances. Do not treat that boundary alone as an approved monitor threshold.",
            ),
        ],
        required_measurements=json.loads((ROOT / "measurements.json").read_text()),
        physical_tests_performed=0,
        audio_performance_verified=False,
        stability_qualified=False,
        manufacturing_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = analyze()
    sources = [
        source
        for source in ROOT.rglob("*")
        if source.is_file()
        and "__pycache__" not in source.parts
        and "generated" not in source.relative_to(ROOT).parts
    ]
    sources += [
        PARENT / name
        for name in [
            "components.json",
            "integration.json",
            "dependencies.json",
            "adc_driver.kicad_sch",
            "analyze.py",
            "generated/circuit-analysis.json",
            "pcb/adc_driver.kicad_pcb",
            "pcb/generated/filled.kicad_pcb",
        ]
    ]
    sources += [PARENT / "pcb/paths.py", REPO / "tests/tooling/test_adc_qualification.py"]
    sources += [REPO / report["native_geometry_record"], REPO / report["actual_filled_geometry"]]
    report["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in sources if p.exists()}
    path = OUT / "review.json"
    content = json.dumps(report, indent=2) + "\n"
    if args.check:
        assert path.read_text() == content, "Stale E12 qualification review"
    else:
        OUT.mkdir(exist_ok=True)
        path.write_text(content)
    print(
        "E12 design review: plane coverage and final interface fail; physical/stability qualification remains open"
    )


if __name__ == "__main__":
    main()
