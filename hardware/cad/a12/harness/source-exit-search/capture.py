"""Capture read-only native obstacle and fed-R58 electronics evidence."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
SOURCE = ROOT.parent / "generated/source-obstacles"
FORMED = ROOT.parent / "generated/output-formed-6715-east-pair-r58"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target = ROOT / "inputs"
    assert not target.exists()
    target.mkdir()
    v = json.loads((SOURCE / "verification.json").read_text())
    a = json.loads((FORMED / "analysis.json").read_text())
    assert v["actual_local_obstacle_solids_accepted"] and not v["changed_inputs"]
    hashes = {}
    for data in [v, a]:
        for group in ["source_sha256", "evidence_sha256"]:
            for name, digest in data.get(group, {}).items():
                assert sha(REPO / name) == digest, ("Stale input", name)
                hashes[name] = digest
    files = {
        SOURCE / "verification.json": "obstacle-verification.json",
        FORMED / "analysis.json": "formed-analysis.json",
        FORMED / "verification.json": "formed-verification.json",
        FORMED / "obstacles.json": "electronics.json",
        ROOT.parent / "output-wire-6715.json": "wire.json",
    }
    for name in ["case", "return", "positive", "switch_lead_witness"]:
        files[SOURCE / (name + ".stl")] = name + ".stl"
    for p, name in files.items():
        digest = sha(p)
        shutil.copyfile(p, target / name)
        assert sha(p) == sha(target / name) == digest
        hashes[str(p.relative_to(REPO))] = digest
    source = REPO / a["source_R58_proposal"] / "rail_disconnect.kicad_pcb"
    assert sha(source) == a["source_native_PCB_sha256"]
    shutil.copyfile(source, target / "fed-source.kicad_pcb")
    hashes[str(source.relative_to(REPO))] = sha(source)
    report = dict(
        original_source_sha256=hashes,
        copied_inputs_sha256={p.name: sha(p) for p in target.iterdir() if p.is_file()},
        clipping_window_mm=[[154, 104, 3], [185, 139, 37]],
        source_face_z_mm=a["source_face_z_mm"],
        source_pcb_electrical_routing_closed=False,
        source_joint_independent_native_pass_is_required_separate=True,
        physical_qualified=False,
    )
    (ROOT / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Captured", len(hashes), "original inputs")


if __name__ == "__main__":
    main()
