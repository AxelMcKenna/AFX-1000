"""Capture the explicit two-part NF233 successor; preserve first NF231 model."""

import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr

from .capture import REPO, ROOT, sha


def strip_nets(node):
    if not isinstance(node, list):
        return node
    return [strip_nets(v) for v in node if not isinstance(v, list) or not v or v[0] != "net"]


def fps(path):
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(read_sexpr(path.read_text()), "footprint")
    }


def capture():
    dst = ROOT / "inputs/NF233"
    if dst.exists():
        raise RuntimeError("NF233 capture already exists")
    source = REPO / "hardware/qualification/boards/startup_negative_circuit/ready_integration/pcb"
    a = fps(ROOT / "inputs/NF231/negative_startup_placement.kicad_pcb")
    b = fps(source / "negative_startup_ready.kicad_pcb")
    assert len(a) == 231 and len(b) == 233 and set(b) - set(a) == {"U49", "C88"}
    assert all(strip_nets(fp) == strip_nets(b[n]) for n, fp in a.items())
    hashes = {}
    copied = {}
    for p in [
        p
        for p in source.rglob("*")
        if p.is_file()
        and p.suffix not in {".lck", ".kicad_prl"}
        and not p.name.startswith("~")
        and "__pycache__" not in p.parts
    ] + [source.parent / "components.json"]:
        rel = Path("components.json") if p == source.parent / "components.json" else p.relative_to(source)
        h = sha(p)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, out)
        assert sha(out) == h == sha(p)
        hashes[str(p)] = h
        copied[str(out.relative_to(ROOT))] = h
    d = dict(
        parent231_full_footprint_geometry_identical_after_only_net_fields_removed=True,
        changed_existing_FP_net_assignments=[n for n in a if a[n] != b[n]],
        added_actual_footprints=["U49", "C88"],
        originals_sha256=hashes,
        copied_input_sha256=copied,
        later_native_routing_not_inherited=True,
        physical_qualified=False,
    )
    (ROOT / "NF233-delta-capture.json").write_text(json.dumps(d, indent=2) + "\n")
    print(json.dumps(dict(copied=len(copied), added=2, preserved_geometry=231)))


if __name__ == "__main__":
    capture()
