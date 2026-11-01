"""Rebind captured geometry into fresh scratch paths; never live recapture."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .stage import OUT, ROOT, sha, write
from .verify import guard_output, inputs, row_errors


def prepare_rebind(destination):
    destination = Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(ROOT.resolve()):
        raise RuntimeError("Rebind needs a nonexistent scratch directory outside the sealed packet")
    c = json.loads((ROOT / "capture.json").read_text())
    assert all(sha(ROOT / n) == h for n, h in c["derived_context_sha256"].items())
    destination.mkdir(parents=True)
    derived = {}
    originals = {}
    for n, h in c["derived_context_sha256"].items():
        p = ROOT / n
        target = destination / n
        target.parent.mkdir(parents=True, exist_ok=True)
        originals[n] = h
        if p.suffix == ".scad":
            target.write_text(p.read_text().replace(str(ROOT / "context"), str(destination / "context")))
        else:
            shutil.copyfile(p, target)
        derived[str(target)] = sha(target)
    for name in ["context-derived.scad", "parts.scad", "config.json", "cases.json"]:
        p = OUT / name
        target = destination / name
        originals["generated/" + name] = sha(p)
        if p.suffix == ".scad":
            target.write_text(p.read_text().replace(str(ROOT / "context"), str(destination / "context")))
        else:
            shutil.copyfile(p, target)
        derived[str(target)] = sha(target)
    write(
        destination / "rebind-manifest.json",
        dict(
            source_packet=str(ROOT),
            source_capture_sha256=sha(ROOT / "capture.json"),
            originals_sha256=originals,
            rebound_sha256=derived,
            transformation="Only absolute captured context prefix rebound; no geometry edited or live files imported",
            live_recapture=False,
            original_sources_modified=False,
        ),
    )
    return destination


def replay(executable, destination, output, selected=None):
    output = guard_output(output)
    if output.exists():
        raise RuntimeError("Captured replay requires a fresh, nonexistent output directory")
    model = prepare_rebind(destination)
    output.mkdir(parents=True)
    specmap = json.loads((model / "cases.json").read_text())
    names = selected or list(specmap)
    assert all(n in specmap for n in names)
    cfg = json.loads((model / "config.json").read_text())
    bindings = inputs()
    bindings[str(Path(__file__).resolve())] = sha(Path(__file__))
    bindings.update({str(p): sha(p) for p in model.rglob("*") if p.is_file()})
    rows = {}
    for name in names:
        spec = specmap[name]
        target = output / (name + ".stl")
        v = dict(
            part="cp_only",
            thermal_part="cp_only",
            positive_part="cp_only",
            candidate_case="cp_only",
            trial="cp_only",
            ui_case="cp_only",
            eb_case="cp_only",
            ps_case="cp_only",
            cp_case="cp_only",
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=cfg["fasteners"],
            board_mounts=cfg["mounts"],
            rear_ports=cfg["rear_ports"],
            openings=cfg["openings"],
        )
        v[spec["selector"]] = spec["value"]
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for k, value in v.items():
            cmd += ["-D", k + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(model / "context-derived.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (output / (name + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            returncode=p.returncode,
            statistics=mesh(target) if target.exists() else None,
            command=cmd,
            role=spec["role"],
        )
        row["errors"] = row_errors(name, row, spec, output)
        row["clear"] = not row["errors"]
        rows[name] = row
        changed = [n for n, h in bindings.items() if sha(Path(n)) != h]
        result = dict(
            scope=__doc__,
            cases=rows,
            all_requested_clear=not changed and all(r["clear"] for r in rows.values()),
            full_required_set=names == list(specmap),
            required_count=len(specmap),
            input_sha256=bindings,
            changed_inputs=changed,
            source_packet=str(ROOT),
            rebind_manifest_sha256=sha(model / "rebind-manifest.json"),
            artifact_sha256={
                str(p): sha(p)
                for n in rows
                for p in [output / (n + ".log"), output / (n + ".stl")]
                if p.exists()
            },
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        )
        write(output / "verification.json", result)
        print(json.dumps(dict(case=name, clear=row["clear"], errors=row["errors"])), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True)
    parser.add_argument("--rebind-root", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--cases", nargs="*")
    args = parser.parse_args()
    r = replay(args.openscad, args.rebind_root, args.outdir, args.cases)
    raise SystemExit(0 if r["all_requested_clear"] else 1)
