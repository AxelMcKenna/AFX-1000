"""Generate the passive rear inlet needed by the complete P03 replacement.

No current passes through the rear switch. The original E23 3 A input guard is
not in series with P03. Native construction and physical qualification are
separate; this source is not a release or a proven fault-protection circuit.
"""

import argparse
import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

from ...common.flat_schematic import generate as schematic
from ...common.netlists import netlist
from ...common.placement import footprint_root, placed_footprint, project_settings
from ...common.reports import sha
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import transform
from ..place import MOUNTS, OUTLINE

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated"
PROJECT = "rear_inlet"
POSES = {
    "J1": (40, 10.7, 180, "F"),
    "S1": (54, 1.2, 180, "F"),
    "F1": (28, 20.5, 0, "F"),
    "J2": (44, 28, 0, "F"),
    "J3": (16, 27, 180, "F"),
}


def pin(number, name, net):
    return dict(number=str(number), name=name, kind="passive", side="L", net=net)


def components():
    original = json.loads((ROOT.parent / "components.json").read_text())
    selected = {p["ref"]: copy.deepcopy(p) for p in original if p["ref"] in {"J1", "S1", "F1"}}
    for p in selected.values():
        p["footprint"] = p["footprint"].replace("RMX_Input:", "RMX_Inlet:")
    selected["F1"].update(
        part="0451006.MRL 6A 125V",
        note="Backup fuse only; adapter/fuse/wire/jack fault coordination unqualified",
    )
    selected["F1"]["pins"] = [pin(1, "1", "DC_JACK"), pin(2, "2", "DC_IN")]
    selected["J1"]["pins"] = [pin(1, "CENTER+", "DC_JACK"), pin(2, "SLEEVE", "AGND"), pin(3, "SWITCH", None)]
    selected["J1"]["note"] = (
        "Center-positive rear inlet,5A catalog limit; no original E23 eFuse in this variant. Mating plug/heating/fault coordination pending."
    )
    selected["S1"]["note"] = (
        "Logic switch only: AUX to RUN in ON, ground to RUN in OFF; no load power through switch."
    )
    selected["J2"] = dict(
        ref="J2",
        part="B2PS-VH(LF)(SN)",
        footprint="Connector_JST:JST_VH_B2PS-VH_1x02_P3.96mm_Horizontal",
        pins=[pin(1, "DC_IN", "DC_IN"), pin(2, "RETURN", "AGND")],
        source="https://www.jst.com/wp-content/uploads/2025/06/eVH.pdf",
        note="VHR-2N + SVH-41T-P1.1, AWG16. 10A catalog with AWG16; 10.5mm mated height/~20.5mm depth before wire bend. Native/physical assembly and thermal review required.",
    )
    selected["J3"] = dict(
        ref="J3",
        part="B3B-XH-A(LF)(SN)",
        footprint="Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical",
        pins=[
            pin(1, "SWITCH_SUPPLY", "SWITCH_SUPPLY"),
            pin(2, "POWER_RUN", "POWER_RUN"),
            pin(3, "RETURN", "AGND"),
        ],
        source="https://www.jst-mfg.com/product/pdf/eng/eXH.pdf",
        note="Logic-only keyed interface; final contact/wire/crimp process and mated envelope review pending",
    )
    for i, p in enumerate(selected.values()):
        p["x"] = round((50 + (i % 3) * 80) / 1.27) * 1.27
        p["y"] = round((50 + (i // 3) * 60) / 1.27) * 1.27
    return list(selected.values())


def generate(cli):
    parts = components()
    OUT.mkdir(exist_ok=True)
    schematic(
        ROOT,
        "E23I2",
        PROJECT,
        parts,
        [
            (
                20,
                170,
                "Passive rear inlet for P03. No E23 guard in series. Switch carries logic only; physical/fault qualification pending.",
            )
        ],
        (297, 210),
        [],
    )
    local = ROOT / "RMX_Inlet.pretty"
    local.mkdir(exist_ok=True)
    for name in ["PJ102AH_RearEdge_E23", "JS102011SAQN_RearEdge_E23"]:
        shutil.copyfile(
            ROOT.parent / "RMX_Input.pretty" / (name + ".kicad_mod"), local / (name + ".kicad_mod")
        )
    libs = footprint_root(str(cli))
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-inlet-kicad",
        KICAD10_FOOTPRINT_DIR=str(libs),
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    table = read_sexpr((ROOT / "fp-lib-table").read_text())
    table.append(
        read_sexpr(
            '(lib (name "MountingHole") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/MountingHole.pretty") (options "") (descr "M2 mounting holes"))'
        )
    )
    (ROOT / "fp-lib-table").write_text(sexpr(table) + "\n")
    subprocess.run(
        [
            str(cli),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            str(OUT / "netlist.xml"),
            str(ROOT / (PROJECT + ".kicad_sch")),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    _, pins = netlist(OUT / "netlist.xml")
    nets = {net: i + 1 for i, net in enumerate(sorted({n for p in pins.values() for n in p.values()}))}
    board = read_sexpr("""(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
    (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
    (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    stack = json.loads((ROOT / "stackup.json").read_text())
    first(board, "setup").append(
        read_sexpr(f"""(stackup
      (layer "F.Mask" (type "Top Solder Mask") (thickness {stack["mask_nominal_mm"]}))
      (layer "F.Cu" (type "copper") (thickness {stack["copper_nominal_mm"]}))
      (layer "dielectric 1" (type "core") (thickness {stack["dielectric_nominal_mm"]}) (material "FR4 candidate"))
      (layer "B.Cu" (type "copper") (thickness {stack["copper_nominal_mm"]}))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness {stack["mask_nominal_mm"]})))""")
    )
    board.extend(
        [a("net"), code, net if net.startswith("unconnected-") else "/" + net] for net, code in nets.items()
    )
    footprints = {}
    hashes = {}
    for p in parts:
        lib, name = p["footprint"].split(":")
        path = (ROOT if lib == "RMX_Inlet" else libs) / (lib + ".pretty") / (name + ".kicad_mod")
        fp = placed_footprint(
            dict(p, value=p["part"], mpn=p["part"], nets=pins[p["ref"]]),
            POSES[p["ref"]],
            path,
            nets,
            namespace="rmx:E23I2:",
        )
        for pad in children(fp, "pad"):
            if children(pad, "net") and str(first(pad, "net")[-1]).startswith("/unconnected-"):
                first(pad, "net")[-1] = str(first(pad, "net")[-1])[1:]
        footprints[p["ref"]] = fp
        hashes[p["footprint"]] = sha(path)
        board.append(fp)
    mount = libs / "MountingHole.pretty/MountingHole_2.2mm_M2.kicad_mod"
    for i, (x, y) in enumerate(MOUNTS, 1):
        fp = placed_footprint(
            dict(
                ref=f"H{i}",
                footprint="MountingHole:MountingHole_2.2mm_M2",
                value="M2_CLEARANCE",
                mpn="",
                source="",
                nets={},
            ),
            (x, y, 0, "F"),
            mount,
            nets,
            namespace="rmx:E23I2:",
        )
        first(fp, "attr").extend([a("board_only"), a("exclude_from_bom"), a("exclude_from_pos_files")])
        board.append(fp)
    for p, q in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        board.append(
            read_sexpr(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    pads = {}
    for ref, fp in footprints.items():
        for pad in children(fp, "pad"):
            if pad[1]:
                x, y = transform(fp, first(pad, "at")[1:3])
                pads[ref, str(pad[1])] = (x - 100, y - 100)
    paths = []

    def route(net, layer, points, width):
        paths.append(dict(net=net, layer=layer, width=width, points=points))
        for p, q in zip(points, points[1:]):
            if p == q:
                continue
            board.append(
                read_sexpr(
                    f'(segment (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (width {width}) (layer "{layer}.Cu") (net {nets[net]}))'
                )
            )

    def via(net, p):
        board.append(
            read_sexpr(
                f'(via (at {100 + p[0]} {100 + p[1]}) (size .7) (drill .3) (layers "F.Cu" "B.Cu") (net {nets[net]}))'
            )
        )

    def p(ref, pin):
        return pads[ref, str(pin)]

    route("DC_JACK", "F", [p("J1", 1), (40, 11.2), (23, 11.2), (23, 20.5)], 3)
    route("DC_JACK", "F", [(23, 20.5), p("F1", 1)], 1.2)
    route("DC_IN", "F", [p("F1", 2), (32, 20.5)], 1.2)
    route("DC_IN", "F", [(32, 20.5), (44, 20.5), p("J2", 1)], 3)
    route("AGND", "B", [p("J1", 2), (47.96, 4.7), p("J2", 2)], 3)
    route("AGND", "F", [p("S1", 3), (51.5, 7)], 0.4)
    via("AGND", (51.5, 7))
    route("AGND", "B", [(51.5, 7), (47.96, 7)], 0.4)
    route("AGND", "B", [p("J3", 3), (11, 36), (47.96, 36), p("J2", 2)], 0.4)
    for net, sp, vp, jp in [("SWITCH_SUPPLY", 1, (42, 17), 1), ("POWER_RUN", 2, (42, 15), 2)]:
        src = p("S1", sp)
        target = p("J3", jp)
        route(net, "F", [src, (src[0], vp[1]), vp], 0.3)
        via(net, vp)
        route(net, "B", [vp, (target[0], vp[1]), target], 0.3)
    (ROOT / (PROJECT + ".kicad_pcb")).write_text(
        "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
    )
    project = json.loads((ROOT / (PROJECT + ".kicad_pro")).read_text())
    settings = project_settings()
    settings["rules"].update(min_clearance=0.25, min_track_width=0.25)
    project["board"] = {"design_settings": settings}
    (ROOT / (PROJECT + ".kicad_pro")).write_text(json.dumps(project, indent=2) + "\n")
    (OUT / "routing.json").write_text(
        json.dumps(
            dict(
                revision="E23I2",
                footprint_sha256=hashes,
                paths=paths,
                via_count=3,
                physical_fit_verified=False,
                thermal_qualified=False,
                fault_coordination_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("E23I2: passive rear inlet generated, five components; native/independent checks required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    generate(parser.parse_args().kicad_cli.resolve())
