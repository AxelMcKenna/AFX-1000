"""Separate E19 direct-wire input proposal; canonical processor board is untouched.

Keeps the actual J1 positive pad and all other parts/copper, enlarges both
bores/lands, and moves only the return pad to 4 mm pitch. Native closure does
not qualify current distribution, wire soldering, retention or fabrication.
"""

import argparse
import copy
import csv
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from ..generate import REPO, sha

SOURCE = REPO / "hardware/electronics/processor_carrier"
ROOT = Path(__file__).resolve().parent
NAME = "AWG18_Solder_2x1_P4mm_D2p2"
FOOTPRINT = "RMX_Carrier:" + NAME
VALUE = "Alpha6715_AWG18_DIRECT_SOLDER_PROPOSAL"
CLI = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def reference(fp):
    return next(p[2] for p in children(fp, "property") if p[1] == "Reference")


def alter(fp):
    assert str(fp[1]) == "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
    assert list(map(float, first(fp, "at")[1:])) == [114, 105]
    fp[1] = FOOTPRINT
    for prop in children(fp, "property"):
        if prop[1] in ("Value", "MPN"):
            prop[2] = VALUE
    fp[:] = [
        n
        for n in fp
        if not (
            isinstance(n, list)
            and n
            and (str(n[0]).startswith("fp_") or (n[0] == "property" and n[1] == "KiLib_Generator"))
        )
    ]
    first(fp, "descr")[1] = (
        "Unqualified AWG18 direct-wire solder input; 2.2 mm bores, 3.4 mm lands, 4 mm pitch"
    )
    first(fp, "tags")[1] = "direct wire solder prototype"
    fp.append(
        read_sexpr(
            '(fp_rect (start -1.95 -1.95) (end 1.95 5.95) (stroke (width .05) (type solid)) (fill no) (layer "F.CrtYd"))'
        )
    )
    for pad in children(fp, "pad"):
        pin = str(pad[1])
        assert pin in ("1", "2") and pad[2] == "thru_hole"
        assert float(first(pad, "drill")[1]) == 1
        assert str(first(pad, "net")[-1]).lstrip("/") == ("5V_DIG" if pin == "1" else "AGND")
        pad[3] = a("circle")
        first(pad, "at")[1:] = [a(0), a(0 if pin == "1" else 4)]
        first(pad, "size")[1:] = [a(3.4), a(3.4)]
        first(pad, "drill")[1] = a(2.2)


def build(workspace):
    assert not workspace.exists(), "Use a fresh proposal workspace"
    inputs = []
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru")
            or p.name in ("fp-lib-table", "sym-lib-table", "components.json", "bom.csv")
        ):
            inputs.append(p)
        elif p.is_dir() and p.suffix == ".pretty":
            inputs.extend(q for q in p.rglob("*") if q.is_file())
    hashes = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    workspace.mkdir(parents=True)
    for p in inputs:
        target = workspace / p.relative_to(SOURCE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    pcb = workspace / "processor_carrier.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    j1 = next(f for f in children(tree, "footprint") if reference(f) == "J1")
    other = [sexpr(f) for f in children(tree, "footprint") if f is not j1]
    copper = [
        sexpr(n) for n in tree if isinstance(n, list) and n and n[0] in ("segment", "via", "arc", "zone")
    ]
    alter(j1)
    assert other == [sexpr(f) for f in children(tree, "footprint") if f is not j1]
    assert copper == [
        sexpr(n) for n in tree if isinstance(n, list) and n and n[0] in ("segment", "via", "arc", "zone")
    ]
    pcb.write_text(sexpr(tree) + "\n")
    library = copy.deepcopy(j1)
    library[1] = NAME
    library[:] = [
        n for n in library if not (isinstance(n, list) and n and n[0] in ("at", "uuid", "embedded_fonts"))
    ]
    for pad in children(library, "pad"):
        pad[:] = [n for n in pad if not (isinstance(n, list) and n and n[0] in ("net", "uuid"))]
    for prop in children(library, "property"):
        if prop[1] == "Reference":
            prop[2] = "REF**"
        prop[:] = [n for n in prop if not (isinstance(n, list) and n and n[0] == "uuid")]
    (workspace / ("RMX_Carrier.pretty/" + NAME + ".kicad_mod")).write_text(sexpr(library) + "\n")
    sch = workspace / "processor_carrier.kicad_sch"
    schematic = read_sexpr(sch.read_text())
    symbol = next(
        s
        for s in children(schematic, "symbol")
        if any(p[1:3] == ["Reference", "J1"] for p in children(s, "property"))
    )
    for prop in children(symbol, "property"):
        if prop[1] == "Value":
            prop[2] = VALUE
        elif prop[1] == "Footprint":
            prop[2] = FOOTPRINT
    sch.write_text(sexpr(schematic) + "\n")
    path = workspace / "components.json"
    components = json.loads(path.read_text())
    part = next(p for p in components if p["ref"] == "J1")
    part.update(
        part=VALUE,
        footprint=FOOTPRINT,
        source="https://www.alphawire.com/products/wire/ecogen/ecowire/6715",
        note="Separate direct-solder geometry proposal; max pretinned OD1.4mm, finished bores2.1..2.3mm, solder/strain/current/life unqualified",
    )
    path.write_text(json.dumps(components, indent=2) + "\n")
    path = workspace / "bom.csv"
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row["Reference"] == "J1":
            row.update(Part_or_value=VALUE, Footprint=FOOTPRINT, Source=part["source"], Note=part["note"])
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buf.getvalue())
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    out = workspace / "generated"
    out.mkdir()
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        candidate_pcb_sha256=sha(pcb),
        helper_sha256=sha(Path(__file__)),
        unchanged_other_footprints=len(other),
        unchanged_tracks_vias_zones=True,
        world_pad_centers_mm=[[44, 47, 8.1], [44, 51, 8.1]],
        finished_bore_requirement_mm=[2.1, 2.3],
        copper_land_diameter_mm=3.4,
        minimum_nominal_annulus_at_maximum_hole_mm=0.55,
        maximum_pretinned_bundle_OD_requirement_mm=1.4,
        relative_centering_allocation_mm=0.3,
        source_and_receiver_joint_acceptance_each_ohm=0.0005,
        minimum_source_relative_fit_diametral_margin_mm=0.1,
        full_current_path_extracted=False,
        solder_and_strain_process_approved=False,
        physical_fit_verified=False,
        fabrication_released=False,
        canonical_modified=False,
    )
    (out / "proposal.json").write_text(json.dumps(report, indent=2) + "\n")
    print(workspace.relative_to(REPO), sha(pcb), flush=True)


