"""Retain original supply copper after a bounded native rounding difference.

This handles one diagnosed refill, not arbitrary changes to preserved zones.
All previously filled authored copper is copied unchanged. Only the six
declared ground-zone fills are taken from the completed native refill.
"""
import copy
import json
import shutil
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.verify_native_zone_unfracture import verify


def run():
    source = STAGING / 'two-board-power-aux-cap-ground-01'
    failed = STAGING / 'two-board-power-aux-cap-ground-filled-01'
    diagnosis = STAGING / 'two-board-aux-cap-ground-refill-diagnosis-01/native-comparison.json'
    out = STAGING / 'two-board-power-aux-cap-ground-filled-03'
    assert not out.exists()
    diagnostic = json.loads(diagnosis.read_text())
    for name, digest in diagnostic['source_sha256'].items():
        assert sha(REPO / name) == digest, name
    rows = diagnostic['unexpected_native_fill_changes']
    assert len(rows) == 1
    row = rows[0]
    uid = '0552f897-fa23-5173-9e85-a8133b7a4048'
    assert row['uuid'] == uid and row['layer'] == 'In2.Cu'
    bound = verify(row['before_polygons'], row['after_polygons'], displacement=2e-6)
    assert bound['symmetric_difference_area_mm2'] < 1e-6
    assert sorted(len(p['holes']) for p in row['before_polygons']) == sorted(len(p['holes']) for p in row['after_polygons'])
    authored = read_sexpr((source / 'power_protection.kicad_pcb').read_text())
    export = failed / 'native-zone-export.kicad_pcb'
    native = read_sexpr(export.read_text())
    filled = {str(first(z, 'uuid')[1]): z for z in children(native, 'zone')}
    manifest = json.loads((source / 'aux-cap-ground-routing.json').read_text())
    declared = set(manifest['refilled_existing_zones'])
    assert len(declared) == 6 and uid not in declared
    exact = {}; retained = []; copied = 0
    for zone in children(authored, 'zone'):
        ident = str(first(zone, 'uuid')[1])
        if children(zone, 'filled_polygon'):
            assert ident not in declared
            retained.append(ident)
            if ident != uid:
                exact[ident] = True
        else:
            assert ident in declared
            polygons = children(filled[ident], 'filled_polygon')
            assert polygons
            zone.extend(copy.deepcopy(polygons))
            copied += len(polygons)
    assert len(retained) == 41 and len(exact) == 40
    paths = [Path(__file__), diagnosis, export,
             REPO / 'hardware/fabrication/verify_native_zone_unfracture.py',
             *[p for p in source.rglob('*') if p.is_file()]]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    shutil.copytree(source, out)
    board = out / 'power_protection.kicad_pcb'
    board.write_text(sexpr(authored) + '\n')
    shutil.copy2(export, out / export.name)
    result = dict(source_sha256=hashes,
                  artifact_sha256={p.name: sha(p) for p in [board, out / export.name]},
                  filled_zones=47, new_filled_polygons=copied,
                  unchanged_existing_zone_canonical_polygon_match=exact,
                  retained_existing_zone_rounding_only={uid: bound},
                  original_fill_retained_exactly=retained,
                  native_drc_pending=True, fabrication_released=False,
                  decision='Keep all 41 original zone fills exactly; use native refill only for the six declared ground zones. The one supply-zone difference is below 2 nm and 1e-6 square mm, with unchanged component and hole counts.')
    (out / 'local-plane-fill.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(retained_original_fills=len(retained), exact_native_matches=len(exact),
                          rounding_only_difference=bound, copied_ground_polygons=copied)))


if __name__ == '__main__':
    run()
