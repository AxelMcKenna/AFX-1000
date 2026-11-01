"""Private E19 force-input ear; preserve the sealed 76-part power parent."""

import copy
import csv
import hashlib
import io
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-power/stitch_trial"
SOURCE_SHA = "e011588d1e9ab6d239004d411aac56ec64003ded19598417959ae3d48f740e14"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def new_id(old):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-e19-input-ear-J13-" + str(old)))


def clone_ids(node):
    if not isinstance(node, list):
        return
    if node and node[0] == "uuid":
        node[1] = new_id(node[1])
    else:
        for q in node:
            clone_ids(q)


def reference(fp):
    return next(p[2] for p in children(fp, "property") if p[1] == "Reference")


def run():
    assert sha(SOURCE / "processor_carrier.kicad_pcb") == SOURCE_SHA
    assert not (ROOT / "processor_carrier.kicad_pcb").exists(), "Use fresh proposal folder"
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, ROOT / p.name)
        elif p.is_file() and (
            p.suffix in [".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"]
            or p.name in ["components.json", "bom.csv", "fp-lib-table", "sym-lib-table"]
        ):
            shutil.copy2(p, ROOT / p.name)
    out = ROOT / "generated"
    out.mkdir()
    board = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    j1 = next(f for f in children(board, "footprint") if reference(f) == "J1")
    fp = copy.deepcopy(j1)
    clone_ids(fp)
    first(fp, "at")[1:] = [a(258), a(158)]
    for prop in children(fp, "property"):
        if prop[1] == "Reference":
            prop[2] = "J13"
    board.append(fp)
    removed = []
    for line in list(children(board, "gr_line")):
        if first(line, "layer")[1] == "Edge.Cuts":
            removed.append(sexpr(line))
            board.remove(line)
    outline = [(100, 100), (250, 100), (250, 153), (264, 153), (264, 165), (100, 165)]
    newedge = []
    for i, (p, q) in enumerate(zip(outline, outline[1:] + outline[:1])):
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"afx-e19-ear-edge-{i}"))
        edge = read_sexpr(
            f'(gr_line(start {p[0]} {p[1]})(end {q[0]} {q[1]})(stroke(width .1)(type default))(layer "Edge.Cuts")(uuid "{uid}"))'
        )
        board.append(edge)
        newedge.append(sexpr(edge))
    zones = []
    for layer, net, box in [
        ("F.Cu", "5V_DIG", (143, 119, 262, 164)),
        ("B.Cu", "5V_DIG", (143, 119, 262, 164)),
        ("In2.Cu", "5V_DIG", (143, 119, 262, 164)),
        ("In1.Cu", "AGND", (248, 153.5, 263, 164.5)),
    ]:
        x0, y0, x1, y1 = box
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"afx-e19-ear-zone-{layer}-{net}"))
        z = read_sexpr(
            f'(zone(net "/{net}")(layer "{layer}")(uuid "{uid}")(hatch edge .5)(priority 1)(connect_pads yes(clearance .2))(min_thickness .15)(fill yes(thermal_gap .3)(thermal_bridge_width .5))(polygon(pts(xy {x0} {y0})(xy {x1} {y0})(xy {x1} {y1})(xy {x0} {y1}))))'
        )
        board.append(z)
        zones.append(sexpr(z))
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(board) + "\n")
    sch = read_sexpr((ROOT / "processor_carrier.kicad_sch").read_text())
    old = next(
        s
        for s in children(sch, "symbol")
        if any(p[1:3] == ["Reference", "J1"] for p in children(s, "property"))
    )
    symbol = copy.deepcopy(old)
    clone_ids(symbol)
    dy = 474.98
    first(symbol, "at")[2] = a(float(first(symbol, "at")[2]) + dy)
    for prop in children(symbol, "property"):
        first(prop, "at")[2] = a(float(first(prop, "at")[2]) + dy)
        if prop[1] == "Reference":
            prop[2] = "J13"
    project = first(first(symbol, "instances"), "project")
    for path in children(project, "path"):
        first(path, "reference")[1] = "J13"
    sch.append(symbol)
    wires = []
    for y, net in [(537.21, "5V_DIG"), (542.29, "AGND")]:
        for tag, text in [
            (
                "wire",
                f'(wire(pts(xy 219.71 {y})(xy 214.63 {y}))(stroke(width 0)(type default))(uuid "{new_id(net + "wire")}"))',
            ),
            (
                "label",
                f'(label "{net}"(at 214.63 {y} 0)(effects(font(size 1 1))(justify right bottom))(uuid "{new_id(net + "label")}"))',
            ),
        ]:
            item = read_sexpr(text)
            sch.append(item)
            wires.append(sexpr(item))
    assert str(first(fp, "uuid")[1]) == str(first(symbol, "uuid")[1])
    (ROOT / "processor_carrier.kicad_sch").write_text(sexpr(sch) + "\n")
    parts = json.loads((ROOT / "components.json").read_text())
    c = copy.deepcopy(next(c for c in parts if c["ref"] == "J1"))
    c.update(
        ref="J13",
        x=234.95,
        y=539.75,
        note="Private ear input force pads; shared2.4A input target, all branch/PDN/assembly/strain/contact/fit qualification pending. Original J1 wire is unfitted service access.",
    )
    parts.append(c)
    assert len(parts) == 77
    (ROOT / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    with (ROOT / "bom.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    row = copy.deepcopy(next(c for c in rows if c["Reference"] == "J1"))
    row.update(Reference="J13", Note=c["note"])
    rows.append(row)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    (ROOT / "bom.csv").write_text(buf.getvalue())
    ledger = dict(
        source_parent_pcb_sha256=SOURCE_SHA,
        new_source_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        original_component_pin_maps_and_poses_required_unchanged=True,
        original_copper_removed=[],
        removed_original_outline=removed,
        actual_new_outline=newedge,
        new_native_J13_footprint=sexpr(fp),
        new_schematic_symbol=sexpr(symbol),
        new_schematic_wires_labels=wires,
        new_authored_zones=zones,
        world_board_ear_bbox_mm=[180, 95, 194, 107],
        J13_native_pad_centres_mm={"1": [258, 158], "2": [258, 162]},
        J13_world_pad_centres_mm={"1": [188, 100], "2": [188, 104]},
        minimum_copper_to_bottom_edge_nominal_mm=1.3,
        existing_J1_unfitted_service_wire=True,
        shared_input_current_target_a=2.4,
        known_existing_5v_branch_current_a={"Seed_including_nested3v3": 1.0, "LED5v": 0.764},
        remaining_shared_input_branch_or_reserve_current_a=0.636,
        remaining_branch_terminal_and_return_locations_assigned=False,
        full_tensor_extraction_started=False,
        native_refill_erc_parity_connectivity_required=True,
        source_parent_modified=False,
        mechanical_fit_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "design-change.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print("Created77part ear", ledger["new_source_pcb_sha256"])


if __name__ == "__main__":
    run()
