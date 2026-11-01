"""Captured-source NP01 calculations and actual native-land comparisons.

No parent generation/import is executed. A new --output is required for replay;
the default creates a new analyses/ directory and refuses to replace it.
"""

import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection import selection

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_sexpr(text):
    """Small independent reader; quoted KiCad tokens remain strings."""
    tokens = iter(re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text))

    def read(token):
        if token == "(":
            result = []
            for token in tokens:
                if token == ")":
                    return result
                result.append(read(token))
            raise ValueError("Unclosed expression")
        return json.loads(token) if token.startswith('"') else token

    result = read(next(tokens))
    if next(tokens, None) is not None:
        raise ValueError("Trailing expression")
    return result


def children(node, tag):
    return [v for v in node if isinstance(v, list) and v and v[0] == tag]


def first(node, tag):
    return children(node, tag)[0]


def native_footprints(pcb):
    answer = {}
    for f in children(read_sexpr(pcb.read_text()), "footprint"):
        props = {p[1]: p[2] for p in children(f, "property")}
        if "Reference" not in props:
            continue
        fa = first(f, "at")
        angle = float(fa[3]) if len(fa) > 3 else 0.0
        pads = []
        for p in children(f, "pad"):
            at = first(p, "at")
            pa = float(at[3]) if len(at) > 3 else 0.0
            size = [float(v) for v in first(p, "size")[1:3]]
            # Pad angles saved by KiCad are absolute; centers are FP-local.
            rel = (pa - angle) % 180
            if math.isclose(rel, 90, abs_tol=1e-6):
                size.reverse()
            elif not math.isclose(rel, 0, abs_tol=1e-6):
                raise ValueError(f"Nonorthogonal pad {props['Reference']}.{p[1]}")
            drill = children(p, "drill")
            pads.append(
                dict(
                    number=p[1],
                    xy_mm=[float(at[1]), float(at[2])],
                    size_mm=size,
                    drill=drill[0][1:] if drill else None,
                )
            )
        answer[props["Reference"]] = dict(footprint=f[1], pads=pads)
    return answer


# Pad size is [length along the two-pad axis, width]; C = center distance.
# No custom thermal/creepage rule is inferred from these recommendations.
LANDS = {
    "TNPU0805_IPC28950": dict(center_mm=0.95, size_mm=[0.9, 1.45], source="vishay-lands-28950.pdf", page=1),
    "TNPU0603_IPC28950": dict(center_mm=0.8, size_mm=[0.9, 1.0], source="vishay-lands-28950.pdf", page=1),
    "TNPW0805_IPC28950": dict(center_mm=0.95, size_mm=[0.9, 1.45], source="vishay-lands-28950.pdf", page=1),
    "TNPW1206_IPC28950": dict(center_mm=1.45, size_mm=[1.15, 1.8], source="vishay-lands-28950.pdf", page=1),
    "CRCW2010_reflow20035": dict(
        center_mm=2.475, size_mm=[1.45, 2.8], source="vishay-CRCW-20035.pdf", page=11
    ),
    "WSL2512_7m_to500m": dict(center_mm=2.855, size_mm=[1.65, 3.68], source="vishay-WSL-30100.pdf", page=2),
    "KEMET0603_LevelB": dict(center_mm=0.8, size_mm=[0.95, 1.0], source="kemet-C0G-2025.pdf", page=12),
    "KEMET1206_LevelB": dict(center_mm=1.5, size_mm=[1.15, 1.8], source="kemet-C0G-2025.pdf", page=12),
    "KEMET1210_LevelB": dict(center_mm=1.5, size_mm=[1.15, 2.7], source="kemet-C0G-2025.pdf", page=12),
}


def pad_geometry(fp):
    pads = sorted(fp["pads"], key=lambda p: p["xy_mm"][0])
    if len(pads) != 2 or any(abs(p["xy_mm"][1]) > 1e-7 for p in pads):
        raise ValueError("Expected collinear two-terminal footprint")
    left, right = pads
    return dict(
        centers_mm=[p["xy_mm"] for p in pads],
        sizes_mm=[p["size_mm"] for p in pads],
        gap_mm=right["xy_mm"][0] - right["size_mm"][0] / 2 - left["xy_mm"][0] - left["size_mm"][0] / 2,
        span_mm=right["xy_mm"][0] + right["size_mm"][0] / 2 - left["xy_mm"][0] + left["size_mm"][0] / 2,
    )


