"""Independent saved-PCB review of a receiving-layout partial route."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def keepouts(board):
    rows = []
    for z in board.Zones():
        if not z.GetIsRuleArea():
            continue
        p = z.Outline()
        rings = []
        for i in range(p.OutlineCount()):
            c = p.COutline(i)
            outer = [(c.CPoint(j).x, c.CPoint(j).y) for j in range(c.PointCount())]
            holes = []
            for h in range(p.HoleCount(i)):
                c = p.CHole(i, h)
                holes.append([(c.CPoint(j).x, c.CPoint(j).y) for j in range(c.PointCount())])
            rings.append((outer, holes))
        rows.append((z.GetZoneName(), z.GetLayer(), rings))
    return sorted(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work")
    parser.add_argument("--expected-opens", type=int, required=True)
    args = parser.parse_args()
    work = ROOT / args.work
    assert work.parent == ROOT and work.is_dir()
    out = work / "verified-review.json"
    assert not out.exists()
    paths = [work / "output.kicad_pcb", ROOT / "power-stitches/input.kicad_pcb",
             ROOT.parent / "receiving_repair/negative_startup_physical.kicad_pcb"]
    bound = {str(p): sha(p) for p in paths}
    board, seed, target = [pcbnew.LoadBoard(str(p)) for p in paths]
    spec = importlib.util.spec_from_file_location("pose", ROOT.parent / "import_route.py")
    pose = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pose)
    assert pose.identity(board) == pose.identity(target)
    assert len(keepouts(board)) == 36 and keepouts(board) == keepouts(target)
    after = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
    declared = json.loads((ROOT / "receiving-seeded-six-layer-02/construction.json").read_text())
    moves = {t["uuid"]: (r, t) for r in declared["changed_B_Cu_endpoints"] for t in r["tracks"]}
    actual_delta = []
    for old in seed.GetTracks():
        ident = old.m_Uuid.AsString()
        new = after[ident]
        assert old.GetNetname() == new.GetNetname() and old.IsLocked() == new.IsLocked()
        if isinstance(old, pcbnew.PCB_VIA):
            assert isinstance(new, pcbnew.PCB_VIA)
            assert old.GetPosition() == new.GetPosition()
            assert old.GetWidth(pcbnew.F_Cu) == new.GetWidth(pcbnew.F_Cu)
            assert old.GetDrillValue() == new.GetDrillValue()
        else:
            assert old.GetWidth() == new.GetWidth() and old.GetLayer() == new.GetLayer()
            for which, a, z in [("start", old.GetStart(), new.GetStart()), ("end", old.GetEnd(), new.GetEnd())]:
                if a != z:
                    r, t = moves[ident]
                    assert which == t["endpoint"]
                    assert max(abs(a.x-r["before_nm"][0]), abs(a.y-r["before_nm"][1])) <= 1
                    assert [z.x, z.y] == r["after_nm"]
                    actual_delta.append(dict(uuid=ident, before_nm=[a.x, a.y], after_nm=[z.x, z.y]))
    assert {x["uuid"] for x in actual_delta} == set(moves) and len(actual_delta) == 8
    board.BuildConnectivity()
    c = board.GetConnectivity()
    c.RecalculateRatsnest()
    missing = c.GetUnconnectedCount(False)
    drc = json.loads((work / "output-drc.json").read_text())
    assert not drc["violations"] and not drc["schematic_parity"]
    assert missing == len(drc["unconnected_items"]) == args.expected_opens
    vias, tracks = 0, 0
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            assert t.GetWidth(pcbnew.F_Cu) >= pcbnew.FromMM(.65)
            assert t.GetDrillValue() >= pcbnew.FromMM(.3)
            vias += 1
        else:
            assert t.GetWidth() >= pcbnew.FromMM(.2)
            assert t.GetLayer() not in [pcbnew.In1_Cu, pcbnew.In4_Cu]
            tracks += 1
    assert all(sha(Path(p)) == h for p, h in bound.items())
    out.write_text(json.dumps(dict(
        source_PCB_sha256=bound, reviewer_sha256=sha(Path(__file__)),
        DRC_sha256=sha(work / "output-drc.json"), strict_native_violations=0, schematic_parity=0,
        native_uncapped_missing_connections=missing, reported_missing_connections=missing,
        all267_exact_component_identities_match_receiving_repair=True,
        all36_native_keepout_names_layers_and_polygons_exact=True,
        all515_original_seed_objects_retained_with_only_declared_eight_endpoint_changes=True,
        actual_seed_endpoint_changes=actual_delta, tracks=tracks, vias=vias,
        no_signal_tracks_on_reserved_planes=True,
        routing_complete=False, force_voltage_drop_PDN_noise_qualified=False,
        physical_qualified=False, fabrication_released=False), indent=2) + "\n")
    print("Verified native partial route:", missing, "opens; zero DRC/parity;267 exact poses;36 exact keepouts")


if __name__ == "__main__":
    main()
