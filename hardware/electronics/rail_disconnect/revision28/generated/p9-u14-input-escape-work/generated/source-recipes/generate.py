"""Build explicit E28 geometry over frozen E27; never mutate historical sources."""

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.placement import placed_footprint
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .. import generate as schematic_generator
from ..spec import COMPONENTS
from .manufacturer import SOURCES
from .manufacturer import main as footprint_main
from .terminals import PORTS
from .terminals import main as terminal_main

ROOT = Path(__file__).resolve().parent
MOVES = {
    ref: (139, 18.5 + 3.5 * i, 0, "B")
    for i, ref in enumerate(("R41", "R43", "R84", "R86", "R92", "R93", "R91", "R94"))
}
STACKUP = {
    "status": "candidate requirements; fabricator acceptance pending",
    "copper_layer_count": 6,
    "finished_copper_mm": {"nominal": 0.080, "minimum": 0.070, "maximum": 0.090},
    "dielectric_nominal_mm": [0.110, 0.320, 0.260, 0.320, 0.110],
    "laminate_thickness_mm": {"nominal": 1.600, "minimum": 1.500, "maximum": 1.700},
    "via_finished_plating_mm": {"minimum": 0.025, "maximum": 0.035},
    "copper_center_nominal_depth_mm": [0.040, 0.230, 0.630, 0.970, 1.370, 1.560],
    "outer_mask_nominal_mm": 0.010,
    "temperature_maximum_c": 85,
    "trace_resistivity_max_20c_ohm_m": 1.8e-8,
    "barrel_resistivity_max_20c_ohm_m": 2.0e-8,
    "temperature_coefficient_max_per_c": 0.0041,
    "conductivity_requirements_accepted": False,
    "passive_vias": "0.3mm drill/0.6mm land filled/capped through vias in0805 lands; IPC4761TypeVII candidate process; assembler/fabricator acceptance pending",
    "manufacturing_accepted": False,
    "dielectric_material": "FR4 candidate, Tg >= 170 C; actual supplier resin/glass pending",
}


def stackup():
    layers = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
    rows = [
        '(layer "F.SilkS" (type "Top Silk Screen"))',
        '(layer "F.Paste" (type "Top Solder Paste"))',
        '(layer "F.Mask" (type "Top Solder Mask") (thickness .01))',
    ]
    for i, layer in enumerate(layers):
        rows.append(f'(layer "{layer}" (type "copper") (thickness .08))')
        if i < 5:
            d = STACKUP["dielectric_nominal_mm"][i]
            rows.append(
                f'(layer "dielectric {i + 1}" (type "prepreg") '
                f'(thickness {d}) (material "FR4 candidate") (epsilon_r 4.5) (loss_tangent .02))'
            )
    rows.extend(
        [
            '(layer "B.Mask" (type "Bottom Solder Mask") (thickness .01))',
            '(layer "B.Paste" (type "Bottom Solder Paste"))',
            '(layer "B.SilkS" (type "Bottom Silk Screen"))',
            '(copper_finish "ENIG candidate")',
            "(dielectric_constraints no)",
        ]
    )
    return read_sexpr("(stackup " + " ".join(rows) + ")")


def component_contract():
    parts = copy.deepcopy(COMPONENTS)
    for part in parts:
        if part["part"] in SOURCES:
            part["footprint"] = f"RMX_E28:{part['part']}_TI_Q5B"
    for index, ref in enumerate(PORTS):
        parts.append(
            dict(
                ref=ref,
                part="7466003R",
                footprint="RMX_E28:7466003R_M3_SMT_Annulus_NPTH",
                pins=[dict(number="1", name="QUIET_RETURN_FORCE", kind="passive", side="L", net="AGND")],
                x=1097.28 + index * 50.8,
                y=1168.4,
                source="https://www.we-online.com/components/products/datasheet/7466003R.pdf",
                note="Actual SMT force-return stud; Kelvin/signal return remains on original headers. Contact resistance requires measurement.",
            )
        )
    return parts


