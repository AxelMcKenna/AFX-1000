"""Copy the exact accepted ROOT21 native run and its bound inputs without changing it."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
OUT = ROOT / "native_evidence"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (OUT / "capture.json").exists():
        raise ValueError("Preserve completed native capture")
    original = ROOT.parent / "generated/receiver-full-route"
    proof = json.loads((original / "verification.json").read_text())
    if not proof["whole_pair_native_geometry_clear"] or proof["changed_inputs"] or len(proof["cases"]) != 21:
        raise ValueError("Rejected ROOT native route")
    OUT.mkdir(exist_ok=True)
    bound = {}
    for key in ["source_sha256", "evidence_inputs_sha256", "evidence_sha256"]:
        for relative, h in proof.get(key, {}).items():
            p = REPO / relative
            if sha(p) != h:
                raise ValueError("Stale ROOT native input:" + relative)
            bound[relative] = h
    print(
        "Copying",
        len(bound),
        "exactinputs",
        sum((REPO / p).stat().st_size for p in bound),
        "bytes",
        flush=True,
    )
    for relative, h in bound.items():
        dst = OUT / "context" / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / relative, dst)
        if sha(dst) != h:
            raise ValueError("Failed exact capture:" + relative)
    artifacts = {}
    for p in original.iterdir():
        if p.is_file() and (p.suffix in [".json", ".scad", ".log", ".stl"]):
            dst = OUT / p.name
            shutil.copy2(p, dst)
            artifacts[p.name] = sha(dst)
    raw = (OUT / "checks.scad").read_text()
    replay = raw.replace(str(REPO) + "/", str(OUT / "context") + "/")
    (OUT / "replay-checks.scad").write_text(replay)
    cap = dict(
        original_run=str(original.relative_to(REPO)),
        bound_source_evidence_sha256=bound,
        copied_raw_artifact_sha256=artifacts,
        replay_SCAD_rewrites_only_absolute_repository_root=True,
        replay_SCAD_sha256=sha(OUT / "replay-checks.scad"),
        selected_paths_sha256=sha(ROOT / "generated/selected-paths.json"),
        original_native_receipt_sha256=sha(OUT / "verification.json"),
        all21_geometric_cases_accepted=True,
        physical_fit_verified=False,
        forming_strain_relief_or_solder_qualified=False,
        electrical_harness_qualified=False,
        fabrication_released=False,
    )
    (OUT / "capture.json").write_text(json.dumps(cap, indent=2) + "\n")
    print("Native exact capture complete", flush=True)


if __name__ == "__main__":
    main()