def land_comparison(rows, fps):
    result = []
    for row in rows:
        if row["ref"] not in fps:
            result.append(
                dict(
                    ref=row["ref"],
                    actual_parent_pad_available=False,
                    reason="Added after physical233 parent; no invented pads",
                )
            )
            continue
        fp = fps[row["ref"]]
        actual = pad_geometry(fp)
        target = LANDS.get(row["land"])
        d = dict(
            ref=row["ref"],
            actual_parent_pad_available=True,
            footprint=fp["footprint"],
            actual=actual,
            target=target,
            comparison_is_manufacturer_recommendation_NOT_DRC=True,
            new_package_differs_from_parent=(row["ref"] in ["C1", "C2"] or row.get("family") == "TNPU0603"),
        )
        if target:
            expected = dict(
                centers_mm=[[-target["center_mm"], 0], [target["center_mm"], 0]],
                sizes_mm=[target["size_mm"]] * 2,
            )
            d["matches_recommended_pattern_exactly"] = all(
                math.isclose(a, b, abs_tol=1e-6)
                for key in expected
                for aa, bb in zip(actual[key], expected[key])
                for a, b in zip(aa, bb)
            )
        else:
            d["matches_recommended_pattern_exactly"] = None
            d["hold"] = "TDK PA/PB/PC drawing and WIMA formed-lead/factory tolerances need process review"
        result.append(d)
    return result


def interval(nominal, fraction):
    return [nominal * (1 - fraction), nominal * (1 + fraction)]


def monitor_trip(ri, fb, rt_components, rb, resistor_error, p):
    """Enumerate every independent resistor/reference/sign corner.

    This replays the captured NF03C comparator mathematical model only. The
    opamp/comparator/ref numbers retain their original unaccepted assumptions.
    """
    corners = [interval(x, resistor_error) for x in [ri, fb, *rt_components, rb]]
    answers = []
    for vals in itertools.product(
        *corners, interval(1.25, p["existing_protect_reference_complete_error_requirement_fraction"]), [-1, 1]
    ):
        a, b = vals[:2]
        rt = sum(vals[2 : 2 + len(rt_components)])
        bottom, ref, sign = vals[-3:]
        gain = b / a
        threshold = ref * bottom / (rt + bottom)
        sensor_error = (
            p["opamp_offset_plus_drift_receiving_requirement_v"] * (1 + gain)
            + p["opamp_input_bias_complete_receiving_requirement_a"] * b
        )
        ref_bias = p["comparator_input_bias_full_temperature_table_a"] * (10000 + rt * bottom / (rt + bottom))
        error = sensor_error + ref_bias + p["comparator_offset_full_temperature_table_v"]
        answers.append((threshold + sign * error) / gain)
    return [min(answers), max(answers)]


def monitor_scenarios(parts, p):
    r = {v["ref"]: selection.resistance(v["part"]) for v in parts if v["ref"].startswith("R")}
    models = {
        "N19_protected_UV": ("R23", "R24", ["R25", "R26"], "R27"),
        "N19_protected_OV": ("R23", "R24", ["R29", "R30"], "R31"),
        "N12_protected_UV": ("R40", "R41", ["R42", "R43"], "R44"),
        "N12_protected_OV": ("R40", "R41", ["R46"], "R47"),
    }
    return dict(
        model_scope="Captured NF03C protected comparator equation, actual261 resistor values; not whole startup simulation",
        original_precision_endpoint_monitor_false_retained=True,
        all_analog_reference_offset_bias_inputs_unaccepted=True,
        results={
            name: {
                str(e): monitor_trip(r[a], r[b], [r[k] for k in c], r[d], e, p)
                for e in [0.001, 0.0025, 0.005]
            }
            for name, (a, b, c, d) in models.items()
        },
        source_UV_NOT_replayed="External E28 source-sense ratio/cross-domain/protection contract needs full coordinated model",
        acceptance_limits_invented=False,
        electrical_qualified=False,
    )


