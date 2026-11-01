"""Fresh source-bound full native checkpoint; never assert physical acceptance."""

import json
import os
import subprocess
import sys

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import read_sexpr

from .analyze import ROOT, analyze, sha
from .validate import validate


def main():
    assert not (ROOT / "handoff.json").exists(), "Sealed successor: create a new packet"
    repo = ROOT.parents[4]
    out = ROOT / "generated"
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    py39 = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9"
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-fpc-m2-final",
        FONTCONFIG_FILE=str(repo / "build-hardware/kicad-fonts.conf"),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=".",
    )
    runs = []

    def run(cmd, label):
        p = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, env=env, timeout=180)
        (out / (label + ".log")).write_text(p.stdout + p.stderr)
        runs.append(dict(label=label, command=cmd, returncode=p.returncode))
        assert p.returncode == 0, (label, p.stdout, p.stderr)

    before = sha(ROOT / "fan_power_health.kicad_pcb")
    run([cli, "--version"], "version")
    run(
        [
            cli,
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(out / "netlist.xml"),
            str(ROOT / "fan_power_health.kicad_sch"),
        ],
        "final-netlist",
    )
    run(
        [
            cli,
            "sch",
            "erc",
            "--format",
            "json",
            "--output",
            str(out / "erc.json"),
            str(ROOT / "fan_power_health.kicad_sch"),
        ],
        "final-erc",
    )
    # Saved actual fill was generated with --refill-zones --save-board. This
    # final pass checks those real saved polygons WITHOUT an in-memory refill.
    run(
        [
            cli,
            "pcb",
            "drc",
            "--format",
            "json",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--exit-code-violations",
            "--output",
            str(out / "final-drc.json"),
            str(ROOT / "fan_power_health.kicad_pcb"),
        ],
        "final-drc",
    )
    assert sha(ROOT / "fan_power_health.kicad_pcb") == before
    run([py39, str(ROOT / "native_measure.py")], "native-reference")
    r = analyze()
    (out / "analysis.json").write_text(json.dumps(r, indent=2) + "\n")
    invariant = validate(read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text()))
    drc = json.loads((out / "final-drc.json").read_text())
    assert all(not drc[k] for k in ["violations", "unconnected_items", "schematic_parity", "ignored_checks"])
    erc = json.loads((out / "erc.json").read_text())
    assert not [v for s in erc["sheets"] for v in s["violations"]]
    parts = json.loads((ROOT / "components.json").read_text())
    actual, pins = netlist(out / "netlist.xml")
    assert len(actual) == len(parts) == 91
    for c in parts:
        assert actual[c["ref"]].findtext("value") == c["part"]
        assert actual[c["ref"]].findtext("footprint") == c["footprint"]
        for p in c["pins"]:
            got = pins[c["ref"]][p["number"]]
            assert got == p["net"] if p["net"] is not None else got.startswith("unconnected-"), (
                c["ref"],
                p["number"],
            )
    run(
        [
            sys.executable,
            "-m",
            "unittest",
            "hardware.qualification.boards.fan_health.composite_nf_branch.test_branch",
            "-v",
        ],
        "tests",
    )
    run(
        [
            "/Users/axelmckrnna/.cache/uv/archive-v0/4FxQ2rYyAjvgsfLW/bin/ruff",
            "check",
            *[str(p) for p in sorted(ROOT.glob("*.py"))],
        ],
        "ruff",
    )
    primary_sources = json.loads((ROOT / "sources/manifest.json").read_text())
    for f, h in primary_sources.items():
        assert sha(ROOT / "sources" / f) == h, f
    parent_counts = {}
    for name in ["composite", "composite_mount"]:
        parent = ROOT.parent / name
        handoff = json.loads((parent / "handoff.json").read_text())
        for f, h in handoff["files_sha256"].items():
            assert sha(parent / f) == h, (name, f)
        parent_counts[name] = len(handoff["files_sha256"])
    (out / "commands.json").write_text(json.dumps(runs, indent=2) + "\n")
    report = dict(
        revision="FPC_M2-protected-NF-RAW5-native-closed",
        parts=91,
        PCB_sha256=before,
        SCH_sha256=sha(ROOT / "fan_power_health.kicad_sch"),
        ERC_errors=0,
        ERC_warnings=0,
        DRC_errors=0,
        DRC_warnings=0,
        opens=0,
        parity=0,
        ignored_checks=[],
        actual_native_pin_value_footprint_differences=0,
        portable_tests=12,
        physical_primary_TPS2553_pin_maps_checked=3,
        geometry_and_copper_invariants=invariant,
        actual_reference_check=json.loads((ROOT / "native-reference-check.json").read_text()),
        inherited1p76_PH_board_thickness_status=r["connector"]["inherited1p76_PCB_scenario_status"],
        original_sealed_files_rechecked=parent_counts,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [*sorted(ROOT.glob("*.py")), ROOT / "components.json", ROOT / "sources/manifest.json"]
        },
        artifact_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "fan_power_health.kicad_pcb",
                ROOT / "fan_power_health.kicad_sch",
                out / "netlist.xml",
                out / "erc.json",
                out / "filled-drc.json",
                out / "final-drc.json",
                out / "analysis.json",
                out / "commands.json",
                out / "tests.log",
                out / "ruff.log",
            ]
        },
        full_unit_geometry_adopted=False,
        PDN_qualified=False,
        noise_qualified=False,
        startup_qualified=False,
        partial_power_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    report["files_sha256"] = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.name not in ["handoff.json", ".DS_Store"]
        and not p.name.endswith((".kicad_prl", ".lck"))
    }
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Sealed", len(report["files_sha256"]), "files:", sha(ROOT / "handoff.json"))


if __name__ == "__main__":
    main()
