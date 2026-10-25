"""Independently check E26 pin geometry and full native copper connectivity."""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr
from ..placement.check import mechanical
from ..verify import contract

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
OUT = ROOT / "generated"


def preserved_geometry(tree, base):
    def footprints(t):
        return {
            next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
            for f in children(t, "footprint")
        }

    actual, original = footprints(tree), footprints(base)
    assert set(actual) == set(original)
    for ref in ("C4", "C8", "C12", "C16", "C20", "C24"):
        assert actual[ref] == original[ref], (ref, "bulk capacitor must remain frozen")
    for key in ("layers", "general"):
        assert first(tree, key) == first(base, key), (key, "board envelope/stack count changed")
    assert children(tree, "gr_line") == children(base, "gr_line"), "board outline changed"
    for ref in ("H1", "H2", "H3", "H4"):
        assert actual[ref] == original[ref], (ref, "mount changed")


def check(cli, require_closed=False):
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    base = read_sexpr((PARENT / "placement/rail_disconnect.kicad_pcb").read_text())

    preserved_geometry(tree, base)
    with tempfile.TemporaryDirectory(prefix="rmx-e26-check-") as folder:
        temp = Path(folder)
        for n in ("rail_disconnect.kicad_sch", "sym-lib-table", "RMX_E17.kicad_sym"):
            shutil.copy2(PARENT / n, temp / n)
        for n in ("rail_disconnect.kicad_pcb", "rail_disconnect.kicad_pro", "fp-lib-table"):
            shutil.copy2(ROOT / n, temp / n)
        shutil.copytree(ROOT / "RMX_Disconnect.pretty", temp / "RMX_Disconnect.pretty")
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
            FONTCONFIG_FILE=str(ROOT.parents[3] / "build-hardware/kicad-fonts.conf"),
        )

        def run(*args):
            p = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, text=True)
            assert p.returncode == 0, (args, p.stdout, p.stderr)
            return p.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            temp / "rail_disconnect.kicad_sch",
        )
        parts, pins = netlist(OUT / "netlist.xml")
        contract(parts, pins)
        stripped = [
            n for n in tree if not isinstance(n, list) or not n or n[0] not in ("segment", "via", "zone")
        ]
        packet = mechanical(stripped, parts, pins)
        packet["revision"] = "E26"
        packet["physical_fit_verified"] = False
        packet["pcb_sha256"] = sha(pcb)
        (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
        run(
            "pcb",
            "drc",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--refill-zones",
            "--save-board",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            temp / "rail_disconnect.kicad_pcb",
        )
        native = json.loads((OUT / "drc.json").read_text())
        shutil.copy2(temp / "rail_disconnect.kicad_pcb", OUT / "filled.kicad_pcb")
        review = dict(
            revision="E26-pilot",
            native_drc_violations=len(native["violations"]),
            schematic_parity_issues=len(native["schematic_parity"]),
            native_open_connections=len(native["unconnected_items"]),
            native_findings=[
                dict(type=v["type"], severity=v["severity"], description=v["description"])
                for v in native["violations"]
            ],
            strict_native_check_passed=not native["violations"] and not native["schematic_parity"],
            connectivity_closed=not native["unconnected_items"],
            pcb_sha256=sha(pcb),
            native_drc_sha256=sha(OUT / "drc.json"),
            physical_fit_verified=False,
            copper_loss_or_current_balance_qualified=False,
            build_ready=False,
        )
        (OUT / "pilot-findings.json").write_text(json.dumps(review, indent=2) + "\n")
        shutil.copy2(temp / "rail_disconnect.kicad_pcb", OUT / "filled.kicad_pcb")
        for name, layers in (("top", "F.Cu,F.Fab,Edge.Cuts"), ("bottom", "B.Cu,B.Fab,Edge.Cuts")):
            run(
                "pcb",
                "export",
                "svg",
                "--mode-single",
                "--page-size-mode",
                "2",
                "--exclude-drawing-sheet",
                "--layers",
                layers,
                "-o",
                OUT / (name + ".svg"),
                temp / "rail_disconnect.kicad_pcb",
            )
    repo = ROOT.parents[3]
    pilot_sources = [
        *ROOT.glob("*.py"),
        *ROOT.glob("*.json"),
        ROOT / "README.md",
        pcb,
        ROOT / "rail_disconnect.kicad_pro",
        ROOT / "fp-lib-table",
        *list((ROOT / "RMX_Disconnect.pretty").glob("*.kicad_mod")),
        *[
            OUT / name
            for name in (
                "placement-inputs.json",
                "routing-inputs.json",
                "placement.json",
                "drc.json",
                "filled.kicad_pcb",
                "netlist.xml",
                "top.svg",
                "bottom.svg",
            )
        ],
        *[
            PARENT / name
            for name in (
                "rail_disconnect.kicad_sch",
                "components.json",
                "verify.py",
                "RMX_E17.kicad_sym",
                "sym-lib-table",
                "placement/rail_disconnect.kicad_pcb",
                "placement/generate.py",
                "placement/check.py",
                "placement/generated/inputs.json",
                "placement/generated/verification.json",
                "placement/generated/netlist.xml",
                "routing/check.py",
            )
        ],
        *[
            PARENT.parent / name
            for name in (
                "common/sexpr.py",
                "common/netlists.py",
                "common/reports.py",
                "common/placement.py",
                "output_stage/check_placement.py",
            )
        ],
        repo / "tests/tooling/test_disconnect_revision26.py",
    ]
    review.update(
        routed_segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_sha256={str(p.relative_to(repo)): sha(p) for p in sorted(set(pilot_sources)) if p.exists()},
        physical_fault_or_startup_verified=False,
        actual_copper_extraction_completed=False,
        dc_loss_current_balance_or_thermal_qualified=False,
    )
    (OUT / "pilot-findings.json").write_text(json.dumps(review, indent=2) + "\n")
    assert not native["violations"] and not native["schematic_parity"], (
        len(native["violations"]),
        len(native["schematic_parity"]),
    )
    if require_closed:
        assert not native["unconnected_items"], len(native["unconnected_items"])
    files = [
        *ROOT.glob("*.py"),
        *ROOT.glob("*.json"),
        ROOT / "README.md",
        pcb,
        ROOT / "rail_disconnect.kicad_pro",
        ROOT / "fp-lib-table",
        *list((ROOT / "RMX_Disconnect.pretty").glob("*.kicad_mod")),
        OUT / "placement-inputs.json",
        OUT / "placement.json",
        OUT / "drc.json",
        OUT / "filled.kicad_pcb",
        OUT / "netlist.xml",
        PARENT / "placement/rail_disconnect.kicad_pcb",
        PARENT / "components.json",
        PARENT / "rail_disconnect.kicad_sch",
        PARENT / "verify.py",
        PARENT / "placement/check.py",
    ]
    report = dict(
        revision="E26",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kicad_version=version,
        circuit_components=164,
        baseline_outline_mounts_and_bulk_preserved=True,
        independent_pin_value_contract_passed=True,
        routed_segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        native_drc_violations=0,
        schematic_parity_issues=0,
        native_open_connections=len(native["unconnected_items"]),
        pcb_routed=not native["unconnected_items"],
        physical_fit_verified=False,
        dc_loss_current_balance_or_thermal_qualified=False,
        physical_fault_or_startup_verified=False,
        build_ready=False,
        source_sha256={os.path.relpath(p, ROOT): sha(p) for p in files if p.exists()},
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "E26native:",
        report["routed_segments"],
        "segments/",
        report["through_vias"],
        "vias;0DRC/parity;",
        report["native_open_connections"],
        "opens",
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", required=True)
    p.add_argument("--require-closed", action="store_true")
    a = p.parse_args()
    check(Path(a.kicad_cli).resolve(), a.require_closed)


if __name__ == "__main__":
    main()
