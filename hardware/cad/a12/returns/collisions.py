"""Actual native courtyard envelopes, declared heights and source-port gating."""

import json

from hardware.cad.a12.positive_links.selected_parts import requirement

from .generate import OUT, REPO, load, points, sha


def height(ref, footprint, part):
    selected = requirement(footprint, part)
    if selected is not None:
        return (
            selected["assembled_projection_requirement_mm"],
            selected["basis"] + ": " + selected["mpn"],
            False,
        )
    name = (footprint + " " + part).lower()
    if "probe2" in name:
        return 0.2, "Bare copper probe pads; no fitted body or mate", True
    if "7466003r" in name:
        return (
            5.4,
            "Project envelope5.4=nominal5+0.2dimension reserve+0.2seating; DIN ISO2768-1m drawing/process application still open",
            False,
        )
    if "eeufr1c472" in name:
        return 27.5, "Panasonic25mm body plus dimensional/seat reserve; final tolerance approval open", False
    if "eeufr1c152" in name:
        return 22.5, "Panasonic20mm body plus dimensional/seat reserve; final tolerance approval open", False
    if "pinheader" in name or "header" in name or ref.startswith("J"):
        return (
            10,
            "Unselected mated connector/header ceiling; actual assembly must be selected and source-bound",
            False,
        )
    if ref.startswith("L"):
        return 9, "Conservative inductor height allocation; actual MPN height/mount approval open", False
    if ref.startswith(("U", "Q")):
        return 3, "Conservative IC/transistor assembly height allocation; exact MPN/seat approval open", False
    if "capacitor_tht" in name:
        return 25, "Unverified through-hole capacitor assembly height ceiling", False
    if ref.startswith("C"):
        return (
            3,
            "Conservative capacitor assembly height allocation; actual MPN thickness/seat approval open",
            False,
        )
    return 2, "Conservative resistor/diode/small-part assembly allocation; exact height approval open", False


def native_packet(d):
    from hardware.electronics.common.sexpr import children, first, read_sexpr
    from hardware.electronics.output_stage.check_placement import courtyard

    bodies = []
    ports = {}
    missing = []
    exact_parts = REPO / "hardware/cad/a12/positive_links/selected_parts.py"
    selection = REPO / "hardware/electronics/power_distribution/p03/component-selections.json"
    hashes = {str(p.relative_to(REPO)): sha(p) for p in (exact_parts, selection)}
    boards = []
    for board, spec in d["native_boards"].items():
        path = REPO / spec["path"]
        hashes[spec["path"]] = sha(path)
        components = path.with_name("components.json")
        parts = {p["ref"]: p for p in json.loads(components.read_text())}
        hashes[str(components.relative_to(REPO))] = sha(components)
        tree = read_sexpr(path.read_text())
        datum = spec["datum"]
        pcbtop = d["assembled_board_bottom_z_mm"][board] + spec["thickness"]
        edges = []
        for line in children(tree, "gr_line"):
            if first(line, "layer")[1] == "Edge.Cuts":
                edges.extend([list(map(float, first(line, tag)[1:3])) for tag in ("start", "end")])
        boards.append(
            [
                board,
                datum[0] + min(p[0] for p in edges) - 100,
                datum[1] + min(p[1] for p in edges) - 100,
                d["assembled_board_bottom_z_mm"][board],
                max(p[0] for p in edges) - min(p[0] for p in edges),
                max(p[1] for p in edges) - min(p[1] for p in edges),
                spec["thickness"],
            ]
        )
        for fp in children(tree, "footprint"):
            props = {str(p[1]): str(p[2]) for p in children(fp, "property")}
            ref = props.get("Reference", "?")
            if ref.startswith("H") or str(first(fp, "layer")[1]) != "F.Cu":
                continue
            at = first(fp, "at")
            actual = [
                float(at[1]) - 100 + datum[0],
                float(at[2]) - 100 + datum[1],
                d.get("assembled_terminal_top_override_z_mm", {}).get(board, pcbtop + 5),
            ]
            intentional = False
            for net, terminal in spec["terminals"].items():
                if ref == terminal:
                    expected = points(d, net)[0 if board == "E28" else -1]
                    match = all(abs(a - b) < 0.001 for a, b in zip(actual, expected))
                    ports[board + "_" + net] = dict(
                        ref=ref,
                        actual_mm=actual,
                        expected_mm=expected,
                        position_contract_matches=match,
                        height_source_approved=False,
                        z_basis="Declared measured terminal-top input when supplied; otherwise nominal body5mm above board. Native KiCad establishes XY,not assembled Z.",
                    )
                    intentional = match
            if intentional:
                continue
            try:
                box = courtyard(fp, "F.CrtYd")
            except AssertionError:
                missing.append(dict(board=board, ref=ref))
                continue
            box = [
                box[0] - 100 + datum[0],
                box[1] - 100 + datum[1],
                box[2] - 100 + datum[0],
                box[3] - 100 + datum[1],
            ]
            if box[2] < 125 or box[0] > 185 or box[3] < 106 or box[1] > 155:
                continue
            h, note, approved = height(ref, str(fp[1]), parts.get(ref, {}).get("part", ""))
            bodies.append(
                [
                    board + "_" + ref,
                    box[0],
                    box[1],
                    pcbtop,
                    box[2] - box[0],
                    box[3] - box[1],
                    h,
                    note,
                    approved,
                ]
            )
    return dict(
        source_sha256=hashes,
        actual_port_manifest=ports,
        all_four_native_ports_match=len(ports) == 4
        and all(r["position_contract_matches"] for r in ports.values()),
        bodies=bodies,
        boards=boards,
        missing_native_courtyards=missing,
        all_component_and_mate_heights_approved=False,
        scope="Actual F.CrtYd XY prisms with explicit conservative height classes; intentional matched terminal contacts omitted. Unselected heights remain holds even after empty intersection.",
        physical_fit_verified=False,
    )


