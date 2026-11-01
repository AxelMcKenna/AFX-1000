"""Coordinated existing OUT-barrel consolidation and adjacent-AGND trial; no existing source endpoint edits."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.generate import sha
from hardware.electronics.common.placement import footprint_root
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

from .synthesize import METAL, ROOT

OUT = ROOT / "consolidated_variant"
EXTRA_AGND = [(125.35, 119.05), (125.85, 121.8), (125.35, 121.8)]
RETAINED_OUTPUT_BARREL = (122.125, 119.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    for p in (ROOT / "variant").iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, OUT / p.name, dirs_exist_ok=True)
        elif p.suffix in {".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"} or p.name in {
            "fp-lib-table",
            "sym-lib-table",
        }:
            shutil.copy2(p, OUT / p.name)
    source = ROOT / "variant/power_p03.kicad_pcb"
    tree = read_sexpr(source.read_text())
    removed = []
    for v in list(children(tree, "via")):
        x, y = map(float, first(v, "at")[1:3])
        if (
            str(first(v, "net")[1]).lstrip("/") == "V2V5_AUX"
            and METAL[0] <= x <= METAL[2]
            and METAL[1] <= y <= METAL[3]
            and (x, y) != RETAINED_OUTPUT_BARREL
        ):
            removed.append(
                dict(
                    uuid=str(first(v, "uuid")[1]), exact_sexpr=sexpr(v), native_xy_mm=[x, y], node="V2V5_AUX"
                )
            )
            tree.remove(v)
    assert len(removed) == 3
    for xy in EXTRA_AGND:
        tree.append(
            read_sexpr(f'(via(at {xy[0]} {xy[1]})(size .7)(drill .25)(layers "F.Cu" "B.Cu")(net "/AGND"))')
        )
    pcb = OUT / "power_p03.kicad_pcb"
    pcb.write_text(sexpr(tree) + "\n")
    cli = Path(args.kicad_cli)
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-u102-consolidated-trial",
        KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        KICAD10_SYMBOL_DIR=str(cli.resolve().parents[1] / "SharedSupport/symbols"),
    )
    runs = []
    for argv in [
        ["--version"],
        [
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "-o",
            str(OUT / "erc.json"),
            str(OUT / "power_p03.kicad_sch"),
        ],
        [
            "pcb",
            "drc",
            "--severity-all",
            "--schematic-parity",
            "--refill-zones",
            "--save-board",
            "--format",
            "json",
            "-o",
            str(OUT / "drc.json"),
            str(pcb),
        ],
    ]:
        run = subprocess.run([str(cli), *argv], capture_output=True, text=True, env=env, timeout=180)
        runs.append(
            dict(argv=[str(cli), *argv], returncode=run.returncode, stdout=run.stdout, stderr=run.stderr)
        )
    (OUT / "native-commands.json").write_text(json.dumps(runs, indent=2) + "\n")
    drc = json.loads((OUT / "drc.json").read_text())
    erc = json.loads((OUT / "erc.json").read_text())
    hard = [v for v in drc["violations"] if v["type"] not in {"track_dangling", "via_dangling"}]
    report = dict(
        source_pcb_sha256=sha(source),
        candidate_pcb_sha256=sha(pcb),
        removed_output_vias=removed,
        actual_added_AGND_native_mm=EXTRA_AGND,
        retained_output_barrel_native_mm=RETAINED_OUTPUT_BARREL,
        hard_drc=len(hard),
        parity=len(drc.get("schematic_parity", [])),
        erc=sum(len(s["violations"]) for s in erc["sheets"]),
        opens=len(drc["unconnected_items"]),
        dangling_warnings=len(drc["violations"]) - len(hard),
        protected_inner_tracks_and_nonoutput_barrels_unchanged=True,
        original_9_direct_EP_barrels_unchanged=True,
        extra_barrels_are_not_direct_EP_contacts=True,
        electrical_obligations=[
            "Restore all original output connections from3 removed barrel endpoints via deliberate source output fanout",
            "Preserve intentional OUT-to-C10610uF-to-AGND loop; C106 is underside atnative132.525,122; C107100nF is not a replacement",
            "EffectiveC/ESR/startup/load-step/shared return and actual filled/capped barrel process remain unqualified",
        ],
        physical_tests_performed=0,
        thermal_path_qualified=False,
        electrically_complete=False,
        canonical_modified=False,
    )
    (OUT / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    construction = json.loads((ROOT / "variant/construction.json").read_text())
    construction["pcb_sha256"] = sha(pcb)
    (OUT / "construction.json").write_text(json.dumps(construction, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "removed_output_vias"}, indent=2))
    return 1 if hard or report["parity"] or report["erc"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
