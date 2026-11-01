"""Diagnostic native P03 DC ground-transfer matrix with finite via barrels.

No ideal common P03 ground is assumed. Mesh/material/electrode assumptions are
explicit and unqualified; this is not a certified resistance or voltage bound.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu

from hardware.electronics.common.netlists import number
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.rail_disconnect.revision28.copper import LAYERS, Mesh, Union

REPO = Path(__file__).resolve().parents[3]
POWER = REPO / "hardware/electronics/power_distribution/p03"
OUT = REPO / "hardware/validation/board-qualification/generated/p03-ground"
REFERENCE = ("J101", "2")
CRITICAL = {
    REFERENCE,
    ("J20", "1"),
    ("J21", "1"),
    ("R201", "2"),
    ("U20", "5"),
    ("U21", "4"),
    ("R243", "2"),
    ("U22", "8"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stack(tree):
    depths, thickness, depth = [], [], 0.0
    for layer in children(first(first(tree, "setup"), "stackup"), "layer"):
        name = str(layer[1])
        if name not in LAYERS and not name.startswith("dielectric "):
            continue
        value = float(first(layer, "thickness")[1])
        assert value > 0
        if name in LAYERS:
            assert name == LAYERS[len(depths)]
            depths.append(depth + value / 2)
            thickness.append(value)
        depth += value
    assert len(depths) == 6 and math.isclose(
        depth, float(first(first(tree, "general"), "thickness")[1]), abs_tol=1e-6
    )
    return np.array(depths), np.array(thickness), depth


def graph(mesh, depths, thickness, plating, depth_scale, temperature):
    ids = np.full(mesh.mask.shape, -1, dtype=int)
    count = int(np.count_nonzero(mesh.mask))
    assert count
    ids[mesh.mask] = np.arange(count)
    union = Union(count)
    rings = []
    for xy, drill, radius in mesh.holes:
        region = (mesh.x[:, None] - xy[0]) ** 2 + (mesh.y[None, :] - xy[1]) ** 2 <= radius**2
        rows = []
        for layer in range(6):
            cells = ids[layer][region & mesh.mask[layer]]
            if len(cells):
                for cell in cells[1:]:
                    union.join(int(cells[0]), int(cell))
                rows.append((layer, int(cells[0])))
        rings.append((drill, rows))
    _, mapping = np.unique([union.root(index) for index in range(count)], return_inverse=True)
    size = int(mapping.max() + 1)
    u, v, conductance = [], [], []
    # Explicit unaccepted project resistivity/temperature scenarios, independent
    # of E28's construction constants. Units below are ohm mm and millimetres.
    rho = 1.8e-5 * (1 + 0.0041 * (temperature - 20))
    barrel_rho = 2.0e-5 * (1 + 0.0041 * (temperature - 20))
    for axis in (1, 2):
        one, two = [slice(None)] * 3, [slice(None)] * 3
        one[axis], two[axis] = slice(None, -1), slice(1, None)
        a, b = ids[tuple(one)], ids[tuple(two)]
        valid = (a >= 0) & (b >= 0)
        aa, bb = mapping[a[valid]], mapping[b[valid]]
        keep = aa != bb
        layers = np.nonzero(valid)[0]
        u.append(aa[keep])
        v.append(bb[keep])
        conductance.append((thickness[layers] / rho)[keep])
    via_u, via_v, via_g = [], [], []
    for drill, rows in rings:
        area = math.pi * ((drill / 2 + plating) ** 2 - (drill / 2) ** 2)
        for (la, a), (lb, b) in zip(rows, rows[1:]):
            via_u.append(mapping[a])
            via_v.append(mapping[b])
            via_g.append(area / (barrel_rho * (depths[lb] - depths[la]) * depth_scale))
    u.append(np.asarray(via_u, dtype=int))
    v.append(np.asarray(via_v, dtype=int))
    conductance.append(np.asarray(via_g))
    u, v, conductance = np.concatenate(u), np.concatenate(v), np.concatenate(conductance)
    assert np.all(conductance > 0) and np.isfinite(conductance).all()
    degree = np.bincount(u, weights=conductance, minlength=size) + np.bincount(
        v, weights=conductance, minlength=size
    )
    laplacian = sparse.coo_matrix(
        (
            np.concatenate([degree, -conductance, -conductance]),
            (np.concatenate([np.arange(size), u, v]), np.concatenate([np.arange(size), v, u])),
        ),
        shape=(size, size),
    ).tocsr()

    def electrode(key, front_only=False):
        raw = []
        for layer, region in mesh.pads[key].items():
            if not front_only or layer == 0:
                raw.extend(mapping[ids[layer][region & mesh.mask[layer]]])
        nodes, counts = np.unique(raw, return_counts=True)
        return nodes.astype(int), counts / max(1, sum(counts))

    return laplacian, electrode, dict(nodes=size, edges=len(u), plated_holes=len(rings))


def analyze(tree, construction, step):
    mesh = Mesh(tree, "AGND", step, bounds=(160, 45))
    depths, thickness, nominal = stack(tree)
    assert np.allclose(
        thickness,
        [
            construction["outer_finished_copper_minimum_required_um"] / 1000,
            *([construction["inner_finished_copper_minimum_required_um"] / 1000] * 4),
            construction["outer_finished_copper_minimum_required_um"] / 1000,
        ],
    )
    lap, electrode, stats = graph(
        mesh, depths, thickness, construction["via_wall_minimum_required_um"] / 1000, 1.76 / nominal, 85
    )
    reference, _ = electrode(REFERENCE, front_only=True)
    assert len(reference), "Input ground electrode is unresolved at this grid"
    _, labels = connected_components(lap, directed=False)
    active = np.isin(labels, np.unique(labels[reference]))
    free = active.copy()
    free[reference] = False
    indices = np.flatnonzero(free)
    free_ids = np.full(lap.shape[0], -1, dtype=int)
    free_ids[indices] = np.arange(len(indices))
    ports, weights, unresolved = [], {}, {}
    for key in sorted(mesh.pads):
        if key[0].startswith(("C", "H")):
            continue
        nodes, weight = electrode(key, front_only=key == REFERENCE)
        if not len(nodes) or not active[nodes].all():
            unresolved[".".join(key)] = (
                "Electrode missing or partly outside input-connected mesh; no fictitious connection added"
            )
            continue
        ports.append(key)
        weights[key] = (nodes, weight)
    missing = sorted(".".join(key) for key in CRITICAL if key not in weights)
    if missing:
        return dict(
            grid_mm=step,
            **stats,
            status="mesh_unresolved",
            ports=[".".join(key) for key in ports],
            unresolved_ports=unresolved,
            critical_unresolved_ports=missing,
            transfer_ohm=None,
            explanation="Refine the mesh and independently close native connections; no missing electrode or disconnected current path is repaired numerically",
            ground_transfer_qualified=False,
        )
    system = lap[indices][:, indices].tocsc()
    factor = splu(system)
    transfer = np.zeros((len(ports), len(ports)))
    residuals, kcl, energies = [], [], []
    for column, key in enumerate(ports):
        nodes, weight = weights[key]
        rhs = np.zeros(len(indices))
        keep = free[nodes]
        np.add.at(rhs, free_ids[nodes[keep]], weight[keep])
        result = factor.solve(rhs)
        voltage = np.zeros(lap.shape[0])
        voltage[indices] = result
        residual = float(np.max(abs(system @ result - rhs)))
        assert residual < 1e-7, (key, residual)
        ground_current = float(np.sum((lap @ voltage)[reference]))
        balance = abs(ground_current + sum(rhs))
        assert balance < 1e-6, (key, balance)
        for row, other in enumerate(ports):
            other_nodes, other_weight = weights[other]
            transfer[row, column] = float(other_weight @ voltage[other_nodes])
        energy = float(result @ (system @ result))
        assert abs(energy - float(result @ rhs)) < 1e-9
        residuals.append(residual)
        kcl.append(balance)
        energies.append(energy)
    reciprocal_error = float(np.max(abs(transfer - transfer.T)))
    assert reciprocal_error < 1e-9
    assert np.min(transfer) > -1e-10
    positions = {key: index for index, key in enumerate(ports)}
    references = {}
    for probe in sorted(CRITICAL - {REFERENCE}):
        references[".".join(probe)] = {
            ".".join(port): float(transfer[positions[probe], positions[port]]) for port in ports
        }
    values = {}
    for fp in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        if props["Reference"] in {"R200", "R206", "R201", "R242", "R243"}:
            values[props["Reference"]] = number(props["Value"])
    dig_ratio = (values["R200"] + values["R206"]) / values["R201"]
    ana_ratio = values["R242"] / values["R243"]
    modes = {}
    for name, coefficients in {
        "digital_ideal_fb_ground_error": {
            ("U20", "5"): 1 + dig_ratio,
            ("R201", "2"): -dig_ratio,
            ("J21", "1"): -1,
        },
        "analog_ideal_reference_ground_error": {
            ("U21", "4"): 1 + ana_ratio,
            ("R243", "2"): -ana_ratio,
            ("J20", "1"): -1,
        },
    }.items():
        response = sum(coefficient * transfer[positions[key]] for key, coefficient in coefficients.items())
        modes[name] = {
            "coefficients": {".".join(key): value for key, value in coefficients.items()},
            "ohm_by_unit_ground_injection": {
                ".".join(port): float(response[positions[port]]) for port in ports
            },
        }
    return dict(
        grid_mm=step,
        status="diagnostic_estimate",
        **stats,
        input_connected_nodes=int(active.sum()),
        unrelated_unpowered_mesh_nodes_excluded=int((~active).sum()),
        ports=[".".join(key) for key in ports],
        unresolved_ports=unresolved,
        transfer_ohm=transfer.tolist(),
        critical_observer_transfer_ohm=references,
        ideal_dc_source_ground_sensitivity=modes,
        maximum_absolute_kcl_residual_a=max(kcl),
        maximum_solver_residual_a=max(residuals),
        reciprocity_error_ohm=reciprocal_error,
        unit_injection_energy_w=energies,
        mesh_complete_for_all_noncapacitive_ground_pads=not unresolved,
        full_current_ledger_and_external_ground_network_solved=False,
        ground_transfer_qualified=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", default=".4,.2")
    args = parser.parse_args()
    board = POWER / "power_p03.kicad_pcb"
    contract = POWER / "construction.json"
    native, construction_bytes = board.read_bytes(), contract.read_bytes()
    construction = json.loads(construction_bytes)
    assert sha(native) == construction["pcb_sha256"], "Live PCB/construction snapshot is inconsistent"
    source_paths = [
        Path(__file__),
        REPO / "hardware/electronics/rail_disconnect/revision28/copper.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/common/netlists.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    sources = {str(path.relative_to(REPO)): sha(path.read_bytes()) for path in source_paths}
    output = OUT / (sha(native)[:12] + "-" + sources[str(Path(__file__).relative_to(REPO))][:8])
    output.mkdir(parents=True, exist_ok=True)
    (output / "board-snapshot.kicad_pcb").write_bytes(native)
    (output / "construction-snapshot.json").write_bytes(construction_bytes)
    tree = read_sexpr(native.decode())
    rows = []
    for step in map(float, args.steps.split(",")):
        print("P03 ground grid", step, flush=True)
        rows.append(analyze(tree, construction, step))
        (output / f"grid-{step:g}.json").write_text(json.dumps(rows[-1], indent=2) + "\n")
        print(
            "status",
            rows[-1]["status"],
            "resolved ports",
            len(rows[-1]["ports"]),
            "nodes",
            rows[-1]["nodes"],
            "KCL",
            rows[-1].get("maximum_absolute_kcl_residual_a"),
            flush=True,
        )
    assert all(sha((REPO / name).read_bytes()) == value for name, value in sources.items()), (
        "Model code changed during extraction"
    )
    report = dict(
        revision="P03-native-ground-diagnostic",
        native_pcb_sha256=sha(native),
        construction_sha256=sha(construction_bytes),
        source_sha256=sources,
        live_pcb_and_construction_still_current=board.read_bytes() == native
        and contract.read_bytes() == construction_bytes,
        snapshot_pcb=str((output / "board-snapshot.kicad_pcb").relative_to(REPO)),
        method="Native saved AGND fills/tracks/physical lands, finite cylindrical barrels and layer-specific sheets; uniform distributed per-pad current/voltage electrodes; input F-pad is the sole grounded boundary",
        temperature_scenario_c=85,
        trace_resistivity_requirement_20c_ohm_m=1.8e-8,
        barrel_resistivity_requirement_20c_ohm_m=2.0e-8,
        temperature_coefficient_assumed_per_c=0.0041,
        modeled_barrel_depth_total_mm=1.76,
        actual_accepted_thickness_range=None,
        material_requirements_manufacturer_accepted=False,
        limitations=[
            "Cell-center rasterization and ideal within-layer plated annuli are diagnostic, not resistance bounds",
            "Rounded rectangular pads are rectangularized; finite contact/solder/terminal spreading and package-internal ground distribution are unqualified",
            "Independent per-pad unit injections are basis functions, not a physical load-current ledger",
            "Source-ground sensitivity uses ideal DC feedback expressions; real package/reference/loop behavior must be verified",
            "No forced link, artificial shunt, gmin, current cancellation or physical measurement is introduced",
            "Native routing, external ground-network coupling, fabrication tolerances, frequency/noise behavior and physical Kelvin measurements remain open",
        ],
        cases=rows,
        physical_tests_performed=0,
        copper_loss_qualified=False,
        complete_endpoint_voltage_budget_closed=False,
        fabrication_released=False,
        build_ready=False,
    )
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(output, flush=True)


if __name__ == "__main__":
    main()
