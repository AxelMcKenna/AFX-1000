"""Build a copied J4/PCB-ear proposal; never mutate the operating board.

Only J4's placement, solder lands, wire identification and a short right-edge
extension change. Original traces/vias and all other footprints stay intact.
Native connectivity does not qualify a narrow pour neck to the new terminal.
"""

import argparse
import copy
import csv
import io
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from ..generate import REPO, sha

SOURCE = REPO / "hardware/electronics/rail_disconnect/revision28"
ROOT = Path(__file__).resolve().parent
FOOTPRINT = "AWG14_Force_2x1_P6mm_D3p0"
VALUE = "Alpha6717_AWG14_DIG_FORCE_PROPOSAL"
WORLD_PAD1 = [165.3, 137.0]
NATIVE_PAD1 = [257.3, 128.5]


def alter_lands(fp):
    for pad in children(fp, "pad"):
        assert float(first(pad, "drill")[1]) == 2.2
        first(pad, "size")[1:] = [a(3), a(3)]
    for rect in children(fp, "fp_rect"):
        if first(rect, "layer")[1] in ("F.CrtYd", "B.CrtYd"):
            first(rect, "start")[1:] = [a(-1.75), a(-1.75)]
            first(rect, "end")[1:] = [a(1.75), a(7.75)]


def build(workspace):
    assert not workspace.exists(), "Use a fresh proposal workspace"
    source_paths = []
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru")
            or p.name in ("fp-lib-table", "sym-lib-table", "components.json", "bom.csv")
        ):
            source_paths.append(p)
        elif p.is_dir() and p.suffix == ".pretty":
            source_paths.extend(q for q in p.rglob("*") if q.is_file())
    hashes = {str(p.relative_to(REPO)): sha(p) for p in source_paths}
    workspace.mkdir(parents=True)
    for p in source_paths:
        target = workspace / p.relative_to(SOURCE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    pcb = workspace / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    footprints = children(tree, "footprint")
    j4 = next(f for f in footprints if any(p[1:3] == ["Reference", "J4"] for p in children(f, "property")))
    unchanged = [sexpr(f) for f in footprints if f is not j4]
    old_tracks = [sexpr(n) for n in tree if isinstance(n, list) and n and n[0] in ("segment", "via", "arc")]
    first(j4, "at")[1:] = [a(x) for x in NATIVE_PAD1]
    j4[1] = "RMX_E28:" + FOOTPRINT
    for p in children(j4, "property"):
        if p[1] == "Value":
            p[2] = VALUE
    alter_lands(j4)
    edge = next(
        n
        for n in children(tree, "gr_line")
        if first(n, "layer")[1] == "Edge.Cuts"
        and list(map(float, first(n, "start")[1:])) == [256, 100]
        and list(map(float, first(n, "end")[1:])) == [256, 137.012881]
    )
    points = [[256, 100], [256, 126.5], [259.3, 126.5], [259.3, 136.5], [256, 136.5], [256, 137.012881]]
    tree.remove(edge)
    for i, (start, end) in enumerate(zip(points, points[1:])):
        line = copy.deepcopy(edge)
        first(line, "start")[1:] = [a(x) for x in start]
        first(line, "end")[1:] = [a(x) for x in end]
        uid = a(str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-j4-ear-" + str(i))))
        if children(line, "uuid"):
            first(line, "uuid")[1] = uid
        else:
            line.append([a("uuid"), uid])
        tree.append(line)
    assert unchanged == [sexpr(f) for f in children(tree, "footprint") if f is not j4]
    assert old_tracks == [
        sexpr(n) for n in tree if isinstance(n, list) and n and n[0] in ("segment", "via", "arc")
    ]
    pcb.write_text(sexpr(tree) + "\n")
    library = read_sexpr((SOURCE / "RMX_E28.pretty/AWG14_Force_2x1_P6mm.kicad_mod").read_text())
    library[1] = FOOTPRINT
    alter_lands(library)
    (workspace / ("RMX_E28.pretty/" + FOOTPRINT + ".kicad_mod")).write_text(sexpr(library) + "\n")
    sch = workspace / "rail_disconnect.kicad_sch"
    schematic = read_sexpr(sch.read_text())
    symbol = next(
        s
        for s in children(schematic, "symbol")
        if any(p[1:3] == ["Reference", "J4"] for p in children(s, "property"))
    )
    for p in children(symbol, "property"):
        if p[1] == "Value":
            p[2] = VALUE
        if p[1] == "Footprint":
            p[2] = "RMX_E28:" + FOOTPRINT
    sch.write_text(sexpr(schematic) + "\n")
    components = json.loads((workspace / "components.json").read_text())
    component = next(c for c in components if c["ref"] == "J4")
    component.update(
        part=VALUE,
        footprint="RMX_E28:" + FOOTPRINT,
        source="https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=6717",
        note="Isolated relocation/land/wire proposal. Source joint<=.5mOhm remains measured acceptance; all conductor/fit/strain/process qualification open.",
    )
    (workspace / "components.json").write_text(json.dumps(components, indent=2) + "\n")
    with (workspace / "bom.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        if row["Reference"] == "J4":
            row.update(
                Part_or_value=VALUE,
                Footprint_candidate="RMX_E28:" + FOOTPRINT,
                Datasheet=component["source"],
                Design_note=component["note"],
            )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    (workspace / "bom.csv").write_text(buf.getvalue())
    assert all(sha(REPO / name) == h for name, h in hashes.items()), "Operating source changed during capture"
    receipt = dict(
        scope="Isolated J4/ear geometry and wire proposal; no current-carrying path qualification",
        source_sha256=hashes,
        source_pcb_sha256=hashes[str((SOURCE / "rail_disconnect.kicad_pcb").relative_to(REPO))],
        candidate_pcb_sha256=sha(pcb),
        helper_sha256=sha(Path(__file__)),
        world_pad1_mm=WORLD_PAD1,
        world_pad2_mm=[WORLD_PAD1[0], WORLD_PAD1[1] + 6],
        ear_box_world_xy_mm=[164, 135, 167.3, 145],
        nominal_other_board_gap_mm=0.7,
        land_diameter_mm=3,
        finished_hole_requirement_mm=[2.1, 2.3],
        minimum_nominal_annulus_at_maximum_hole_mm=0.35,
        unchanged_other_footprints=len(unchanged),
        original_tracks_vias_unchanged=True,
        native_checked=False,
        current_path_resistance_qualified=False,
        strain_relief_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (workspace / "proposal.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(workspace, sha(pcb))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    build(parser.parse_args().workspace.resolve())
