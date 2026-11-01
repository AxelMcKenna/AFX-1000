"""Fresh source-bound R2 native proof; reports actual failures without release claims."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root
from ...common.sexpr import read_sexpr
from ..qualification.audit import REPO, path_witness, plane_coverage, sha
from .design import COMPONENTS, ROOT, thresholds
from .verify import check_circuit, leakage_screen, pd_levels

OUT = ROOT / "generated/native"


def source_paths():
    result = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "generated" not in p.relative_to(ROOT).parts and "__pycache__" not in p.parts
    ]
    result += [
        REPO / "tests/tooling/test_adc_revision2.py",
        ROOT.parent / "spec.py",
        ROOT.parent / "generate.py",
        ROOT.parent / "verify.py",
        ROOT.parent / "pcb/generate.py",
        ROOT.parent / "pcb/router.py",
        ROOT.parent / "pcb/paths.py",
        ROOT.parent / "qualification/audit.py",
    ]
    return sorted(set(result))


def run(cli):
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="afx-e12-r2-native-") as directory:
        temp = Path(directory)
        for name in [
            "adc_driver.kicad_sch",
            "adc_driver.kicad_pcb",
            "adc_driver.kicad_pro",
            "adc_driver.kicad_dru",
            "RMX_E12.kicad_sym",
            "sym-lib-table",
            "fp-lib-table",
        ]:
            shutil.copy2(ROOT / name, temp / name)
        shutil.copytree(ROOT / "RMX_Power.pretty", temp / "RMX_Power.pretty")
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )

        def command(name, arguments):
            result = subprocess.run([str(cli), *arguments], env=env, capture_output=True, text=True)
            (OUT / (name + "-log.txt")).write_text(result.stdout + result.stderr)
            assert result.returncode == 0, (name, result.returncode, result.stderr)

        command(
            "netlist",
            [
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "--output",
                str(OUT / "netlist.xml"),
                str(temp / "adc_driver.kicad_sch"),
            ],
        )
        command(
            "erc",
            [
                "sch",
                "erc",
                "--format",
                "json",
                "--severity-all",
                "--output",
                str(OUT / "erc.json"),
                str(temp / "adc_driver.kicad_sch"),
            ],
        )
        command(
            "drc",
            [
                "pcb",
                "drc",
                "--refill-zones",
                "--save-board",
                "--all-track-errors",
                "--schematic-parity",
                "--severity-all",
                "--format",
                "json",
                "--output",
                str(OUT / "drc.json"),
                str(temp / "adc_driver.kicad_pcb"),
            ],
        )
        shutil.copy2(temp / "adc_driver.kicad_pcb", OUT / "filled.kicad_pcb")
        for name, layers in [
            ("top", "F.Cu,F.Silkscreen,Edge.Cuts"),
            ("bottom", "B.Cu,B.Silkscreen,Edge.Cuts"),
            ("ground-plane", "In1.Cu,Edge.Cuts"),
        ]:
            folder = OUT / (name + ".svg")
            command(
                name,
                [
                    "pcb",
                    "export",
                    "svg",
                    "--layers",
                    layers,
                    "--page-size-mode",
                    "2",
                    "--mode-single",
                    "--output",
                    str(folder),
                    str(temp / "adc_driver.kicad_pcb"),
                ],
            )
    parts, pins = netlist(OUT / "netlist.xml")
    check_circuit(parts, pins)
    erc = json.loads((OUT / "erc.json").read_text())
    drc = json.loads((OUT / "drc.json").read_text())
    counts = dict(
        erc=sum(len(s["violations"]) for s in erc["sheets"]),
        drc=len(drc["violations"]),
        opens=len(drc["unconnected_items"]),
        parity=len(drc["schematic_parity"]),
    )
    filled = read_sexpr((OUT / "filled.kicad_pcb").read_text())
    coverage = plane_coverage(filled)
    witnesses = {}
    for ci, ch in enumerate(("L", "R")):
        u = "U" + str(ci + 1)
        pump = "U" + str(ci + 5)
        for net, a, b in [
            ("V5_REG", (u, "3"), ("C" + str(13 + ci * 14), "1")),
            ("NBIAS_" + ch, (u, "6"), ("C" + str(14 + ci * 14), "1")),
            ("FLY_P_" + ch, (pump, "1"), ("C" + str(8 + ci * 14), "1")),
            ("FLY_N_" + ch, (pump, "8"), ("C" + str(8 + ci * 14), "2")),
        ]:
            try:
                witnesses[".".join(a) + "-" + ".".join(b)] = path_witness(filled, net, a, b)
            except AssertionError as error:
                witnesses[".".join(a) + "-" + ".".join(b)] = {"failed": str(error)}
    linear = json.loads((ROOT / "generated/headroom.json").read_text())
    for name, digest in linear["source_sha256"].items():
        assert sha(REPO / name) == digest, ("Stale R2 linear screen", name)
    shutil.copy2(ROOT / "generated/headroom.json", OUT / "headroom.json")
    windows = thresholds()
    pd = pd_levels()
    report = dict(
        revision="E12-R2",
        component_count=len(COMPONENTS),
        actual_r2_linear_headroom_screen=linear,
        mount_count=4,
        counts=counts,
        native_connectivity_passed=not any(counts.values()),
        independent_terminal_value_contract_passed=True,
        sensitive_pad_plane_coverage=coverage,
        all_sensitive_pad_centres_free_of_plane_fill=not any(any(p.values()) for p in coverage.values()),
        actual_route_witnesses=witnesses,
        bias_monitor_threshold_corners=windows,
        pd_level_corners=pd,
        leakage_screen=leakage_screen(),
        original_conditional_minimum_internal_output_v=0.1338795540624857,
        original_conditional_headroom_at_upper_trip_v=0.1338795540624857 - windows["upper_trip_v"][1],
        original_point_three_volt_headroom_screen_passes=0.1338795540624857 - windows["upper_trip_v"][1]
        >= 0.3,
        window_covers_conditional_filtered_pump_range=windows["lower_trip_v"][1] < -0.256
        and windows["upper_trip_v"][0] > -0.20198,
        conditional_filtered_pump_range_v=[-0.256, -0.20198],
        physical_tests_performed=0,
        fabrication_released=False,
        build_ready=False,
        full_board_stability_verified=False,
        final_converter_pin_feedback_verified=False,
        approved_cable_length_mm=None,
        physical_stackup_fabricator_approved=False,
        blockers=[
            "Official ESS pin/package and switched/DC input model missing; final codec co-location incomplete",
            "Power-off/partial-power current and analog isolation limits not established; PD is not analog isolation",
            "Selected MLCC effective capacitance/ripple/ESR under DC bias,temperature and age requires measurement",
            "Stackup material,trace parasitics,mask/paste and assembly process require fabricator confirmation",
            "Comparator leakage/lifetime resistor allocations and all startup/fault timing require physical qualification",
            "Complete-chain noise/THD/SNR,loop stability,thermal and EMC remain unmeasured",
        ],
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in source_paths()},
        evidence_sha256={
            str(p.relative_to(OUT)): sha(p)
            for p in OUT.rglob("*")
            if p.is_file() and p.name != "verification.json"
        },
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("E12-R2 native counts", counts, "physical release false")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", type=Path, required=True)
    args = p.parse_args()
    run(args.kicad_cli)


if __name__ == "__main__":
    main()
