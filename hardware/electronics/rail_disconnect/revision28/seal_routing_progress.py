"""Seal a reviewable partial-routing draft and verify every archived byte."""

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BASE = ROOT / "generated/p9-u14-input-escape-work"
WORK = ROOT / "generated/u28-return-dual-plane-work"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = WORK / "generated"
    handoff = out / "handoff.json"
    archive = out / "source-and-evidence.tar.gz"
    assert not handoff.exists() and not archive.exists()
    native = json.loads((out / "native-u28-return-dual-plane1.json").read_text())
    raw = json.loads((out / "drc-u28-return-dual-plane1.json").read_text())
    assert native["counts"] == dict(violations=82, unconnected_items=32, schematic_parity=0, erc=0)
    assert not any(r["severity"] == "error" for r in raw["violations"])
    assert native["source_unchanged_after_check"] and native["pcb_sha256"] == sha(
        WORK / "rail_disconnect.kicad_pcb"
    )
    source_files = set(ROOT.glob("*.py")) | {ROOT / "stackup.json", Path(__file__)}
    source_files.update((ROOT.parents[1] / "common").glob("*.py"))
    source_files.update((ROOT.parent / "revision26").glob("*.py"))
    for project in (BASE, WORK):
        for p in project.rglob("*"):
            if p.is_file() and "generated" not in p.relative_to(project).parts:
                source_files.add(p)
    artifacts = {p for p in out.iterdir() if p.is_file()}
    for folder in (
        "u23-band-placement-work",
        "u26-band-placement-work",
        "u27-band-placement-work",
        "u28-band-placement-work",
    ):
        for name in ("placement-proposal.json", "numeric-MCAD-screen.json", "numeric-mesh-screen.json"):
            artifacts.add(ROOT / "generated" / folder / "generated" / name)
    artifacts.update((ROOT / "generated/routing-recipe-history-before-format").iterdir())
    paths = source_files | artifacts
    expected = {str(p.relative_to(REPO)): sha(p) for p in sorted(paths)}
    index_bytes = (json.dumps(expected, indent=2) + "\n").encode()
    with archive.open("wb") as raw_stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_stream, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tar:
                for name, digest in expected.items():
                    data = (REPO / name).read_bytes()
                    assert hashlib.sha256(data).hexdigest() == digest
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o644
                    tar.addfile(info, io.BytesIO(data))
                info = tarfile.TarInfo("ARCHIVE-SHA256.json")
                info.size = len(index_bytes)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(index_bytes))
    with tarfile.open(archive, "r:gz") as tar:
        assert len(tar.getmembers()) == len(expected) + 1
        for name, digest in expected.items():
            assert hashlib.sha256(tar.extractfile(name).read()).hexdigest() == digest
        assert tar.extractfile("ARCHIVE-SHA256.json").read() == index_bytes
    assert all(sha(REPO / name) == digest for name, digest in expected.items())
    report = dict(
        source_baseline="Sealed U14, 43 native opens, preserved unchanged",
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(source_files)},
        artifact_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(artifacts)},
        archive_path=str(archive.relative_to(REPO)),
        archive_sha256=sha(archive),
        archive_members=len(expected) + 1,
        every_decompressed_member_byte_verified=True,
        native_counts=native["counts"],
        hard_DRC=0,
        exact_PCB_sha256=sha(WORK / "rail_disconnect.kicad_pcb"),
        byte_replay="README.md: literal delta reproduces exact board; changed-source and changed-literal controls reject",
        previous_sources_and_failure_reports_preserved=True,
        canonical_not_promoted=True,
        fresh_complete_MCAD_and_source_to_load_multiport_validation_pending=True,
        startup_fault_SOA_thermal_physical_and_fabrication_release=False,
        build_ready=False,
    )
    handoff.write_text(json.dumps(report, indent=2) + "\n")
    print("Handoff SHA256:", sha(handoff))
    print("Archive members byte-verified:", report["archive_members"])


if __name__ == "__main__":
    main()
