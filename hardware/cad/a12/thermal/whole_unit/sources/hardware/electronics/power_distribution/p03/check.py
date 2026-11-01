"""Fresh P03 native checks in an isolated project and independent pin assertions."""

import argparse
import datetime as dt
import gzip
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist, number
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, read_sexpr
from .assembly import constraints as assembly_constraints
from .construction import monitor_vip_inventory
from .internal_pg import EXPECTED_PINS
from .spec import REMOVED, REPO, ROOT

OUT = ROOT / "generated"


def native_inputs():
    """Native inputs exclude generated outputs and immutable comparisons.

    Hashing every output alongside its producer creates a circular freshness
    requirement: refreshing the analytical report would stale an unchanged
    native check. Artifact hashes are recorded separately instead.
    """
    files = {
        ROOT / name
        for name in (
            "power_p03.kicad_pcb",
            "power_p03.kicad_sch",
            "power_p03.kicad_pro",
            "power_p03.kicad_dru",
            "RMX_P03.kicad_sym",
            "fp-lib-table",
            "sym-lib-table",
            "components.json",
            "bom.csv",
            "check.py",
            "assembly.py",
            "spec.py",
            "internal_pg.py",
            "construction.py",
        )
    }
    files.update((ROOT / "RMX_P03.pretty").glob("*.kicad_mod"))
    files.update(
        ROOT.parents[1] / "common" / name
        for name in (
            "netlists.py",
            "sexpr.py",
            "reports.py",
            "placement.py",
        )
    )
    assert all(p.is_file() for p in files), "Native check source inventory is incomplete"
    return sorted(files)