def available_power(P70, zero_C, ambient_C, value_factor=1):
    return P70 * value_factor * max(0, min(1, (zero_C - ambient_C) / (zero_C - 70)))


def dc_power_screens():
    cases = []
    for name, refs, volts, ohms, error, p70, zero in [
        ("AUX_clamp_feed_conservative_full_5p2V", ["R4", "R11"], 5.2, 402, 0.03, 0.14, 125),
        ("LED_rail_bleed_conservative_5p2V", ["R97"], 5.2, 240, 0.03, 0.27, 125),
    ]:
        loss = volts**2 / (ohms * (1 - error))
        capacity = available_power(p70, zero, 85)
        cases.append(
            dict(
                name=name,
                refs=refs,
                volts_case=volts,
                resistance_complete_fraction_requirement=error,
                watts_per_part=loss,
                power_with_20pct_provision_W=loss * 1.2,
                catalog_derated_at85_W=capacity,
                conditional_20pct_DC_screen_clear=loss * 1.2 <= capacity,
            )
        )
    # The mate must be at its minimum; element loss is maximal at R=mate,
    # which here is the both-minimum corner (not one high/one low).
    combinations = [(a, b) for a, b in itertools.product(interval(402, 0.03), repeat=2)]
    loss = max(26.4**2 * a / (a + b) ** 2 for a, b in combinations)
    cases.append(
        dict(
            name="two_equal_feed_resistors_startup_full_module_voltage",
            refs=["R56", "R57", "R73", "R74"],
            volts_case=26.4,
            resistance_complete_fraction_requirement=0.03,
            watts_per_part=loss,
            power_with_20pct_provision_W=loss * 1.2,
            catalog_derated_at85_W=available_power(0.75, 155, 85),
            conditional_20pct_DC_screen_clear=loss * 1.2 <= available_power(0.75, 155, 85),
            startup_duration_energy_and_hot_board_NOT_accepted=True,
        )
    )
    shunts = []
    for r in [0.33, 0.12]:
        factor = 1 - 0.2 * (r - 0.1) / 0.4
        drift = 0.005 + 75e-6 * 65 + (0.01 + 0.0005 / r) + (0.005 + 0.0005 / r) + (0.005 + 0.0005 / r)
        shunts.append(
            dict(
                ohm=r,
                value_derating_factor=factor,
                power_at85_W=available_power(1, 170, 85, factor),
                planning_initial_TCR_loadlife_solder_bias_humidity_fraction=drift,
                complete5pct_planning_sum_met=drift <= 0.05,
                sum_is_NOT_joint_lifetime_guarantee=True,
                pulse_current_duration_repetition_AND_Kelvin_trace_errors_open=True,
            )
        )
    return dict(
        cases=cases,
        shunts=shunts,
        ambient_case_C=85,
        voltages_are_declared_receiving_cases_NOT_guaranteed_operating_bounds=True,
        no_assembly_film_temperature_or_pulse_pass=True,
        pulse_refs_needing_waveforms=["R6", "R7", "R13", "R14", "R70", "R87", "R72", "R89"],
        catalog_Rth_is_NOT_installed_Rth=True,
        physical_qualified=False,
    )


