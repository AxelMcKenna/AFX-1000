"""Source-loaded base/cut-wall/apertured-lid finite network, finite seams.

No base temperature is prescribed. All materials, heat transfer, source-to-base
paths and replacement metal construction remain unaccepted scenarios.
"""

import math

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve

from .base_fields import base_fields
from .correlations import SIGMA, upward_h, vertical_h


def solve(
    contract,
    design,
    sources,
    geometry,
    bottom_h,
    fin_face,
    heat_scale=1.0,
    contact_r=(0.1, 0.1),
    decoupled=False,
):
    nx, ny = contract["coarse_grid"]
    nb = nx * ny
    nl = len(geometry["lid_polys"])
    nw = len(geometry["wall"])
    lo = nb
    wo = nb + nl
    n = nb + nl + nw
    k = contract["k_metal_w_per_mk"]
    ambient = contract["ambient_c"]
    eps = contract["emissivity"]
    wall_t = contract["walls"]["thickness"] * 1e-3
    lid_t = contract["lid"]["thickness"] * 1e-3
    ledge_t = contract["joints"]["new_conductive_ledge_thickness"] * 1e-3
    d = dict(design, scenario_aluminum_k=k)
    assignment = [dict(row, watts=row["watts"] * heat_scale) for row in sources]
    bf = base_fields(d, assignment, bottom_h, grid=(nx, ny))
    matrix = lil_matrix((n, n))
    matrix[:nb, :nb] = bf["conduction"]
    q = np.zeros(n)
    q[:nb] = bf["q"]
    base_contacts = []
    top_contacts = []
    pure_base = 0.0
    pure_top = 0.0

    def connect(a, b, g):
        assert math.isfinite(g) and g > 0
        matrix[a, a] += g
        matrix[b, b] += g
        matrix[a, b] -= g
        matrix[b, a] -= g

    for a, b, length, distance in geometry["lid_neighbors"]:
        connect(lo + a, lo + b, k * lid_t * length / distance)
    for a, b, kind, cross, distance in geometry["wall_neighbors"]:
        connect(wo + a, wo + b, k * wall_t * cross / distance)
    P = geometry["metadata"]["base_contact_length_mm"]
    Atotal = geometry["metadata"]["contact_area_mm2"]
    Rb, Rt = contact_r
    assert Rb > 0 and Rt > 0
    for bi, wi, width, normal, dz in geometry["base_links"]:
        rc = Rb * P / width
        rb = (normal * 0.5e-3) / (k * bf["thickness"] * width * 1e-3)
        rw = (dz * 0.5e-3) / (k * wall_t * width * 1e-3)
        if not decoupled:
            g = 1 / (rc + rb + rw)
            connect(bi, wo + wi, g)
            base_contacts.append((bi, wo + wi, g))
            pure_base += 1 / rc
    for wi, li, area, normal, inplane in geometry["top_links"]:
        # Effective contact length derives from actual overlaparea/declared1.5mm seat width.
        # Each contact R is normalized by total ACTUAL area, never node count.
        length = (area / 1.5) * 1e-3
        A = area * 1e-6
        rc = Rt * Atotal / area
        rw = (geometry["wall"][wi]["dz"] * 0.5e-3) / (k * wall_t * length)
        rledge = max(0, normal * 1e-3 - wall_t / 2) / (k * ledge_t * length)
        rlid = lid_t / 2 / (k * A) + inplane * 1e-3 / (k * lid_t * length)
        g = 1 / (rc + rw + rledge + rlid)
        connect(wo + wi, lo + li, g)
        top_contacts.append((wo + wi, lo + li, g))
        pure_top += 1 / rc
    assert abs(pure_top - 1 / Rt) < 1e-8
    assert decoupled or abs(pure_base - 1 / Rb) < 1e-8
    conduction = matrix.tocsr()
    graph_components, _ = connected_components(conduction, directed=False)
    assert graph_components == (2 if decoupled else 1), (
        "Unexpected conduction graph components",
        graph_components,
    )
    wall_area = np.array(
        [
            row["width"] * row["dz"] * 1e-6 * contract["walls"]["exposed_metal_fraction"]
            for row in geometry["wall"]
        ]
    )
    exposed = geometry["lid_exposed"]
    roots = geometry["lid_roots"]
    finareas = geometry["lid_fin"]
    temp = np.full(n, ambient + 20.0)
    if decoupled:
        temp[lo:] = ambient
    rad = np.r_[eps * contract["bottom_radiation_view"] * bf["rad"], eps * exposed, eps * wall_area]
    iteration = 0

    def surface_coeff(t):
        gconv = np.zeros(n)
        gconv[:nb] = bottom_h * bf["conv"]
        if decoupled:
            return gconv, dict(unheated_decoupled_upper_surfaces_at_ambient=True)
        top_mean = float(exposed @ t[lo:wo] / exposed.sum())
        tc = upward_h(
            design["housing"][0] * design["housing"][1] * 1e-6,
            2 * sum(design["housing"][:2]) * 1e-3,
            top_mean,
            ambient,
        )
        gconv[lo:wo] = tc["h"] * exposed
        fc = vertical_h(0.018, float(finareas @ t[lo:wo] / finareas.sum()), ambient)
        ml = math.sqrt(2 * fc["h"] / (k * 0.002)) * (0.018 + 0.001)
        eta = math.tanh(ml) / ml
        raw = fin_face * finareas * fc["h"] * eta
        good = (raw > 0) & (roots > 0)
        effective = np.zeros(nl)
        effective[good] = 1 / (1 / raw[good] + lid_t / 2 / (k * roots[good]))
        gconv[lo:wo] += effective
        faces = {}
        for face in ["N", "E", "S", "W"]:
            ids = np.array([i for i, row in enumerate(geometry["wall"]) if row["face"] == face])
            mean = float(wall_area[ids] @ t[wo + ids] / wall_area[ids].sum())
            corr = vertical_h(0.0436, mean, ambient)
            gconv[wo + ids] = corr["h"] * wall_area[ids]
            faces[face] = dict(mean_c=mean, correlation=corr)
        return gconv, dict(
            top_mean_c=top_mean,
            top_correlation=tc,
            fin_correlation=fc,
            fin_efficiency=eta,
            finite_lid_thickness_at_fin_roots=True,
            fin_convection_w=float(np.sum(effective * (t[lo:wo] - ambient))),
            wall_faces=faces,
        )

    for iteration in range(120):
        conv, correlations = surface_coeff(temp)
        kelvin = temp + 273.15
        ambk = ambient + 273.15
        loss = conv * (temp - ambient) + SIGMA * rad * (kelvin**4 - ambk**4)
        grad = conv + 4 * SIGMA * rad * kelvin**3
        a = conduction.copy()
        a.setdiag(a.diagonal() + grad)
        new = spsolve(a, q - loss + grad * temp)
        assert np.isfinite(new).all()
        delta = float(np.max(abs(new - temp)))
        temp = new
        if delta < 1e-8:
            break
    assert iteration < 119, ("No coupled convergence", delta)
    conv, correlations = surface_coeff(temp)
    loss = conv * (temp - ambient) + SIGMA * rad * ((temp + 273.15) ** 4 - (ambient + 273.15) ** 4)
    balance = conduction @ temp + loss - q
    total = float(loss.sum())
    target = math.fsum(x["watts"] for x in assignment)
    assert abs(total - target) < 1e-6, (total, target)
    assert np.max(abs(balance)) < 1e-6
    base_to_wall = sum(g * (temp[a] - temp[b]) for a, b, g in base_contacts)
    wall_to_lid = sum(g * (temp[a] - temp[b]) for a, b, g in top_contacts)
    base_loss = float(loss[:nb].sum())
    lid_loss = float(loss[lo:wo].sum())
    wall_loss = float(loss[wo:].sum())
    assert abs(target - base_loss - base_to_wall) < 1e-6
    assert abs(base_to_wall - wall_loss - wall_to_lid) < 1e-6
    assert abs(wall_to_lid - lid_loss) < 1e-6
    local = {}
    for source in sources:
        x, y, w, h = source["rect_housing_mm"]
        weights = bf["rect_weights"](x / 1000, y / 1000, w / 1000, h / 1000)
        local[source["id"]] = dict(
            ideal_base_projection_mean_c=float(weights @ temp[:nb]),
            ideal_base_projection_peak_c=float(temp[:nb][weights > 0].max()),
        )
    report = dict(
        source_heat_w=target,
        heat_scale=heat_scale,
        stress_is_planning_diagnostic=heat_scale != 1,
        ambient_assumed_c=ambient,
        k_assumed_w_per_mk=k,
        bottom_h_assumed=bottom_h,
        fin_face_fraction_assumed=fin_face,
        wall_exposed_fraction_assumed=contract["walls"]["exposed_metal_fraction"],
        contact_reference_r_k_per_w=list(contact_r),
        total_contact_reference_r_k_per_w=sum(contact_r),
        decoupled_base_wall=decoupled,
        base_peak_c=float(temp[:nb].max()),
        base_min_c=float(temp[:nb].min()),
        base_mean_c=float(temp[:nb].mean()),
        lid_peak_c=float(temp[lo:wo].max()),
        lid_min_c=float(temp[lo:wo].min()),
        wall_peak_c=float(temp[wo:].max()),
        wall_min_c=float(temp[wo:].min()),
        base_peak_xy_mm=[
            float((np.argmax(temp[:nb]) % nx + 0.5) * design["housing"][0] / nx),
            float((np.argmax(temp[:nb]) // nx + 0.5) * design["housing"][1] / ny),
        ],
        losses_w=dict(base=base_loss, walls=wall_loss, lid_and_fins=lid_loss, total=total),
        signed_heat_flows_w=dict(base_to_wall=base_to_wall, wall_to_lid=wall_to_lid),
        contact_pure_conductance_w_per_k=dict(base_wall=pure_base, wall_lid=pure_top),
        contact_normalization=dict(actual_base_contact_length_mm=P, actual_lid_seat_contact_area_mm2=Atotal),
        energy_residual_w=total - target,
        max_node_balance_residual_w=float(np.max(abs(balance))),
        iterations=iteration + 1,
        final_delta_c=delta,
        converged=True,
        base_temperature_prescribed=False,
        ideal_projection_temperatures=local,
        correlations=correlations,
        grid=[nx, ny],
        wall_nodes=nw,
        lid_nodes=nl,
        total_nodes=n,
        conduction_graph_components=int(graph_components),
        geometry_integrity=geometry["metadata"],
        base_fin_efficiency_assumed=bf["eta"],
        actual_metal_construction_matched=False,
        thermal_qualified=False,
        physical_qualified=False,
    )
    return report, dict(base=temp[:nb].reshape(ny, nx), lid=temp[lo:wo], wall=temp[wo:])
