"""Private J4 ground-pad pitch study; sealed R58 and canonical stay immutable."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = "fed472582baae77623eb76495e82da3286fbedd94ca43a41858120a419ca5cc8"


def main(workspace):
    source = ROOT / "generated/r58-joint-work"
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    pcb = source / "rail_disconnect.kicad_pcb"
    assert hashlib.sha256(pcb.read_bytes()).hexdigest() == SOURCE_SHA
    workspace.mkdir()
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("sym-lib-table", "fp-lib-table", "components.json")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    (workspace / "generated").mkdir()
    tree = read_sexpr(pcb.read_text())
    original = copy.deepcopy(tree)
    j4 = next(
        f
        for f in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == "J4" for p in children(f, "property"))
    )
    original_j4 = copy.deepcopy(j4)
    assert list(map(float, first(j4, "at")[1:])) == [253, 112, 0]
    old, new = "AWG14_Force_2x1_P6mm", "AWG14_Force_2x1_P9mm_Engineering"
    assert j4[1] == "RMX_E28:" + old

    def change(fp):
        ground = next(p for p in children(fp, "pad") if p[1] == "2")
        assert list(map(float, first(ground, "at")[1:])) == [0, 6]
        assert list(map(float, first(ground, "size")[1:])) == [4.2, 4.2]
        assert float(first(ground, "drill")[1]) == 2.2
        first(ground, "at")[2] = a("9")
        for rect in children(fp, "fp_rect"):
            assert first(rect, "layer")[1] in ("F.CrtYd", "B.CrtYd")
            assert list(map(float, first(rect, "end")[1:])) == [2.35, 8.35]
            first(rect, "end")[2] = a("11.35")

    change(j4)
    j4[1] = "RMX_E28:" + new
    # Everything outside this complete footprint stays literally identical.
    assert [n for n in tree if n is not j4] == [n for n in original if n != original_j4]
    assert children(j4, "pad")[0] == children(original_j4, "pad")[0]
    (workspace / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    lib = workspace / "RMX_E28.pretty" / (old + ".kicad_mod")
    footprint = read_sexpr(lib.read_text())
    change(footprint)
    footprint[1] = new
    (lib.parent / (new + ".kicad_mod")).write_text(sexpr(footprint) + "\n")
    schematic = workspace / "rail_disconnect.kicad_sch"
    content = schematic.read_text()
    assert content.count("RMX_E28:" + old) == 1
    schematic.write_text(content.replace("RMX_E28:" + old, "RMX_E28:" + new))
    components = workspace / "components.json"
    parts = json.loads(components.read_text())
    ref = next(p for p in parts if p["ref"] == "J4")
    assert ref["footprint"] == "RMX_E28:" + old
    ref["footprint"] = "RMX_E28:" + new
    components.write_text(json.dumps(parts, indent=2) + "\n")
    receipt = dict(
        source_pcb_sha256=SOURCE_SHA,
        candidate_pcb_sha256=hashlib.sha256((workspace / pcb.name).read_bytes()).hexdigest(),
        original_j4_native=sexpr(original_j4),
        candidate_j4_native=sexpr(j4),
        old_ground_world_mm=[161, 126.5],
        new_ground_world_mm=[161, 129.5],
        positive_pad_and_j4_origin_unchanged=True,
        all_tracks_vias_other_holes_other_parts_zones_setup_unchanged=True,
        only_ground_hole_location_changed=True,
        native_all_track_and_force_fill_checks_required=True,
        canonical_or_sealed_source_changed=False,
        physical_qualified=False,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (workspace / "generated/j4-pitch-proposal.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert hashlib.sha256(pcb.read_bytes()).hexdigest() == SOURCE_SHA
    print("Isolated J4 pitch9mm candidate:", receipt["candidate_pcb_sha256"])


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.workspace)
