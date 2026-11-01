"""Guarded native runner. Currently blocked; never retry a failing native app."""

import json
import subprocess
from pathlib import Path

from hardware.cad.a12.enclosure_growth.nf265_fpc91.capture import sha, write
from hardware.cad.a12.enclosure_growth.nf265_fpc91.verify import ENGINE, errors, specs, variables
from hardware.cad.a12.thermal.enlarged_base.verify import mesh

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
STOP = REPO / "hardware/validation/board-qualification/NATIVE-CAD-STOP.json"


def fatal_result(returncode, output):
    if returncode not in [0, 1]:
        return "native-process-abort-or-unexpected-exit"
    if any(s in output for s in ["Incompatible processor", "Segmentation fault", "Abort trap", "dyld["]):
        return "native-runtime-failure"
    if returncode == 1 and "Current top level object is empty." not in output:
        return "native-execution-failure"
    return None


def run():
    if STOP.exists():
        raise RuntimeError("Native CAD launches are disabled; inspect NATIVE-CAD-STOP.json. No process launched.")
    work = ROOT / "workspace"
    replay = json.loads((work / "replay.json").read_text())
    assert all(sha(Path(n)) == h for n, h in replay["rebound_source_sha256"].items())
    target = work / "guarded-native"
    target.mkdir(exist_ok=False)
    results = {}
    for name, spec in specs().items():
        if STOP.exists():
            raise RuntimeError("Native CAD stop marker appeared; no next process launched")
        command = [str(ENGINE), "--hardwarnings", "--backend=Manifold", "--export-format=binstl",
                   "-o", str(target / (name + ".stl"))]
        for k, v in variables(name).items():
            command += ["-D", k + "=" + json.dumps(v)]
        command += [replay["entry"]]
        try:
            p = subprocess.run(command, capture_output=True, text=True, timeout=60)
            text = p.stdout + p.stderr
            failure = fatal_result(p.returncode, text)
        except subprocess.TimeoutExpired:
            write(STOP, dict(native_cad_launches_disabled=True, reason="Native CAD command timed out", automatic_retries_authorized=False))
            raise RuntimeError("Native CAD timed out; batch stopped, no retry") from None
        (target / (name + ".log")).write_text(text)
        if failure:
            write(STOP, dict(native_cad_launches_disabled=True, reason=failure,
                             returncode=p.returncode, case=name, automatic_retries_authorized=False))
            write(target / "aborted.json", dict(case=name, reason=failure, completed_cases=results,
                                                no_further_processes_launched=True, physical_qualified=False))
            raise RuntimeError("Native CAD failed; stopped on first failure, no retry")
        artifact = target / (name + ".stl")
        row = dict(returncode=p.returncode, command=command,
                   statistics=mesh(artifact) if artifact.exists() else None)
        row["errors"] = errors(name, row, spec, target)
        row["clear"] = not row["errors"]
        results[name] = row
        write(target / "verification.json", dict(cases=results, physical_qualified=False,
                                                  all_requested_clear=False, complete=False))
    write(target / "verification.json", dict(cases=results, physical_qualified=False, complete=True,
                                              all_requested_clear=all(r["clear"] for r in results.values())))


if __name__ == "__main__":
    run()
