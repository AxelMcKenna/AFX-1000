"""Export P03 complete source circuit as native KiCad engineering documents."""

import argparse
import csv
import io
import json
import os
import subprocess
from pathlib import Path

from ...common.flat_schematic import generate
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from . import footprints
from .spec import ROOT, components


def schematic(cli):
    parts = components()
    generate(
        ROOT,
        "P03",
        "power_p03",
        parts,
        [
            (
                30,
                30,
                "P03 complete replacement: guarded12V, direct precision digital buck, quiet analog5V, retained bipolar rail generation.",
            ),
            (
                30,
                3460,
                f"All {len(parts)} components form this single new 160x45 module; old E14/E23/P02 sources are not connected in parallel.",
            ),
            (
                30,
                3470,
                "Input 4A profile, source/protected/load boundaries and controlled E28 late closure are separately reviewed. No physical/release claim.",
            ),
        ],
        page=(1300, 3500),
        flags=[
            ("DC_IN", 38.1, 3429),
            ("AGND", 101.6, 3429),
            ("VIN_IC", 228.6, 3429),
            ("5V_DIG_SRC", 355.6, 3429),
            ("P03_PRE6V", 419.1, 3429),
            ("RAW_P22", 482.6, 3429),
            ("RAW_N22", 546.1, 3429),
            ("RAW_P17", 609.6, 3429),
            ("RAW_N17", 673.1, 3429),
            ("NREF_2V5", 736.6, 3429),
        ],
    )
    footprints.write()
    # Retained inductors live in the local library, never an unresolved parent
    # footprint dependency in the candidate project.
    text = (ROOT / "power_p03.kicad_sch").read_text().replace("RMX_Power:", "RMX_P03:")
    schematic_tree = read_sexpr(text)
    for symbol in children(schematic_tree, "symbol"):
        if any(p[1:3] == ["Reference", "J103"] for p in children(symbol, "property")):
            first(symbol, "in_bom")[1] = a("no")
    for symbol in children(first(schematic_tree, "lib_symbols"), "symbol"):
        if str(symbol[1]).endswith("_J103"):
            first(symbol, "in_bom")[1] = a("no")
    (ROOT / "power_p03.kicad_sch").write_text(sexpr(schematic_tree) + "\n")
    library = ROOT / "RMX_P03.kicad_sym"
    library_tree = read_sexpr(library.read_text())
    for symbol in children(library_tree, "symbol"):
        if str(symbol[1]).endswith("_J103"):
            first(symbol, "in_bom")[1] = a("no")
    library.write_text(sexpr(library_tree) + "\n")
    bom_path = ROOT / "bom.csv"
    rows = list(csv.reader(io.StringIO(bom_path.read_text())))
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(row for row in rows if not row or row[0] != "J103")
    bom_path.write_text(buffer.getvalue())
    for c in parts:
        c["footprint"] = c["footprint"].replace("RMX_Power:", "RMX_P03:")
    (ROOT / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    table = ROOT / "fp-lib-table"
    table.write_text(
        "\n".join(l for l in table.read_text().splitlines() if '(name "RMX_Power")' not in l) + "\n"
    )
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["KICAD10_SYMBOL_DIR"] = str(cli.resolve().parents[1] / "SharedSupport/symbols")
    for args in [
        [
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(out / "netlist.xml"),
            str(ROOT / "power_p03.kicad_sch"),
        ],
        [
            "sch",
            "erc",
            "--format",
            "json",
            "--output",
            str(out / "erc.json"),
            str(ROOT / "power_p03.kicad_sch"),
        ],
        ["sch", "export", "svg", "--output", str(out), str(ROOT / "power_p03.kicad_sch")],
    ]:
        result = subprocess.run([str(cli), *args], env=env, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
    print(f"P03 complete native schematic: {len(parts)} components; no physical measurement or release")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    args = parser.parse_args()
    schematic(args.kicad_cli)


if __name__ == "__main__":
    main()
