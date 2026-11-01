"""Join a frozen ground matrix to its actual signed-current electrode ledger.

Package pins are separate electrodes. Unknown current sharing produces a
coefficient interval, never an assumed equal split. This diagnostic does not
invent missing source/load currents or qualify an endpoint voltage.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
POWER = REPO / "hardware/electronics/power_distribution/p03"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def interval_product(a, b):
    """Closed interval product; signed currents may reverse endpoint order."""
    assert len(a) == len(b) == 2
    assert all(math.isfinite(x) for x in (*a, *b))
    assert a[0] <= a[1] and b[0] <= b[1]
    values = [x * y for x in a for y in b]
    return [min(values), max(values)]


def current_terms(case, ledger):
    modes = case.get("ideal_dc_source_ground_sensitivity", {})
    declared = []
    for row in ledger["dc_converter_electrodes"]:
        declared.append(
            dict(
                electrodes=[row["ref"] + "." + pin for pin in row["pins"]],
                signed_total_current_expression_a=row["expression"],
                signed_total_current_interval_a=None,
                package_current_sharing_verified=False,
            )
        )
    for row in ledger["local_static_current_electrodes"]:
        current = row["signed_current_a"]
        declared.append(
            dict(
                electrodes=[row["ref"] + "." + row["pin"]],
                signed_total_current_expression_a=None,
                signed_total_current_interval_a=[current, current],
                scenario_scope=row["scope"],
            )
        )
    missing = sorted({key for row in declared for key in row["electrodes"] if key not in case["ports"]})
    observers = {}
    for name, mode in modes.items():
        coefficients = mode["ohm_by_unit_ground_injection"]
        rows, static = [], [0.0, 0.0]
        for declared_row in declared:
            row = dict(declared_row)
            unresolved = [key for key in row["electrodes"] if key not in coefficients]
            row["unresolved_electrodes"] = unresolved
            row["coefficient_interval_ohm"] = None
            row["scenario_contribution_interval_v"] = None
            if not unresolved:
                values = {key: coefficients[key] for key in row["electrodes"]}
                row["coefficient_by_electrode_ohm"] = values
                row["coefficient_interval_ohm"] = [min(values.values()), max(values.values())]
                # This interval applies to any nonnegative fractions of the
                # aggregate signed current. It does not permit arbitrary
                # circulating package currents; those require a separate model.
                row["sharing_model"] = "Unknown nonnegative fractions summing to one; no equal split"
                interval = row["signed_total_current_interval_a"]
                if interval is not None:
                    contribution = interval_product(row["coefficient_interval_ohm"], interval)
                    row["scenario_contribution_interval_v"] = contribution
                    static = [static[index] + contribution[index] for index in range(2)]
            rows.append(row)
        observers[name] = dict(
            current_terms=rows,
            local_static_terms_only_interval_v=None if missing else static,
            includes_converter_or_downstream_currents=False,
        )
    return dict(
        grid_mm=case["grid_mm"],
        matrix_status=case["status"],
        ledger_unresolved_electrodes=missing,
        native_noncapacitive_ground_electrodes_unresolved=case["unresolved_ports"],
        observer_sensitivities=observers,
        complete_signed_current_solution=False,
    )


def generate(snapshot, ledger_path):
    snapshot = snapshot.resolve()
    matrix_path = snapshot / "verification.json"
    inputs = {matrix_path: matrix_path.read_bytes(), ledger_path: ledger_path.read_bytes()}
    matrix = json.loads(inputs[matrix_path])
    ledger = json.loads(inputs[ledger_path])
    board_key = "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    if ledger["source_sha256"].get(board_key) != matrix["native_pcb_sha256"]:
        raise ValueError("Current ledger and ground matrix refer to different native PCBs")
    for name, expected in ledger["source_sha256"].items():
        path = REPO / name
        data = path.read_bytes()
        if digest(data) != expected:
            raise ValueError((name, "Current ledger source is stale; use matching frozen inputs"))
        inputs[path] = data
    # Grid reports are independently bound by the matrix receipt. Never accept
    # a modified transfer response just because it has the expected field names.
    for case in matrix["cases"]:
        path = snapshot / f"grid-{case['grid_mm']:g}.json"
        data = path.read_bytes()
        if digest(data) != matrix["evidence_sha256"].get(str(path.relative_to(REPO))):
            raise ValueError((path, "Matrix grid artifact does not match receipt"))
        if json.loads(data) != case:
            raise ValueError((path, "Matrix embedded case differs from grid artifact"))
        inputs[path] = data
    model = Path(__file__).resolve()
    inputs[model] = model.read_bytes()
    cases = [current_terms(case, ledger) for case in matrix["cases"]]
    output = snapshot / "signed-current-diagnostic"
    output.mkdir(exist_ok=True)
    frozen = {}
    for path, data in inputs.items():
        name = str(path.relative_to(REPO))
        target = output / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        frozen[str(target.relative_to(REPO))] = digest(data)
    report = dict(
        scope="Source-bound symbolic converter currents and declared static-current scenarios only",
        native_pcb_sha256=matrix["native_pcb_sha256"],
        source_sha256={str(path.relative_to(REPO)): digest(data) for path, data in inputs.items()},
        frozen_input_sha256=frozen,
        cases=cases,
        omitted_or_unclosed_current_terms=ledger["omitted_or_unclosed_current_terms"],
        limitations=[
            "No unknown current is set to zero; converter expressions remain symbolic",
            "Local static terms are only the ledger's declared allocations, not guaranteed complete IC currents",
            "Package sharing intervals exclude unbounded internal circulating current",
            "Material, discretization, contacts, external return network and real feedback loops remain unqualified",
        ],
        complete_endpoint_voltage_budget_closed=False,
        physical_tests_performed=0,
        fabrication_released=False,
        build_ready=False,
    )
    assert all(path.read_bytes() == data for path, data in inputs.items()), "Inputs changed during capture"
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, default=POWER / "generated/dc-current-ports.json")
    args = parser.parse_args()
    generate(args.snapshot, args.ledger.resolve())
