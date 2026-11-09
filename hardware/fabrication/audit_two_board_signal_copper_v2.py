"""Native physical connection regression audit, including the failed plane trial."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, SOURCES, sha

OUT = STAGING / "two-board-signal-routed-native-03"


def audit():
    assert sys.platform == "linux"
    import pcbnew
    paths = [Path(__file__)]
    boards = []  # Keep native parents alive while examining SWIG objects.

    def load(path):
        paths.append(path)
        board = pcbnew.LoadBoard(str(path))
        board.BuildConnectivity()
        board.GetConnectivity().RecalculateRatsnest()
        boards.append(board)
        return board

    def groups(board, prefix="", delta=(0, 0), select=None):
        pads = {}
        keys = {}
        for f in board.GetFootprints():
            ref = f.GetReference()
            if select and not ref.startswith(select):
                continue
            for p in f.Pads():
                if not p.GetNumber() or not p.GetNetname():
                    continue
                pos = p.GetPosition()
                key = (prefix + ref, p.GetNumber(), round(pcbnew.ToMM(pos.x)-delta[0], 6), round(pcbnew.ToMM(pos.y)-delta[1], 6))
                ident = p.m_Uuid.AsString()
                pads[ident] = p
                keys[ident] = key
        remaining, result = set(pads), []
        conn = board.GetConnectivity()
        while remaining:
            ident = min(remaining)
            members = ({ident} | {v.m_Uuid.AsString() for v in conn.GetConnectedItems(pads[ident])}) & set(pads)
            assert members
            result.append(frozenset(keys[k] for k in members))
            remaining -= members
        return result

    def copper(board, delta=(0, 0)):
        result = Counter()
        for t in board.GetTracks():
            start, end = t.GetStart(), t.GetEnd()
            pts = tuple(round(pcbnew.ToMM(v)-delta[i % 2], 6) for i, v in enumerate([start.x, start.y, end.x, end.y]))
            kind = t.GetClass()
            layer = board.GetLayerName(t.GetLayer())
            drill = pcbnew.ToMM(t.GetDrillValue()) if kind == "PCB_VIA" else None
            result[(kind, pts, layer, round(pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if kind == "PCB_VIA" else t.GetWidth()), 6), drill)] += 1
        return result

    final = load(OUT / "signal_main.kicad_pcb")
    failed = load(STAGING / "two-board-signal-routed-native-02/signal_main.kicad_pcb")
    evidence, source_copper, all_regressions = [], Counter(), []
    for role, delta in [("A", (30, 42)), ("D", (184, 44))]:
        folder, name, _ = SOURCES[role]
        original = load(folder / (name + ".kicad_pcb"))
        old = groups(original, prefix=role + "_")
        current = groups(final, delta=delta, select=role + "_")
        bad = groups(failed, delta=delta, select=role + "_")
        regressions = [sorted(g) for g in old if not any(g <= v for v in current)]
        bad_regressions = [g for g in old if not any(g <= v for v in bad)]
        assert set.union(*map(set, old)) == set.union(*map(set, current)), role
        source_copper.update(copper(original, delta=(-delta[0], -delta[1])))
        all_regressions.extend(regressions)
        evidence.append(dict(role=role, source_pad_groups=len(old), final_pad_groups=len(current),
            source_pad_instances=sum(map(len, old)), regressed_groups=regressions,
            rejected_plane_trial_regressed_groups=len(bad_regressions)))
    copper_delta = dict(missing=sum((source_copper-copper(final)).values()), extra=sum((copper(final)-source_copper).values()))
    assert not any(copper_delta.values()), copper_delta
    assert not all_regressions
    assert sum(r["rejected_plane_trial_regressed_groups"] for r in evidence) > 0
    erc_path, drc_path = OUT / "erc.json", OUT / "drc.json"
    paths += [erc_path, drc_path, OUT / "netlist.xml", OUT / "review.json",
              STAGING / "two-board-signal-native-03/circuit-audit.json",
              STAGING / "two-board-signal-copper-04/construction.json",
              REPO / "hardware/fabrication/native_two_board_signal_v3.py"]
    erc, drc = json.loads(erc_path.read_text()), json.loads(drc_path.read_text())
    assert not drc["violations"] and not [v for s in erc["sheets"] for v in s.get("violations", [])]
    assert len(drc["schematic_parity"]) == 1 and drc["schematic_parity"][0]["type"] == "missing_footprint"
    assert not erc["ignored_checks"] and not drc["ignored_checks"]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        source_connection_retention=evidence, source_track_and_via_geometry_delta=copper_delta,
        rejected_plane_conversion_detected=True,
        via_width_API_has_explicit_front_layer=True,
        supersedes="copper-retention.json: first audit used deprecated layerless via-width API",
        final_opens=final.GetConnectivity().GetUnconnectedCount(False),
        source_opens=235, new_shared_nets=16, expected_final_opens=251,
        copper_objects=len(list(final.GetTracks())),
        source_connections_preserved=True, geometry_findings=0, erc_findings=0,
        missing_footprint="A_U201", fabrication_released=False)
    assert result["final_opens"] == result["expected_final_opens"]
    with (OUT / "copper-retention-v2.json").open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "source_sha256"}))


if __name__ == "__main__":
    audit()
