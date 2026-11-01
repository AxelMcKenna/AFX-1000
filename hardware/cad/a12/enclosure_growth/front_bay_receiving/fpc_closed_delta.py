"""Capture final electrically closed FPC84 and prove the precise C7 body subset.

UUID and net-number rebuilding is explicit; native net NAMES must remain equal.
No failed full-unit receiving case becomes a pass through this proof.
"""

import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .capture import REPO, ROOT, sha


def canonical(x):
    if not isinstance(x, list):
        return x
    return [canonical(v) for v in x if not isinstance(v, list) or not v or v[0] not in ["uuid", "net"]]


def packet(p):
    tree = read_sexpr(p.read_text())
    nets = {n[1]: n[-1] for n in children(tree, "net")}
    fps = {
        next(x[2] for x in children(f, "property") if x[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    mapping = {}
    for ref, fp in fps.items():
        mapping[ref] = {}
        for pad in children(fp, "pad"):
            node = children(pad, "net")
            value = (
                None if not node else node[0][-1] if len(node[0]) > 2 else nets.get(node[0][1], node[0][1])
            )
            mapping[ref][pad[1]] = value
    return fps, mapping


def build():
    source = REPO / "hardware/qualification/boards/fan_health/composite"
    dst = ROOT / "inputs/FPCClosed"
    if dst.exists():
        raise RuntimeError("Final source capture is one-shot")
    h = json.loads((source / "handoff.json").read_text())
    assert len(h["files_sha256"]) == 340
    assert all(sha(source / n) == v for n, v in h["files_sha256"].items())
    hashes = {}
    dst.mkdir()
    for n, v in h["files_sha256"].items():
        out = dst / n
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / n, out)
        assert sha(out) == v == sha(source / n)
        hashes[str(out.relative_to(ROOT))] = v
    shutil.copyfile(source / "handoff.json", dst / "handoff.json")
    a, oldnets = packet(ROOT / "inputs/FPC84/fan_power_health.kicad_pcb")
    b, newnets = packet(dst / "fan_power_health.kicad_pcb")
    assert set(a) == set(b) and oldnets == newnets
    changed = [n for n in a if canonical(a[n]) != canonical(b[n])]
    assert changed == ["C7"]
    old = courtyard(a["C7"], "F.CrtYd")
    new = courtyard(b["C7"], "F.CrtYd")
    assert new[0] >= old[0] and new[1] >= old[1] and new[2] <= old[2] and new[3] <= old[3]
    assert first(a["C7"], "at") == first(b["C7"], "at")
    assert first(a["C7"], "layer") == first(b["C7"], "layer") == ["layer", "F.Cu"]
    result = dict(
        source_handoff_sha256=sha(source / "handoff.json"),
        closed_PCB_sha256=sha(dst / "fan_power_health.kicad_pcb"),
        copied_input_sha256=hashes,
        all84_native_net_name_pinmaps_equal=True,
        raw_footprint_identity_not_claimed=True,
        canonicalization_removed_fields_only=["uuid", "net"],
        unchanged_complete_geometry_after_canonicalization=83,
        only_changed_part="C7",
        anchor_and_side_unchanged=True,
        old_native_courtyard_mm=old,
        new_native_courtyard_mm=new,
        new_body_projection_max_mm=0.97,
        old_receiving_projection_mm=1.9,
        exact_body_basis="KEMET CF0.80+0.07=0.87max plus PROJECT0.10seat=0.97; not0.95",
        new_receiving_body_strict_subset=True,
        old_failed_fullunit_cases_not_promoted=True,
        physical_qualified=False,
        electrical_unit_qualified=False,
        full_harness_qualified=False,
        source_sha256={
            str(p): sha(p)
            for p in [Path(__file__), ROOT / "inputs/FPC84/fan_power_health.kicad_pcb", dst / "handoff.json"]
        },
    )
    (ROOT / "generated/FPCClosed-C7-delta.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                closed_PCB=result["closed_PCB_sha256"],
                files=len(hashes),
                native_pinmaps=84,
                unchanged_canonical_geometry=83,
                C7_strict_subset=True,
            )
        )
    )


if __name__ == "__main__":
    build()