def build():
    footprint_main()
    terminal_main()
    parts = component_contract()
    schematic_generator.COMPONENTS = parts
    schematic_generator.ROOT = ROOT
    schematic_generator.main()
    # Use fixed project routing rules rather than the empty schematic project.
    shutil.copy2(ROOT.parent / "revision27/rail_disconnect.kicad_pro", ROOT / "rail_disconnect.kicad_pro")
    shutil.copytree(
        ROOT.parent / "revision27/RMX_Disconnect.pretty", ROOT / "RMX_Disconnect.pretty", dirs_exist_ok=True
    )
    source = ROOT.parent / "revision27/rail_disconnect.kicad_pcb"
    tree = read_sexpr(source.read_text())
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    by_ref = {part["ref"]: part for part in parts}
    replaced = []
    for i, fp in enumerate(tree):
        if not isinstance(fp, list) or not fp or fp[0] != "footprint":
            continue
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref not in by_ref or by_ref[ref]["part"] not in SOURCES:
            if ref in MOVES:
                pose = MOVES[ref]
                at = first(fp, "at")
                at[1:4] = [100 + pose[0], 100 + pose[1], pose[2]]
            continue
        c = by_ref[ref]
        pin_nets = {p["number"]: p["net"] for p in c["pins"] if p["net"] is not None}
        pose = first(fp, "at")
        angle = float(pose[3]) if len(pose) > 3 else 0
        side = str(first(fp, "layer")[1])[0]
        native_pose = (float(pose[1]) - 100, float(pose[2]) - 100, angle, side)
        path = ROOT / "RMX_E28.pretty" / f"{c['part']}_TI_Q5B.kicad_mod"
        replacement = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pin_nets),
            native_pose,
            path,
            nets,
            namespace="rmx:E28:",
        )
        tree[i] = replacement
        replaced.append({"ref": ref, "part": c["part"], "pose": list(native_pose)})
    for ref, (x, y, _) in PORTS.items():
        c = by_ref[ref]
        tree.append(
            placed_footprint(
                dict(c, value=c["part"], mpn=c["part"], nets={"1": "AGND"}),
                (x, y, 0, "F"),
                ROOT / "RMX_E28.pretty/7466003R_M3_SMT_Annulus_NPTH.kicad_mod",
                nets,
                namespace="rmx:E28:",
            )
        )
    setup = first(tree, "setup")
    setup[:] = [v for v in setup if not isinstance(v, list) or not v or v[0] != "stackup"]
    setup.append(stackup())
    # KiCad total includes the two mask coats: 1.600 mm laminate + .020 mm mask.
    first(first(tree, "general"), "thickness")[1] = 1.620
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:copper:{index}")))])
    (ROOT / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    table = read_sexpr((ROOT / "fp-lib-table").read_text())
    for name in ("RMX_E28", "RMX_Disconnect"):
        for entry in children(table, "lib"):
            if first(entry, "name")[1] == name:
                first(entry, "uri")[1] = "${KIPRJMOD}/" + name + ".pretty"
        if not any(first(e, "name")[1] == name for e in children(table, "lib")):
            table.append(
                read_sexpr(
                    f'(lib (name "{name}") (type "KiCad") '
                    f'(uri "${{KIPRJMOD}}/{name}.pretty") (options "") (descr "E28 candidate"))'
                )
            )
    (ROOT / "fp-lib-table").write_text(sexpr(table) + "\n")
    (ROOT / "stackup.json").write_text(json.dumps(STACKUP, indent=2) + "\n")
    receipt = {
        "revision": "E28",
        "parent_pcb_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "q5b_replacements": replaced,
        "moves": MOVES,
        "return_ports": PORTS,
        "physical_build_qualified": False,
        "routing_repaired": False,
        "primary_sources": SOURCES,
    }
    (ROOT / "generated/geometry.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"E28 replaced {len(replaced)} Q5B footprints; native recheck required")


if __name__ == "__main__":
    build()
