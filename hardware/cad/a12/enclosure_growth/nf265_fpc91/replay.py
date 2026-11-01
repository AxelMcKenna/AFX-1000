"""Captured-source-only replay staging; never recaptures live parent designs."""

import argparse
import json
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .capture import ROOT, closure, sha, write
from .verify import ENGINE, errors, specs, variables


def stage(output):
    output = Path(output).resolve()
    if output.exists():
        raise RuntimeError("Refuse existing replay output")
    # This is the already-captured derived model, not any current canonical
    # board/generator. Every SCAD and imported mesh is explicitly rebound.
    entry = ROOT / "tail_shape/checks.scad"
    original = closure(entry)
    output.mkdir(parents=True)
    copies = {}
    for p, h in original.items():
        dst = output / "captured" / p.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".scad":
            dst.write_text(p.read_text().replace(str(ROOT) + "/", str(output / "captured") + "/"))
        else:
            dst.write_bytes(p.read_bytes())
        assert sha(p) == h
        copies[str(dst)] = sha(dst)
    cfg = ROOT / "inputs/hardware/cad/a12/enclosure_growth/unified_airpath/model/config.json"
    write(
        output / "replay.json",
        dict(
            captured_source_sha256={str(p): h for p, h in original.items()},
            rebound_source_sha256=copies,
            entry=str(output / "captured" / entry.relative_to(ROOT)),
            configuration=json.loads(cfg.read_text()),
            configuration_sha256=sha(cfg),
            replay_source_sha256=sha(Path(__file__)),
            original_packet_handoff_sha256=sha(ROOT / "handoff.json")
            if (ROOT / "handoff.json").exists()
            else None,
            live_parent_designs_read=False,
            physical_qualified=False,
        ),
    )
    return output


def execute(output, names=None):
    path = output / "replay.json"
    replay = json.loads(path.read_text())
    assert all(sha(Path(n)) == h for n, h in replay["rebound_source_sha256"].items())
    target = output / "native"
    if target.exists():
        raise RuntimeError("Refuse existing native replay output")
    names = names or list(specs())
    assert names and len(names) == len(set(names)) and all(n in specs() for n in names)
    target.mkdir()
    rows = {}
    for name in names:
        command = [
            str(ENGINE),
            "--hardwarnings",
            "--backend=Manifold",
            "--export-format=binstl",
            "-o",
            str(target / (name + ".stl")),
        ]
        for k, v in variables(name).items():
            command += ["-D", k + "=" + json.dumps(v)]
        command += [replay["entry"]]
        p = subprocess.run(command, capture_output=True, text=True)
        (target / (name + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            returncode=p.returncode,
            command=command,
            statistics=mesh(target / (name + ".stl")) if (target / (name + ".stl")).exists() else None,
        )
        row["errors"] = errors(name, row, specs()[name], target)
        row["clear"] = not row["errors"]
        rows[name] = row
        report = dict(
            cases=rows,
            required_cases=names,
            all_requested_clear=len(rows) == len(names) and all(r["clear"] for r in rows.values()),
            replay_manifest_sha256=sha(path),
            engine_sha256=sha(ENGINE),
            input_sha256=replay["rebound_source_sha256"],
            artifact_sha256={str(p): sha(p) for p in target.iterdir() if p.suffix in {".log", ".stl"}},
            physical_qualified=False,
            full_harness_qualified=False,
        )
        write(target / "verification.json", report)
        print(json.dumps(dict(case=name, clear=row["clear"])), flush=True)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", required=True, type=Path)
    p.add_argument("--run-native", action="store_true")
    p.add_argument("--cases", nargs="+")
    a = p.parse_args()
    out = stage(a.outdir)
    if a.run_native:
        raise SystemExit(not execute(out, a.cases)["all_requested_clear"])
