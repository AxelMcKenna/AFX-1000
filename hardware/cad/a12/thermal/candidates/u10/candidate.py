"""Separate relocated-U10 RAW_N22 thermal feasibility variant; canonical PCB untouched."""

import argparse
import copy
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from hardware.electronics.common.placement import footprint_root
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from .network import REPO, sha

ROOT = Path(__file__).resolve().parent
VARIANT = ROOT / "variant"
POLYGON = [[190.1, 127.7], [194.75, 127.7], [194.75, 131.4], [190.1, 131.4]]
INNER = [[190.1, 126.1], [194.75, 126.1], [194.75, 131.4], [190.1, 131.4]]
EP_VIAS = [(193.8, y) for y in [128.75, 129.25, 129.75]] + [(194.4, 128.75)]
SINK_VIAS = [(191.8, 131), (190.4, 130.9)]


def geometry_inventory(tree):
    def floats(row):
        return tuple(float(v) for v in row[1:])

    fps = []
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        pads = []
        for p in children(f, "pad"):
            pads.append(
                (
                    p[1],
                    p[2],
                    p[3],
                    floats(first(p, "at")),
                    floats(first(p, "size")),
                    str(first(p, "net")[1]) if children(p, "net") else None,
                )
            )
        fps.append((ref, str(f[1]), floats(first(f, "at")), first(f, "layer")[1], tuple(sorted(pads))))
    tracks = [
        (
            floats(first(s, "start")),
            floats(first(s, "end")),
            floats(first(s, "width")),
            first(s, "layer")[1],
            first(s, "net")[1],
        )
        for s in children(tree, "segment")
    ]
    vias = [
        (
            floats(first(v, "at")),
            floats(first(v, "size")),
            floats(first(v, "drill")),
            tuple(first(v, "layers")[1:]),
            first(v, "net")[1],
        )
        for v in children(tree, "via")
    ]
    return dict(footprints=sorted(fps), tracks=sorted(tracks), vias=sorted(vias))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kicad-cli", required=True)
    args = p.parse_args()
    src = ROOT / "sources"
    VARIANT.mkdir(exist_ok=True)
    for name in ["erc.json", "drc.json", "receipt.json", "construction.json", "native-commands.json"]:
        (VARIANT / name).unlink(missing_ok=True)
    for f in src.iterdir():
        if f.suffix in {".kicad_pro", ".kicad_dru", ".kicad_sym", ".kicad_sch"} or f.name in {
            "fp-lib-table",
            "sym-lib-table",
        }:
            shutil.copy2(f, VARIANT / f.name)
    shutil.copytree(src / "RMX_P03.pretty", VARIANT / "RMX_P03.pretty", dirs_exist_ok=True)
    base = src / "power_p03.kicad_pcb"
    tree = read_sexpr(base.read_text())
    baseline = geometry_inventory(tree)
    old = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "U10"] for p in children(f, "property"))
    )
    template = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "U11"] for p in children(f, "property"))
    )
    moved = copy.deepcopy(template)
    oldnets = {str(p[1]): copy.deepcopy(first(p, "net")) for p in children(old, "pad") if children(p, "net")}
    first(moved, "at")[1:] = [a(194.2), a(129.3)]
    for prop in children(moved, "property"):
        if prop[1] == "Reference":
            prop[2] = "U10"
    for pad in children(moved, "pad"):
        if str(pad[1]) in oldnets:
            pad[:] = [q for q in pad if not (isinstance(q, list) and q and q[0] == "net")]
            pad.append(oldnets[str(pad[1])])
    for key in ["path", "sheetname", "sheetfile"]:
        if children(old, key):
            moved[:] = [q for q in moved if not (isinstance(q, list) and q and q[0] == key)]
            moved.append(copy.deepcopy(first(old, key)))

    def ids(obj):
        if not isinstance(obj, list):
            return
        if obj and obj[0] == "uuid":
            obj[1] = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-u10-front:" + str(obj[1])))
        for q in obj:
            ids(q)

    ids(moved)
    first(moved, "uuid")[1] = first(old, "uuid")[1]
    tree[tree.index(old)] = moved
    plan = json.loads((ROOT / "relocation-clearance-plan.json").read_text())
    assert plan["source_pcb_sha256"] == sha(base)
    remove_ids = {r["uuid"] for r in plan["removed_source_objects"]}
    removed = []
    for obj in list(tree):
        if (
            isinstance(obj, list)
            and obj
            and obj[0] in {"segment", "via"}
            and children(obj, "uuid")
            and first(obj, "uuid")[1] in remove_ids
        ):
            removed.append(dict(uuid=first(obj, "uuid")[1], kind=obj[0], node=first(obj, "net")[1]))
            tree.remove(obj)
    assert {v["uuid"] for v in removed} == remove_ids
    original = geometry_inventory(tree)
    xy = " ".join(f"(xy {x} {y})" for x, y in POLYGON)
    tree.append(
        read_sexpr(f"""(zone (net "/RAW_N22") (layer "B.Cu")
        (name "U10_LATERAL_DRAFT") (hatch edge .5) (priority 20)
        (connect_pads yes (clearance .16)) (min_thickness .15)
        (fill yes (thermal_gap .2) (thermal_bridge_width .5) (island_removal_mode 0))
        (polygon (pts {xy})))""")
    )
    for layer in ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
        xy_inner = " ".join(f"(xy {x} {y})" for x, y in INNER)
        tree.append(
            read_sexpr(f'''(zone (net "/RAW_N22") (layer "{layer}")
            (name "U10_INNER_BRIDGE_DRAFT") (hatch edge .5) (priority 20)
            (connect_pads yes (clearance .16)) (min_thickness .15)
            (fill yes (thermal_gap .2) (thermal_bridge_width .5) (island_removal_mode 0))
            (polygon (pts {xy_inner})))''')
        )
    for x, y in EP_VIAS + SINK_VIAS:
        tree.append(
            read_sexpr(f"""(via(at {x} {y})(size .6)(drill .25)(layers "F.Cu" "B.Cu")(net "/RAW_N22"))""")
        )
    pcb = VARIANT / "power_p03.kicad_pcb"
    pcb.write_text(sexpr(tree) + "\n")
    cli = Path(args.kicad_cli)
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-u10-native-config",
        KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        KICAD10_SYMBOL_DIR=str(cli.resolve().parents[1] / "SharedSupport/symbols"),
    )
    commands = []
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
        run = subprocess.run([str(cli), *argv], env=env, capture_output=True, text=True)
        commands.append(dict(argv=run.args, returncode=run.returncode, stdout=run.stdout, stderr=run.stderr))
        (VARIANT / "native-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
    native = read_sexpr(pcb.read_text())
    actual = geometry_inventory(native)
    assert actual["footprints"] == original["footprints"] and actual["tracks"] == original["tracks"], (
        "Source parts/tracks changed"
    )
    assert all(v in actual["vias"] for v in original["vias"]), "Authored nonremoved vias changed"
    assert len(actual["vias"]) == len(original["vias"]) + len(EP_VIAS) + len(SINK_VIAS)
    drc = json.loads((VARIANT / "drc.json").read_text())
    erc = json.loads((VARIANT / "erc.json").read_text())
    issues = [v for s in erc["sheets"] for v in s["violations"]]
    report = dict(
        revision="U10-front-pose-thermal-feasibility-DRAFT",
        original_pcb_sha256=sha(base),
        candidate_pcb_sha256=sha(pcb),
        canonical_pcb_modified=False,
        authored_zone=dict(face="B.Cu", node="RAW_N22", polygon_native_mm=POLYGON),
        all_other_original_footprints_preserved=True,
        deliberately_removed_track_via_count=len(removed),
        proposed_U10_pose_native=[194.2, 129.3, 0, "F"],
        baseline_U10_pose_native=[192.5, 128.5, 0, "B"],
        deliberate_local_reroute_obligations=removed,
        original_pose_and_routing_preserved=False,
        electrically_closed=False,
        actual_added_thermal_vias_native_mm=EP_VIAS + SINK_VIAS,
        direct_ep_via_count=len(EP_VIAS),
        added_sink_via_count=len(SINK_VIAS),
        actual_added_inner_layers=["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"],
        baseline_geometry_counts={k: len(v) for k, v in baseline.items()},
        authored_geometry_counts={k: len(v) for k, v in original.items()},
        native_erc_issues=len(issues),
        native_drc_violations=len(drc["violations"]),
        native_opens=len(drc["unconnected_items"]),
        parity_issues=len(drc.get("schematic_parity", [])),
        electrical_stability_and_plane_return_effects_qualified=False,
        source_sha256={
            str(q.relative_to(REPO)): sha(q) for q in [base, ROOT / "candidate.py", src / "construction.json"]
        },
        physical_tests_performed=0,
        fabrication_released=False,
        thermal_path_qualified=False,
    )
    (VARIANT / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    # Native fill may remove unconnected fragments; only the actual saved fill is modeled.
    construction = json.loads((src / "construction.json").read_text())
    construction.update(
        pcb_sha256=sha(pcb),
        revision="U10-lateral-copper-only-unreleased",
        parent_construction_sha256=sha(src / "construction.json"),
    )
    (VARIANT / "construction.json").write_text(json.dumps(construction, indent=2) + "\n")
    if (
        issues
        or any(v["type"] not in {"track_dangling", "via_dangling"} for v in drc["violations"])
        or drc.get("schematic_parity", [])
    ):
        raise SystemExit("Native U10 variant has actual findings; do not accept")


if __name__ == "__main__":
    main()
