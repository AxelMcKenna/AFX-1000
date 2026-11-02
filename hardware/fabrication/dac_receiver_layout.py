"""Place the existing E08 circuit without changing its unresolved ESS interface.

The outline is a planning envelope for the receiver region. It is not a
decision to put raw DAC signals on an inter-board harness. The final codec and
ADC-driver integration must replace the prototype J1 boundary on shared copper.
"""

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.bypass_layout import mount

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1] / "hardware/electronics/dac_receiver"
STOCK = ROOT / "staging/dac-receiver-stock-01"
SIZE = (84, 64)
POSES = {
    "U1": (20, 18), "U2": (20, 44), "U3": (33, 31),
    "U4": (53, 31), "U5": (73, 31),
    "J1": (4, 24), "J2": (80, 19), "J3": (42, 56, 90),
    "R1": (13, 16.73, 90), "C1": (10, 16.73, 90),
    "R2": (27, 18, 90), "C2": (30, 18, 90),
    "R3": (12.5, 22), "R4": (25, 22.5),
    "R5": (27, 25.5), "R6": (24, 36.5),
    "R7": (27, 29.73, 90), "C3": (24, 29.73, 90),
    "R8": (44, 34.5), "R9": (48, 38),
    "R10": (47, 29.73, 90), "C4": (44, 26, 90),
    "R11": (52, 37), "C5": (52, 40), "R12": (66, 28),
    "R13": (13, 42.73, 90), "C6": (10, 42.73, 90),
    "R14": (27, 44, 90), "C7": (30, 44, 90),
    "R15": (12.5, 48), "R16": (25, 48.5),
    "R17": (40.5, 25.5), "R18": (40.5, 36.5),
    "R19": (39, 31, 90), "C8": (42, 31, 90),
    "R20": (59.5, 35), "R21": (57.5, 38),
    "R22": (60, 31, 90), "C9": (63, 31, 90),
    "R23": (61.5, 38), "C10": (61.5, 41),
    "R24": (80, 29.5, 90),
    "R25": (69, 21), "R26": (69, 43),
    "R27": (68.5, 25), "R28": (68.5, 39),
    "C11": (25, 13), "C12": (18, 23, 180),
    "C13": (25, 39), "C14": (18, 49, 180),
    "C15": (37, 27), "C16": (29, 35.5, 180),
    "C17": (57, 25), "C18": (48, 36, 180),
    "C19": (38, 51), "C20": (51, 51),
    "C21": (59, 15), "C22": (59, 49),
    "C23": (76, 25), "C24": (69, 35.8, 180),
}
MOUNTS = ((4, 4), (80, 4), (4, 60), (80, 60))


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="dac-receiver-placement-02")
    args = parser.parse_args()
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    out = ROOT / "staging" / args.label
    assert not out.exists(), "Preserve earlier candidates"
    parts = json.loads((SOURCE / "components.json").read_text())
    actual, pins = netlist(SOURCE / "generated/netlist.xml")
    assert len(parts) == 60 and set(POSES) == set(actual) == {p["ref"] for p in parts}
    assert all(pins[p["ref"]] == p["nets"] for p in parts)
    inputs = [SOURCE / p for p in (
        "components.json", "dac_receiver.kicad_sch", "generated/netlist.xml",
        "fp-lib-table", "sym-lib-table", "dependencies.json")]
    inputs += [STOCK / "capture.json", Path(__file__)]
    out.mkdir()
    shutil.copytree(STOCK, out / "libraries")
    (out / "libraries/capture.json").unlink()
    own = out / "libraries/AFX_DAC.pretty"
    own.mkdir()
    (own / "M2_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    table = read_sexpr((SOURCE / "fp-lib-table").read_text())
    for lib in children(table, "lib"):
        nickname = first(lib, "name")[1]
        first(lib, "uri")[1] = "${KIPRJMOD}/libraries/" + nickname + ".pretty"
    table.append([a("lib"), [a("name"), "AFX_DAC"], [a("type"), "KiCad"],
                  [a("uri"), "${KIPRJMOD}/libraries/AFX_DAC.pretty"],
                  [a("options"), ""], [a("descr"), "Planning-envelope mounts"]])
    (out / "fp-lib-table").write_text(sexpr(table) + "\n")
    table = read_sexpr((SOURCE / "sym-lib-table").read_text())
    for lib in children(table, "lib"):
        original = Path(first(lib, "uri")[1].replace("${KIPRJMOD}", str(SOURCE)))
        inputs.append(original)
        shutil.copyfile(original, out / "libraries" / original.name)
        first(lib, "uri")[1] = "${KIPRJMOD}/libraries/" + original.name
    (out / "sym-lib-table").write_text(sexpr(table) + "\n")
    nets = {n: i + 1 for i, n in enumerate(sorted({n for p in pins.values() for n in p.values()}))}
    board = read_sexpr('''(kicad_pcb (version 20240108) (generator pcbnew)
      (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal)
        (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
        (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))''')
    board.extend([a("net"), code, "/" + net] for net, code in nets.items())
    libraries = {}
    for part in parts:
        ref = part["ref"]
        assert actual[ref].findtext("value") == part["value"]
        assert actual[ref].findtext("footprint") == part["footprint"]
        lib, name = part["footprint"].split(":")
        path = out / "libraries" / (lib + ".pretty") / (name + ".kicad_mod")
        libraries[str(path.relative_to(out))] = sha(path)
        pose = POSES[ref]
        pose = (*pose[:2], pose[2] if len(pose) == 3 else 0, "F")
        board.append(placed_footprint(part, pose, path, nets, origin=(0, 0), namespace="AFX:E08:PCB01:"))
    for i, xy in enumerate(MOUNTS, 1):
        part = dict(ref="H" + str(i), value="M2_CLEARANCE", nets={},
                    footprint="AFX_DAC:M2_Clearance", source="", mpn="")
        board.append(placed_footprint(part, (*xy, 0, "F"), own / "M2_Clearance.kicad_mod",
                                      nets, origin=(0, 0), namespace="AFX:E08:PCB01:"))
    x, y = SIZE
    corners = ((0, 0), (x, 0), (x, y), (0, y))
    for start, end in zip(corners, (*corners[1:], corners[0])):
        board.append([a("gr_line"), [a("start"), *start], [a("end"), *end],
                      [a("stroke"), [a("width"), .05], [a("type"), a("default")]],
                      [a("layer"), "Edge.Cuts"]])
    for layer in ("In1.Cu", "In2.Cu"):
        board.append(read_sexpr(f'''(zone (net {nets['AGND']}) (net_name "/AGND") (layer "{layer}")
          (hatch edge .5) (connect_pads (clearance .2)) (min_thickness .2)
          (fill yes (thermal_gap .25) (thermal_bridge_width .3))
          (polygon (pts (xy .5 .5) (xy {x-.5} .5) (xy {x-.5} {y-.5}) (xy .5 {y-.5}))))'''))
    (out / "dac_receiver.kicad_pcb").write_text(sexpr(board) + "\n")
    shutil.copyfile(SOURCE / "dac_receiver.kicad_sch", out / "dac_receiver.kicad_sch")
    # Native export remains authoritative; parse here to ensure the paired file is XML.
    ET.parse(SOURCE / "generated/netlist.xml")
    shutil.copyfile(SOURCE / "generated/netlist.xml", out / "netlist.xml")
    profile = dict(meta=dict(filename="dac_receiver.kicad_pro", version=1),
        board=dict(design_settings=dict(rules=dict(min_clearance=.2, min_track_width=.2,
            min_copper_edge_clearance=.5, min_hole_clearance=.25,
            min_through_hole_diameter=.3, min_via_annular_width=.15))),
        net_settings=dict(classes=[dict(name="Default", clearance=.2, track_width=.2,
                                       via_diameter=.65, via_drill=.3)]))
    (out / "dac_receiver.kicad_pro").write_text(json.dumps(profile, indent=2) + "\n")
    (out / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    record = dict(source_sha256={str(p): sha(p) for p in inputs},
        captured_library_sha256=libraries, planning_envelope_mm=[*SIZE, 1.6],
        poses=POSES, mount_centres_mm=MOUNTS, electrical_parts=60,
        unchanged_original_pin_nets_values_and_footprints=True,
        final_audio_board_partition_selected=False,
        raw_DAC_boundary_requires_codec_colocation=True,
        raw_DAC_harness_approved=False, ESS_output_scale_resolved=False,
        final_gain_calibration_resolved=False, enclosure_fit_qualified=False,
        thermal_and_analog_performance_qualified=False,
        native_checks_pending=True, fabrication_released=False)
    (out / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Placed unchanged 60-part E08 circuit in 84x64mm planning envelope; native checks pending")


if __name__ == "__main__":
    run()
