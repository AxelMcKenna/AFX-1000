"""Retain raw full-shell and board seating witnesses; never call them empty passes."""
import json
import math
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w

HERE = Path(__file__).resolve().parent

def run():
    data, parts, _, _ = w.load_manifest(HERE / 'hardware-candidate.json')
    w.assert_current({'sources': data['_loaded_sources']})
    boards = w.board_state(data)
    assert boards['geometry_fresh']
    identities = []
    for name in ['panel_touch_hardware_r26', 'cooling_shell', 'panel_touch_c3_r25']:
        identity, _ = w.job('component', parts[name], parts)
        result, _ = w.execute('component', parts[name], parts, expected=identity)
        assert result['passed'] and not result['runtime_failure'], name
        identities.append(identity)
    rows = []
    for name, left, other, z in [
            ('hardware_shell_seat', 'panel_touch_hardware_r26', 'cooling_shell', 4.8),
            ('hardware_board_seat', 'panel_touch_hardware_r26', 'panel_touch_c3_r25', 21.6),
            ('board_shell_seat', 'panel_touch_c3_r25', 'cooling_shell', 20.0)]:
        check = dict(id=name, left=[left], right=[other], expect='empty')
        identity, folder = w.job('check', check, parts)
        result, reused = w.execute('check', check, parts, expected=identity)
        assert not result['runtime_failure'], name
        out = HERE / name
        out.mkdir(exist_ok=True)
        for file in folder.iterdir():
            if file.name in ['result.json', 'geometry.scad', 'geometry.stl', 'native.log']:
                target = out / file.name
                if target.exists():
                    assert target.read_bytes() == file.read_bytes()
                else:
                    target.write_bytes(file.read_bytes())
        m = result['mesh']
        planar = (not result['passed'] and m['min_mm'][2] == m['max_mm'][2] and math.isclose(m['min_mm'][2], z, abs_tol=1e-5))
        rows.append(dict(check=name, expected_seat_z=z, exact_planar_seat=planar,
                         native_empty_pass=result['passed'], mesh=m, identity=identity, cached=reused))
        identities.append(identity)
        print(name, 'exact planar seat' if planar else 'UNRESOLVED WITNESS', flush=True)
    for identity in identities:
        w.assert_current(identity)
    w.assert_current({'sources': data['_loaded_sources']})
    w.assert_current({'sources': boards['source_sha256']})
    (HERE / 'seat-review.json').write_text(json.dumps(dict(results=rows, snapshot_sha256=data['_loaded_sources'],
                                                         reviewer_sha256={w.relative(Path(__file__)): w.sha(Path(__file__))},
                                                         seat_contacts_not_empty_passes=True, physical_qualified=False), indent=2) + '\n')
    assert all(r['exact_planar_seat'] for r in rows), 'Inspect retained non-planar or absent contact'

if __name__ == '__main__':
    run()