def footprint_text(name, land):
    center = land["center_mm"]
    x, y = land["size_mm"]
    lines = [
        f'(footprint "{name}" (version 20241229) (generator "NP01") (layer "F.Cu") (attr smd)',
        f' (descr "Candidate from {land["source"]} p{land["page"]}; process/thermal DFM unaccepted")',
    ]
    for n, sign in [(1, -1), (2, 1)]:
        lines.append(
            f' (pad "{n}" smd rect (at {sign * center:.6f} 0) (size {x:.6f} {y:.6f}) (layers "F.Cu" "F.Paste" "F.Mask"))'
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def report_errors(d):
    errors = []
    if len(d["selections"]["rows"]) != 196 or {p["ref"] for p in d["selections"]["rows"]} != {
        f"R{i}" for i in range(1, 98)
    } | {f"C{i}" for i in range(1, 100)}:
        errors.append("Incomplete or duplicate passive inventory")
    for row in d["selections"]["rows"]:
        if row["selected_for_production"] or row.get("effective_complete_tolerance_accepted", False):
            errors.append(f"{row['ref']}: unsupported adoption/complete tolerance")
        if row.get("complete_receiving_original_fraction") == 0.001:
            if row["TCR_ppm_per_K"] == 2 and not 500 <= row["ohm"] <= 20000:
                errors.append(f"{row['ref']}: TNPU2ppm outside checked range")
            if any(s["complete_0p1pct_met"] for s in row["planning_error_scenarios"]):
                errors.append(f"{row['ref']}: falsely closed original complete0.1%")
        body = row["body_max_mm"]
        if body is not None and not math.isclose(
            row["body_plus_seat_max_mm"], body[2] + row["seat_requirement_mm"], abs_tol=1e-9
        ):
            errors.append(f"{row['ref']}: incomplete height stack")
    byref = {r["ref"]: r for r in d["land_comparison"]}
    for ref in ["C1", "C2", "R26", "R30", "R34"]:
        if not byref[ref]["new_package_differs_from_parent"]:
            errors.append(f"{ref}: missing physical-package change")
    for ref in ["R69", "R86"]:
        if byref[ref]["matches_recommended_pattern_exactly"]:
            errors.append(f"{ref}: generic2512 falsely accepted as WSL land")
    for name, vals in d["monitor_scenarios"]["results"].items():
        for smaller, larger in [("0.001", "0.0025"), ("0.0025", "0.005")]:
            if not vals[larger][0] <= vals[smaller][0] <= vals[smaller][1] <= vals[larger][1]:
                errors.append(f"{name}: nonconservative tolerance enclosure")
    if d.get("electrical_qualified") or d.get("physical_qualified") or d.get("fabrication_released"):
        errors.append("Unsupported qualification")
    return errors


def build(output=None, selected=None):
    out = Path(output) if output else ROOT / "analyses"
    if out.exists():
        raise RuntimeError("Refusing to overwrite sealed/existing output")
    selections_path = Path(selected) if selected else ROOT / "generated/selections.json"
    s = json.loads(selections_path.read_text())
    pcb = ROOT / "sources/NF233-physical/negative_startup_ready.kicad_pcb"
    p = json.loads((ROOT / "sources/reference-baseline/parameters.json").read_text())
    parts = json.loads((ROOT / "sources/NF261/components.json").read_text())
    d = dict(
        revision="NP01-independent-analyses",
        selections=s,
        land_comparison=land_comparison(s["rows"], native_footprints(pcb)),
        monitor_scenarios=monitor_scenarios(parts, p),
        DC_power_screens=dc_power_screens(),
        J6_primary_domain_erratum=dict(
            original_unsealed_message_wrong_domain=True,
            isolated_secondary_feed_ohms_DO_NOT_bound_primary_connector_loss=True,
            primary_current_case_A=0.17413,
            two_interface_aftertest_requirement_ohm=0.04,
            primary_drop_case_V=0.17413 * 0.04,
            inrush_minimum_primary_voltage_and_hot_contacts_accepted=False,
        ),
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        source_sha256={
            str(x): sha(x)
            for x in [
                Path(__file__),
                Path(selection.__file__),
                selections_path,
                pcb,
                ROOT / "sources/NF261/components.json",
                ROOT / "sources/reference-baseline/parameters.json",
            ]
        },
    )
    errors = report_errors(d)
    if errors:
        raise ValueError(errors)
    out.mkdir()
    lib = out / "NP01.pretty"
    lib.mkdir()
    for name, land in LANDS.items():
        (lib / f"{name}.kicad_mod").write_text(footprint_text(name, land))
    d["candidate_footprint_sha256"] = {str(p): sha(p) for p in sorted(lib.glob("*.kicad_mod"))}
    (out / "analysis.json").write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                passives=len(s["rows"]),
                recommended_land_candidates=len(LANDS),
                original_complete0p1_closed=False,
                physical_qualified=False,
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--selected", type=Path, help="Previously generated selections for captured replay")
    args = parser.parse_args()
    build(args.output, args.selected)
