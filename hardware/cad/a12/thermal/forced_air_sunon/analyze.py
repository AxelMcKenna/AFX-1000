"""Exact-part fan comparison with source curves; no installed-flow guarantee."""

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.cad.a12.thermal.air_path_budget.analyze import orifice_drop

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
AP = ROOT.parent / "air_path_budget"
NUMBER = r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?"
CFM_TO_M3H = 0.028316846592 * 60
PARTS = {
    "V1": dict(
        model="MF40100V1-1000U-G99",
        pdf="/private/tmp/afx-sunon-mf40100v1-g99.pdf",
        expected_pdf_sha256="580372d445b040b56f5faab666a1e4b8483154a08bd435485547df66bc393a2a",
        spec="D04114160G-02",
        url="https://www.sunon.com/PROSEARCH_FILES/%28D04114160G-02%29-1.pdf",
        current_max_a=0.157,
        current_rated_a=0.136,
        power_max_w=0.79,
        safety_power_w=0.83,
        rpm=7000,
        noise_dba=27.3,
        axes=[161.28, 425.04, 233.999612, 534.839612, 0.2],
        free_cfm=8,
        static_inH2O=0.19,
    ),
    "V2": dict(
        model="MF40100V2-1000U-G99",
        pdf="/private/tmp/afx-sunon-mf40100v2-g99.pdf",
        expected_pdf_sha256="541666c0a1a18ed7a34687d0d8532419607157f57902b9a2640d66a50f167b31",
        spec="D04114220G-01",
        url="https://www.sunon.com/PROSEARCH_FILES/%28D04114220G-01%29-1.pdf",
        current_max_a=0.109,
        current_rated_a=0.094,
        power_max_w=0.55,
        safety_power_w=0.65,
        rpm=5800,
        noise_dba=20.6,
        axes=[160.08, 411.48, 235.919612, 532.079612, 0.12],
        free_cfm=7,
        static_inH2O=0.12,
    ),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_curve(svg, part):
    """Read the actual blue vector polyline, applying its PDF/SVG matrix."""
    paths = [
        p
        for p in ET.parse(svg).iter()
        if p.tag.endswith("}path")
        and p.attrib.get("stroke") == "rgb(0%, 0%, 50.196838%)"
        and p.attrib.get("stroke-width") == "8.984"
    ]
    assert len(paths) == 4
    x0, x8, top, bottom, pmax = part["axes"]
    points = []
    for path in paths:
        matrix = [float(n) for n in re.findall(NUMBER, path.attrib["transform"])]
        assert len(matrix) == 6 and matrix[1] == matrix[2] == 0
        commands = path.attrib["d"]
        assert set(re.findall(r"[A-Za-z]", commands)) <= {"M", "L"}
        values = [float(n) for n in re.findall(NUMBER, commands)]
        assert len(values) % 2 == 0
        for x, y in zip(values[::2], values[1::2]):
            x, y = matrix[0] * x + matrix[4], matrix[3] * y + matrix[5]
            q = (x - x0) / (x8 - x0) * 8
            p = (bottom - y) / (bottom - top) * pmax
            if q < -0.001 or p < -0.001:
                raise ValueError("Unexpected curve outside calibrated graph")
            points.append([max(q, 0), max(p, 0)])
    points.sort()
    assert abs(points[0][0]) < 0.001
    assert abs(points[-1][0] - part["free_cfm"]) < 0.01
    assert abs(points[0][1] - part["static_inH2O"]) < 0.001
    # Explicitly snap only the two endpoint graph-rounding errors.
    points[0] = [0, part["static_inH2O"]]
    points[-1] = [part["free_cfm"], 0]
    for a, b in zip(points, points[1:]):
        assert b[0] > a[0] and b[1] <= a[1] + 1e-5
    return points


def pressure(curve, total_m3h, speed_ratio=1):
    """Affinity-law sensitivity, not a guaranteed hot or installed fan curve."""
    if total_m3h < 0 or not 0 < speed_ratio <= 1:
        raise ValueError("Invalid flow/speed")
    q = total_m3h / 2 / CFM_TO_M3H / speed_ratio
    if q > curve[-1][0]:
        return None
    for (q0, p0), (q1, p1) in zip(curve, curve[1:]):
        if q0 <= q <= q1:
            p = p0 + (p1 - p0) * (q - q0) / (q1 - q0)
            return p * 249.08891 * speed_ratio**2 * (298.15 / 313.15)
    raise AssertionError("No interpolation segment")


def main():
    ROOT.mkdir(exist_ok=True)
    generated = ROOT / "generated"
    generated.mkdir(exist_ok=True)
    ap = json.loads((AP / "analysis.json").read_text())
    result = dict(
        revision="SF01-unadopted-exact-tach-fan-comparison",
        parts={},
        AP01_handoff_sha256=sha(AP / "handoff.json"),
        air_path_target=ap["candidate_air_path"],
        rated_voltage_v=5,
        operating_voltage_v=[3.5, 6],
        starting_voltage_v=3.5,
        starting_test_temperature_c=25,
        speed_tolerance_fraction=0.15,
        temperature_range_c=[-10, 70],
        fan_frame_max_mm=[40.5, 40.5, 10.5],
        thickness_min_mm=10,
        mounting_pitch_mm=32,
        mounting_pitch_tolerance_mm=0.3,
        mounting_hole_diameter_mm=4.3,
        hole_diameter_tolerance_mm=0.3,
        wire_AWG=26,
        wire_length_mm=[290, 310],
        tach=dict(
            pulses_per_revolution=2,
            max_pullup_v=6,
            max_sink_ma=5,
            max_low_v=0.5,
            electrical_rows_test_condition="25C/rated5V; no hot/partial-power guarantee",
            locked_output_can_be_high_or_low=True,
        ),
        physical_qualified=False,
        installed_flow_verified=False,
        installed_noise_verified=False,
        fabrication_released=False,
    )
    for name, part in PARTS.items():
        assert sha(Path(part["pdf"])) == part["expected_pdf_sha256"]
        svg = generated / (name + "-curve.svg")
        subprocess.run(["pdftocairo", "-svg", "-f", "5", "-l", "5", part["pdf"], str(svg)], check=True)
        curve = extract_curve(svg, part)
        provision = 1.2 * 2 * part["current_max_a"]
        cases = []
        for speed in [1, 0.85, 0.85 * 4.8 / 5]:
            p = pressure(curve, 9.2, speed)
            for cd in [0.6, 0.75, 0.9]:
                ports = 2 * orifice_drop(8, 2200, cd)
                for area in [ap["existing_guard"]["actual_48gon_net_open_area_each_mm2"], 800]:
                    guard = orifice_drop(4.6, area, cd)
                    cases.append(
                        dict(
                            assumed_speed_ratio=speed,
                            assumed_Cd=cd,
                            guard_area_each_mm2=area,
                            pressure_sensitivity_pa=p,
                            interior_ports_loss_pa=ports,
                            guard_loss_pa=guard,
                            remaining_channel_pressure_sensitivity_pa=p - ports - guard,
                        )
                    )
        result["parts"][name] = dict(
            **part,
            pdf_sha256=sha(Path(part["pdf"])),
            extracted_svg_sha256=sha(svg),
            curve_points_cfm_inH2O=curve,
            two_fan_twenty_percent_current_provision_a=provision,
            remaining_digital_reserve_a=0.416 - provision,
            known_plus_fans_a=1.984 + provision,
            pressure_cases=cases,
            current_bound_applies_to_hot_installed_startup_or_locked_rotor=False,
            actual_source_to_fan_voltage_interval_v=None,
            exact_clamp_shim_and_harness_implemented=False,
        )
    result["preferred_prototype_candidate"] = "V1"
    result["selection_basis"] = (
        "V1 leaves5.080Pa in the most adverse tested new800mm2 guard case; V2 leaves only0.019Pa. Neither sensitivity is a physical pressure guarantee."
    )
    result["receiving_conditions"] = [
        "The max current/power rows are not a startup/stall waveform or full-temperature installed bound; catalogue current tests are25C/freeair after10min.",
        "The1.2 current factor is planning reserve, not a certified physical maximum. Fan controller/tach current must share remaining reserve.",
        "The0.85 speed and0.85*(4.8/5) affinity models are sensitivities, not guaranteed voltage/speed or pressure lower envelopes.",
        "20% starting-voltage target4.2V is based on25C/freeair3.5V starting only; hot/installed restart needs characterization.",
        "Exact old1000U model data is used. The2026 catalogue10000 model is not silently substituted.",
        "Thinner10..10.5mm fan requires a new clamping stack. Old12.5mm receiving planes are not actual contacting faces.",
        "Manufacturer suggestsM4 mounting and torque; any M3 floating-bolt alternative needs explicit structural/clamp qualification.",
        "No protection, connectors, strain relief, partial-power, ESD, fault shutoff, tach interface or firmware is implemented here.",
        "No fan curve supplies the unknown board/channel/pin loss or proves local component temperatures.",
    ]
    sources = [Path(__file__), AP / "analysis.json", AP / "handoff.json", AP / "analyze.py"]
    result["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in sources}
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    for name, part in result["parts"].items():
        adverse = next(
            r
            for r in part["pressure_cases"]
            if r["assumed_Cd"] == 0.6
            and r["guard_area_each_mm2"] == 800
            and r["assumed_speed_ratio"] == 0.85 * 4.8 / 5
        )
        print(
            name,
            "current provision",
            round(part["two_fan_twenty_percent_current_provision_a"], 4),
            "A; remaining",
            round(part["remaining_digital_reserve_a"], 4),
            "A; adverse model remaining pressure",
            round(adverse["remaining_channel_pressure_sensitivity_pa"], 3),
            "Pa",
        )


if __name__ == "__main__":
    main()
