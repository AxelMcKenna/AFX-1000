#!/usr/bin/env python3
"""Native E05 ERC, pin/interface audit and exported-netlist circuit analysis.

The AC solver uses ideal op-amps, resistors, capacitors and settled contacts.
It does not establish semiconductor distortion, stability, noise or bench fit.
"""

import argparse
import cmath
import datetime
import hashlib
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..common.circuits import linear_solve
from ..common.netlists import netlist as netlist
from ..common.netlists import number as number
from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
CONTRACT = {
    "U1": {
        "1": "M_DRV_L",
        "2": "M_FB_L",
        "3": "RECV_L",
        "4": "N19",
        "5": "RECV_R",
        "6": "M_FB_R",
        "7": "M_DRV_R",
        "8": "P19",
    },
    "U2": {
        "1": "S_DRV_L",
        "2": "S_FB_L",
        "3": "RECV_L",
        "4": "N12",
        "5": "RECV_R",
        "6": "S_FB_R",
        "7": "S_DRV_R",
        "8": "P12",
    },
    "K3": {
        "1": "5V",
        "8": "GAIN_LOW",
        "3": "PROC_OUT_L",
        "2": "M_AC_L",
        "4": "S_AC_L",
        "6": "PROC_OUT_R",
        "7": "M_AC_R",
        "5": "S_AC_R",
    },
    "J1": {"1": "RECV_L", "2": "AGND", "3": "RECV_R"},
    "J2": {"1": "PROC_OUT_L", "2": "AGND", "3": "PROC_OUT_R"},
    "J3": {"1": "5V", "2": "GAIN_LOW"},
    "J4": {"1": "P19", "2": "AGND", "3": "N19", "4": "P12", "5": "N12"},
    "R17": {"1": "RECV_L", "2": "AGND"},
    "R18": {"1": "RECV_R", "2": "AGND"},
}
STAGES = []
for i, (mode, ch, amp) in enumerate([("M", "L", "U1"), ("M", "R", "U1"), ("S", "L", "U2"), ("S", "R", "U2")]):
    names = [mode + "_" + node + "_" + ch for node in ("FB", "DRV", "SER", "AC")]
    fb, drive, series, ac = names
    for ref, a, b in [
        (f"R{4 * i + 1}", fb, drive),
        (f"R{4 * i + 2}", fb, "AGND"),
        (f"R{4 * i + 3}", drive, series),
        (f"R{4 * i + 4}", ac, "AGND"),
        (f"C{i + 1}", series, ac),
        (f"C{i + 13}", series, ac),
    ]:
        CONTRACT[ref] = {"1": a, "2": b}
    STAGES.append(
        dict(
            mode=mode,
            channel=ch,
            amp=amp,
            rf=f"R{4 * i + 1}",
            rg=f"R{4 * i + 2}",
            rs=f"R{4 * i + 3}",
            bleed=f"R{4 * i + 4}",
            caps=[f"C{i + 1}", f"C{i + 13}"],
        )
    )
for i, rail in enumerate(("P19", "N19", "P12", "N12")):
    CONTRACT[f"C{i + 5}"] = CONTRACT[f"C{i + 9}"] = {"1": rail, "2": "AGND"}


