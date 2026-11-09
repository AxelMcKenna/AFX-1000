"""Read-only diagnosis of native zone area before and after unfracturing."""
import json
import sys
from pathlib import Path
from hardware.fabrication.capture_partial_board import polygons
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    assert sys.platform == 'linux'
    import pcbnew
    source = STAGING/'two-board-power-aux-ground-native-01/power_protection.kicad_pcb'
    out = STAGING/'two-board-aux-unfracture-review-01'
    assert not out.exists()
    board = pcbnew.LoadBoard(str(source))
    rows = []
    for z in board.Zones():
        p = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()))
        oldarea = p.Area()/1e12
        old = polygons(p)
        p.Unfracture()
        newarea = p.Area()/1e12
        row = dict(uuid=z.m_Uuid.AsString(), layer=board.GetLayerName(z.GetLayer()),
                   before_area_mm2=oldarea, after_area_mm2=newarea,
                   delta_mm2=newarea-oldarea, before=old, after=polygons(p))
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ['before','after']}), flush=True)
    out.mkdir()
    (out/'diagnostic.json').write_text(json.dumps(dict(
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),source]},
        zones=rows,diagnostic_only=True,fabrication_released=False),indent=2)+'\n')


if __name__ == '__main__':
    run()
