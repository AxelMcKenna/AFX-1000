"""Separate U102 actual bottom-copper repair; no source/canonical mutation."""

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
SOURCE = ROOT / "sources/native"
VARIANT = ROOT / "variant"
METAL = [121.75, 117.5, 128.75, 122.5]
TIM = [120.75, 116.5, 129.75, 123.5]
PROTECTED = {"DC_IN", "VIN_IC", "POWER_RUN", "FAST_OV_REF", "P03_ALL_SOURCES_READY", "POWER_READY"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    VARIANT.mkdir(exist_ok=True)
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, VARIANT / p.name, dirs_exist_ok=True)
        elif p.suffix in {".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"} or p.name in {
            "fp-lib-table",
            "sym-lib-table",
        }:
            shutil.copy2(p, VARIANT / p.name)
    base = SOURCE / "power_p03.kicad_pcb"
    capture = json.loads((SOURCE / "capture.json").read_text())
    assert capture["pcb_sha256"] == sha(base)
    tree = read_sexpr(base.read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net") if len(n) > 2}
    removed = []
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"segment", "via"}:
            continue
        raw = str(first(obj, "net")[1]).lstrip("/")
        node = names.get(raw, raw)
        if node == "AGND" or node in PROTECTED:
            continue
        if obj[0] == "segment":
            if first(obj, "layer")[1] != "B.Cu":
                continue
            a = list(map(float, first(obj, "start")[1:3]))
            b = list(map(float, first(obj, "end")[1:3]))
            r = float(first(obj, "width")[1]) / 2 + 0.16
            hit = (
                min(a[0], b[0]) - r < METAL[2]
                and max(a[0], b[0]) + r > METAL[0]
                and min(a[1], b[1]) - r < METAL[3]
                and max(a[1], b[1]) + r > METAL[1]
            )
        else:
            x, y = map(float, first(obj, "at")[1:3])
            r = float(first(obj, "size")[1]) / 2 + 0.16
            hit = METAL[0] - r < x < METAL[2] + r and METAL[1] - r < y < METAL[3] + r
        if hit:
            removed.append(
                dict(uuid=str(first(obj, "uuid")[1]), kind=obj[0], node=node, exact_sexpr=sexpr(obj))
            )
            tree.remove(obj)
    x0, y0, x1, y1 = METAL
    tree.append(
        read_sexpr(f"""(zone(net "/AGND")(layer "B.Cu")(name "U102_STRONGER_BOTTOM_FIELD")(hatch edge .5)(priority 20)
        (connect_pads yes(clearance .16))(min_thickness .15)
        (fill yes(thermal_gap .2)(thermal_bridge_width .5)(island_removal_mode 0))
        (polygon(pts(xy {x0} {y0})(xy {x1} {y0})(xy {x1} {y1})(xy {x0} {y1}))))""")
    )
    pcb = VARIANT / "power_p03.kicad_pcb"
    pcb.write_text(sexpr(tree) + "\n")
    cli = Path(args.kicad_cli)
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-u102stronger-native",
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
            str(VARIANT / "erc.json"),
            str(VARIANT / "power_p03.kicad_sch"),
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
            str(VARIANT / "drc.json"),
            str(pcb),
        ],
    ]:
        run = subprocess.run([str(cli), *argv], capture_output=True, text=True, env=env, timeout=180)
        runs.append(
            dict(argv=[str(cli), *argv], returncode=run.returncode, stdout=run.stdout, stderr=run.stderr)
        )
    (VARIANT / "native-commands.json").write_text(json.dumps(runs, indent=2) + "\n")
    drc = json.loads((VARIANT / "drc.json").read_text())
    erc = json.loads((VARIANT / "erc.json").read_text())
    hard = [v for v in drc["violations"] if v["type"] not in {"track_dangling", "via_dangling"}]
    report = dict(
        protected_control_supply_nodes=sorted(PROTECTED),
        source_pcb_sha256=sha(base),
        candidate_pcb_sha256=sha(pcb),
        removed_objects=removed,
        hard_drc=len(hard),
        parity=len(drc.get("schematic_parity", [])),
        erc=sum(len(s["violations"]) for s in erc["sheets"]),
        opens=len(drc["unconnected_items"]),
        dangling_warnings=len(drc["violations"]) - len(hard),
        all_component_poses_unchanged=True,
        physical_tests_performed=0,
        electrically_complete=False,
        thermal_path_qualified=False,
        canonical_modified=False,
    )
    (VARIANT / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    construction = json.loads((SOURCE / "construction.json").read_text())
    construction["pcb_sha256"] = sha(pcb)
    (VARIANT / "construction.json").write_text(json.dumps(construction, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "removed_objects"}, indent=2))
    print("Removed", len(removed), "actual copper objects")
    return 1 if hard or report["parity"] or report["erc"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
