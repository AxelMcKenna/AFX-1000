"""Actual filled-copper seven-channel network diagnostic, never a release pass.

Different parallel chips retain separate terminals. Each channel contributes
20mohm (TI full-temperature maximum) between its own input/output electrodes.
Only the two lands belonging to a single chip terminal are equipotential.
The result includes shared geometry and unequal branch currents for this
all-RON-maximum corner; it never assumes equal current or ampacity sharing.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .copper import LAYERS, STACKUP, Mesh, Union, children, first, read_sexpr, solve_network
from .manufacturer import ROOT

MODULE_ROOT = Path(__file__).resolve().parent


def model_inputs(distributed_barrels=False):
    files = [
        MODULE_ROOT / name
        for name in (
            "coupled.py",
            "copper.py",
            "native_mesh.py",
            "distributed_mesh.py",
            "generate.py",
            "stackup.json",
        )
    ]
    return dict(
        model_source_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        candidate_sheet_thickness_each_layer_mm=0.07,
        candidate_copper_temperature_c=85,
        candidate_minimum_barrel_wall_mm=0.025,
        trace_resistivity_at20c_ohm_m=STACKUP["trace_resistivity_max_20c_ohm_m"],
        barrel_resistivity_at20c_ohm_m=STACKUP["barrel_resistivity_max_20c_ohm_m"],
        temperature_coefficient_per_c=STACKUP["temperature_coefficient_max_per_c"],
        material_temperature_and_process_bounds_accepted=False,
        within_layer_plated_annuli_idealized=not distributed_barrels,
        distributed_barrel_wall_sectors=32 if distributed_barrels else None,
        wall_circumferential_conduction_included=True if distributed_barrels else None,
        package_contact_and_solder_spreading_qualified=False,
    )


def restrict_stud_electrode(mesh, tree, ref, radius):
    """Restrict terminal contact only; retain the complete conducting annulus."""
    assert 0 < radius <= 3.5, "Contact radius is an unaccepted nominal/assembly scenario"
    footprint = next(
        fp
        for fp in children(tree, "footprint")
        if next(p[2] for p in children(fp, "property") if p[1] == "Reference") == ref
    )
    x, y = (float(v) - 100 for v in first(footprint, "at")[1:3])
    regions = mesh.pads[(ref, "1")]
    assert set(regions) == {0}, "This scenario applies to the actual top-side SMT stud"
    original = int(np.count_nonzero(regions[0]))
    contact = regions[0] & ((mesh.x[:, None] - x) ** 2 + (mesh.y[None, :] - y) ** 2 <= radius**2)
    assert np.any(contact), "Contact scenario misses the actual annular copper"
    regions[0] = contact
    return dict(
        terminal=ref + ".1",
        contact_radius_mm=radius,
        original_electrode_cells=original,
        scenario_electrode_cells=int(np.count_nonzero(contact)),
        actual_conducting_copper_unchanged=True,
        manufacturer_or_assembler_contact_bound_accepted=False,
        physical_qualified=False,
    )


def restrict_pad_contact_layer(mesh, ref, pin, layer):
    """Select the external contact face, retaining every physical PTH barrel."""
    assert layer in ("F.Cu", "B.Cu")
    regions = mesh.pads[(ref, str(pin))]
    index = LAYERS.index(layer)
    assert index in regions
    original = [LAYERS[i] for i in sorted(regions)]
    mesh.pads[(ref, str(pin))] = {index: regions[index]}
    return dict(
        terminal=ref + "." + str(pin),
        original_contact_layers=original,
        scenario_contact_layer=layer,
        actual_copper_and_barrels_unchanged=True,
        interface_assembly_bound_accepted=False,
        physical_qualified=False,
    )


def make_mesh(board, tree, net, step, native_pad_geometry, bounds=(156, 45.25), distributed_barrels=False):
    from .native_mesh import require_domain_coverage

    require_domain_coverage(tree, net, bounds, native_pad_geometry)
    if native_pad_geometry is None:
        assert not distributed_barrels, "Distributed walls require actual native pad geometry"
        assert tuple(bounds) == (156, 45.25), "Changed domains require actual native pad polygons"
        return Mesh(tree, net, step, bounds=bounds)
    from .native_mesh import NativePadMesh

    assert native_pad_geometry["source_pcb_sha256"] == hashlib.sha256(board.read_bytes()).hexdigest()
    if distributed_barrels:
        from .distributed_mesh import DistributedBarrelMesh

        return DistributedBarrelMesh(tree, net, step, native_pad_geometry, bounds=bounds)
    return NativePadMesh(tree, net, step, native_pad_geometry, bounds=bounds)


def positive(
    board,
    domain,
    step=0.2,
    stud_contact_radius_mm=None,
    load_contact_layer=None,
    native_pad_geometry=None,
    bounds=(156, 45.25),
    distributed_barrels=False,
):
    tree = read_sexpr(board.read_text())
    if domain == "digital":
        refs = ("U15", "U16", "U17", "U33")
        netin, netout = "5V_DIG_SRC", "5V_DIG"
        source, load = ("J11", "1"), ("J4", "1")
        current = 2.4
    else:
        refs = ("U13", "U14", "U32")
        netin, netout = "V5_REG_SRC", "V5_REG"
        source, load = ("J10", "1"), ("J3", "6")
        current = 0.251
    input_mesh = make_mesh(board, tree, netin, step, native_pad_geometry, bounds, distributed_barrels)
    contact = None
    if stud_contact_radius_mm is not None:
        contact = restrict_stud_electrode(input_mesh, tree, source[0], stud_contact_radius_mm)
    inputs = input_mesh.network()
    output_mesh = make_mesh(board, tree, netout, step, native_pad_geometry, bounds, distributed_barrels)
    load_contact = None
    if load_contact_layer is not None:
        load_contact = restrict_pad_contact_layer(output_mesh, *load, load_contact_layer)
    outputs = output_mesh.network()
    offset = inputs["n"]
    total = offset + outputs["n"]
    union = Union(total)
    terminals = []
    for ref in refs:
        ends = []
        for network, pins, base in ((inputs, ("5", "12"), 0), (outputs, ("6", "11"), offset)):
            ids = np.unique(network["electrodes"]([(ref, p) for p in pins])) + base
            if not len(ids):
                return dict(status="unresolved_native_chip_land", ref=ref, domain=domain, grid_mm=step)
            for node in ids[1:]:
                union.join(int(ids[0]), int(node))
            ends.append(int(ids[0]))
        terminals.append(ends)
    roots = np.array([union.root(i) for i in range(total)])
    _, mapping = np.unique(roots, return_inverse=True)
    u = np.concatenate((inputs["u"], outputs["u"] + offset))
    v = np.concatenate((inputs["v"], outputs["v"] + offset))
    g = np.concatenate((inputs["g"], outputs["g"]))
    u, v = mapping[u], mapping[v]
    keep = u != v
    edge_domain = np.concatenate(
        (np.zeros(len(inputs["u"]), dtype=int), np.ones(len(outputs["u"]), dtype=int))
    )[keep]
    u, v, g = u[keep], v[keep], g[keep]
    copper_edges = len(u)
    chan_u = np.array([mapping[a] for a, b in terminals])
    chan_v = np.array([mapping[b] for a, b in terminals])
    u = np.concatenate((u, chan_u))
    v = np.concatenate((v, chan_v))
    g = np.concatenate((g, np.full(len(refs), 50.0)))
    src = mapping[inputs["electrodes"]([source])]
    sink = mapping[outputs["electrodes"]([load]) + offset]
    result = solve_network(u, v, g, int(mapping.max() + 1), src, sink, details=True)
    result.update(
        domain=domain,
        grid_mm=step,
        extraction_bounds_mm=list(bounds),
        source_terminal=source,
        load_terminal=load,
        fully_on_channels=list(refs),
        ron_full_temp_max_ohm=0.020,
        source_board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
        physical_qualified=False,
        ampacity_equal_sharing_assumed=False,
        source_stud_contact_scenario=contact,
        full_stud_copper_electrode_used=stud_contact_radius_mm is None,
        load_contact_scenario=load_contact,
        all_load_pad_layers_clamped=load_contact_layer is None,
        native_pad_geometry_used=native_pad_geometry is not None,
        model_inputs=model_inputs(distributed_barrels),
        distributed_barrel_model_used=distributed_barrels,
    )
    if distributed_barrels:
        result["distributed_barrel_attachment_diagnostic"] = {
            name: dict(
                physical_holes=mesh.distributed_barrel_diagnostic["physical_holes"],
                maximum_attachment_displacement_mm=max(
                    (
                        row["max_attachment_displacement_mm"]
                        for row in mesh.distributed_barrel_diagnostic["barrels"]
                    ),
                    default=0,
                ),
                within_layer_annuli_shorted=False,
                wall_circumferential_conduction_included=True,
            )
            for name, mesh in (("input", input_mesh), ("output", output_mesh))
        }
    if result["status"] == "diagnostic_estimate":
        voltage = result.pop("voltage")
        excitation = result.pop("current_at_one_volt")
        fractions = 50 * (voltage[chan_u] - voltage[chan_v]) / excitation
        copper_energy = (
            g[:copper_edges] * (voltage[u[:copper_edges]] - voltage[v[:copper_edges]]) ** 2 / excitation**2
        )
        rcu = float(np.sum(copper_energy))
        rchips = float(0.020 * np.sum(fractions**2))
        result.update(
            branch_fraction_at_identical_max_ron=dict(zip(refs, map(float, fractions))),
            branch_current_at_declared_load_a=dict(zip(refs, map(float, fractions * current))),
            actual_copper_energy_estimate_ohm=rcu,
            input_copper_energy_estimate_ohm=float(np.sum(copper_energy[edge_domain == 0])),
            output_copper_energy_estimate_ohm=float(np.sum(copper_energy[edge_domain == 1])),
            chip_energy_estimate_ohm=rchips,
            copper_plus_unequal_chip_penalty_ohm=result["ohm"] - 0.020 / len(refs),
            energy_closure_error_ohm=result["ohm"] - rcu - rchips,
            p02_copper_allocation_ohm=0.003,
            conditional_estimate_within_allocation=result["ohm"] - 0.020 / len(refs) <= 0.003,
        )
    result["limitations"] = [
        "Cell-centre mesh is diagnostic, not a certified upper bound; convergence and process coupons required",
        "Ideal electrical contact within each chip terminal electrode; finite solder/contact and pad spreading unqualified",
        "RON20mohm full-temperature corner is monotone worst total DC resistance if all channels fully ON; current fractions are not guaranteed sharing",
        "Every branch ampacity must tolerate the entire load; master alone charges complete bulk during startup",
        "No startup/SOA/reverse-transient/dynamic/thermal or fabrication approval follows",
    ]
    return result


def returns(
    board,
    step=0.4,
    stud_contact_radius_mm=None,
    load_contact_layer=None,
    native_pad_geometry=None,
    bounds=(156, 45.25),
    distributed_barrels=False,
):
    tree = read_sexpr(board.read_text())
    mesh = make_mesh(board, tree, "AGND", step, native_pad_geometry, bounds, distributed_barrels)
    contacts = []
    if stud_contact_radius_mm is not None:
        contacts = [restrict_stud_electrode(mesh, tree, ref, stud_contact_radius_mm) for ref in ("J7", "J8")]
    load_contacts = []
    if load_contact_layer is not None:
        load_contacts = [
            restrict_pad_contact_layer(mesh, ref, "2", load_contact_layer) for ref in ("J3", "J4")
        ]
    net = mesh.network()
    result = solve_network(
        net["u"],
        net["v"],
        net["g"],
        net["n"],
        net["electrodes"]([("J4", "2")]),
        net["electrodes"]([("J8", "1")]),
        details=True,
    )
    if result["status"] == "diagnostic_estimate":
        v = result.pop("voltage")
        i = result.pop("current_at_one_volt")
        a = v[net["electrodes"]([("J3", "2")])]
        b = v[net["electrodes"]([("J7", "1")])]
        result["open_circuit_analog_terminal_transfer_range_ohm"] = [
            float((a.min() - b.max()) / i),
            float((a.max() - b.min()) / i),
        ]
    result.update(
        grid_mm=step,
        extraction_bounds_mm=list(bounds),
        physical_qualified=False,
        source_board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
        scope="E28 only, currentJ4.2→J8.1 and open-circuitJ3.2−J7.1; BOTH real bars plus P03 multiport network still required",
        full_bar_contact_resistance_qualified=False,
        coupled_p03_return_completed=False,
        stud_contact_scenarios=contacts,
        full_stud_copper_electrode_used=stud_contact_radius_mm is None,
        load_contact_scenarios=load_contacts,
        all_load_pad_layers_clamped=load_contact_layer is None,
        native_pad_geometry_used=native_pad_geometry is not None,
        model_inputs=model_inputs(distributed_barrels),
        distributed_barrel_model_used=distributed_barrels,
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board", type=Path)
    p.add_argument("--steps", default=".2,.1")
    p.add_argument("--returns", action="store_true")
    p.add_argument("--output", type=Path)
    p.add_argument("--stud-contact-radius", type=float)
    p.add_argument("--load-contact-layer", choices=("F.Cu", "B.Cu"))
    p.add_argument("--native-pad-geometry", type=Path)
    p.add_argument("--distributed-barrels", action="store_true")
    p.add_argument("--bounds", default="156,45.25", help="Complete copper domain width,height in board mm")
    a = p.parse_args()
    native_pads = json.loads(a.native_pad_geometry.read_text()) if a.native_pad_geometry else None
    bounds = tuple(map(float, a.bounds.split(",")))
    destination = a.output or (
        ROOT
        / "generated"
        / ("coupled-return-diagnostic.json" if a.returns else "coupled-positive-diagnostic.json")
    )
    assert destination.resolve().is_relative_to((ROOT / "generated").resolve())
    rows = []
    for step in map(float, a.steps.split(",")):
        for domain in ("returns",) if a.returns else ("analog", "digital"):
            row = (
                returns(
                    a.board,
                    step,
                    a.stud_contact_radius,
                    a.load_contact_layer,
                    native_pads,
                    bounds,
                    a.distributed_barrels,
                )
                if a.returns
                else positive(
                    a.board,
                    domain,
                    step,
                    a.stud_contact_radius,
                    a.load_contact_layer,
                    native_pads,
                    bounds,
                    a.distributed_barrels,
                )
            )
            if a.native_pad_geometry:
                row["native_pad_geometry_sha256"] = hashlib.sha256(
                    a.native_pad_geometry.read_bytes()
                ).hexdigest()
            rows.append(row)
            # Preserve every completed grid even if a later refinement is
            # interrupted. The rows still identify their exact grids/sources;
            # no absent finer result or convergence pass is manufactured.
            destination.write_text(json.dumps(rows, indent=2) + "\n")
            print(domain, step, row, flush=True)


if __name__ == "__main__":
    main()
