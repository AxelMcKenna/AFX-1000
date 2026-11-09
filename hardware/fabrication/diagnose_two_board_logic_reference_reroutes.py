"""Measure a reroute-only native control with every original zone retained."""
import argparse
import json
import sys
from pathlib import Path

from hardware.fabrication.capture_partial_board import polygons
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    assert sys.platform == 'linux'
    import pcbnew

    base = STAGING / 'two-board-power-startup-logic-native-02'
    candidate = STAGING / 'two-board-power-logic-references-02'
    out = STAGING / 'two-board-logic-reference-refill-diagnostic-01'
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=['reroutes_only'], required=True)
    label = parser.parse_args().case
    target = out / (label + '.json')
    assert not target.exists()
    route = json.loads((candidate / 'logic-reference-routing.json').read_text())
    new_zones = {z['uuid'] for z in route['added_zones']}
    paths = [Path(__file__), REPO / 'hardware/fabrication/capture_partial_board.py',
             candidate / 'logic-reference-routing.json']
    for folder in [base, candidate]:
        paths.extend(folder / name for name in [
            'power_protection.kicad_pcb', 'power_protection.kicad_pro',
            'power_protection.kicad_dru'])
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}

    def snapshot(board):
        result = {}
        for zone in board.Zones():
            poly = pcbnew.SHAPE_POLY_SET(zone.GetFilledPolysList(zone.GetLayer()))
            poly.Unfracture()
            result[zone.m_Uuid.AsString()] = dict(
                layer=board.GetLayerName(zone.GetLayer()), net=zone.GetNetname(),
                polygons=polygons(poly))
        return result

    out.mkdir(exist_ok=True)
    folder = base if label == 'unchanged_baseline' else candidate
    # Keep the baseline board and every original zone intact; replace only
    # the explicitly declared tracks/vias with their candidate counterparts.
    from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
    import copy
    import shutil
    original = read_sexpr((base / 'power_protection.kicad_pcb').read_text())
    changed = read_sexpr((candidate / 'power_protection.kicad_pcb').read_text())
    retired = set(route['retired_objects'])
    added = {u for r in route['routes'] for u in r['segment_uuids']} | {v['uuid'] for v in route['vias']}
    original[:] = [n for n in original if not (isinstance(n, list) and n and n[0] in ['segment', 'via'] and str(first(n, 'uuid')[1]) in retired)]
    additions = [n for n in changed if isinstance(n, list) and n and n[0] in ['segment', 'via'] and str(first(n, 'uuid')[1]) in added]
    assert len(additions) == len(added)
    original.extend(copy.deepcopy(additions))
    scratch = out / 'reroutes-only-control'
    scratch.mkdir()
    path = scratch / 'power_protection.kicad_pcb'
    path.write_text(sexpr(original) + '\n')
    for name in ['power_protection.kicad_pro', 'power_protection.kicad_dru']:
        shutil.copy2(base / name, scratch / name)
    board = pcbnew.LoadBoard(str(path))
    # Retain SWIG references while removing native objects.
    removed = []
    if label == 'candidate_without_added_zones':
        for zone in list(board.Zones()):
            if zone.m_Uuid.AsString() in new_zones:
                board.Remove(zone)
                removed.append(zone)
    before = snapshot(board)
    assert pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    after = snapshot(board)
    assert pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    second = snapshot(board)
    record = dict(label=label, before=before, after=after,
                  repeat_refill_identical=after == second)
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    with target.open('x') as f:
        json.dump(dict(source_sha256=hashes, native_version=pcbnew.GetBuildVersion(),
                       case=record, artifact_sha256={str(p.relative_to(out)): sha(p) for p in scratch.iterdir()}, fabrication_released=False), f)
    print(json.dumps(dict(case=label, repeat_refill_identical=after == second)), flush=True)


if __name__ == '__main__':
    run()
