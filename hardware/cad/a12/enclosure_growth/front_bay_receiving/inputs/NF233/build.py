"""Append the actual READY buffer/bypass without moving any parent part.

Use the embedded KiCad Python. The independent native DRC is a separate step.
"""

import hashlib
import json
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (ROOT / "handoff.json").exists()
    source = ROOT / "sources/parent.kicad_pcb"
    manifest = json.loads((ROOT / "sources/manifest.json").read_text())
    assert sha(source) == manifest["parent.kicad_pcb"]["sha256"]
    manager = pcbnew.GetSettingsManager()
    project = ROOT / "negative_startup_ready.kicad_pro"
    assert manager.LoadProject(str(project))
    board = pcbnew.LoadBoard(str(source))
    board.SetProject(manager.GetProject(str(project)))
    parent = {f.GetReference(): (f.GetValue(), f.GetPosition().x, f.GetPosition().y,
                               f.GetOrientationDegrees(), f.IsFlipped()) for f in board.GetFootprints()}
    assert len(parent) == 231 and not list(board.GetTracks())
    components = json.loads((ROOT.parent / "components.json").read_text())
    assert len(components) == 233
    names = {p["net"] for c in components for p in c["pins"] if p["net"]}
    for name in names:
        if not board.FindNet(name):
            board.Add(pcbnew.NETINFO_ITEM(board, name))
    plan = json.loads((ROOT / "sources/parent-placement.json").read_text())
    site = json.loads((ROOT / "sources/new-buffer-site.json").read_text())
    xy = site["U49_anchor_mm"]
    delta = [xy[i] - site["template_U34_anchor_mm"][i] for i in range(2)]
    cap = site["template_bypass_placement"]
    capxy = [cap["anchor_mm"][i] + delta[i] for i in range(2)]
    placement = {
        "U49": dict(anchor_mm=xy, rotation_deg=0, courtyard_rect_mm=site["best_front_courtyard"]),
        "C88": dict(side="B", anchor_mm=capxy, rotation_deg=cap["rotation_deg"], courtyard_rect_mm=site["best_back_courtyard"]),
    }
    for ref, library, alias in [
        ("U49", "NF03P_Layout.pretty", "Package_TO_SOT_SMD__SOT-363_SC-70-6_LocalSilk"),
        ("C88", "sources/footprints", "Capacitor_SMD__C_0603_1608Metric"),
    ]:
        path = ROOT / library / (alias + ".kicad_mod")
        assert path.is_file(), path
        fp = pcbnew.FootprintLoad(str(path.parent), alias)
        assert fp is not None
        board.Add(fp)
        fp.SetReference(ref)
        fp.SetValue(next(c["part"] for c in components if c["ref"] == ref))
        fp.SetFPID(pcbnew.LIB_ID("NF03P_Layout" if ref == "U49" else "NF03P_CAPTURED", alias))
        p = placement[ref]
        fp.SetPosition(pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in p["anchor_mm"])))
        if p.get("side") == "B":
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(p["rotation_deg"])
        fp.Reference().SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fp.Value().SetVisible(False)
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"]} for c in components}
    for ref in ["U5", "U6", "U11", "U12"]:
        expected[ref]["3"] = None
    for fp in board.GetFootprints():
        pins = expected[fp.GetReference()]
        assert {p.GetNumber() for p in fp.Pads() if p.GetNumber()} == set(pins)
        for pad in fp.Pads():
            if pad.GetNumber():
                name = pins[pad.GetNumber()]
                pad.SetNet(board.FindNet(name) if name else board.FindNet(0))
    for item in board.GetDrawings():
        if isinstance(item, pcbnew.PCB_TEXT) and item.GetText() == "NF03P / UNROUTED REVIEW":
            item.SetText("NF04R / UNROUTED REVIEW")
    output = ROOT / "negative_startup_ready.kicad_pcb"
    pcbnew.SaveBoard(str(output), board)
    reloaded = pcbnew.LoadBoard(str(output))
    actual = {f.GetReference(): {p.GetNumber(): p.GetNetname() or None for p in f.Pads() if p.GetNumber()} for f in reloaded.GetFootprints()}
    assert actual == expected
    for fp in reloaded.GetFootprints():
        if fp.GetReference() in parent:
            pose = (fp.GetValue(), fp.GetPosition().x, fp.GetPosition().y, fp.GetOrientationDegrees(), fp.IsFlipped())
            assert pose == parent[fp.GetReference()]
    byref = {f.GetReference(): f for f in reloaded.GetFootprints()}
    a = next(p for p in byref["U49"].Pads() if p.GetNumber() == "5").GetPosition()
    b = next(p for p in byref["C88"].Pads() if p.GetNumber() == "1").GetPosition()
    distance = math.hypot(a.x - b.x, a.y - b.y) / 1e6
    assert distance <= 1.543
    plan["placements"].update(placement)
    plan["parts"] = 233
    plan["scope"] = "NF04R READY successor; parent poses unchanged; unrouted review only"
    (ROOT / "placement.json").write_text(json.dumps(plan, indent=2) + "\n")
    report = dict(parts=233, native_pin_parity_differences=0, all231_parent_poses_and_values_preserved=True,
                  new_placements=placement, native_new_bypass_VCC_pad_separation_mm=distance,
                  source_sha256={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p) for p in [Path(__file__), source, ROOT.parent / "components.json", ROOT / "sources/new-buffer-site.json", ROOT / "sources/manifest.json"]},
                  pcb_sha256=sha(output), native_DRC_required=True, board_routed=False,
                  actual_wiring_body_mates_mounting_and_airflow_qualified=False,
                  physical_qualified=False, fabrication_released=False)
    (ROOT / "native-pcb.json").write_text(json.dumps(report, indent=2) + "\n")
    print("NF04R233-part PCB; all parent poses/values preserved; native new bypass", distance, "mm")


if __name__ == "__main__":
    main()
