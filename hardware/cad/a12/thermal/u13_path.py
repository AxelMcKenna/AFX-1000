"""Conditional native-copper U13 EP→via→TIM screen; never a junction pass."""

import argparse
import gzip
import json
import math
from pathlib import Path

from .analyze import HEAT, native_heat_and_vias, via_resistance
from .generate import OUT, REPO, ROOT, contact_contains, lands, load, sha


def read_construction(path, pcb_sha256):
    contract = json.loads(Path(path).read_text())
    if not isinstance(contract, dict) or contract.get("pcb_sha256") != pcb_sha256:
        raise ValueError("Construction contract is stale for this native input")
    for key in ("via_wall_minimum_required_um", "board_nominal_thickness_mm"):
        value = contract.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("Construction requires finite positive numeric " + key)
    return contract


def solve(
    d,
    grid=160,
    copper_um=70,
    tim_gap_mm=1.22,
    contact_c_per_w=0,
    copper_k=385,
    tim_k=6,
    layers=("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"),
    pcb_path=None,
    dielectric_override_mm=None,
    via_wall_um=25,
    outer_copper_override_um=None,
    finished_bore_override_mm=None,
):
    assert copper_k > 0 and tim_k > 0 and tim_gap_mm > 0 and contact_c_per_w >= 0
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse.linalg import spsolve

    from hardware.electronics.common.sexpr import children, first, read_sexpr
    from hardware.electronics.output_stage.check_placement import transform

    pcb = (
        Path(pcb_path)
        if pcb_path is not None
        else REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    )
    tree = read_sexpr(pcb.read_text())
    site = next(s for s in lands(d) if s["refs"] == ["U13"])
    # Convert the metal contact from housing to actual native PCB coordinates.
    gx, gy, w, h = site["metal_global"]
    x0, y0 = gx - 68, gy - 8
    dx, dy = w / grid, h / grid
    xx, yy = np.meshgrid(x0 + (np.arange(grid) + 0.5) * dx, y0 + (np.arange(grid) + 0.5) * dy)
    xy = np.column_stack([xx.ravel(), yy.ravel()])
    sink_mask = contact_contains(site, xy[:, 0] + 68, xy[:, 1] + 8)
    n = grid * grid
    mask = {layer: np.zeros(n, dtype=bool) for layer in layers}
    z = 0.0
    centres = {}
    thickness = {}
    dielectric_index = 0
    for row in children(first(first(tree, "setup"), "stackup"), "layer"):
        value = float(first(row, "thickness")[1])
        if str(row[1]) in ("F.Cu", "B.Cu") and outer_copper_override_um is not None:
            value = outer_copper_override_um / 1000
        if str(row[1]).startswith("dielectric") and dielectric_override_mm is not None:
            value = dielectric_override_mm[dielectric_index]
            dielectric_index += 1
        if str(row[1]) in layers:
            centres[str(row[1])] = z + value / 2
            thickness[str(row[1])] = value
        z += value
    assert z > 0 and set(centres) == set(layers)
    if dielectric_override_mm is not None:
        assert dielectric_index == len(dielectric_override_mm) == 5
    board_depth = z

    def polygon_contains(poly):
        inside = np.zeros(n, dtype=bool)
        for a, b in zip(poly, poly[1:] + poly[:1]):
            if a[1] == b[1]:
                continue
            inside ^= ((a[1] > xy[:, 1]) != (b[1] > xy[:, 1])) & (
                xy[:, 0] < (b[0] - a[0]) * (xy[:, 1] - a[1]) / (b[1] - a[1]) + a[0]
            )
        return inside

    for zone in children(tree, "zone"):
        if not children(zone, "net") or str(first(zone, "net")[1]).lstrip("/") != "AGND":
            continue
        for fill in children(zone, "filled_polygon"):
            layer = str(first(fill, "layer")[1])
            if layer not in mask:
                continue
            poly = [list(map(float, p[1:3])) for p in children(first(fill, "pts"), "xy")]
            if (
                min(p[0] for p in poly) > x0 + w
                or max(p[0] for p in poly) < x0
                or min(p[1] for p in poly) > y0 + h
                or max(p[1] for p in poly) < y0
            ):
                continue
            mask[layer] |= polygon_contains(poly)
    fp = next(
        f
        for f in children(tree, "footprint")
        if next((p[2] for p in children(f, "property") if p[1] == "Reference"), None) == "U13"
    )
    ep = next(p for p in children(fp, "pad") if str(p[1]) == "11")
    epxy = transform(fp, first(ep, "at")[1:3])
    epw, eph = map(float, first(ep, "size")[1:3])
    epmask = (np.abs(xy[:, 0] - epxy[0]) <= epw / 2) & (np.abs(xy[:, 1] - epxy[1]) <= eph / 2)
    mask["F.Cu"] |= epmask
    _, fields = native_heat_and_vias(d, pcb)
    field = next(s for s in fields if s["id"] == site["id"])
    vias = []
    native_vias = children(tree, "via")
    for via in field["actual_vias_inside_metal_contact"]:
        x, y = via["x_global_mm"] - 68, via["y_global_mm"] - 8
        item = next(v for v in native_vias if math.dist(list(map(float, first(v, "at")[1:3])), [x, y]) < 1e-6)
        outer = float(first(item, "size")[1]) / 2
        finished_bore = (
            via["finished_bore_mm"] if finished_bore_override_mm is None else finished_bore_override_mm
        )
        inner = finished_bore / 2
        radius2 = (xy[:, 0] - x) ** 2 + (xy[:, 1] - y) ** 2
        annulus = (radius2 <= outer**2) & (radius2 >= inner**2)
        contacts = np.flatnonzero(annulus)
        assert len(contacts) > 0, "Via annulus unresolved; refine grid"
        for layer in layers:
            mask[layer] |= annulus
            mask[layer] &= radius2 >= inner**2
        assert inner + via_wall_um / 1000 < outer, "Physical barrel wall exceeds actual pad radius"
        vias.append(
            (
                contacts,
                via_resistance(drill_mm=finished_bore, plating_um=via_wall_um)
                * 385
                / copper_k
                * board_depth
                / 1.6,
                abs(x - epxy[0]) <= epw / 2 and abs(y - epxy[1]) <= eph / 2,
            )
        )
    epmask &= mask["F.Cu"]
    active = np.concatenate([mask[layer] for layer in layers])
    indices = np.flatnonzero(active)
    lookup = {int(p): i for i, p in enumerate(indices)}
    matrix = lil_matrix((len(indices), len(indices)))
    q = np.zeros(len(indices))

    def link(p, pp, g):
        a, b = lookup[p], lookup[pp]
        matrix[a, a] += g
        matrix[b, b] += g
        matrix[a, b] -= g
        matrix[b, a] -= g

    # No FR4 or parallel air heat-transfer credit is assumed; actual AGND planes are included.
    area = dx * dy * 1e-6
    via_count = 0
    for layer in range(len(layers)):
        for j in range(grid):
            for i in range(grid):
                p = layer * n + j * grid + i
                if p not in lookup:
                    continue
                for di, dj in ((1, 0), (0, 1)):
                    ii, jj = i + di, j + dj
                    if ii >= grid or jj >= grid:
                        continue
                    pp = layer * n + jj * grid + ii
                    if pp not in lookup:
                        continue
                    link(
                        p,
                        pp,
                        copper_k
                        * (thickness[layers[layer]] / 1000)
                        * (copper_um / 70)
                        * (dy / dx if di else dx / dy),
                    )
                if layer == len(layers) - 1 and sink_mask[p % n]:
                    matrix[lookup[p], lookup[p]] += tim_k * area / (tim_gap_mm / 1000)
    for contacts, r, _ in vias:
        for layer in range(len(layers) - 1):
            fraction = (centres[layers[layer + 1]] - centres[layers[layer]]) / board_depth
            for p in contacts:
                link(int(p) + layer * n, int(p) + (layer + 1) * n, 1 / (r * fraction * len(contacts)))
        via_count += 1
    ep_nodes = [lookup[int(p)] for p in np.flatnonzero(epmask)]
    assert ep_nodes and vias
    q[ep_nodes] = 1 / len(ep_nodes)
    full_matrix = matrix.tocsr()
    _, labels = connected_components(full_matrix, directed=False)
    sink_nodes = [lookup[int(p)] for p in indices if p >= (len(layers) - 1) * n and sink_mask[p % n]]
    grounded_labels = set(int(labels[p]) for p in sink_nodes)
    keep = np.array([int(label) in grounded_labels for label in labels])
    assert float(q[~keep].sum()) < 1e-12, (
        "A powered EP copper island has no declared path to TIM; reject model"
    )
    # Unheated islands with no sink have an undefined absolute temperature and
    # no influence on this path. Remove those blocks; never add fictitious gmin.
    discarded = int((~keep).sum())
    mapping = np.full(len(indices), -1, dtype=int)
    mapping[keep] = np.arange(int(keep.sum()))
    matrix = full_matrix[keep][:, keep]
    q = q[keep]
    ep_nodes = [int(mapping[p]) for p in ep_nodes]
    temperature = spsolve(matrix, q)
    assert np.all(np.isfinite(temperature)), "Disconnected copper grid/convergence failure; do not use result"
    residual = float(np.max(np.abs(matrix.tocsr() @ temperature - q)))
    assert residual < 1e-8
    peak = float(max(temperature[p] for p in ep_nodes))
    mean = float(np.mean(temperature[ep_nodes]))
    full_t = np.full(len(indices), np.nan)
    full_t[keep] = temperature
    raster_t = np.full(len(layers) * n, np.nan)
    raster_t[indices] = full_t
    sheet_energy = {}
    for layer_index, layer in enumerate(layers):
        values = raster_t[layer_index * n : (layer_index + 1) * n].reshape(grid, grid)
        sheet_energy[layer] = float(
            copper_k
            * (thickness[layer] / 1000)
            * (copper_um / 70)
            * (
                np.nansum(np.diff(values, axis=1) ** 2) * dy / dx
                + np.nansum(np.diff(values, axis=0) ** 2) * dx / dy
            )
        )
    via_energy = 0.0
    direct_via_energy = 0.0
    remote_via_energy = 0.0
    for contacts, r, direct in vias:
        for layer_index in range(len(layers) - 1):
            fraction = (centres[layers[layer_index + 1]] - centres[layers[layer_index]]) / board_depth
            delta = raster_t[layer_index * n + contacts] - raster_t[(layer_index + 1) * n + contacts]
            energy = float(np.nansum(delta**2) / (r * fraction * len(contacts)))
            via_energy += energy
            if direct:
                direct_via_energy += energy
            else:
                remote_via_energy += energy
    sink_t = raster_t[(len(layers) - 1) * n :][sink_mask & mask["B.Cu"]]
    tim_energy = float(np.nansum(sink_t**2) * tim_k * area / (tim_gap_mm / 1000))
    assert abs(sum(sheet_energy.values()) + via_energy + tim_energy - mean) < 1e-7
    land = (
        (d["base"]["thermal_land_top_z"] - d["base"]["plate_top_z"])
        / 1000
        / (167 * site["metal_contact_area_mm2"] * 1e-6)
    )
    total = 3 + peak + land + contact_c_per_w
    power = HEAT["U13"][2]
    required = (85 - 60) / power
    return dict(
        native_pcb_sha256=sha(pcb),
        native_ep=dict(xy_mm=epxy, size_mm=[epw, eph]),
        metal_contact_area_mm2=site["metal_contact_area_mm2"],
        sink_domain_area_raster_mm2=float(sink_mask.sum() * dx * dy),
        contact_relief=site.get("corner_relief"),
        grid=[grid, grid],
        outer_copper_assumed_um=copper_um,
        actual_stack_copper_centres_mm=centres,
        actual_nominal_copper_thickness_mm=thickness,
        native_stack_total_mm=board_depth,
        dielectric_override_mm=dielectric_override_mm,
        via_wall_assumed_minimum_um=via_wall_um,
        outer_copper_override_um=outer_copper_override_um,
        finished_bore_override_mm=finished_bore_override_mm,
        stack_override_is_an_approved_manufacturer_build=False,
        included_layers=list(layers),
        actual_filled_copper_grid_area_mm2={k: float(v.sum() * dx * dy) for k, v in mask.items()},
        actual_matching_through_vias=via_count,
        actual_via_centres_inside_ep=sum(
            abs(v["x_global_mm"] - 68 - epxy[0]) <= epw / 2 and abs(v["y_global_mm"] - 8 - epxy[1]) <= eph / 2
            for v in field["actual_vias_inside_metal_contact"]
        ),
        copper_k_assumed_w_per_mk=copper_k,
        tim_k_typical_w_per_mk=tim_k,
        tim_gap_assumed_mm=tim_gap_mm,
        ep_peak_to_land_network_c_per_w=peak,
        ep_mean_to_land_network_c_per_w=mean,
        unit_heat_energy_decomposition_c_per_w=dict(
            sheet_spreading_by_layer=sheet_energy,
            sheet_spreading_total=sum(sheet_energy.values()),
            via_barrels_all_segments=via_energy,
            direct_ep_via_barrels=direct_via_energy,
            remote_field_via_barrels=remote_via_energy,
            tim_bulk_under_actual_bottom_copper=tim_energy,
            total_equals_ep_mean_network=mean,
            peak_above_uniform_source_mean=peak - mean,
            basis="For1W uniformly distributed overactualEPcells, sum(g*dT^2) overactual sheet/via/TIMnetwork. These are effective energy shares,not independent series resistors. Package3K/W,landaxialandassumedcontactaddedseparately.",
        ),
        package_theta_jc_c_per_w=3,
        aluminum_land_axial_c_per_w=land,
        extra_contact_assumed_c_per_w=contact_c_per_w,
        conditional_total_junction_to_base_c_per_w=total,
        power_allocation_w=power,
        conditional_junction_at_60c_base_c=60 + power * total,
        conditional85c_allocation_satisfied_before_uncertainty=60 + power * total <= 85,
        maximum_base_for_85c_junction_before_uncertainty_c=85 - power * total,
        required_total_junction_to_base_at_60c_c_per_w=required,
        remaining_contact_and_parameter_uncertainty_budget_c_per_w=required - (3 + peak + land),
        remaining_after_declared_contact_for_parameter_uncertainty_c_per_w=required - total,
        kcl_residual_w=residual,
        disconnected_zero_heat_copper_cells_excluded=discarded,
        fictitious_sink_or_gmin_added=False,
        solver_converged=True,
        assumptions="Selected native copper sheets discretized from actual saved AGND fills,EP rectangle and matching via nodes. Cell-centre occupancy with each actual via pad annulus represented by lumped vertical barrel conductance distributed across its raster cells; local annular radial spreading and copper-cap conduction are not solved,adiabatic patch edges;non-AGND layers,FR4 and parallel air cooling receive no credit. TIM sinks only beneath bottom copper;mask/contact resistance and package theta uncertainty are not bounded. These are declared scenarios,not guaranteed material minima or a full-board FEA.",
        physical_junction_verified=False,
        thermal_path_qualified=False,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb")
    parser.add_argument(
        "--construction", help="Source-bound fabrication requirements JSON; no received-board approval"
    )
    args = parser.parse_args()
    d = load()
    pcb = (
        Path(args.pcb)
        if args.pcb
        else REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    )
    start = sha(pcb)
    source_path = REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    construction = None
    construction_path = None
    wall = 25
    if args.construction:
        construction_path = Path(args.construction).resolve()
        construction = read_construction(construction_path, start)
        source_path = construction_path.with_name("power_p03.kicad_pcb")
        assert sha(source_path) == start, "Construction source PCB differs from copied model input"
        wall = float(construction["via_wall_minimum_required_um"])
        assert wall > 0
    scenarios = [
        solve(
            d, grid=160, copper_um=70, tim_gap_mm=gap, contact_c_per_w=contact, pcb_path=pcb, via_wall_um=wall
        )
        for gap, contact in ((1.22, 0), (1.22, 0.8), (1.5, 2))
    ]
    fine = solve(
        d, grid=320, copper_um=70, tim_gap_mm=1.22, contact_c_per_w=0, pcb_path=pcb, via_wall_um=wall
    )
    material_sensitivity = solve(
        d, grid=160, tim_gap_mm=1.5, contact_c_per_w=2, copper_k=350, tim_k=4, pcb_path=pcb, via_wall_um=wall
    )
    assert sha(pcb) == start, "Native copper changed; reject and rerun"
    outer_only = solve(d, grid=160, layers=("F.Cu", "B.Cu"), pcb_path=pcb, via_wall_um=wall)
    if construction:
        assert abs(scenarios[0]["native_stack_total_mm"] - construction["board_nominal_thickness_mm"]) < 1e-6
    assert sha(pcb) == start and all(
        r["native_pcb_sha256"] == start for r in scenarios + [fine, outer_only, material_sensitivity]
    ), "Native copper changed during full run; reject and rerun"
    report = dict(
        revision="A12-T01-U13-network",
        scenarios=scenarios,
        finer_grid=fine,
        outer_only_limited_path=outer_only,
        lower_conductivity_illustrative_sensitivity=material_sensitivity,
        illustrative_sensitivity_is_a_manufacturer_bound=False,
        coarse_fine_peak_network_difference_c_per_w=abs(
            fine["ep_peak_to_land_network_c_per_w"] - scenarios[0]["ep_peak_to_land_network_c_per_w"]
        ),
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in (ROOT / "u13_path.py", ROOT / "design.json", ROOT / "analyze.py")
        },
        native_copper_origin_repo_path=str(source_path.relative_to(REPO)),
        native_copper_origin_sha256=start,
        input_snapshot_path=str(pcb),
        construction_requirements=construction,
        via_wall_input_basis="Required fabrication minimum, not received microsection"
        if construction
        else "Uncertified25um wall assumption",
        contact_spreading_and_parameter_uncertainty_guaranteed=False,
        whole_path_acceptance=dict(
            formula="T_base_upper + P_IC_upper * R_junction_to_base_upper <=85C",
            conservative_ic_power_allocation_w=HEAT["U13"][2],
            manufacturer_guaranteed_tim_k_lower_w_per_mk=None,
            certified_copper_k_and_via_plating_lower_bound=None,
            assembly_contact_resistance_upper_c_per_w=None,
            bounded_package_and_land_spreading_upper_c_per_w=None,
            positive_expanded_temperature_and_power_uncertainty=None,
            bounded_total_path_upper_c_per_w=None,
            missing_bound_inputs_are_not_zero=True,
            guardbanded_85c_project_acceptance=False,
        ),
        physical_tests_performed=0,
        thermal_qualified=False,
    )
    report["source_sha256"][report["native_copper_origin_repo_path"]] = start
    if construction_path:
        report["source_sha256"][str(construction_path.relative_to(REPO))] = sha(construction_path)
        for path, expected in construction.get("source_sha256", {}).items():
            assert sha(REPO / path) == expected, "Construction dependency changed: " + path
            report["source_sha256"][path] = expected
    for dependency in (
        "hardware/cad/a12/thermal/generate.py",
        "hardware/electronics/common/sexpr.py",
        "hardware/electronics/output_stage/check_placement.py",
    ):
        report["source_sha256"][dependency] = sha(REPO / dependency)
    snapshot = OUT / "native-inputs" / ("p03-" + start + ".kicad_pcb.gz")
    snapshot.parent.mkdir(exist_ok=True)
    snapshot.write_bytes(gzip.compress(pcb.read_bytes(), mtime=0))
    report["compressed_native_input_evidence"] = str(snapshot.relative_to(REPO))
    (OUT / "u13-path.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
