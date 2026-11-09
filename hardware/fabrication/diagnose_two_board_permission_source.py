"""Isolate the R107 via's effect on the unchanged digital source outline."""
import copy
import json
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.capture_partial_board import polygons
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    assert sys.platform == 'linux'
    import pcbnew

    base = STAGING / 'two-board-power-startup-completion-native-06'
    candidate = STAGING / 'two-board-power-permission-native-03'
    out = STAGING / 'two-board-permission-source-diagnostic-01'
    assert not out.exists()
    out.mkdir()
    sources = [Path(__file__), REPO / 'hardware/fabrication/capture_partial_board.py',
               base / 'power_protection.kicad_pcb', base / 'power_protection.kicad_pro',
               base / 'power_protection.kicad_dru', candidate / 'power_protection.kicad_pcb',
               candidate / 'permission-routing.json']
    hashes = {str(p.relative_to(REPO)): sha(p) for p in sources}
    original = read_sexpr(sources[2].read_text())
    changed = read_sexpr((candidate / 'power_protection.kicad_pcb').read_text())
    route = json.loads((candidate / 'permission-routing.json').read_text())
    via = next(v for v in route['vias'] if v['position_mm'] == [141.55, 131.6])
    item = next(n for n in children(changed, 'via') if str(first(n, 'uuid')[1]) == via['uuid'])
    zone_id = 'de233285-cc07-5d51-9dbd-88a46856bbca'
    cases = {}
    artifacts = []
    for label in ['baseline_refill', 'R107_via_only']:
        tree = copy.deepcopy(original)
        if label == 'R107_via_only':
            tree.append(copy.deepcopy(item))
        zone = next(z for z in children(tree, 'zone') if str(first(z, 'uuid')[1]) == zone_id)
        zone[:] = [n for n in zone if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
        folder = out / label
        folder.mkdir()
        path = folder / 'power_protection.kicad_pcb'
        path.write_text(sexpr(tree) + '\n')
        for name in ['power_protection.kicad_pro', 'power_protection.kicad_dru']:
            shutil.copy2(base / name, folder / name)
        board = pcbnew.LoadBoard(str(path))
        assert pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        zone = next(z for z in board.Zones() if z.m_Uuid.AsString() == zone_id)
        poly = pcbnew.SHAPE_POLY_SET(zone.GetFilledPolysList(zone.GetLayer()))
        poly.Unfracture()
        cases[label] = dict(zone_uuid=zone_id, layer='In4.Cu', polygons=polygons(poly))
        pcbnew.SaveBoard(str(path), board)
        artifacts.extend(folder.iterdir())
        print(label + ' completed', flush=True)
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    result = dict(source_sha256=hashes,
                  artifact_sha256={str(p.relative_to(out)): sha(p) for p in artifacts if p.is_file()},
                  isolated_new_via=via, cases=cases,
                  scope='Native source-fill causality experiment; not an electrical qualification',
                  fabrication_released=False)
    (out / 'source-control.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    run()
