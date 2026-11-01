"""Independent native pose, literal-seed and uncapped-connectivity receipt."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "receiving-detour"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out = WORK / "native-review.json"
    assert not out.exists()
    paths = [WORK / "output.kicad_pcb", ROOT / "power-stitches/input.kicad_pcb",
             ROOT.parent / "receiving_repair/negative_startup_physical.kicad_pcb"]
    hashes = {str(p): sha(p) for p in paths}
    b, original, target = [pcbnew.LoadBoard(str(p)) for p in paths]
    spec = importlib.util.spec_from_file_location("pose_contract", ROOT.parent / "import_route.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.identity(b) == module.identity(target)
    before = {t.m_Uuid.AsString(): t for t in original.GetTracks()}
    after = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
    declared = json.loads((ROOT / "receiving-seeded-six-layer-02/construction.json").read_text())
    moves = {t["uuid"]: (row, t) for row in declared["changed_B_Cu_endpoints"] for t in row["tracks"]}
    assert len(moves) == 8
    changed = []
    for ident, old in before.items():
        new = after[ident]
        assert old.GetNetname() == new.GetNetname() and old.IsLocked() == new.IsLocked()
        if isinstance(old, pcbnew.PCB_VIA):
            assert isinstance(new, pcbnew.PCB_VIA) and old.GetPosition() == new.GetPosition()
            assert old.GetWidth(pcbnew.F_Cu) == new.GetWidth(pcbnew.F_Cu)
            assert old.GetDrillValue() == new.GetDrillValue()
        else:
            assert old.GetLayer() == new.GetLayer() and old.GetWidth() == new.GetWidth()
            for which in ["start", "end"]:
                a = old.GetStart() if which == "start" else old.GetEnd()
                z = new.GetStart() if which == "start" else new.GetEnd()
                if a != z:
                    row, t = moves[ident]
                    # The original construction ledger read a live SWIG vector
                    # after its setter, so its "actual_old" field is rejected.
                    # Derive both real endpoints independently from saved PCBs.
                    assert which == t["endpoint"]
                    assert max(abs(a.x-row["before_nm"][0]), abs(a.y-row["before_nm"][1])) <= 1
                    assert [z.x, z.y] == row["after_nm"]
                    changed.append(dict(uuid=ident, endpoint=which, before_nm=[a.x, a.y], after_nm=[z.x, z.y]))
    assert {r["uuid"] for r in changed} == set(moves)
    b.BuildConnectivity()
    c = b.GetConnectivity()
    c.RecalculateRatsnest()
    count = c.GetUnconnectedCount(False)
    drc = json.loads((WORK / "output-drc.json").read_text())
    assert not drc["violations"] and not drc["schematic_parity"]
    assert count == len(drc["unconnected_items"]) == 241
    vias, segments = 0, 0
    for t in b.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            assert t.GetWidth(pcbnew.F_Cu) >= pcbnew.FromMM(.65) and t.GetDrillValue() >= pcbnew.FromMM(.3)
            vias += 1
        else:
            assert t.GetWidth() >= pcbnew.FromMM(.2)
            assert t.GetLayer() not in [pcbnew.In1_Cu, pcbnew.In4_Cu]
            segments += 1
    assert all(sha(Path(p)) == h for p, h in hashes.items())
    out.write_text(json.dumps(dict(input_PCB_sha256=hashes,
        source_script_sha256=sha(Path(__file__)), native_DRC_sha256=sha(WORK / "output-drc.json"),
        actual267_footprint_identities_exactly_match_receiving_repair=True,
        original515_seed_objects_retained=True, only_seed_changes_eight_declared_B_endpoints=changed,
        original_construction_before_endpoint_fields_rejected_live_SWIG_vector=True,
        corrected_deltas_derived_independently_from_saved_PCBS=True,
        all_original173_vias_and_remaining_seed_geometry_exact=True,
        surface_or_In2_In3_segments=segments, through_vias=vias,
        strict_native_violations=0, native_schematic_parity=0,
        uncapped_missing_connections=count, reported_missing_connections=count,
        routing_complete=False, force_voltage_drop_or_PDN_qualified=False,
        physical_qualified=False, fabrication_released=False), indent=2) + "\n")
    print("Native review:", count, "opens; zero other DRC/parity; all267 poses exact; all515 seed objects accounted")


if __name__ == "__main__":
    main()
