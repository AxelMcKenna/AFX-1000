"""U102 candidate only: saved copper/via network; no frozen-kit changes or physical pass."""

import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.analyze import via_resistance
from hardware.cad.a12.thermal.generate import REPO, sha


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
    contact_native,
    domain_native=(120, 115, 132, 127),
    grid=160,
    copper_um=70,
    tim_gap_mm=1.22,
    contact_c_per_w=0,
    copper_k=385,
    tim_k=6,
    layers=("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"),
    pcb_path=None,
    package_theta=14.9,
    power=0.961306923312642,
    ceiling=110,
    source_minimum_ep=True,
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
    x0, y0, xmax, ymax = domain_native
    w, h = xmax - x0, ymax - y0
    cx0, cy0, cx1, cy1 = contact_native
    assert x0 <= cx0 < cx1 <= xmax and y0 <= cy0 < cy1 <= ymax
    contact_area = (cx1 - cx0) * (cy1 - cy0)
    dx, dy = w / grid, h / grid
    xx, yy = np.meshgrid(x0 + (np.arange(grid) + 0.5) * dx, y0 + (np.arange(grid) + 0.5) * dy)
    xy = np.column_stack([xx.ravel(), yy.ravel()])
    sink_mask = (xy[:, 0] >= cx0) & (xy[:, 0] <= cx1) & (xy[:, 1] >= cy0) & (xy[:, 1] <= cy1)
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

    def rectangle_mask(centre, size, angle=0, corner=0):
        theta = math.radians(angle)
        delta = xy - np.asarray(centre)
        u = np.abs(delta[:, 0] * math.cos(theta) - delta[:, 1] * math.sin(theta))
        v = np.abs(delta[:, 0] * math.sin(theta) + delta[:, 1] * math.cos(theta))
        a, b = size[0] / 2, size[1] / 2
        if corner:
            return (
                (np.maximum(u - (a - corner), 0) ** 2 + np.maximum(v - (b - corner), 0) ** 2 <= corner**2)
                & (u <= a)
                & (v <= b)
            )
        return (u <= a) & (v <= b)

    net_names = {str(p[1]): str(p[2]).lstrip("/") for p in children(tree, "net") if len(p) > 2}

    def ground(obj):
        if not children(obj, "net"):
            return False
        raw = str(first(obj, "net")[1]).lstrip("/")
        return net_names.get(raw, raw) == "AGND"

    selected_pad_count = 0
    for footprint in children(tree, "footprint"):
        fp_at = first(footprint, "at")
        fp_angle = float(fp_at[3]) if len(fp_at) > 3 else 0
        for pad in children(footprint, "pad"):
            if not ground(pad):
                continue
            pad_layers = list(map(str, first(pad, "layers")[1:]))
            used = [k for k in layers if k in pad_layers or "*.Cu" in pad_layers]
            if not used:
                continue
            centre = transform(footprint, first(pad, "at")[1:3])
            size = list(map(float, first(pad, "size")[1:3]))
            if (
                centre[0] + max(size) < x0
                or centre[0] - max(size) > xmax
                or centre[1] + max(size) < y0
                or centre[1] - max(size) > ymax
            ):
                continue
            at = first(pad, "at")
            angle = fp_angle + (float(at[3]) if len(at) > 3 else 0)
            shape = str(pad[3])
            corner = 0
            if shape == "roundrect":
                corner = min(size) * float(first(pad, "roundrect_rratio")[1])
            elif shape in ("oval", "circle"):
                corner = min(size) / 2
            elif shape != "rect":
                raise ValueError("Unsupported native AGND pad shape:" + shape)
            padmask = rectangle_mask(centre, size, angle, corner)
            if not padmask.any():
                continue
            for k in used:
                mask[k] |= padmask
            selected_pad_count += 1
    selected_track_count = 0
    for segment in children(tree, "segment"):
        if not ground(segment):
            continue
        layer = str(first(segment, "layer")[1])
        if layer not in mask:
            continue
        a = np.asarray(list(map(float, first(segment, "start")[1:3])))
        b = np.asarray(list(map(float, first(segment, "end")[1:3])))
        delta = b - a
        denominator = float(delta @ delta)
        fraction = np.clip(((xy - a) @ delta) / denominator, 0, 1) if denominator else np.zeros(n)
        distance2 = ((xy - a - fraction[:, None] * delta) ** 2).sum(axis=1)
        trackmask = distance2 <= (float(first(segment, "width")[1]) / 2) ** 2
        if trackmask.any():
            selected_track_count += 1
            mask[layer] |= trackmask
    assert not any(ground(arc) for arc in children(tree, "arc")), "AGND arcs require explicit extraction"
    fp = next(
        f
        for f in children(tree, "footprint")
        if next((p[2] for p in children(f, "property") if p[1] == "Reference"), None) == "U102"
    )
    ep = next(p for p in children(fp, "pad") if str(p[1]) == "9")
    epxy = transform(fp, first(ep, "at")[1:3])
    epw, eph = map(float, first(ep, "size")[1:3])
    epmask = (np.abs(xy[:, 0] - epxy[0]) <= epw / 2) & (np.abs(xy[:, 1] - epxy[1]) <= eph / 2)
    mask["F.Cu"] |= epmask
    nets = {str(p[1]): str(p[2]).lstrip("/") for p in children(tree, "net") if len(p) > 2}
    vias = []
    for item in children(tree, "via"):
        x, y = map(float, first(item, "at")[1:3])
        if not (x0 <= x <= xmax and y0 <= y <= ymax):
            continue
        radius2 = (xy[:, 0] - x) ** 2 + (xy[:, 1] - y) ** 2
        finished_bore = (
            float(first(item, "drill")[1]) if finished_bore_override_mm is None else finished_bore_override_mm
        )
        inner = finished_bore / 2
        # All physical holes remove sheet copper, including foreign-net holes.
        for layer in layers:
            mask[layer] &= radius2 >= inner**2
        raw = str(first(item, "net")[1]).lstrip("/")
        node = nets.get(raw, raw)
        if node != "AGND" or list(map(str, first(item, "layers")[1:3])) != ["F.Cu", "B.Cu"]:
            continue
        outer = float(first(item, "size")[1]) / 2
        annulus = (radius2 <= outer**2) & (radius2 >= inner**2)
        contacts = np.flatnonzero(annulus)
        assert len(contacts) > 0, "Unresolved actual via annulus"
        for layer in layers:
            mask[layer] |= annulus
        assert inner + via_wall_um / 1000 < outer
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
    # Use manufacturer's minimum exposed-pad dimensions for the injected source,
    # while retaining the larger actual native copper pad as a sheet conductor.
    source_dimensions = (1.34, 1.66) if source_minimum_ep else (epw, eph)
    epmask = (np.abs(xy[:, 0] - epxy[0]) <= source_dimensions[0] / 2) & (
        np.abs(xy[:, 1] - epxy[1]) <= source_dimensions[1] / 2
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
    land = 5.28 / 1000 / (167 * contact_area * 1e-6)
    total = package_theta + peak + land + contact_c_per_w
    required = (ceiling - 60) / power
    return dict(
        native_pcb_sha256=sha(pcb),
        extracted_matching_native_pads=selected_pad_count,
        extracted_matching_native_segments=selected_track_count,
        sink_area_under_matching_bottom_copper_mm2=float((sink_mask & mask["B.Cu"]).sum() * dx * dy),
        native_ep=dict(xy_mm=epxy, size_mm=[epw, eph]),
        metal_contact_area_mm2=contact_area,
        sink_domain_area_raster_mm2=float(sink_mask.sum() * dx * dy),
        contact_native_mm=list(contact_native),
        domain_native_mm=list(domain_native),
        source_dimensions_mm=list(source_dimensions),
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
        actual_via_centres_inside_ep=sum(row[2] for row in vias),
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
            basis="For1W uniformly distributed overactualEPcells, sum(g*dT^2) overactual sheet/via/TIMnetwork. These are effective energy shares,not independent series resistors. Package metric added separately: not a guaranteed upper bound;,landaxialandassumedcontactaddedseparately.",
        ),
        package_theta_jc_c_per_w=package_theta,
        aluminum_land_axial_c_per_w=land,
        extra_contact_assumed_c_per_w=contact_c_per_w,
        conditional_total_junction_to_base_c_per_w=total,
        power_allocation_w=power,
        conditional_junction_at_60c_base_c=60 + power * total,
        conditional_project_allocation_satisfied_before_uncertainty=60 + power * total <= ceiling,
        maximum_base_for_project_junction_before_uncertainty_c=ceiling - power * total,
        required_total_junction_to_base_at_60c_c_per_w=required,
        remaining_contact_and_parameter_uncertainty_budget_c_per_w=required - (package_theta + peak + land),
        remaining_after_declared_contact_for_parameter_uncertainty_c_per_w=required - total,
        kcl_residual_w=residual,
        disconnected_zero_heat_copper_cells_excluded=discarded,
        fictitious_sink_or_gmin_added=False,
        solver_converged=True,
        assumptions="Selected native copper sheets discretized from actual saved AGND fills, native pads/straight segments and matching via nodes; all via bores remove copper. Native AGND arcs rejected. Cell-centre occupancy with each actual via pad annulus represented by lumped vertical barrel conductance distributed across its raster cells; local annular radial spreading and copper-cap conduction are not solved,adiabatic patch edges;non-AGND layers,FR4 and parallel air cooling receive no credit. TIM sinks only beneath bottom copper;mask/contact resistance and package theta uncertainty are not bounded. These are declared scenarios,not guaranteed material minima or a full-board FEA.",
        physical_junction_verified=False,
        thermal_path_qualified=False,
    )
