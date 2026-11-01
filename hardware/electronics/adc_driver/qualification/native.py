"""Fresh E12 native checks and a zones-only plane-opening trial; never order hardware."""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from ...common.placement import footprint_root
from ...common.sexpr import children, first, read_sexpr, sexpr
from ..pcb import check as original_checker
from ..pcb.paths import ground_contract, header_sense_contract, local_feedback
from .audit import OUT, PARENT, REPO, ROOT, SENSITIVE_PINS, footprints, pad, plane_coverage, sha


def relief_areas(tree, margin=0.5):
    """A trial margin, not a manufacturer-specified extraction/clearance value."""
    assert margin > 0
    result = []
    for ref, pin in SENSITIVE_PINS:
        fp = footprints(tree)[ref]
        terminal, (x, y) = pad(tree, ref, pin)
        assert float(first(fp, "at")[3]) % 180 == 0, "Trial assumes current FDA rotation"
        w, h = map(float, first(terminal, "size")[1:3])
        x0, x1, y0, y1 = x - w / 2 - margin, x + w / 2 + margin, y - h / 2 - margin, y + h / 2 + margin
        identity = uuid.uuid5(uuid.NAMESPACE_URL, f"afx:E12-Q01:relief:{ref}:{pin}")
        result.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layers "In1.Cu" "In4.Cu")
            (uuid {identity}) (hatch edge .5) (connect_pads (clearance .25)) (min_thickness .25)
            (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
            (polygon (pts (xy {x0:.6f} {y0:.6f}) (xy {x1:.6f} {y0:.6f})
            (xy {x1:.6f} {y1:.6f}) (xy {x0:.6f} {y1:.6f}))))""")
        )
    return result


def run_native(cli):
    original_out = OUT / "native-original"
    original_out.mkdir(parents=True, exist_ok=True)
    for name in ("inputs.json", "placed.kicad_pcb"):
        shutil.copy2(PARENT / "pcb/generated" / name, original_out / name)
    # Redirect every exported/check output; frozen candidate sources stay untouched.
    original_checker.OUT = original_out
    original_checker.check(cli)
    base_path = PARENT / "pcb/adc_driver.kicad_pcb"
    base = read_sexpr(base_path.read_text())
    trial = ROOT / "plane-opening-trial"
    trial.mkdir(exist_ok=True)
    areas = relief_areas(base)
    candidate = base + areas
    assert candidate[: -len(areas)] == base, "Trial changed existing layout or circuit"
    pcb = trial / "adc_driver.kicad_pcb"
    pcb.write_text(sexpr(candidate) + "\n")
    for name in ("adc_driver.kicad_pro", "adc_driver.kicad_dru", "fp-lib-table"):
        shutil.copy2(PARENT / "pcb" / name, trial / name)
    shutil.copytree(PARENT / "pcb/RMX_Power.pretty", trial / "RMX_Power.pretty", dirs_exist_ok=True)
    target = OUT / "native-plane-trial"
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="afx-e12-plane-trial-") as directory:
        temp = Path(directory)
        for name in ("adc_driver.kicad_sch", "RMX_E12.kicad_sym", "sym-lib-table"):
            shutil.copy2(PARENT / name, temp / name)
        for name in ("adc_driver.kicad_pcb", "adc_driver.kicad_pro", "adc_driver.kicad_dru", "fp-lib-table"):
            shutil.copy2(trial / name, temp / name)
        shutil.copytree(trial / "RMX_Power.pretty", temp / "RMX_Power.pretty")
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )
        command = [
            str(cli),
            "pcb",
            "drc",
            "--refill-zones",
            "--save-board",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "-o",
            str(target / "drc.json"),
            str(temp / "adc_driver.kicad_pcb"),
        ]
        run = subprocess.run(command, capture_output=True, text=True, env=env)
        (target / "native-check.txt").write_text(run.stdout + run.stderr)
        assert run.returncode == 0, run.stdout + run.stderr
        shutil.copy2(temp / "adc_driver.kicad_pcb", target / "filled.kicad_pcb")
    native = json.loads((target / "drc.json").read_text())
    filled = read_sexpr((target / "filled.kicad_pcb").read_text())
    coverage = plane_coverage(filled)
    assert not any(any(p.values()) for p in coverage.values()), "Filled metal still under trial pad centres"
    checks = {}
    for name, checker in [
        ("feedback", local_feedback),
        ("header_sense", header_sense_contract),
        ("ground", ground_contract),
    ]:
        try:
            checks[name] = dict(passed=True, result=checker(filled))
        except AssertionError as error:
            checks[name] = dict(passed=False, error=str(error))
    sources = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and "generated" not in p.relative_to(ROOT).parts
    ]
    sources += [p for folder in (original_out, target) for p in folder.rglob("*") if p.is_file()]
    sources += [
        base_path,
        PARENT / "adc_driver.kicad_sch",
        PARENT / "components.json",
        REPO / "tests/tooling/test_adc_qualification.py",
    ]
    report = dict(
        revision="E12-Q01-plane-opening-trial",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        original_board_unchanged_sha256=sha(base_path),
        source_delta="Eight additional In1/In4 copper-pour-only rule areas; existing parts, pads, traces, vias, outline and original zones unchanged",
        relief_margin_mm=0.5,
        relief_margin_is_trial_allocation=True,
        added_rule_areas=8,
        routed_segments=len(children(filled, "segment")),
        through_vias=len(children(filled, "via")),
        native_drc_violations=len(native["violations"]),
        native_open_connections=len(native["unconnected_items"]),
        schematic_parity_issues=len(native["schematic_parity"]),
        native_check_passes=not native["violations"]
        and not native["unconnected_items"]
        and not native["schematic_parity"],
        sensitive_pin_plane_coverage=coverage,
        independent_checks=checks,
        full_sensitive_node_parasitics_extracted=False,
        final_stackup_selected=False,
        manufacturer_macromodel_executed=False,
        physical_tests_performed=0,
        stability_qualified=False,
        fabrication_released=False,
        build_ready=False,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources if p.exists()},
    )
    (OUT / "trial-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Plane-opening trial:",
        report["native_drc_violations"],
        "DRC,",
        report["native_open_connections"],
        "opens; physical qualification false",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    args = parser.parse_args()
    run_native(args.kicad_cli.resolve())


if __name__ == "__main__":
    main()
