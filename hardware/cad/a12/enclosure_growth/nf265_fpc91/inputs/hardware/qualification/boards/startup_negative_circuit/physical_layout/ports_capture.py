"""Bind NC265's exact six physical port proposals into the new layout study."""

import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr, sexpr

from .capture import ROOT, box, sha

PORTS = ROOT.parents[1] / "nf_connector_receiving265"


def main():
    assert not (ROOT / "connector-placement.json").exists()
    source = PORTS / "ports.json"
    data = json.loads(source.read_text())
    parent = ROOT / "sources/NF05R"
    assert data["exact_electrical_source_seal"] == sha(parent / "handoff.json")
    assert data["source_components_sha256"] == sha(parent / "components.json")
    assert data["source_native_netlist_sha256"] == sha(parent / "generated/netlist.xml")
    parts = {c["ref"]: c for c in json.loads((parent / "components.json").read_text())}
    dest = ROOT / "sources/NC265"
    dest.mkdir(exist_ok=False)
    shutil.copyfile(source, dest / "ports.json")
    license_path = PORTS / "ConnectorCandidates.pretty/LICENSE.md"
    shutil.copyfile(license_path, dest / "KiCad-LICENSE.md")
    inventory = json.loads((ROOT / "land-inventory.json").read_text())
    by = {r["ref"]: r for r in inventory["rows"]}
    history = ROOT / "history/before-NC265-ports"
    history.mkdir(exist_ok=False)
    shutil.copyfile(ROOT / "land-inventory.json", history / "land-inventory.json")
    manifest = {"ports.json": dict(original=str(source), sha256=sha(source)),
                "KiCad-LICENSE.md": dict(original=str(license_path), sha256=sha(license_path))}
    for p in data["ports"]:
        ref = p["ref"]
        assert p["physical_pads"] == {n["number"]: n["net"] for n in parts[ref]["pins"]}, ref
        original = Path(p["footprint_file"])
        assert sha(original) == p["footprint_sha256"]
        copied = dest / original.name
        if not copied.exists():
            shutil.copyfile(original, copied)
        else:
            assert sha(copied) == sha(original)
        manifest[original.name] = dict(original=str(original), sha256=sha(original))
        tree = read_sexpr(original.read_text())
        assert {str(n[1]) for n in children(tree, "pad") if str(n[1])} == set(p["physical_pads"])
        alias = "NC265_" + str(tree[1])
        tree[1] = alias
        target = ROOT / "NF06P.pretty" / (alias + ".kicad_mod")
        target.write_text(sexpr(tree) + "\n")
        b = box(tree)
        by[ref].update(proposed_footprint="NF06P:" + alias, library_sha256=sha(target),
                       courtyard_bbox_mm=b, courtyard_area_mm2=(b[2] - b[0]) * (b[3] - b[1]),
                       land_basis="NC265 exact selected connector or force-pigtail candidate; physical/process unaccepted")
    assert sha(source) == manifest["ports.json"]["sha256"]
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "connector-placement.json").write_text(json.dumps(data, indent=2) + "\n")
    (ROOT / "land-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print("Bound six physical NC265 ports and40 exact signed pad assignments; process/fit unqualified")


if __name__ == "__main__":
    main()
