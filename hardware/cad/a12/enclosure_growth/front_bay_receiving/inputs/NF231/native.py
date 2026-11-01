"""Build an unrouted review PCB from captured NF03C footprints and actual nets.

Run with the installed KiCad Python, not the project virtual environment.
"""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (ROOT / "handoff.json").exists(), "Create a successor to sealed evidence"
    parts = json.loads((ROOT / "sources/components.json").read_text())
    plan = json.loads((ROOT / "generated/placement.json").read_text())
    assert not plan.get("pending_backside_bypass_refs"), "Run backside_bypass before building native PCB"
    inventory = json.loads((ROOT / "sources/footprint-area.json").read_text())["rows"]
    by_ref = {r["ref"]: r for r in inventory}
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
    names = sorted({p["net"] for c in parts for p in c["pins"] if p["net"] is not None})
    nets = {}
    for name in names:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
    expected = {}
    physical_nc = []
    footprint_changes = []
    silk_changes = []
    for c in parts:
        ref = c["ref"]
        alias = c["footprint"].replace(":", "__")
        library = ROOT / "sources/footprints" / (alias + ".kicad_mod")
        assert sha(library) == by_ref[ref]["library_sha256"], library
        nickname = "NF03P_CAPTURED"
        if c["footprint"] == "Package_SO:VSSOP-8_2.3x2mm_P0.5mm":
            original_sha = sha(library)
            library = ROOT / "NF03P_Manufacturer.pretty/TI_DCU0008A.kicad_mod"
            land = json.loads((ROOT / "generated/manufacturer-land.json").read_text())
            assert sha(library) == land["custom_footprint_sha256"]
            alias, nickname = "TI_DCU0008A", "NF03P_Manufacturer"
            footprint_changes.append(dict(ref=ref, original_sha256=original_sha,
                                          custom_sha256=sha(library), reason="TI DCU0008A example land"))
        elif c["footprint"] in ["Package_TO_SOT_SMD:SOT-363_SC-70-6", "Package_TO_SOT_SMD:SOT-23-5"]:
            silk = json.loads((ROOT / "generated/layout-silk.json").read_text())[c["footprint"]]
            assert sha(library) == silk["original_sha256"]
            alias, nickname = silk["alias"], "NF03P_Layout"
            library = ROOT / "NF03P_Layout.pretty" / (alias + ".kicad_mod")
            assert sha(library) == silk["local_sha256"]
            silk_changes.append(dict(ref=ref, original_sha256=silk["original_sha256"],
                                     custom_sha256=sha(library), electrical_geometry_changed=False))
        fp = pcbnew.FootprintLoad(str(library.parent), alias)
        assert fp is not None, ref
        fp.SetReference(ref)
        fp.SetValue(c["part"])
        fp.SetFPID(pcbnew.LIB_ID(nickname, alias))
        board.Add(fp)  # Flip needs a live parent BOARD in the KiCad10 API.
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fp.Value().SetLayer(pcbnew.F_Fab)
        fp.Value().SetVisible(False)
        p = plan["placements"][ref]
        fp.SetPosition(pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in p["anchor_mm"])))
        if p.get("side", "F") == "B":
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(p["rotation_deg"])
        pins = {p["number"]: p["net"] for p in c["pins"]}
        if c["part"] == "TLP4590AF(F":
            # Toshiba Rev9.0.A p13 shows a physical lead3; p2's electrical
            # assignment omits it. It must remain unconnected on this PCB.
            assert "3" not in pins
            pins["3"] = None
            physical_nc.append(dict(ref=ref, pad="3", reason="Physical lead3 has no electrical assignment", source_pages=[2, 13]))
        physical_numbers = set()
        for pad in fp.Pads():
            number = pad.GetNumber()
            if not number:
                # Paste-only stencil apertures have no electrical number.
                assert not pad.GetLayerSet().Contains(pcbnew.F_Cu) and not pad.GetLayerSet().Contains(pcbnew.B_Cu)
                continue
            physical_numbers.add(number)
            assert number in pins, (ref, number, "physical pad absent from schematic")
            if pins[number] is not None:
                pad.SetNet(nets[pins[number]])
        assert physical_numbers == set(pins), (ref, physical_numbers, set(pins))
        expected[ref] = pins
    width, height, _ = plan["board_mm"]
    points = [(0, 0), (width, 0), (width, height), (0, height)]
    for a, b in zip(points, points[1:] + points[:1]):
        edge = pcbnew.PCB_SHAPE()
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetWidth(pcbnew.FromMM(.05))
        edge.SetStart(pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in a)))
        edge.SetEnd(pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in b)))
        board.Add(edge)
    note = pcbnew.PCB_TEXT(board)
    note.SetText("NF03P / UNROUTED REVIEW")
    note.SetLayer(pcbnew.F_SilkS)
    note.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(.8), pcbnew.FromMM(.8)))
    note.SetTextThickness(pcbnew.FromMM(.1))
    note.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(width / 2), pcbnew.FromMM(1)))
    board.Add(note)
    output = ROOT / "negative_startup_placement.kicad_pcb"
    pcbnew.SaveBoard(str(output), board)
    (ROOT / "fp-lib-table").write_text(
        '(fp_lib_table (version 7) (lib (name "NF03P_CAPTURED") (type "KiCad") '
        '(uri "${KIPRJMOD}/sources/footprints") (options "") (descr "Captured NF03C library footprints")) '
        '(lib (name "NF03P_Manufacturer") (type "KiCad") (uri "${KIPRJMOD}/NF03P_Manufacturer.pretty") '
        '(options "") (descr "TI DCU0008A example land")) '
        '(lib (name "NF03P_Layout") (type "KiCad") (uri "${KIPRJMOD}/NF03P_Layout.pretty") '
        '(options "") (descr "Local silk cleanup, electrical geometry unchanged")))\n'
    )
    rules = dict(min_clearance=.16, min_track_width=.16, min_copper_edge_clearance=.5,
                 min_hole_clearance=.25, min_through_hole_diameter=.3, min_via_annular_width=.1)
    severities = {name: "error" for name in ["missing_courtyard", "track_not_centered_on_via",
                  "tuning_profile_track_geometries", "footprint_filters_mismatch", "footprint_type_mismatch"]}
    project = dict(meta=dict(filename="negative_startup_placement.kicad_pro", version=1),
                   board=dict(design_settings=dict(rules=rules, rule_severities=severities)),
                   net_settings=dict(classes=[dict(name="Default", clearance=.2, track_width=.2,
                                                    via_diameter=.6, via_drill=.3)]))
    (ROOT / "negative_startup_placement.kicad_pro").write_text(json.dumps(project, indent=2) + "\n")
    reloaded = pcbnew.LoadBoard(str(output))
    actual = {}
    for fp in reloaded.GetFootprints():
        actual[fp.GetReference()] = {
            p.GetNumber(): p.GetNetname() or None for p in fp.Pads() if p.GetNumber()
        }
    assert actual == expected
    result = dict(
        parts=len(actual), copper_layers=reloaded.GetCopperLayerCount(), native_pin_parity_differences=0,
        explicitly_documented_additional_physical_NC_pads=physical_nc,
        documented_manufacturer_footprint_changes=footprint_changes,
        documented_silk_marker_changes=silk_changes,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [
            Path(__file__), ROOT / "place.py", ROOT / "sources/components.json",
            ROOT / "sources/footprint-area.json", ROOT / "generated/placement.json",
        ]}, pcb_sha256=sha(output), tracks=len(list(reloaded.GetTracks())), zones=reloaded.GetAreaCount(),
        unrouted_review_only=True, electrical_placement_accepted=False,
        whole_unit_fit_verified=False, mounting_implemented=False,
        physical_qualified=False, fabrication_released=False,
    )
    (ROOT / "generated/native-pcb.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Actual native review PCB:", len(actual), "parts; exact physical-pad/net parity; unrouted")


if __name__ == "__main__":
    main()