def main():
    d = load()
    generated = json.loads((OUT / "geometry.json").read_text())
    assert generated["design_sha256"] == sha(REPO / "hardware/cad/a12/returns/design.json")
    d["assembled_board_bottom_z_mm"] = generated["effective_measured_plane_inputs"]
    d["assembled_terminal_top_override_z_mm"] = generated.get("effective_terminal_top_override_z_mm", {})
    packet = native_packet(d)
    (OUT / "native-envelopes.json").write_text(json.dumps(packet, indent=2) + "\n")
    rows = packet["bodies"]
    boards = packet["boards"]
    source = (
        """include <returns.scad>
part="component_collision";
module component_prisms(){for(r="""
        + json.dumps(rows)
        + """)translate([r[1],r[2],r[3]])cube([r[4],r[5],r[6]]);}
module board_prisms(){for(r="""
        + json.dumps(boards)
        + """)translate([r[1],r[2],r[3]])cube([r[4],r[5],r[6]]);}
// ±0.65XY covers declared bar-hole float/tolerance/plating/metrology;±0.1Z is a project allocation.
module floating_bar_envelopes(){minkowski(){return_bars();cube([1.3,1.3,.2],center=true);}}
if(part=="component_collision")intersection(){floating_bar_envelopes();component_prisms();}
if(part=="retention_board_collision")intersection(){return_retention();board_prisms();}
if(part=="bar_retention_collision")intersection(){return_bars();return_retention();}
if(part=="bar_bar_collision")intersection(){return_ana_bar();return_dig_bar();}
if(part=="fastener_bar_collision")intersection(){return_fasteners();return_bars();}
if(part=="fastener_board_collision")intersection(){return_fasteners();board_prisms();}
component_index=0;
if(part=="single_component_collision")intersection(){floating_bar_envelopes();let(r=(__ROWS__)[component_index])translate([r[1],r[2],r[3]])cube([r[4],r[5],r[6]]);}
if(part=="positive_control")intersection(){return_bars();translate([145,132,__CONTROL_Z__])cube([1,1,1]);}
if(part=="bars")return_bars();
"""
    )
    source = source.replace("__ROWS__", json.dumps(rows)).replace(
        "__CONTROL_Z__", str(points(d, "ANA")[0][2] + 0.2)
    )
    (OUT / "collisions.scad").write_text(source)
    print(json.dumps({k: v for k, v in packet.items() if k not in ("bodies", "boards")}, indent=2))


if __name__ == "__main__":
    main()