def contract(parts, pins):
    for ref, prefix in (("U1", "RAW"), ("U13", "LO")):
        assert pins[ref] == {
            "1": prefix + "_P_FB",
            "2": "SW_REF_1V" if ref == "U1" else "LO_REF_1V",
            "3": "SW_REF_1V" if ref == "U1" else "LO_REF_1V",
            "4": prefix + "_N_FB",
            "5": "AGND",
            "6": prefix + "_N_SW",
            "7": prefix + "_N_SS",
            "8": "VIN_PROTECTED",
            "9": prefix + "_P_SS",
            "10": prefix + "_P_SW",
            "11": "AGND",
        }, (ref, "LT3471 manufacturer pin contract")
    assert math.isclose(number(parts["C72"].findtext("value")), 100e-9, rel_tol=1e-12)
    assert pins["C72"] == {"1": "LO_REF_1V", "2": "AGND"}, "Actual VREF bypass is C72"
    assert math.isclose(number(parts["C73"].findtext("value")), 68e-12, rel_tol=1e-12)
    assert pins["C73"] == {"1": "RAW_P17", "2": "LO_P_FB"}, (
        "C73 is68pF positive-loop compensation, not VREF bypass"
    )
    assert math.isclose(number(parts["C75"].findtext("value")), 68e-12, rel_tol=1e-12)
    for ref, prefix in (("U20", "D"), ("U23", "A")):
        assert parts[ref].findtext("value") == "TPS543620RPYR", ref
        expected = {
            "1": f"P03_{prefix}_FSEL",
            "2": f"P03_{prefix}_MODE",
            "3": "P03_SOURCES_READY",
            "4": f"P03_{prefix}_FB",
            "5": "AGND",
            "6": f"P03_{prefix}_BP5",
            "7": f"P03_{prefix}_ENABLE",
            "8": "VIN_PROTECTED",
            "9": "AGND",
            "10": f"P03_{prefix}_SW",
            "11": "AGND",
            "12": "VIN_PROTECTED",
            "13": f"P03_{prefix}_SW",
            "14": f"P03_{prefix}_BOOT",
        }
        assert pins[ref] == expected, (ref, "TI manufacturer pin contract", pins[ref])
    assert parts["U101"].findtext("value") == "TPS26630RGER"
    assert pins["U101"]["10"] == "INPUT_ILIM" and pins["R107"] == {"1": "INPUT_ILIM", "2": "AGND"}
    assert math.isclose(number(parts["R107"].findtext("value")), 4020, rel_tol=1e-12)
    for ref, exposed in (
        ("U1", "AGND"),
        ("U13", "AGND"),
        ("U7", "P19_SRC"),
        ("U10", "RAW_N22"),
        ("U11", "RAW_N17"),
        ("U22", "AGND"),
        ("U101", "AGND"),
    ):
        pin = "9" if ref == "U7" else "25" if ref == "U101" else "11"
        assert pins[ref][pin] == exposed, (ref, "hazardous tab/EP mismatch")
    assert parts["U22"].findtext("value") == "LT3045IDD#PBF"
    assert pins["U22"]["6"] == "P03_PRE6V", "Fast SET start is deliberately disabled"
    assert pins["U24"]["8"] == "VIN_PROTECTED", "Analog SET amplifier must power before raw22V"
    assert pins["R242"]["1"] == "P03_ANA_SET", "Do not silently change the analyzed SET feedback boundary"
    for ref in ("U1", "U13"):
        assert pins[ref]["8"] == "VIN_PROTECTED"
    assert "F101" not in parts and not any("VIN_SYS" in n.values() for n in pins.values()), (
        "Rear mandatory fuse replaces duplicate P03 fuse"
    )
    assert math.isclose(number(parts["R48"].findtext("value")), 10000)
    assert math.isclose(number(parts["R105"].findtext("value")), 68100)
    assert pins["J23"] == {"1": "5V_DIG_SRC"} and pins["J24"] == {"1": "V5_REG_SRC"}
    assert pins["J104"] == {"1": "SWITCH_SUPPLY", "2": "POWER_RUN", "3": "AGND"}
    assert pins["J106"] == {"1": "V2V5_AUX", "2": "AGND", "3": "POWER_RUN", "4": "P03_ALL_SOURCES_READY"}
    assert parts["U25"].findtext("value") == "LTC2910HGN#PBF"
    assert pins["U25"]["14"] == pins["U25"]["13"] == "AGND"
    assert pins["U25"]["12"] == "P03_ALL_SOURCES_READY"
    assert math.isclose(number(parts["R316"].findtext("value")), 2200), (
        "Schmitt READY load requires2.2k pullup"
    )
    for n in (200, 220):
        assert math.isclose(number(parts[f"R{n + 3}"].findtext("value")), 18200), (
            "Native4pF ramp selection was lost"
        )
        for k in (0, 2, 3):
            ref = f"C{n + k}"
            assert parts[ref].findtext("footprint") == "Capacitor_SMD:C_0805_2012Metric", (
                ref,
                "Actual selected input/BP5 case",
            )
            required_nominal = 4.7e-6 if k == 0 else 2.2e-6
            assert math.isclose(number(parts[ref].findtext("value")), required_nominal), (
                ref,
                "Old generic bypass restored",
            )
    assert pins["U26"]["5"] == "V2V5_AUX"
    assert parts["U26"].findtext("value") == "SN74LVC1G97DBVR", (
        "Internal open-drain PG requires reviewed Schmitt receiver"
    )
    assert pins["U26"] == EXPECTED_PINS, "Six-pin Schmitt AND configuration changed"
    for ref in ("C210", "C211", "C230", "C231"):
        assert math.isclose(number(parts[ref].findtext("value")), 100e-9), (
            ref,
            "Separate HF bypass was lost",
        )
        assert parts[ref].findtext("footprint") == "Capacitor_SMD:C_0402_1005Metric"
        assert pins[ref] == {"1": "VIN_PROTECTED", "2": "AGND"}
    assert pins["J101"] == {"1": "DC_IN", "2": "AGND"}
    assert pins["J2"] == {
        "1": "P19_SRC",
        "2": "AGND",
        "3": "N19_SRC",
        "4": "P12_SRC",
        "5": "N12_SRC",
        "6": "V5_REG_SRC",
    }
    assert pins["J3"] == {"1": "5V_DIG_SRC", "2": "AGND"}
    assert not (set(parts) & REMOVED), "An old source was accidentally retained in parallel"
    for ref in ("R200", "R206", "R201", "R220", "R221", "R240", "R241", "R242", "R243", "R244"):
        assert ref in parts
    assert sum("TPS543620" in p.findtext("value", "") for p in parts.values()) == 2
    return {
        "complete_source_pin_contract": True,
        "old_5v_sources_removed": True,
        "isolated_board_firmware_required": False,
    }


