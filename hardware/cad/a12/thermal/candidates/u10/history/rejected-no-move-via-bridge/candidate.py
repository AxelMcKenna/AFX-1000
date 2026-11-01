"""Separate U10 B.Cu RAW_N22 lateral-spreader variant; canonical PCB untouched."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from hardware.electronics.common.placement import footprint_root
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

from .network import REPO, sha

ROOT = Path(__file__).resolve().parent
VARIANT = ROOT / "variant"
POLYGON = [[197.1, 124.3], [200.3, 124.3], [200.3, 133.8], [197.1, 133.8]]
INNER = [[191.65, 127.3], [200.3, 127.3], [200.3, 133.8], [191.65, 133.8]]
EP_VIAS = [(x,y) for x in [192.25,192.75] for y in [127.75,128.25,128.75,129.25]]
SINK_VIAS = [(198.7,y) for y in [126.3,128,130,132]]


def geometry_inventory(tree):
    def floats(row):
        return tuple(float(v) for v in row[1:])

    fps = []
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        pads = []
        for p in children(f, "pad"):
            pads.append((p[1], p[2], p[3], floats(first(p, "at")), floats(first(p, "size")),
                         str(first(p, "net")[1]) if children(p, "net") else None))
        fps.append((ref, str(f[1]), floats(first(f, "at")), first(f, "layer")[1], tuple(sorted(pads))))
    tracks = [(floats(first(s, "start")), floats(first(s, "end")), floats(first(s, "width")),
               first(s, "layer")[1], first(s, "net")[1]) for s in children(tree, "segment")]
    vias = [(floats(first(v, "at")), floats(first(v, "size")), floats(first(v, "drill")),
             tuple(first(v, "layers")[1:]), first(v, "net")[1]) for v in children(tree, "via")]
    return dict(footprints=sorted(fps), tracks=sorted(tracks), vias=sorted(vias))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kicad-cli", required=True)
    args = p.parse_args()
    src = ROOT / "sources"
    VARIANT.mkdir(exist_ok=True)
    for f in src.iterdir():
        if f.suffix in {".kicad_pro", ".kicad_dru", ".kicad_sym", ".kicad_sch"} or f.name in {"fp-lib-table", "sym-lib-table"}:
            shutil.copy2(f, VARIANT / f.name)
    shutil.copytree(src / "RMX_P03.pretty", VARIANT / "RMX_P03.pretty", dirs_exist_ok=True)
    base = src / "power_p03.kicad_pcb"
    tree = read_sexpr(base.read_text())
    original = geometry_inventory(tree)
    xy = " ".join(f"(xy {x} {y})" for x, y in POLYGON)
    tree.append(read_sexpr(f'''(zone (net "/RAW_N22") (layer "B.Cu")
        (name "U10_LATERAL_DRAFT") (hatch edge .5) (priority 20)
        (connect_pads yes (clearance .16)) (min_thickness .15)
        (fill yes (thermal_gap .2) (thermal_bridge_width .5) (island_removal_mode 0))
        (polygon (pts {xy})))'''))
    for layer in ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
        xy_inner = " ".join(f"(xy {x} {y})" for x,y in INNER)
        tree.append(read_sexpr(f'''(zone (net "/RAW_N22") (layer "{layer}")
            (name "U10_INNER_BRIDGE_DRAFT") (hatch edge .5) (priority 20)
            (connect_pads yes (clearance .16)) (min_thickness .15)
            (fill yes (thermal_gap .2) (thermal_bridge_width .5) (island_removal_mode 0))
            (polygon (pts {xy_inner})))'''))
    for x,y in EP_VIAS + SINK_VIAS:
        tree.append(read_sexpr(f'''(via(at {x} {y})(size .6)(drill .25)(layers "F.Cu" "B.Cu")(net "/RAW_N22"))'''))
    pcb = VARIANT / "power_p03.kicad_pcb"
    pcb.write_text(sexpr(tree) + "\n")
    cli = Path(args.kicad_cli)
    env = dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/afx-u10-native-config",
               KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
               KICAD10_SYMBOL_DIR=str(cli.resolve().parents[1] / "SharedSupport/symbols"))
    commands = []
    for argv in [["--version"], ["sch", "erc", "--severity-all", "--format", "json", "-o", str(VARIANT / "erc.json"), str(VARIANT / "power_p03.kicad_sch")],
                 ["pcb", "drc", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--format", "json", "-o", str(VARIANT / "drc.json"), str(pcb)]]:
        run = subprocess.run([str(cli), *argv], env=env, capture_output=True, text=True)
        commands.append(dict(argv=run.args, returncode=run.returncode, stdout=run.stdout, stderr=run.stderr))
        (VARIANT / "native-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
    native = read_sexpr(pcb.read_text())
    actual = geometry_inventory(native)
    assert actual["footprints"] == original["footprints"] and actual["tracks"] == original["tracks"], "Source parts/tracks changed"
    assert all(v in actual["vias"] for v in original["vias"]), "Original vias changed"
    assert len(actual["vias"]) == len(original["vias"]) + len(EP_VIAS) + len(SINK_VIAS)
    drc = json.loads((VARIANT / "drc.json").read_text())
    erc = json.loads((VARIANT / "erc.json").read_text())
    issues = [v for s in erc["sheets"] for v in s["violations"]]
    report = dict(revision="U10-four-inner-bridge-lateral-DRAFT", original_pcb_sha256=sha(base),
        candidate_pcb_sha256=sha(pcb), canonical_pcb_modified=False,
        authored_zone=dict(face="B.Cu", node="RAW_N22", polygon_native_mm=POLYGON),
        all_original_footprints_tracks_vias_preserved=True,
        actual_added_thermal_vias_native_mm=EP_VIAS+SINK_VIAS,
        direct_ep_via_count=len(EP_VIAS), added_sink_via_count=len(SINK_VIAS),
        actual_added_inner_layers=["In1.Cu","In2.Cu","In3.Cu","In4.Cu"],
        original_geometry_counts={k:len(v) for k,v in original.items()},
        native_erc_issues=len(issues), native_drc_violations=len(drc["violations"]),
        native_opens=len(drc["unconnected_items"]), parity_issues=len(drc.get("schematic_parity", [])),
        electrical_stability_and_plane_return_effects_qualified=False,
        source_sha256={str(q.relative_to(REPO)):sha(q) for q in [base, ROOT/'candidate.py',src/'construction.json']},
        physical_tests_performed=0, fabrication_released=False, thermal_path_qualified=False)
    (VARIANT / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    # Native fill may remove unconnected fragments; only the actual saved fill is modeled.
    construction = json.loads((src / "construction.json").read_text())
    construction.update(pcb_sha256=sha(pcb), revision="U10-lateral-copper-only-unreleased",
                        parent_construction_sha256=sha(src/'construction.json'))
    (VARIANT / "construction.json").write_text(json.dumps(construction, indent=2) + "\n")
    if issues or drc['violations'] or drc['unconnected_items'] or drc.get('schematic_parity', []):
        raise SystemExit("Native U10 variant has actual findings; do not accept")


if __name__ == "__main__":
    main()
