"""One new coarse finite-PDN diagnostic on actual dc55/newfilled copper, never a bound."""

import hashlib
import itertools
import json
from pathlib import Path

from mesh import Mesh, response

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sources"
BOARD = SRC / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-r1"
S1 = dict(
    name="S1-unaccepted-four70um",
    copper_mm=[0.070] * 4,
    centroids_mm=[0.035, 0.285, 1.315, 1.565],
    dielectric_mm=[0.18, 0.96, 0.18],
    finished_barrel_wall_mm=0.025,
    total_board_nominal_mm=1.6,
    rho20_sheet_ohm_mm=1.724e-5,
    rho20_barrel_ohm_mm=2e-5,
    alpha_per_c=0.00393,
    uniform_temperature_scenario_c=100,
    material_stackup_temperature_or_process_accepted=False,
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    pcb = BOARD / "generated/filled.kicad_pcb"
    padpath = ROOT / "generated/pads.json"
    pads = json.loads((padpath).read_text())
    assert pads["source_pcb_sha256"] == sha(pcb)
    assert sha(pcb) == "90526f6808b97753f8a1e5c3c281ec3b01504860c96c2574050c784f5112b130"
    assert pads["unnetted_NPTH_pads_included_for_hole_voids"]
    tree = read_sexpr(pcb.read_text())
    _, pins = netlist(BOARD / "generated/netlist.xml")
    manifest = json.loads((SRC / "hardware/wiring/generated/system-interconnect.json").read_text())["wires"]
    outward = set()
    for w in manifest:
        if w["net"] == "AGND":
            for board, ref, pin in [w["from"], w["to"]]:
                if board == "processor_carrier" and ref != "J1":
                    outward.add(ref + "." + pin)
    outward |= {"J14.2", "J15.2"}
    ground = outward | {"U1.20", "U1.40"}
    assert len(ground) == 23 and all(pins[ref][pin] == "AGND" for ref, pin in (p.split(".") for p in ground))
    for p in ["J13.1", "J13.2"]:
        assert p.split(".")[0] in pins
    definitions = {
        "5V_DIG": dict(
            source=("J13.1", "F.Cu"),
            drives={
                "seed": ("R1.1", "F.Cu"),
                "led": ("J11.2", "F.Cu"),
                "bypass": ("J14.1", "F.Cu"),
                "monitor": ("J15.1", "F.Cu"),
            },
            measures={
                "seed": ("R1.1", "F.Cu"),
                "led": ("J11.2", "F.Cu"),
                "bypass": ("J14.1", "F.Cu"),
                "monitor": ("J15.1", "F.Cu"),
            },
        ),
        "SEED_VIN": dict(
            source=("R1.2", "F.Cu"), drives={"seed": ("U1.39", "F.Cu")}, measures={"seed": ("U1.39", "F.Cu")}
        ),
        "AGND": dict(
            source=("J13.2", "F.Cu"),
            drives={p: (p, "F.Cu") for p in sorted(ground)},
            measures={
                **{p: (p, "F.Cu") for p in sorted(ground)},
                **{f"C{i}.2": (f"C{i}.2", "B.Cu") for i in range(11, 21)},
            },
        ),
    }
    paths = [
        pcb,
        padpath,
        BOARD / "generated/netlist.xml",
        BOARD / "generated/fanout-ledger.json",
        ROOT / "mesh.py",
        ROOT / "native_pads.py",
        Path(__file__),
        ROOT / "capture.json",
        SRC / "hardware/wiring/generated/system-interconnect.json",
    ]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    results = {}
    for net, d in definitions.items():
        print("RASTER", net, 0.2, flush=True)
        m = Mesh(tree, pads, net, 0.2)
        assert m.bounds == (100.0, 100.0, 264.5, 165.0)
        n = m.network(S1["copper_mm"], S1["centroids_mm"], wall_mm=0.025, temp=100)
        print("FACTOR", net, n["n"], "nodes", flush=True)
        result = response(n, **d)
        result.update(
            finite_physical_barrels=n["finite_holes"],
            all_native_drill_voids=len(m.all_holes),
            maximum_wall_attachment_displacement_mm=n["maximum_wall_attachment_displacement_mm"],
            copper_area_per_layer_mm2=n["copper_area_per_layer_mm2"],
            bounds_native_mm=m.bounds,
        )
        results[net] = result
        print("SOLVED", net, result["max_absolute_kcl_residual_a"], flush=True)
        # Keep each successful net even if a later thin feature is unresolved.
        (ROOT / "generated/coarse-network-progress.json").write_text(
            json.dumps(
                dict(
                    source_sha256=hashes, scenario=S1, grid_mm=0.2, networks=results, physical_qualified=False
                ),
                indent=2,
            )
            + "\n"
        )
    pos = results["5V_DIG"]["transfer_resistance_ohm"]
    g = results["AGND"]["transfer_resistance_ohm"]
    seedtrack = results["SEED_VIN"]["transfer_resistance_ohm"]["seed"]["seed"]
    base = {"seed": 1.0, "led": 0.764, "bypass": 0.14, "monitor": 0.08}
    fixtures = []

    def ground_voltage(currents, target):
        return sum(i * g[port][target] for port, i in currents.items() if port != "J13.2")

    for reserve_at in [None, "bypass", "monitor"]:
        loads = dict(base)
        if reserve_at:
            loads[reserve_at] += 0.416
        for seedpin, ledpin, converterpin, controlpin, monitorpin in itertools.product(
            ["U1.20", "U1.40"], ["J11.1", "J11.8"], ["J5.1", "J6.1"], ["J2.1", "J4.1"], ["J15.2", "J13.2"]
        ):
            currents = {}
            for port, i in [
                (seedpin, 0.925),
                (ledpin, 0.764),
                ("J14.2", loads["bypass"]),
                ("J15.2", loads["monitor"]),
                (converterpin, 0.035),
                (controlpin, 0.020),
                (monitorpin, 0.020),
            ]:
                currents[port] = currents.get(port, 0) + i
            assert abs(sum(currents.values()) - sum(loads.values())) < 1e-12
            positive = {target: sum(i * pos[name][target] for name, i in loads.items()) for target in loads}
            ports = {"seed": seedpin, "led": ledpin, "bypass": "J14.2", "monitor": "J15.2"}
            loop = {
                target: positive[target]
                + ground_voltage(currents, port)
                + (seedtrack if target == "seed" else 0)
                for target, port in ports.items()
            }
            quiet = {
                f"C{i}.2": ground_voltage(currents, f"C{i}.2") - ground_voltage(currents, seedpin)
                for i in range(11, 21)
            }
            fixtures.append(
                dict(
                    hypothetical_reserve_fixture_at=reserve_at,
                    not_a_complete_arbitrary_reserve_bound=bool(reserve_at),
                    positive_loads_a=loads,
                    total_input_allocation_or_fixture_a=sum(loads.values()),
                    ground_fixture_injections_a=currents,
                    actual_unmodeled_remote_loops_zero_not_proven=True,
                    source_reference_injection_cancels_in_plane_but_not_external_lead=currents.get(
                        "J13.2", 0
                    ),
                    positive_only_copper_drop_v=positive,
                    local_fixture_loop_copper_drop_v=loop,
                    Seed_R1_initial_tolerance_only_drop_v=0.47 * 1.01,
                    quiet_to_Seed_reference_fixture_offsets_v=quiet,
                    complete_physical_return_solution=False,
                )
            )
    summaries = {}
    for reserve in [None, "bypass", "monitor"]:
        rows = [x for x in fixtures if x["hypothetical_reserve_fixture_at"] == reserve]
        summaries[str(reserve)] = {
            k: [
                min(x["local_fixture_loop_copper_drop_v"][k] for x in rows),
                max(x["local_fixture_loop_copper_drop_v"][k] for x in rows),
            ]
            for k in base
        }
    assert all(sha(ROOT / p) == h for p, h in hashes.items())
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        grid_mm=0.2,
        lattice_origin_offset_mm=[0.025, 0.025],
        scenario=S1,
        network_temperature_c=100,
        networks=results,
        above_board_source_face="F.Cu",
        source_electrode_process_assumption="Uniform finite F-face annulus injection, not a measured solder-current distribution; process/material bounds unaccepted",
        outward_AGND_ports=sorted(outward),
        all_AGND_drive_ports=sorted(ground),
        old_J1_unfitted_not_driven=True,
        known_positive_allocations_a=base,
        known_positive_total_a=1.984,
        input_max_target_a=2.4,
        reserve_unassigned_a=0.416,
        nested_3v3_child_exports_a={"converter": 0.035, "controls": 0.020, "monitor": 0.020},
        Seed_local_return_for_known_exports_a=0.925,
        fixture_corners=fixtures,
        fixture_loop_copper_drop_intervals_v=summaries,
        fixture_scope="Conditional direct-return placement alternatives only; actual remote coupled ground/circulating currents are NOT bounded by these corners. Full23-port matrix retains symbolic unknown terms. Reserve fixtures atJ14/J15 do not change .140/.080A targetboard requirements or bound any unimplemented reserve endpoint.",
        missing_terms=[
            "Actual targetboardPCBs/mating/harness topology and resistance",
            "3V3bypass/LEDlogic,GPIO/pot/passive/SD peak currents and return sharing",
            "Coupled E28/P03/source-feedback/bar and externalAGNDloops",
            "Actual copper/wall/stack/material/temperature and current-injection distribution",
            "Accepted R1full-temperature/aging/thermal/current load",
            "ACimpedance/effectiveC/stability/dynamics/noise/ampacity/thermal",
        ],
        cold20_scaling_if_same_uniform_material_model_only=1 / (1 + 0.00393 * 80),
        cold_scaled_values_are_not_an_independent_temperature_or_refinement_run=True,
        spatial_refinement_performed=False,
        mechanical_result_gate_before_large_sweep=True,
        prior_matrix_inherited=False,
        full_source_to_load_PDN_solved=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated/coarse.json").write_text(json.dumps(report, indent=2) + "\n")
    print("COARSE SUMMARY", summaries, flush=True)


if __name__ == "__main__":
    run()