def ac_solve(parts, pins, frequency, send, channel):
    # Collapse only the selected physical relay contacts, independently of the
    # drawing. The unused driver keeps its own 20k discharge load.
    parent = {}

    def root(name):
        parent.setdefault(name, name)
        if parent[name] != name:
            parent[name] = root(parent[name])
        return parent[name]

    for common, nc, no in [("3", "2", "4"), ("6", "7", "5")]:
        parent[root(pins["K3"][common])] = root(pins["K3"][no if send else nc])
    fixed = {root(n): 0j for n in ("AGND", "P19", "N19", "P12", "N12", "5V", "GAIN_LOW")}
    fixed[root("RECV_L")] = 1 + 0j if channel == "L" else 0j
    fixed[root("RECV_R")] = 1 + 0j if channel == "R" else 0j
    branches = []
    for ref, c in parts.items():
        if ref.startswith(("R", "C")):
            a, b = root(pins[ref]["1"]), root(pins[ref]["2"])
            value = number(c.findtext("value"))
            y = 1 / value if ref.startswith("R") else 2j * math.pi * frequency * value
            branches.append((a, b, y))
    for pin in ("1", "3"):
        branches.append((root(pins["J2"][pin]), root("AGND"), 1 / 10000))
    amps = []
    for ref in ("U1", "U2"):
        for positive, negative, output in [("3", "2", "1"), ("5", "6", "7")]:
            amps.append(tuple(root(pins[ref][p]) for p in (positive, negative, output)))
    nodes = sorted(({n for a, b, _ in branches for n in (a, b)} | {n for a in amps for n in a}) - set(fixed))
    index = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    size = n + len(amps)
    matrix = [[0j] * size for _ in range(size)]
    rhs = [0j] * size

    def coefficient(row, node, value):
        if node in fixed:
            rhs[row] -= value * fixed[node]
        else:
            matrix[row][index[node]] += value

    for a, b, y in branches:
        for x, z in ((a, b), (b, a)):
            if x not in fixed:
                row = index[x]
                coefficient(row, x, y)
                coefficient(row, z, -y)
    for k, (positive, negative, output) in enumerate(amps):
        matrix[index[output]][n + k] += 1
        coefficient(n + k, positive, 1)
        coefficient(n + k, negative, -1)
    values = dict(zip(nodes, linear_solve(matrix, rhs)))
    values.update(fixed)
    return {ch: values[root(pins["J2"][pin])] for ch, pin in [("L", "1"), ("R", "3")]}


def parallel(a, b):
    return a * b / (a + b)


