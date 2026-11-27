"""Independent checks of exported meshes and source-bound PCB mounting geometry.

This checks printable geometry, not slicer settings, material suitability,
supplier tolerance qualification, or electrical/thermal readiness.
"""
import argparse
import hashlib
import json
from pathlib import Path

import trimesh

from hardware.electronics.common.sexpr import children, first
from hardware.electronics.output_stage.check_placement import transform
from hardware.fabrication.assembly_layout import outline

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("revision")
    args = parser.parse_args()
    folder = ROOT / "generated" / args.revision
    capture = json.loads((ROOT / "capture.json").read_text())
    for relative, expected in capture["source_sha256"].items():
        assert digest(REPO / relative) == expected, relative
    expected_mounts = []
    inlet = {}
    for board in capture["boards"]:
        name = "signal_main.kicad_pcb" if board["id"] == "signal" else "power_protection.kicad_pcb"
        candidates = [p for p in capture["source_sha256"] if p.endswith("/" + name)]
        assert len(candidates) == 1
        tree, polygon = outline(REPO / candidates[0])
        assert list(map(list, list(polygon.exterior.coords)[:-1])) == board["outline"]
        for fp in children(tree, "footprint"):
            props = {p[1]: p[2] for p in children(fp, "property")}
            ref = props["Reference"]
            pads = children(fp, "pad")
            if ref in ("I_J1", "I_S1"):
                inlet[ref] = {"value": props["Value"], "pose": list(map(float, first(fp, "at")[1:]))}
            if pads and all(p[2] == "np_thru_hole" for p in pads):
                for pad in pads:
                    diameter = float(first(pad, "drill")[1])
                    if diameter < 3:
                        expected_mounts.append([ref, *transform(fp, first(pad, "at")[1:3]), board["z"], diameter])
    assert expected_mounts == capture["mounts"]
    assert len(expected_mounts) == 24
    assert inlet["I_J1"] == {"value": "PJ-102AH", "pose": [288.0, 12.1, 180.0]}
    assert inlet["I_S1"] == {"value": "JS102011SAQN", "pose": [302.0, 2.6, 180.0]}
    hits = []
    for ref, xy, z in capture["component_envelopes"] + capture["tail_envelopes"]:
        for context in capture["context"]:
            b, v = context["xy"], context["z"]
            overlaps = [min(xy[2], b[2]) - max(xy[0], b[0]),
                        min(xy[3], b[3]) - max(xy[1], b[1]),
                        min(z[1], v[1]) - max(z[0], v[0])]
            if min(overlaps) > 1e-5:
                hits.append([ref, context["id"], overlaps])
    assert not hits, hits
    meshes = []
    for path in sorted(folder.glob("*/*.stl")):
        if "collision" in path.parent.name or "positive" in path.parent.name:
            continue
        mesh = trimesh.load_mesh(path)
        record = {"file": str(path.relative_to(ROOT)), "sha256": digest(path),
                  "watertight": bool(mesh.is_watertight),
                  "consistent_winding": bool(mesh.is_winding_consistent),
                  "components": len(mesh.split()), "volume_mm3": float(mesh.volume),
                  "bounds_mm": mesh.bounds.tolist(), "extents_mm": mesh.extents.tolist(),
                  "faces": len(mesh.faces)}
        assert record["watertight"] and record["consistent_winding"]
        assert record["components"] == 1 and record["volume_mm3"] > 0, record
        assert mesh.bounds[0, 2] >= -1e-5, record
        meshes.append(record)
    assert meshes
    report = {"revision": args.revision, "scope": "Independent mesh and captured mounting/context review",
              "capture_sha256": digest(ROOT / "capture.json"),
              "review_script_sha256": digest(Path(__file__)),
              "source_bindings_verified": len(capture["source_sha256"]),
              "mount_centers_matching_actual_boards": len(expected_mounts),
              "inlet_actual_footprints": inlet, "component_context_collisions": hits,
              "meshes": meshes,
              "limits": ["No physical fit or printer/material qualification", "Allocated component envelopes, not exact supplier solids",
                         "No electrical or operational thermal approval", "Native collision tests are separate evidence"]}
    target = ROOT / ("independent-review-" + args.revision + ".json")
    assert not target.exists(), "Keep completed reviews immutable"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(target), "meshes_passed": len(meshes), "mounts_matched": len(expected_mounts)}))


if __name__ == "__main__":
    main()
