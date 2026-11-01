"""Capture exact sealed NF261/NF265 and public receiving references."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(folder, expected):
    hand = folder / "handoff.json"
    if sha(hand) != expected:
        raise ValueError("Wrong sealed input: " + str(folder))
    d = json.loads(hand.read_text())
    for name, checksum in d["files_sha256"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts or sha(folder / name) != checksum:
            raise ValueError("Invalid/changed sealed file: " + name)
    return d


def build():
    target = ROOT / "inputs"
    if target.exists() or (ROOT / "capture.json").exists():
        raise RuntimeError("Refusing to recapture a source packet")
    sources = [
        (
            "NF261",
            REPO / "hardware/qualification/boards/startup_negative_circuit/absolute_aux_gate",
            "6459d8269a46bbc6f1c1558bb8dbfc68c12082f9cbaefcf1a4865cbbdc182a02",
        ),
        (
            "NF265",
            REPO / "hardware/qualification/boards/startup_negative_circuit/uv_recovery",
            "f53cdb06d5f8c717ddc7b0b077bedf5ff1b855561d742b6e0197465467738cad",
        ),
    ]
    records = []
    for name, folder, expected in sources:
        d = sealed(folder, expected)
        for rel in ["handoff.json", *d["files_sha256"]]:
            to = target / name / rel
            to.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(folder / rel, to)
            if sha(to) != sha(folder / rel):
                raise ValueError("Copy mismatch")
        sealed(folder, expected)
        records.append(
            dict(
                name=name,
                original=str(folder),
                seal_sha256=expected,
                copied_files=len(d["files_sha256"]) + 1,
                all_source_hashes_checked_before_and_after=True,
            )
        )
    extras = {
        "NC01-analysis.json": "hardware/qualification/boards/nf_connector_receiving/generated/analysis.json",
        "NC01-local-fanout.json": "hardware/qualification/boards/nf_connector_receiving/generated/local-PHD30-fanout.json",
        "NC01-force-proposal.json": "hardware/qualification/boards/nf_connector_receiving/generated/force-pigtail-proposal.json",
        "NP01-analysis.json": "hardware/qualification/boards/nf_passive_selection/analyses/analysis.json",
        "NP01-selections.json": "hardware/qualification/boards/nf_passive_selection/generated/selections.json",
        "NP01-seal.json": "hardware/qualification/boards/nf_passive_selection/handoff.json",
        "NP01P1-seal.json": "hardware/qualification/boards/nf_passive_selection_portable/handoff.json",
        "alpha6715-proposal.json": "hardware/cad/a12/harness/output-wire-6715.json",
        "jst-XH-public.pdf": "hardware/cad/a12/enclosure_growth/front_bay_receiving/sources/jst-eXH-official-US.pdf",
    }
    for name in [
        "alpha3049.pdf",
        "alpha3050.pdf",
        "alpha6715-current.pdf",
        "jst-PH-public-US.pdf",
        "jst-PHD-public-ES.pdf",
        "jst-PHD-public-regional.pdf",
    ]:
        extras["primary/" + name] = (
            "hardware/qualification/boards/nf_connector_receiving/sources/primary/" + name
        )
    for name in [
        "JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod",
        "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical.kicad_mod",
        "LICENSE.md",
    ]:
        extras["KiCad/" + name] = (
            "hardware/qualification/boards/nf_connector_receiving/sources/repository/KiCad/" + name
        )
    for name in ["kemet-X7R-2026.pdf", "vishay-TNPU-28779.pdf", "vishay-TNPW-28758.pdf"]:
        extras["primary/" + name] = (
            "hardware/qualification/boards/nf_passive_selection/sources/primary/" + name
        )
    copied = {}
    for name, source in extras.items():
        p = REPO / source
        to = target / "references" / name
        to.parent.mkdir(parents=True, exist_ok=True)
        before = sha(p)
        shutil.copyfile(p, to)
        if sha(p) != before or sha(to) != before:
            raise ValueError("Reference changed while copying")
        copied[str(to.relative_to(ROOT))] = dict(original=str(p), sha256=before)
    d = dict(
        revision="NC265-exact-capture",
        sealed_sources=records,
        extra_captured_references=copied,
        source_SHA256=sha(Path(__file__)),
        parent_edits=False,
        physical_qualified=False,
    )
    (ROOT / "capture.json").write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(dict(sealed_files=sum(r["copied_files"] for r in records), extra_references=len(copied)))
    )


if __name__ == "__main__":
    build()