def native(workspace, cli):
    """Check a scratch snapshot, saving raw reports and the actual refilled PCB."""
    out = workspace / "generated"
    files = [
        p for p in workspace.rglob("*") if p.is_file() and "generated" not in p.relative_to(workspace).parts
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in files}
    for p in [Path(__file__), REPO / "hardware/electronics/common/sexpr.py", ROOT.parent / "generate.py"]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    commands = []
    with tempfile.TemporaryDirectory(prefix="afx-e19-wire-") as directory:
        temp = Path(directory)
        for p in files:
            target = temp / p.relative_to(workspace)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(cli.parent.parent / "SharedSupport/footprints"),
            FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
        )

        def run(args):
            p = subprocess.run(
                [str(cli), *map(str, args)], env=env, capture_output=True, text=True, timeout=180
            )
            commands.append(
                dict(args=list(map(str, args)), returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
            )
            (out / "native-command-log.json").write_text(json.dumps(commands, indent=2) + "\n")
            assert p.returncode == 0, commands[-1]

        run(
            [
                "sch",
                "erc",
                "--severity-all",
                "--format",
                "json",
                "-o",
                out / "erc.json",
                temp / "processor_carrier.kicad_sch",
            ]
        )
        run(
            [
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
                out / "drc.json",
                temp / "processor_carrier.kicad_pcb",
            ]
        )
        shutil.copyfile(temp / "processor_carrier.kicad_pcb", out / "filled.kicad_pcb")
        run(
            [
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                out / "netlist.xml",
                temp / "processor_carrier.kicad_sch",
            ]
        )
    drc, erc = json.loads((out / "drc.json").read_text()), json.loads((out / "erc.json").read_text())
    counts = dict(
        opens=len(drc["unconnected_items"]),
        parity=len(drc["schematic_parity"]),
        hard_drc=sum(v["severity"] == "error" for v in drc["violations"]),
        warnings=sum(v["severity"] != "error" for v in drc["violations"]),
        erc=sum(len(s["violations"]) for s in erc["sheets"]),
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Candidate changed during native checks"
    report = dict(
        source_sha256=hashes,
        candidate_pcb_sha256=sha(workspace / "processor_carrier.kicad_pcb"),
        artifact_sha256={
            str((out / n).relative_to(REPO)): sha(out / n)
            for n in ["erc.json", "drc.json", "filled.kicad_pcb", "netlist.xml"]
        },
        counts=counts,
        commands=commands,
        native_all_findings_zero=not any(counts.values()),
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "native.json").write_text(json.dumps(report, indent=2) + "\n")
    print(counts, flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--cli", type=Path, default=CLI)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    workspace.relative_to(REPO)
    if not args.check_only:
        build(workspace)
    raise SystemExit(0 if native(workspace, args.cli)["native_all_findings_zero"] else 1)
