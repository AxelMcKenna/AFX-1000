"""Preserve v2 failure; exclude only the nonconductive NPTH core in NEW v3."""

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


def run(out):
    if out.exists():
        raise RuntimeError("Fresh v3 directory required")
    source = ROOT / "prototype-v2/NC265_ports_strain_v2.kicad_pcb"
    before = sha(source)
    board = pcbnew.LoadBoard(str(source))
    out.mkdir()
    excluded = 0
    for z in board.Zones():
        poly = z.Outline()
        if poly.VertexCount() != 128:
            continue
        centre = z.GetBoundingBox().GetCenter()
        u = pcbnew.ToMM(centre.x)
        v = pcbnew.ToMM(centre.y)
        if not any(abs(u - x) < 1e-5 for x in [61, 90]) or abs(v - 21) > 1e-5:
            raise ValueError("Unexpected rule centre")
        hole = poly.NewHole(0)
        r = 1.301 / math.cos(math.pi / 128)
        for i in reversed(range(128)):
            poly.Append(
                pcbnew.FromMM(u + r * math.cos(2 * math.pi * i / 128)),
                pcbnew.FromMM(v + r * math.sin(2 * math.pi * i / 128)),
                0,
                hole,
            )
        excluded += 1
    for fp in board.GetFootprints():
        if fp.GetReference() in ["H101", "H102"]:
            fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM)
    if excluded != 8:
        raise ValueError("Missing exact two-by-four strain rule areas")
    target = out / "NC265_ports_strain_v3.kicad_pcb"
    pcbnew.SaveBoard(str(target), board)
    library = ROOT / "ConnectorCandidates.pretty"
    mechanical = ROOT / "prototype-v2/MechanicalCandidates.pretty"
    (out / "fp-lib-table").write_text(
        '(fp_lib_table (version 7) (lib (name "NC265") (type "KiCad") (uri "'
        + str(library)
        + '") (options "") (descr "actualcandidateports"))(lib (name "NC265Mechanical") (type "KiCad") (uri "'
        + str(mechanical)
        + '") (options "") (descr "actualmechanicalNPTH")))\n'
    )
    mutations = {}
    for name, u in [("foreign_copper_inside_NPTH", 90), ("foreign_copper_in_strain_annulus", 93.4)]:
        b = pcbnew.LoadBoard(str(target))
        track = pcbnew.PCB_TRACK(b)
        track.SetStart(vec(u - 0.1, 21))
        track.SetEnd(vec(u + 0.1, 21))
        track.SetWidth(pcbnew.FromMM(0.3))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNet(b.FindNet("AGND"))
        b.Add(track)
        p = out / (name + ".kicad_pcb")
        pcbnew.SaveBoard(str(p), b)
        mutations[name] = dict(pcb=str(p), sha256=sha(p))
    if sha(source) != before:
        raise ValueError("Original changed")
    d = dict(
        revision="NC265-native-KO-core-repair",
        source_sha256={str(p): sha(p) for p in [Path(__file__), source, ROOT / "ports-v2.json"]},
        actual_PCB_sha256=sha(target),
        actual_strain_annulus_count=8,
        all_clip_and_outer_R3p7_KOs_preserved=True,
        actual_mechanical_holes_diameter_mm=2.6,
        omitted_nonconductive_core_radius_bound_mm=1.301 / math.cos(math.pi / 128),
        physical_hole_radius_mm=1.3,
        native_loaded_hole_clearance_mm=pcbnew.ToMM(board.GetDesignSettings().m_HoleClearance),
        no_blanket_copper_pad_exception=True,
        negative_controls=mutations,
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "repair.json").write_text(json.dumps(d, indent=2) + "\n")
    print(json.dumps(dict(actual_fixed_KOs=8, real_native_mutation_boards=2)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
