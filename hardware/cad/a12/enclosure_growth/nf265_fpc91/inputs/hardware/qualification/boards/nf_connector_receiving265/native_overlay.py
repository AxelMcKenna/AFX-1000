"""NEW native v2 port/strain-hole fixture; original v1 is retained."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def vec(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def build(out):
    if out.exists():
        raise RuntimeError("Fresh v2 native fixture required")
    plan = json.loads((ROOT / "ports-v2.json").read_text())
    source = ROOT / "prototype-v1/NC265_connector_prototype.kicad_pcb"
    board = pcbnew.LoadBoard(str(source))
    fp = next(f for f in board.GetFootprints() if f.GetReference() == "J4")
    fp.SetPosition(vec(79, 21))
    lib = out / "MechanicalCandidates.pretty"
    lib.mkdir(parents=True)
    text = """(footprint "NC265_Strain_M2_NPTH_D2p6_R3p5" (version 20241229) (generator "NC265") (layer "F.Cu")
 (attr exclude_from_pos_files exclude_from_bom)
 (property "Reference" "H?" (at 0 -4) (layer "F.SilkS") (effects (font (size 1 1)(thickness .15))))
 (property "Value" "STRAIN_NPTH" (at 0 4) (layer "F.Fab") (effects (font (size 1 1)(thickness .15))))
 (fp_circle (center 0 0) (end 3.5 0) (stroke (width .05)(type solid)) (fill none) (layer "F.CrtYd"))
 (pad "" np_thru_hole circle (at 0 0) (size 2.6 2.6) (drill 2.6) (layers "*.Cu" "*.Mask"))
)\n"""
    file = lib / "NC265_Strain_M2_NPTH_D2p6_R3p5.kicad_mod"
    file.write_text(text)
    for ref, u in [("H101", 61), ("H102", 90)]:
        fp = pcbnew.FootprintLoad(str(lib), file.stem)
        board.Add(fp)
        fp.SetReference(ref)
        fp.SetValue("STRAIN_NPTH")
        fp.SetPosition(vec(u, 21))
        fp.SetFPID(pcbnew.LIB_ID("NC265Mechanical", file.stem))
        for layer in [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]:
            z = pcbnew.ZONE(board)
            z.SetLayer(layer)
            z.SetIsRuleArea(True)
            for method in [
                "SetDoNotAllowPads",
                "SetDoNotAllowTracks",
                "SetDoNotAllowVias",
                "SetDoNotAllowZoneFills",
            ]:
                getattr(z, method)(True)
            poly = z.Outline()
            poly.NewOutline()
            r = 3.7 / math.cos(math.pi / 128)
            for n in range(128):
                poly.Append(
                    pcbnew.FromMM(u + r * math.cos(n * 2 * math.pi / 128)),
                    pcbnew.FromMM(21 + r * math.sin(n * 2 * math.pi / 128)),
                )
            board.Add(z)
    filename = out / "NC265_ports_strain_v2.kicad_pcb"
    if not pcbnew.SaveBoard(str(filename), board):
        raise ValueError("Native save failed")
    (out / "fp-lib-table").write_text(
        '(fp_lib_table (lib(name "NC265")(type "KiCad")(uri "'
        + str(ROOT / "ConnectorCandidates.pretty")
        + '")(options "")(descr "candidate ports"))(lib(name "NC265Mechanical")(type "KiCad")(uri "'
        + str(lib)
        + '")(options "")(descr "strain receiving holes")))\n'
    )
    loaded = pcbnew.LoadBoard(str(filename))
    actual = {}
    for f in loaded.GetFootprints():
        actual[f.GetReference()] = {
            p.GetNumber(): dict(
                net=p.GetNetname() or None,
                at_mm=[pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)],
                drill_mm=pcbnew.ToMM(p.GetDrillSize().x),
                size_mm=[pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)],
            )
            for p in f.Pads()
        }
    for port in plan["ports"]:
        if {n: p["net"] for n, p in actual[port["ref"]].items()} != port["physical_pads"]:
            raise ValueError("Actual v2 physical pin mismatch")
    if len(actual) != 8 or len(list(loaded.Zones())) != 24:
        raise ValueError("Incomplete actual v2 fixture")
    report = dict(
        revision="NC265-actual-native-port-overlay",
        KiCad_version=pcbnew.Version(),
        actual=actual,
        PCB_sha256=sha(filename),
        source_sha256={str(p): sha(p) for p in [Path(__file__), ROOT / "ports-v2.json", source]},
        actual_Cu_layers=4,
        actual_clip_KOs=16,
        actual_strain_KOs=8,
        actual_np_through_pads=2,
        source_port_pads=40,
        full265_board_completed=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "native-overlay.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(actual_FPs=8, ports=6, source_pad_parity_errors=0, actual_KOs=24)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output.resolve())
