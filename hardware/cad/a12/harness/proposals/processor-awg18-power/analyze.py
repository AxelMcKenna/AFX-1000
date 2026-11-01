"""Actual four-layer E19 multiport DC diagnostic, never a physical PDN pass."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from mesh import Mesh, response

from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent
SCENARIOS = {
    "cu35": dict(
        copper_mm=[0.035] * 4, centroids_mm=[0.0175, 0.2525, 1.3475, 1.5825], dielectric_mm=[0.2, 1.06, 0.2]
    ),
    "cu70": dict(
        copper_mm=[0.070] * 4, centroids_mm=[0.035, 0.285, 1.315, 1.565], dielectric_mm=[0.18, 0.96, 0.18]
    ),
}


def run(baseline, step, scenario):
    folder = ROOT / "generated" / ("baseline" if baseline else "")
    pcb = folder / "filled.kicad_pcb"
    pads = json.loads((folder / "pads.json").read_text())

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    assert pads["source_pcb_sha256"] == sha(pcb)
    tree = read_sexpr(pcb.read_text())
    s = SCENARIOS[scenario]
    results = {}
    code_paths = [ROOT / "analyze.py", ROOT / "mesh.py", ROOT / "native_pads.py", pcb, folder / "pads.json"]
    captured = {str(p.relative_to(ROOT)): sha(p) for p in code_paths}
    definitions = {
        "5V_DIG": dict(
            source=("J1.1", "B.Cu"),
            drives={"seed": ("R1.1", "F.Cu"), "led": ("J11.2", "F.Cu")},
            measures={"seed": ("R1.1", "F.Cu"), "led": ("J11.2", "F.Cu")},
        ),
        "SEED_VIN": dict(
            source=("R1.2", "F.Cu"), drives={"seed": ("U1.39", "F.Cu")}, measures={"seed": ("U1.39", "F.Cu")}
        ),
        "AGND": dict(
            source=("J1.2", "B.Cu"),
            drives={
                name: (name, "F.Cu")
                for name in ["U1.20", "U1.40", "J11.1", "J11.8", "J2.1", "J4.1", "J5.1", "J6.1"]
            },
            measures={
                name: (name, "F.Cu" if not name.startswith(("C1", "C2")) else "B.Cu")
                for name in [
                    "U1.20",
                    "U1.40",
                    "J11.1",
                    "J11.8",
                    "J2.1",
                    "J4.1",
                    "J5.1",
                    "J6.1",
                    *[f"J{i}.1" for i in range(20, 30)],
                    *[f"C{i}.2" for i in range(11, 21)],
                ]
            },
        ),
    }
    for net, d in definitions.items():
        print("Raster", baseline, step, scenario, net, flush=True)
        m = Mesh(tree, pads, net, step)
        cases = {}
        for temp in [20, 100]:
            n = m.network(s["copper_mm"], s["centroids_mm"], wall_mm=0.025, temp=temp)
            r = response(n, **d)
            r.update(
                finite_physical_holes=n["finite_holes"],
                maximum_wall_attachment_displacement_mm=n["maximum_wall_attachment_displacement_mm"],
                actual_copper_area_per_layer_mm2=n["copper_area_per_layer_mm2"],
            )
            cases[str(temp)] = r
            print("Solved", net, temp, r["nodes"], r["max_absolute_kcl_residual_a"], flush=True)
        results[net] = cases
    report = dict(
        scope=__doc__,
        source_pcb_sha256=sha(pcb),
        native_pad_polygons_sha256=sha(folder / "pads.json"),
        source_sha256=captured,
        baseline=baseline,
        grid_mm=step,
        scenario=dict(
            name=scenario,
            **s,
            total_thickness_mm=1.6,
            wall_mm=0.025,
            copper_resistivity_20c_ohm_mm=1.724e-5,
            barrel_resistivity_20c_ohm_mm=2e-5,
            temperature_coefficient_per_c=0.00393,
            fabricator_or_material_accepted=False,
        ),
        networks=results,
        nominal_loads_a=dict(seed_including_nested_3v3=1.0, led_5v=0.764),
        nested_3v3_exports_a=dict(converter=0.035, controls=0.020, monitor=0.020),
        unknowns=[
            "Actual connector/socket internal resistance and current/return division",
            "3V3 currents and external return sharing",
            "LED logic3V3 and GPIO/passive currents",
            "Measured solder/wire/complete interface resistance",
            "Full coupled external AGND loops and source feedback offset",
            "Accepted copper, wall, stack, process, material and operating temperature",
            "AC impedance, effective capacitors, dynamic/noise/ampacity/thermal",
        ],
        endpoint_physical_qualified=False,
        complete_pdn_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    # Full independent Seed/LED return-sharing corners. Nested export removes
    # .075A from local Seed return; its remote ground distribution stays symbolic.
    summaries = {}
    for temp in ["20", "100"]:
        pos = results["5V_DIG"][temp]["transfer_resistance_ohm"]
        seedtrack = results["SEED_VIN"][temp]["transfer_resistance_ohm"]["seed"]["seed"]
        g = results["AGND"][temp]["transfer_resistance_ohm"]
        positive = {target: pos["seed"][target] + 0.764 * pos["led"][target] for target in ["seed", "led"]}
        rows = []
        for sp, lp in itertools.product(["U1.20", "U1.40"], ["J11.1", "J11.8"]):
            # This is the local DC portion only. Missing remote .075A returns
            # are NOT zeroed into a claimed complete endpoint computation.
            local = {q: 0.925 * g[sp][q] + 0.764 * g[lp][q] for q in g[sp]}
            rows.append(
                dict(
                    seed_return_pin=sp,
                    led_return_pin=lp,
                    positive_only_drop_v=positive,
                    seed_local_loop_drop_before_R1_v=positive["seed"] + seedtrack + local[sp],
                    seed_R1_initial_tolerance_only_drop_at_1a_v=0.47 * 1.01,
                    led_local_loop_drop_v=positive["led"] + local[lp],
                    quiet_front_filter_to_seed_offset_v={
                        q: local[q] - local[sp] for q in local if q.startswith("C")
                    },
                    omitted_remote_return_current_a=0.075,
                    complete_return_solution=False,
                )
            )
        summaries[temp] = rows
    assert all(sha(ROOT / n) == digest for n, digest in captured.items()), (
        "Native/model source changed during solve"
    )
    report["local_simultaneous_sharing_corners"] = summaries
    target = ROOT / "generated" / f"{'baseline' if baseline else 'repair'}-{scenario}-grid{step:g}.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print("WROTE", target, flush=True)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", action="store_true")
    p.add_argument("--step", type=float, default=0.2)
    p.add_argument("--scenario", choices=SCENARIOS, default="cu35")
    a = p.parse_args()
    run(a.baseline, a.step, a.scenario)
