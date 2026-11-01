"""Explicit U39/bypass relocation with a six-fragment ordinary control repair."""

import hashlib
import json
import shutil
from pathlib import Path

from shapely.geometry import LineString, Point, box

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from .repair import Router
from .schmitt_receiver_joint_surface import geometry, key

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/v5-nearest-components-work"
WORK = ROOT / "generated/schmitt-u39-joint-placement-work"
POSES = {"U39": (154.5, 147.75), "C82": (153.8, 144.55)}


def shape(g):
    if g["kind"] == "line":
        return LineString([g["start"], g["end"]]).buffer(g["width"] / 2)
    if g["kind"] == "via":
        return Point(*g["xy"]).buffer(g["radius"])
    x, y = g["xy"]
    w, h = g["size"]
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    tree = read_sexpr(original.decode())
    old = Router(tree)
    changes = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in POSES:
            assert first(fp, "layer")[1] == "F.Cu"
            before = sexpr(fp)
            first(fp, "at")[1:3] = [a(str(v)) for v in POSES[ref]]
            changes.append(dict(ref=ref, before=before, after=sexpr(fp)))
    assert len(changes) == 2
    moved = Router(tree)
    blockers = {}
    forbidden = []
    for ref in POSES:
        for pad in moved.by_ref[ref]:
            copper = shape(pad)
            for g in old.geometry:
                if g.get("ref") in POSES or g["net"] == pad["net"] or not set(g["layers"]) & set(pad["layers"]):
                    continue
                gap = copper.distance(shape(g))
                if gap >= 0.205:
                    continue
                if g["kind"] == "line" and g["net"] == "E28_SOURCE_READY":
                    blockers[key(g)] = g
                else:
                    forbidden.append(dict(new_ref=ref, new_pin=pad["pin"], foreign=g, copper_gap_mm=gap))
    assert not forbidden, forbidden
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    tracks = {key(geometry(n, names)): n for n in children(tree, "segment")}
    removed = []
    for k in blockers:
        node = tracks[k]
        removed.append(dict(uuid=str(first(node, "uuid")[1]), net="E28_SOURCE_READY", literal=sexpr(node)))
        tree.remove(node)
    assert len(removed) == 6
    front = []
    for fp in children(tree, "footprint"):
        if first(fp, "layer")[1] != "F.Cu":
            continue
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        front.append((ref, box(*courtyard(fp, "F.CrtYd"))))
    for ref, c in front:
        if ref not in POSES:
            continue
        assert not [(r, c.intersection(q).area) for r, q in front if r != ref and c.intersection(q).area > 1e-10]
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for source in SOURCE.iterdir():
        if source.is_file() and (source.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or source.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(source, WORK / source.name)
        elif source.suffix == ".pretty":
            shutil.copytree(source, WORK / source.name)
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=hashlib.sha256(original).hexdigest(), candidate_pcb_sha256=hashlib.sha256((WORK / path.name).read_bytes()).hexdigest(), recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), source_native_opens=30, footprint_changes=changes, removed_ordinary_control_tracks=removed, every_existing_via_other_footprint_and_force_sense_timing_ground_track_fixed=True, all_ports_bulk_mounts_studs_edges_rules_fixed=True, entire_actual_circuit_and_values_fixed=True, no_historical_power_or_ground_matrix_inherited=True, new_native_MCAD_and_PDN_required=True, physical_qualified=False)
    (WORK / "generated/placement-proposal.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original
    print("Moved U39/C82; six E28_SOURCE_READY fragments require actual reconnection", flush=True)


if __name__ == "__main__":
    main()
