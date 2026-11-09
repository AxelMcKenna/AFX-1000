"""Capture exact unexpected native refill changes without accepting them."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.fill_two_board_power_zones_v2 import canonical
from hardware.fabrication.capture_partial_board import polygons


def run():
    import pcbnew
    source=STAGING/'two-board-power-nf-pin-escape-rework-01/power_protection.kicad_pcb'
    filled=STAGING/'two-board-power-nf-pin-escape-rework-filled-01/native-zone-export.kicad_pcb'
    manifest=source.parent/'nf-pin-escape-routing.json'
    skipped=set(json.loads(manifest.read_text())['refilled_existing_zones'])
    old=pcbnew.LoadBoard(str(source));new=pcbnew.LoadBoard(str(filled));zs={z.m_Uuid.AsString():z for z in new.Zones()};rows=[]
    for z in old.Zones():
        uid=z.m_Uuid.AsString()
        if uid in skipped:continue
        snapshots=[]
        for item in [z,zs[uid]]:
            p=pcbnew.SHAPE_POLY_SET(item.GetFilledPolysList(item.GetLayer()));p.Unfracture();snapshots.append(polygons(p))
        if canonical(snapshots[0])==canonical(snapshots[1]):continue
        rows.append(dict(uuid=uid,layer=old.GetLayerName(z.GetLayer()),before_polygons=snapshots[0],after_polygons=snapshots[1]))
    sources=[Path(__file__),source,filled,manifest,REPO/'hardware/fabrication/fill_two_board_power_zones_v2.py',REPO/'hardware/fabrication/capture_partial_board.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},unexpected_native_fill_changes=rows,accepted=False,fabrication_released=False)
    out=STAGING/'two-board-nf-pin-escape-refill-diagnosis-01';out.mkdir(exist_ok=False)
    (out/'native-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(uuid=r['uuid'],layer=r['layer']) for r in rows]))


if __name__=='__main__':run()