def native(cli, require_closed=False):
    OUT.mkdir(exist_ok=True)
    pcb = ROOT / "power_p03.kicad_pcb"
    prior = OUT / "verification.json"
    if prior.exists():
        history = OUT / "history"
        history.mkdir(exist_ok=True)
        archive = history / ("verification-" + sha(prior)[:16] + ".json.gz")
        if not archive.exists():
            archive.write_bytes(gzip.compress(prior.read_bytes(), mtime=0))
        prior.unlink()
    with tempfile.TemporaryDirectory(prefix="afx-p03-native-") as folder:
        temp = Path(folder)
        for path in ROOT.iterdir():
            if path.suffix in {
                ".kicad_pcb",
                ".kicad_sch",
                ".kicad_pro",
                ".kicad_dru",
                ".kicad_sym",
            } or path.name in {"fp-lib-table", "sym-lib-table"}:
                shutil.copy2(path, temp / path.name)
        shutil.copytree(ROOT / "RMX_P03.pretty", temp / "RMX_P03.pretty")
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
            KICAD10_SYMBOL_DIR=str(cli.resolve().parents[1] / "SharedSupport/symbols"),
        )
        log = []

        def run(*args):
            p = subprocess.run([str(cli), *map(str, args)], env=env, text=True, capture_output=True)
            log.append(
                dict(arguments=list(map(str, args)), exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
            )
            if p.returncode:
                raise RuntimeError(p.stdout + p.stderr)
            return p.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            temp / "power_p03.kicad_sch",
        )
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            temp / "power_p03.kicad_sch",
        )
        parts, pins = netlist(OUT / "netlist.xml")
        independent = contract(parts, pins)
        run(
            "pcb",
            "drc",
            "--severity-all",
            "--schematic-parity",
            "--refill-zones",
            "--save-board",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            temp / "power_p03.kicad_pcb",
        )
        shutil.copy2(temp / "power_p03.kicad_pcb", OUT / "filled.kicad_pcb")
        for side, layers in (
            ("top", "F.Cu,F.Mask,F.SilkS,Edge.Cuts"),
            ("bottom", "B.Cu,B.Mask,B.SilkS,Edge.Cuts"),
        ):
            run(
                "pcb",
                "export",
                "svg",
                "--mode-single",
                "--layers",
                layers,
                "--page-size-mode",
                "2",
                "--output",
                OUT / (side + ".svg"),
                temp / "power_p03.kicad_pcb",
            )
        (OUT / "native-commands.json").write_text(json.dumps(log, indent=2) + "\n")
    erc = json.loads((OUT / "erc.json").read_text())
    issues = [v for s in erc["sheets"] for v in s["violations"]]
    drc = json.loads((OUT / "drc.json").read_text())
    tree = read_sexpr(pcb.read_text())
    assembly_policy = assembly_constraints(tree)
    vip = monitor_vip_inventory(tree)
    assert vip["implements_required_geometry"], (
        "Actual P19 monitor via does not implement the declared construction"
    )
    sources = native_inputs()
    report = dict(
        revision="P03",
        generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        kicad_cli_version=version,
        circuit_components=len(parts),
        routed_segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        native_erc_issues=len(issues),
        native_drc_violations=len(drc["violations"]),
        schematic_parity_issues=len(drc.get("schematic_parity", [])),
        native_open_connections=len(drc["unconnected_items"]),
        independent_contract=independent,
        native_assembly_side_policy=assembly_policy,
        native_monitor_via_in_pad=vip,
        native_connectivity_closed=not issues
        and not drc["violations"]
        and not drc["unconnected_items"]
        and not drc.get("schematic_parity", []),
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(sources)},
        native_artifact_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in (
                OUT / "erc.json",
                OUT / "drc.json",
                OUT / "netlist.xml",
                OUT / "filled.kicad_pcb",
                OUT / "native-commands.json",
                OUT / "top.svg",
                OUT / "bottom.svg",
            )
        },
        stackup_fabricator_accepted=False,
        physical_tests_performed=0,
        thermal_qualified=False,
        ampacity_qualified=False,
        startup_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "current-native.json").write_text(
        json.dumps(
            dict(
                generated_at_utc=report["generated_at_utc"],
                scope="Full native schematic ERC, PCB all-severity DRC/refill and schematic parity",
                pcb_sha256=sha(pcb),
                schematic_sha256=sha(ROOT / "power_p03.kicad_sch"),
                diagnostic="drc.json",
                diagnostic_sha256=sha(OUT / "drc.json"),
                native_drc_violations=report["native_drc_violations"],
                native_open_connections=report["native_open_connections"],
                native_erc_issues=report["native_erc_issues"],
                erc_fresh_for_this_diagnostic=True,
                schematic_parity_checked=True,
                schematic_parity_issues=report["schematic_parity_issues"],
                full_verification_receipt="verification.json",
                full_verification_sha256=sha(OUT / "verification.json"),
                physical_tests_performed=0,
                fabrication_released=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"P03 native: ERC{len(issues)},DRC{len(drc['violations'])},parity{len(drc.get('schematic_parity', []))},opens{len(drc['unconnected_items'])}"
    )
    if require_closed:
        assert report["native_connectivity_closed"], "Native candidate remains open"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    parser.add_argument("--require-closed", action="store_true")
    args = parser.parse_args()
    native(args.kicad_cli, args.require_closed)


if __name__ == "__main__":
    main()
