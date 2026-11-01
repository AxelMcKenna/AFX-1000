"""Separate U10 copper repair trial; all removed connections remain explicit obligations."""

import argparse
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.generate import sha
from hardware.electronics.common.placement import footprint_root
from hardware.electronics.common.sexpr import first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "u10"
VARIANT = ROOT / "variant"
CONTACT = [190.1, 127.7, 193.75, 131.4]
FIELD = [190.1, 127.7, 194.75, 131.4]
EP = [(x, y) for x in [193.8, 194.4] for y in [128.55, 129.05, 129.55, 130.05]]


def point_segment(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    den = vx * vx + vy * vy
    t = max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / den)) if den else 0
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    VARIANT.mkdir(exist_ok=True)
    for p in (BASE / "variant").iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, VARIANT / p.name, dirs_exist_ok=True)
        elif p.suffix in {".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"} or p.name in {
            "fp-lib-table",
            "sym-lib-table",
        }:
            shutil.copy2(p, VARIANT / p.name)
    source = BASE / "variant/power_p03.kicad_pcb"
    tree = read_sexpr(source.read_text())
    removed = []
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"segment", "via"}:
            continue
        node = str(first(obj, "net")[1]).lstrip("/")
        if obj[0] == "segment":
            a = list(map(float, first(obj, "start")[1:3]))
            b = list(map(float, first(obj, "end")[1:3]))
            radius = float(first(obj, "width")[1]) / 2 + 0.16
            layer = first(obj, "layer")[1]
            field_intersection = (
                layer != "F.Cu"
                and min(a[0], b[0]) - radius < FIELD[2]
                and max(a[0], b[0]) + radius > FIELD[0]
                and min(a[1], b[1]) - radius < FIELD[3]
                and max(a[1], b[1]) + radius > FIELD[1]
            )
            ep_intersection = any(point_segment(p, a, b) < 0.3 + radius - 1e-8 for p in EP)
            reject = node != "RAW_N22" and (field_intersection or ep_intersection)
        else:
            xy = list(map(float, first(obj, "at")[1:3]))
            radius = float(first(obj, "size")[1]) / 2 + 0.16
            old_direct = node == "RAW_N22" and 193.4 < xy[0] < 195.05 and 128.1 < xy[1] < 130.5
            field_intersection = (
                FIELD[0] - radius < xy[0] < FIELD[2] + radius
                and FIELD[1] - radius < xy[1] < FIELD[3] + radius
            )
            ep_intersection = any(math.dist(p, xy) < 0.3 + radius - 1e-8 for p in EP)
            reject = old_direct or (node != "RAW_N22" and (field_intersection or ep_intersection))
        if reject:
            removed.append(
                dict(kind=obj[0], node=node, uuid=str(first(obj, "uuid")[1]), exact_sexpr=sexpr(obj))
            )
            tree.remove(obj)
    for x, y in EP:
        tree.append(
            read_sexpr(f'(via(at {x} {y})(size .6)(drill .25)(layers "F.Cu" "B.Cu")(net "/RAW_N22"))')
        )
    pcb = VARIANT / "power_p03.kicad_pcb"
    pcb.write_text(sexpr(tree) + "\n")
    cli = Path(args.kicad_cli)
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-u10stronger-kicad",
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
        run = subprocess.run([str(cli), *argv], env=env, capture_output=True, text=True, timeout=180)
        runs.append(
            dict(argv=[str(cli), *argv], returncode=run.returncode, stdout=run.stdout, stderr=run.stderr)
        )
    (VARIANT / "native-commands.json").write_text(json.dumps(runs, indent=2) + "\n")
    drc = json.loads((VARIANT / "drc.json").read_text())
    erc = json.loads((VARIANT / "erc.json").read_text())
    hard = [v for v in drc["violations"] if v["type"] not in {"track_dangling", "via_dangling"}]
    result = dict(
        source_pcb_sha256=sha(source),
        candidate_pcb_sha256=sha(pcb),
        additional_removed_objects=removed,
        new_direct_ep_centres_native_mm=EP,
        hard_drc=len(hard),
        opens=len(drc["unconnected_items"]),
        parity=len(drc.get("schematic_parity", [])),
        native_erc_issues=sum(len(s["violations"]) for s in erc["sheets"]),
        warnings=len(drc["violations"]) - len(hard),
        electrically_complete=False,
        canonical_modified=False,
        thermal_path_qualified=False,
    )
    (VARIANT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    construction = json.loads((BASE / "variant/construction.json").read_text())
    construction["pcb_sha256"] = sha(pcb)
    construction["additional_u10_via_process_approved"] = False
    (VARIANT / "construction.json").write_text(json.dumps(construction, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "additional_removed_objects"}, indent=2))
    print("Removed", len(removed), "additional objects")
    return 1 if hard or result["parity"] or result["native_erc_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