def circuit_analysis(parts, pins):
    nominal = []
    corners = []
    responses = []
    thermal = []
    voltage = []
    noise = []
    dc = []
    for stage in STAGES:
        mode, ch = stage["mode"], stage["channel"]
        rf, rg, rs, bleed = [number(parts[stage[k]].findtext("value")) for k in ("rf", "rg", "rs", "bleed")]
        ca, cb = [number(parts[ref].findtext("value")) for ref in stage["caps"]]
        cap = ca + cb
        assert math.isclose(rf, 5230 if mode == "M" else 1210)
        assert math.isclose(rg, 1000 if mode == "M" else 2000)
        assert (rs, bleed) == (100, 20000) and math.isclose(ca, 4.7e-6) and math.isclose(cb, 4.7e-6)
        gain = 1 + rf / rg
        load = parallel(bleed, 10000)
        target = 0.775 * 10 ** (0.2) * 10 if mode == "M" else math.sqrt(10)

        def transfer(frequency, rff=rf, rgg=rg, rss=rs, bb=bleed, cc=cap):
            ll = parallel(bb, 10000)
            return (1 + rff / rgg) * ll / (rss + ll + 1 / (2j * math.pi * frequency * cc))

        v = 2 * abs(transfer(1000))
        load_at_amp = parallel(rf + rg, rs + load)
        assert load_at_amp > 2000, (mode, load_at_amp)
        row = dict(
            mode=mode,
            channel=ch,
            ideal_closed_loop_gain=gain,
            loaded_1khz_full_scale_rms_v=v,
            target_full_scale_rms_v=target,
            nominal_scale_error_db=20 * math.log10(v / target),
            passive_20hz_relative_1khz_db=20 * math.log10(abs(transfer(20) / transfer(1000))),
            effective_amplifier_load_ohm=load_at_amp,
            amplifier_peak_at_2vrms_input_v=2 * gain * math.sqrt(2),
            selected_highpass_corner_hz=1 / (2 * math.pi * cap * (rs + load)),
            unselected_discharge_time_constant_s=cap * (rs + bleed),
        )
        assert abs(row["nominal_scale_error_db"]) < 0.02
        nominal.append(row)
        # All six individual tolerance signs per stage: 0.1% feedback/ground,
        # 1% output/bleed resistors, 10% each film cap. Fixed 10k external load.
        extremes = []
        for signs in itertools.product((-1, 1), repeat=6):
            rr, gg, ss, bb, cca, ccb = [
                value * (1 + sign * tol)
                for value, sign, tol in zip(
                    (rf, rg, rs, bleed, ca, cb), signs, (0.001, 0.001, 0.01, 0.01, 0.1, 0.1)
                )
            ]
            cc = cca + ccb
            h20, h1k = transfer(20, rr, gg, ss, bb, cc), transfer(1000, rr, gg, ss, bb, cc)
            extremes.append(
                (
                    20 * math.log10(2 * abs(h1k) / target),
                    20 * math.log10(abs(h20 / h1k)),
                    parallel(rr + gg, ss + parallel(bb, 10000)),
                    cc * (ss + bb),
                )
            )
        corner = dict(
            mode=mode,
            channel=ch,
            cases=len(extremes),
            scale_error_db_range=[min(v[0] for v in extremes), max(v[0] for v in extremes)],
            coupling_20hz_loss_db_range=[min(v[1] for v in extremes), max(v[1] for v in extremes)],
            minimum_effective_amp_load_ohm=min(v[2] for v in extremes),
            maximum_unselected_discharge_time_constant_s=max(v[3] for v in extremes),
        )
        assert max(abs(x) for x in corner["scale_error_db_range"]) < 0.05
        assert corner["coupling_20hz_loss_db_range"][0] > -0.15
        assert corner["minimum_effective_amp_load_ohm"] > 2000
        corners.append(corner)
        for frequency in (20, 1000, 20000):
            result = ac_solve(parts, pins, frequency, mode == "S", ch)
            assert abs(result[ch] - transfer(frequency)) < 1e-9, (mode, ch, frequency, result)
            assert abs(result["R" if ch == "L" else "L"]) < 1e-12
            responses.append(
                dict(
                    mode=mode,
                    channel=ch,
                    frequency_hz=frequency,
                    magnitude=abs(result[ch]),
                    phase_degrees=math.degrees(cmath.phase(result[ch])),
                    opposite_channel_magnitude=abs(result["R" if ch == "L" else "L"]),
                )
            )
        zero = ac_solve(parts, pins, 0, mode == "S", ch)
        assert all(abs(v) < 1e-12 for v in zero.values())
        dc.append(
            dict(
                mode=mode,
                driven_channel=ch,
                dc_input_v=1,
                ideal_output_v={k: float(v.real) for k, v in zero.items()},
            )
        )
        rail, reserve, max_total = (19, 0.3, 40) if mode == "M" else (12, 0.6, 36)
        maximum_gain = 1 + (rf * 1.001) / (rg * 0.999)
        available = rail * 0.99 - reserve
        required = 2.02 * maximum_gain * math.sqrt(2)
        assert available > required and 2 * rail * 1.01 < max_total
        voltage.append(
            dict(
                mode=mode,
                channel=ch,
                rail_nominal_v=rail,
                rail_tolerance=0.01,
                recommended_max_total_supply_v=max_total,
                maximum_total_supply_v=2 * rail * 1.01,
                input_full_scale_nominal_rms_v=2,
                input_scale_tolerance_screen=0.01,
                worst_feedback_tolerance_gain=maximum_gain,
                required_peak_v=required,
                assumed_output_rail_reserve_v=reserve,
                screened_available_peak_v=available,
                screened_peak_margin_v=available - required,
                caveat="OPA2992 reserve from 40V/2k table reused at 38V; not a guaranteed reduced-supply result"
                if mode == "M"
                else "2k load condition; real stability, distortion and power ramps unmeasured",
            )
        )
        # Illustrative white-density calculation only. Frequencies where the
        # data sheet has more low-frequency noise are intentionally not called
        # validated. Numerical integration includes the actual passive coupling.
        en, inn = (7e-9, 60e-15) if mode == "M" else (1.1e-9, 1.7e-12)
        boltzmann = 1.380649e-23
        temperature = 298.15
        density = (
            (gain * en) ** 2
            + 4 * boltzmann * temperature * rf * gain
            + (inn * rf) ** 2
            + 4 * boltzmann * temperature * rs
        )
        total = 0
        last = None
        for step in range(1001):
            f = 20 * 1000 ** (step / 1000)
            zseries = rs + 1 / (2j * math.pi * f * cap)
            zout = 1 / (1 / zseries + 1 / bleed + 1 / 10000)
            h = abs(transfer(f) / gain)
            power = density * h * h + (4 * boltzmann * temperature / bleed) * abs(zout) ** 2
            if last:
                total += (power + last[1]) * (f - last[0]) / 2
            last = (f, power)
        noise.append(
            dict(
                mode=mode,
                channel=ch,
                assumed_flat_voltage_noise_nv_rt_hz=en * 1e9,
                assumed_flat_current_noise_pa_rt_hz=inn * 1e12,
                illustrative_unweighted_output_noise_uv=math.sqrt(total) * 1e6,
                bandwidth_hz=[20, 20000],
                temperature_k=temperature,
                exclusions=[
                    "1/f and frequency-dependent semiconductor noise",
                    "receiver/source noise and positive-input source impedance",
                    "capacitor losses, supplies, PCB coupling and component spread",
                ],
                unit_snr_verified=False,
            )
        )
    for mode, rail, iq, theta in [("M", 19, 0.00284, 131), ("S", 12, 0.0055, 150)]:
        rows = [v for v in nominal if v["mode"] == mode]
        vmax = rail * 1.01
        quiescent = 2 * (2 * vmax) * iq
        classb = 0
        for row in rows:
            amplitude = min(
                math.sqrt(2) * vmax / math.pi, row["amplifier_peak_at_2vrms_input_v"] / math.sqrt(2)
            )
            classb += (2 * vmax * math.sqrt(2) * amplitude / math.pi - amplitude**2) / row[
                "effective_amplifier_load_ohm"
            ]
        thermal.append(
            dict(
                mode=mode,
                max_rail_screen_v=vmax,
                max_per_channel_quiescent_a=iq,
                dual_package_quiescent_w=quiescent,
                ideal_class_b_additional_loss_bound_w=classb,
                package_power_screen_w=quiescent + classb,
                reference_theta_ja_c_per_w=theta,
                illustrative_temperature_rise_c=(quiescent + classb) * theta,
                assumptions="Both channels loaded, ideal class-B output, no PCB/airflow model; not a thermal guarantee",
            )
        )
    return dict(
        ideal_netlist_ac_cases=len(responses),
        tolerance_cases=sum(v["cases"] for v in corners),
        nominal=nominal,
        tolerance_corners=corners,
        ideal_ac=responses,
        ideal_dc=dc,
        voltage_screen=voltage,
        white_noise_screen=noise,
        thermal_screen=thermal,
        exclusions=[
            "Real op-amp transfer, stability, distortion, noise and overload recovery",
            "Capacitor ESR, loss, leakage and dielectric absorption",
            "Load cables, ESD, relay contact resistance/bounce and click amplitude",
            "Power ramps, protection operation, PCB thermal behavior and physical fit",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--footprint-dir", type=Path)
    args = parser.parse_args()
    cli = Path(shutil.which(args.kicad_cli) or args.kicad_cli).resolve()
    fp = args.footprint_dir
    if not fp:
        for candidate in [cli.parents[1] / "SharedSupport/footprints", Path("/usr/share/kicad/footprints")]:
            if candidate.is_dir():
                fp = candidate
                break
    if not fp:
        raise RuntimeError("Pass --footprint-dir for installed KiCad standard libraries")
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-output-kicad-") as temporary:
        temp = Path(temporary)
        env = dict(
            os.environ, KICAD_CONFIG_HOME=str(temp / "config"), KICAD10_FOOTPRINT_DIR=str(fp.resolve())
        )
        if Path("/System/Library/Fonts").is_dir():
            (temp / "cache").mkdir()
            font = temp / "fonts.conf"
            font.write_text(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>'
                + str(temp / "cache")
                + "</cachedir></fontconfig>"
            )
            env["FONTCONFIG_FILE"] = str(font)

        def run(*command):
            result = subprocess.run([str(cli), *map(str, command)], capture_output=True, text=True, env=env)
            if result.returncode:
                raise RuntimeError(f"{command}: {result.returncode}\n{result.stdout}\n{result.stderr}")
            return result.stdout.strip()

        version = run("version")
        run(
            "sch",
            "erc",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            ROOT / "output_stage.kicad_sch",
        )
        assert not any(s["violations"] for s in json.loads((OUT / "erc.json").read_text())["sheets"])
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            ROOT / "output_stage.kicad_sch",
        )
        parts, pins = netlist(OUT / "netlist.xml")
        assert pins == CONTRACT, (pins, CONTRACT)
        assert len(parts) == 41
        assert parts["U1"].findtext("value") == "OPA2992D" and parts["U2"].findtext("value") == "OPA1612AID"
        for i in [1, 2, 3, 4, 13, 14, 15, 16]:
            fields = {v.attrib["name"]: v.text for v in parts[f"C{i}"].findall("fields/field")}
            assert fields["MPN"] == "MKS2C044701O00KSSD", fields
        analysis = circuit_analysis(parts, pins)
        (OUT / "circuit-analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
        external = {}
        for name in ("bypass", "audio_bypass"):
            sheet = ROOT.parent / name / (name + ".kicad_sch")
            destination = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", destination, sheet)
            _, other = netlist(destination)
            if name == "bypass":
                assert other["J5"] == pins["J3"]
            else:
                assert [other["J3"][p] for p in ("4", "5", "6")] == [pins["J2"][p] for p in ("1", "2", "3")]
            external[name] = dict(
                schematic_sha256=hashlib.sha256(sheet.read_bytes()).hexdigest(), interface_matches=True
            )
        footprints = {}
        for ref, c in parts.items():
            identifier = c.findtext("footprint")
            library, name = identifier.split(":")
            path = fp / (library + ".pretty") / (name + ".kicad_mod")
            text = path.read_text()
            pads = set(re.findall(r'\(pad\s+"([^"]+)"', text))
            assert set(pins[ref]) <= pads, (ref, pads)
            footprints[ref] = dict(
                candidate=identifier,
                pad_numbers_match=True,
                library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                physical_fit_verified=False,
            )
        # The cap is nonpolar. Verify the real standard footprint lead spacing
        # and finished drill, rather than accepting its filename as evidence.
        capid = parts["C1"].findtext("footprint")
        library, name = capid.split(":")
        text = (fp / (library + ".pretty") / (name + ".kicad_mod")).read_text()
        pads = re.findall(
            r'\(pad\s+"([12])"\s+thru_hole\s+circle\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(size\s+[0-9.]+\s+[0-9.]+\)\s+\(drill\s+([0-9.]+)\)',
            text,
        )
        assert pads == [("1", "0", "0", "0.8"), ("2", "5", "0", "0.8")], pads
        run(
            "sch",
            "export",
            "svg",
            "--exclude-drawing-sheet",
            "-o",
            str(OUT) + os.sep,
            ROOT / "output_stage.kicad_sch",
        )
        files = [
            ROOT / f
            for f in [
                "generate.py",
                "verify.py",
                "output_stage.kicad_sch",
                "output_stage.kicad_pro",
                "RMX_E05.kicad_sym",
                "sym-lib-table",
                "fp-lib-table",
                "components.json",
                "bom.csv",
                "dependencies.json",
            ]
        ]
        report = dict(
            revision="E05",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=len(parts),
            erc_violations=0,
            exact_exported_pin_contract_matches=True,
            external_interfaces=external,
            ideal_ac_cases=analysis["ideal_netlist_ac_cases"],
            tolerance_cases=analysis["tolerance_cases"],
            ideal_dc_cases=len(analysis["ideal_dc"]),
            capacitor_lead_pitch_mm=5,
            capacitor_drill_mm=0.8,
            candidate_footprints=footprints,
            full_analog_schematic=False,
            pcb_routing_scope="not checked here; see generated/routing-verification.json",
            assembled=False,
            physical_audio_verified=False,
            source_hashes=source_hashes(ROOT, files),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC, 41 pin contracts, E02/E03 interfaces, 12 ideal AC and 256 tolerance cases passed. No PCB/bench claim."
    )


if __name__ == "__main__":
    main()
