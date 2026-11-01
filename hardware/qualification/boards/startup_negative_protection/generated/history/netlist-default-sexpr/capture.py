"""Read-only native circuit capture for NF02; no parent sources are rewritten."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
P03 = REPO / "hardware/electronics/power_distribution/p03"
COMBINED = P03 / "candidates/aux-u10-combined"
E28 = REPO / "hardware/electronics/rail_disconnect/revision28"
NF01 = ROOT.parent / "startup_negative_feasibility"
SC02 = ROOT.parent / "startup_circuit_negative"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")


def capture(kicad):
    assert not (ROOT / "sources/capture.json").exists(), "Immutable capture; use a separate successor"
    nf = json.loads((NF01 / "seal.json").read_text())
    assert all(sha(REPO / n) == h for n, h in nf["sha256"].items())
    sc = json.loads((SC02 / "generated/verification.json").read_text())
    sc_changed = [
        n
        for field in ["source_sha256", "evidence_sha256"]
        for n, h in sc[field].items()
        if sha(REPO / n) != h
    ]
    originals = [
        COMBINED / "power_p03.kicad_sch",
        COMBINED / "components.json",
        COMBINED / "generated/current-native.json",
        COMBINED / "power_p03.kicad_pcb",
        E28 / "rail_disconnect.kicad_sch",
        E28 / "components.json",
        P03 / "generated/bipolar-ledger.json",
        P03 / "generated/analysis.json",
        P03 / "bipolar.py",
        P03 / "models.py",
        P03 / "spec.py",
        REPO / "hardware/electronics/common/netlists.py",
        NF01 / "comparison.json",
        NF01 / "seal.json",
        SC02 / "generated/verification.json",
    ]
    before = {str(p.relative_to(REPO)): sha(p) for p in originals}
    copied = {}
    for p in originals:
        dst = ROOT / "sources/snapshot" / p.relative_to(REPO)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dst)
        copied[str(dst.relative_to(ROOT))] = sha(dst)
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    native = {}
    for name, sch in [("p03", COMBINED / "power_p03.kicad_sch"), ("e28", E28 / "rail_disconnect.kicad_sch")]:
        output = ROOT / "sources" / (name + "-fresh-netlist.xml")
        cmd = [str(kicad), "sch", "export", "netlist", "--output", str(output), str(sch)]
        p = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=120)
        (ROOT / "sources" / (name + "-export.log")).write_text(p.stdout + p.stderr)
        assert p.returncode == 0 and output.exists(), name
        native[name] = dict(
            command=cmd,
            returncode=p.returncode,
            netlist_sha256=sha(output),
            schematic_sha256=sha(sch),
            log_sha256=sha(ROOT / "sources" / (name + "-export.log")),
        )
    assert all(sha(REPO / n) == h for n, h in before.items()), "Source changed during capture"
    write(
        ROOT / "sources/capture.json",
        dict(
            original_source_sha256=before,
            copied_source_sha256=copied,
            nf01_all_sealed_sources_current=True,
            sc02_changed_historical_dependencies=sc_changed,
            native_exports=native,
            parent_sources_modified=False,
        ),
    )
    print(
        "Captured", len(originals), "sources; fresh P03/E28 exports; SC02 stale dependencies", len(sc_changed)
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--kicad-cli", type=Path, required=True)
    capture(p.parse_args().kicad_cli)
