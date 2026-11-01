"""Retained0.636A destinations from actual manifest and fresh native schematics.

No new ports or current redistribution are implemented. The manifest remains
logical, and its original E28-star source differs from a future E19 fanout.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.power_distribution.p02.distribution import LOADS

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
CLI = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    manifest = REPO / "hardware/wiring/generated/system-interconnect.json"
    ledger = REPO / "hardware/electronics/power_distribution/p02/distribution.py"
    source = {str(p.relative_to(REPO)): sha(p) for p in [manifest, ledger, Path(__file__)]}
    commands = []
    native = {}
    for board in ["sequenced_bypass", "rail_monitor"]:
        folder = REPO / "hardware/electronics" / board
        with tempfile.TemporaryDirectory(prefix="afx-ear-fanout-") as tmp:
            temp = Path(tmp)
            for p in folder.iterdir():
                if p.is_file() and (
                    p.suffix in [".kicad_sch", ".kicad_pro", ".kicad_sym"] or p.name == "sym-lib-table"
                ):
                    source[str(p.relative_to(REPO))] = sha(p)
                    shutil.copyfile(p, temp / p.name)
            target = ROOT / "generated" / ("fanout-" + board + ".xml")
            args = [
                str(CLI),
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                str(target),
                str(temp / (board + ".kicad_sch")),
            ]
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=120,
                env=dict(
                    os.environ,
                    KICAD_CONFIG_HOME=str(temp / "config"),
                    FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
                ),
            )
            commands.append(
                dict(args=args, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
            )
            assert proc.returncode == 0, commands[-1]
            parts, pins = netlist(target)
            expected = (
                {"1": "5V", "2": "AGND", "3": "3V3"}
                if board == "sequenced_bypass"
                else {"1": "5V_DIG", "2": "V3V3_IO", "3": "AGND"}
            )
            assert pins["J1"] == expected
            native[board] = dict(
                actual_fresh_netlist_sha256=sha(target),
                J1_pinmap=pins["J1"],
                J1_schematic_footprint=parts["J1"].findtext("footprint"),
                actual_native_PCB_exists=(folder / (board + ".kicad_pcb")).exists(),
                all_header_AGND_nodes=[
                    f"{ref}.{pin}"
                    for ref, ps in pins.items()
                    if ref.startswith("J")
                    for pin, net in ps.items()
                    if net == "AGND"
                ],
            )
    wires = [
        w for w in json.loads(manifest.read_text())["wires"] if w["harness"] in ["DIG-BYPASS", "DIG-MONITOR"]
    ]
    assert len(wires) == 4
    for w in wires:
        assert w["from"] == ["rail_disconnect", "J4", "1" if w["net"] == "5V_DIG" else "2"]
    bypass = sum(LOADS[x][2] for x in ["bypass", "gain_input", "gain_output"])
    monitor = LOADS["monitor_digital"][2]
    reserve = LOADS["digital_reserve"][2]
    assert abs(bypass + monitor + reserve - 0.636) < 1e-12
    report = dict(
        scope=__doc__,
        source_sha256=source,
        commands=commands,
        actual_manifest_wires=wires,
        actual_native_destination_contracts=native,
        retained_positive_wire_current_allocations_a={
            "DIG-BYPASS": bypass,
            "DIG-MONITOR": monitor,
            "digital_reserve_no_physical_endpoint": reserve,
        },
        destinations={
            "DIG-BYPASS": {
                "positive": ["sequenced_bypass", "J1", "1"],
                "ground": ["sequenced_bypass", "J1", "2"],
            },
            "DIG-MONITOR": {"positive": ["rail_monitor", "J1", "1"], "ground": ["rail_monitor", "J1", "3"]},
            "digital_reserve": None,
        },
        destination_5V_local_alias="sequenced_bypass J1.1 native5V is the manifest5V_DIG boundary; no new rail source is inferred",
        currents_are_retained_allocations_not_native_load_guarantees=True,
        return_constraints="Nominal digital branch components .140/.080A contribute to signed AGND KCL, but return-pin current is not independently bounded: shared AGND headers/3V3/control and bipolar domains require actual coupled model. No equal split or cancellation assumed.",
        manifest_current_source="E28J4 logical star",
        future_E19_source_ports_implemented=False,
        conflict_to_resolve="Routing full2.4A through E19J13 while retaining manifestE28-star branches would double-allocate the topology. Explicitly choose/implement source and real fanout; preserve load totals.",
        reserve_actual_load_or_connector_assigned=False,
        receiver_J1_unfitted_service_preserved=True,
        source_J13_multiwire_joint_qualified=False,
        full_PDN_solved=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    for rel, h in source.items():
        assert sha(REPO / rel) == h
    (ROOT / "generated/fanout-requirements.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Positive allocation", bypass, monitor, reserve, "no receiverfanout implemented")


if __name__ == "__main__":
    run()
