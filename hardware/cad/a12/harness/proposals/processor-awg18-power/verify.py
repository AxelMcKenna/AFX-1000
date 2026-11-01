"""Fail-closed source/native bindings for diagnostic reports; never a release gate."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_report(path, report=None):
    path = Path(path).resolve()
    folder = path.parent.parent
    report = json.loads(path.read_text()) if report is None else report
    for key in [
        "endpoint_physical_qualified",
        "complete_pdn_qualified",
        "physical_qualified",
        "fabrication_released",
    ]:
        assert report[key] is False, "A diagnostic cannot qualify hardware"
    for name, digest in report["source_sha256"].items():
        p = (folder / name).resolve()
        assert p.is_relative_to(folder.resolve()), "Model input escapes workspace"
        assert sha(p) == digest, ("Stale model source", name)
    dataset = folder / "generated" / ("baseline" if report["baseline"] else "")
    pcb = dataset / "filled.kicad_pcb"
    pads = json.loads((dataset / "pads.json").read_text())
    assert report["source_pcb_sha256"] == sha(pcb) == pads["source_pcb_sha256"]
    assert pads["actual_layers"] == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    assert pads["source_modified"] is False
    native = json.loads((dataset / "native.json").read_text())
    for group in ["source_sha256", "artifact_sha256"]:
        for name, digest in native[group].items():
            p = (REPO / name).resolve()
            assert p.is_relative_to(REPO.resolve())
            assert sha(p) == digest, ("Stale native evidence", name)
    assert all(type(v) is int and v == 0 for v in native["counts"].values())
    artifacts = native["artifact_sha256"]
    drcname = next(n for n in artifacts if n.endswith("/drc.json"))
    ercname = next(n for n in artifacts if n.endswith("/erc.json"))
    drc = json.loads((REPO / drcname).read_text())
    erc = json.loads((REPO / ercname).read_text())
    assert not drc["violations"] and not drc["unconnected_items"] and not drc["schematic_parity"]
    assert not any(s["violations"] for s in erc["sheets"])
    scenario = report["scenario"]
    assert (
        len(scenario["copper_mm"]) == len(scenario["centroids_mm"]) == 4
        and scenario["fabricator_or_material_accepted"] is False
    )
    for net, cases in report["networks"].items():
        assert set(cases) == {"20", "100"}
        for case in cases.values():
            assert (
                math.isfinite(case["max_absolute_kcl_residual_a"])
                and case["max_absolute_kcl_residual_a"] < 1e-7
            )
            assert case["equipotential_pad_or_via_short_used"] is False
            assert set(case["actual_copper_area_per_layer_mm2"]) == {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"}
    return True


if __name__ == "__main__":
    paths = [
        *ROOT.joinpath("generated").glob("*-grid*.json"),
        *ROOT.joinpath("stitch_trial/generated").glob("*-grid*.json"),
    ]
    count = 0
    for p in paths:
        d = json.loads(p.read_text())
        if "local_simultaneous_sharing_corners" in d:
            validate_report(p, d)
            count += 1
    print("Source/native diagnostic reports verified:", count)
