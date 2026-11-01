"""One-shot immutable receiving-input capture; never rebuild a sealed packet."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
NF = REPO / "hardware/qualification/boards/startup_negative_circuit/physical_layout"
FPC = REPO / "hardware/qualification/boards/fan_health/composite_nf_branch"
NC = REPO / "hardware/qualification/boards/nf_connector_receiving265"
FR = ROOT.parent / "front_bay_receiving"
UA = ROOT.parent / "unified_airpath"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2) + "\n")


def checked_seal(folder):
    data = json.loads((folder / "handoff.json").read_text())
    for n, h in data["files_sha256"].items():
        assert sha(folder / n) == h, (folder, n)
    return data


def closure(entry):
    """Literal closure plus explicitly named absolute model directories.

    Absolute directory variables are used by the captured UA positive-link
    imports. Every existing STL in such a directory is retained, not only the
    currently rendered object. An unresolvable include/import is an error.
    """
    found = {}
    todo = [entry.resolve()]
    while todo:
        p = todo.pop().resolve()
        if p in found:
            continue
        assert p.is_file(), p
        found[p] = sha(p)
        if p.suffix != ".scad":
            continue
        source = p.read_text()
        for a, b in re.findall(r'(?:include|use)\s*<([^>]+)>|import\(\s*"([^"]+)"', source):
            q = Path(a or b)
            todo.append(q if q.is_absolute() else p.parent / q)
        for value in re.findall(r'"(/[^"\n]+)"', source):
            q = Path(value)
            if q.is_dir():
                todo.extend(q.glob("*.stl"))
            elif q.is_file() and q.suffix in {".stl", ".scad", ".off", ".3mf"}:
                todo.append(q)
    return found


def capture():
    if (ROOT / "capture.json").exists() or (ROOT / "inputs").exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("Capture refuses existing output; use a NEW sibling")
    seals = {str(p.relative_to(REPO)): checked_seal(p) for p in [FPC, NC, FR, UA]}
    nf_files = [
        p
        for p in NF.iterdir()
        if p.is_file()
        and p.suffix in {".json", ".py", ".csv", ".kicad_pcb", ".kicad_pro", ".kicad_sch", ".kicad_sym"}
    ]
    nf_files += [NF / "fp-lib-table", NF / "sym-lib-table"]
    nf_files += list((NF / "NF06P.pretty").glob("*.kicad_mod"))
    nf_files += [
        p for p in (NF / "generated").rglob("*") if p.is_file() and p.suffix in {".json", ".xml", ".txt"}
    ]
    entries = [FR / "mount_variant5/checks.scad", NC / "mechanical-v2/geometry.scad"]
    original = {}
    for p in entries:
        original.update(closure(p))
    for p in nf_files:
        original[p.resolve()] = sha(p)
    for folder in [FPC, NC]:
        for n, h in seals[str(folder.relative_to(REPO))]["files_sha256"].items():
            original[(folder / n).resolve()] = h
    for folder in [FPC, NC, FR, UA]:
        original[folder / "handoff.json"] = sha(folder / "handoff.json")
    # Historical receipt/metadata prove the ancestry without importing every
    # prior rendered diagnostic mesh into the current geometry.
    for p in [FR / "generated/interface-final.json", UA / "model/config.json"]:
        original[p] = sha(p)
    original[Path(__file__)] = sha(Path(__file__))
    before = {str(p.relative_to(REPO)): h for p, h in original.items()}
    copied = {}
    for p, expected in original.items():
        data = p.read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected, p
        dst = ROOT / "inputs" / p.relative_to(REPO)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        copied[str(dst.relative_to(ROOT))] = sha(dst)
    after = {str(p.relative_to(REPO)): sha(p) for p in original}
    assert before == after, "Input changed across capture; keep failed copy and use new folder"
    mapping = {p: ROOT / "context" / p.relative_to(REPO) for p in original}
    derived = {}
    for p, dst in mapping.items():
        if p.suffix not in {".scad", ".stl", ".off", ".3mf"}:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".scad":
            source = p.read_text()
            source = source.replace(str(REPO) + "/", str(ROOT / "context") + "/")
            dst.write_text(source)
        else:
            dst.write_bytes((ROOT / "inputs" / p.relative_to(REPO)).read_bytes())
        derived[str(dst.relative_to(ROOT))] = sha(dst)
    write(
        ROOT / "capture.json",
        dict(
            revision="NF265-FPC91-receiving-capture-01",
            original_source_sha256=before,
            after_capture_source_sha256=after,
            copied_input_sha256=copied,
            derived_context_sha256=derived,
            parent_seals={
                n: dict(files=len(d["files_sha256"]), handoff_sha256=sha(REPO / n / "handoff.json"))
                for n, d in seals.items()
            },
            native_NF_electrical_parts=265,
            native_NF_total_footprints=267,
            NF_unrouted_opens=499,
            FPC_electrical_parts=91,
            canonical_sources_changed=False,
            later_E28_269_or_routing_scratch_adopted=False,
            physical_qualified=False,
            full_harness_qualified=False,
        ),
    )
    print(
        json.dumps(
            dict(
                captured_files=len(before),
                context_files=len(derived),
                NF_PCB_sha256=sha(NF / "negative_startup_physical.kicad_pcb"),
                NF_components_sha256=sha(NF / "components.json"),
                NF_placement_sha256=sha(NF / "placement.json"),
            )
        )
    )


if __name__ == "__main__":
    capture()
