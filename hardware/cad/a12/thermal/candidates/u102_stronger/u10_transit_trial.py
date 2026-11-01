"""Read-only-source U10 thermal transit trial: all actual barrels and non-B routes retained."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.generate import sha
from hardware.electronics.common.placement import footprint_root
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "u10_B_trial"
SOURCE = ROOT / "sources/closed-U10"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kicad-cli", required=True)
    a = p.parse_args()
    OUT.mkdir(exist_ok=True)
    for f in SOURCE.iterdir():
        if f.suffix in {".kicad_sch", ".kicad_pro", ".kicad_dru"}:
            shutil.copy2(f, OUT / f.name)
    original = ROOT.parents[4] / "electronics/power_distribution/p03/candidates/u10-eight-ep-on-42add"
    # Libraries are read-only source dependencies, never modifications to the owner.
    for name in ["RMX_P03.kicad_sym", "fp-lib-table", "sym-lib-table"]:
        shutil.copy2(original / name, OUT / name)
    shutil.copytree(original / "RMX_P03.pretty", OUT / "RMX_P03.pretty", dirs_exist_ok=True)
    pcb = SOURCE / "power_p03.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    inspection = json.loads((ROOT / "generated/U10-bottom-transit-inspection.json").read_text())
    assert inspection["source_pcb_sha256"] == sha(pcb)
    ids = {r["uuid"] for r in inspection["bbox_halo_candidates"]}
    removed = []
    for item in list(children(tree, "segment")):
        if first(item, "uuid")[1] in ids:
            removed.append(
                dict(
                    uuid=first(item, "uuid")[1],
                    net=str(first(item, "net")[1]).lstrip("/"),
                    exact_sexpr=sexpr(item),
                )
            )
            tree.remove(item)
    assert len(removed) == len(ids) == 40
    target = OUT / "power_p03.kicad_pcb"
    target.write_text(sexpr(tree) + "\n")
    cli = Path(a.kicad_cli)
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-u10-transit-native",
        KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        KICAD10_SYMBOL_DIR=str(cli.resolve().parents[1] / "SharedSupport/symbols"),
    )
    logs = []
    for args in [
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
            str(target),
        ],
    ]:
        run = subprocess.run([str(cli), *args], env=env, capture_output=True, text=True, timeout=180)
        logs.append(
            dict(argv=[str(cli), *args], returncode=run.returncode, stdout=run.stdout, stderr=run.stderr)
        )
    (OUT / "native-commands.json").write_text(json.dumps(logs, indent=2) + "\n")
    drc = json.loads((OUT / "drc.json").read_text())
    erc = json.loads((OUT / "erc.json").read_text())
    hard = [v for v in drc["violations"] if v["type"] not in {"track_dangling", "via_dangling"}]
    report = dict(
        source_pcb_sha256=sha(pcb),
        candidate_pcb_sha256=sha(target),
        removed_B_segments=removed,
        hard_drc=len(hard),
        parity=len(drc.get("schematic_parity", [])),
        erc=sum(len(s["violations"]) for s in erc["sheets"]),
        opens=len(drc["unconnected_items"]),
        warnings=len(drc["violations"]) - len(hard),
        all_original_barrels_and_non_B_tracks_retained=True,
        all_footprints_unchanged=True,
        electrical_restoration_required=True,
        physical_tests_performed=0,
        thermal_path_qualified=False,
        canonical_modified=False,
    )
    (OUT / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    construction = json.loads((SOURCE / "construction.json").read_text())
    construction["pcb_sha256"] = sha(target)
    (OUT / "construction.json").write_text(json.dumps(construction, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "removed_B_segments"}, indent=2))
    return 1 if hard or report["parity"] or report["erc"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
