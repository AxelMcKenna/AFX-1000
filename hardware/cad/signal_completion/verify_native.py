"""Native isolated acceptance for a surface routing candidate; never edit a baseline."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

assert sys.platform == 'linux'
import pcbnew
from hardware.electronics.common.sexpr import children, read_sexpr, sexpr
from hardware.fabrication.capture_partial_board import polygons

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'hardware/cad/two_board_sensor_05/signal_dac/native-r148'
CANDIDATE, OUTPUT = (Path(v) for v in sys.argv[1:])
assert OUTPUT.is_dir() and not list(OUTPUT.iterdir())
manifest = json.loads((CANDIDATE / 'routing.json').read_text())
for name, expected in manifest['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, ('stale source', name)
assert hashlib.sha256((CANDIDATE / 'signal_main.kicad_pcb').read_bytes()).hexdigest() == manifest['candidate_sha256']
for path in BASE.iterdir():
    if path.is_file() and (path.suffix in ('.kicad_sch', '.kicad_pro', '.kicad_dru') or path.name in ('sym-lib-table', 'fp-lib-table')):
        shutil.copy2(path, OUTPUT / path.name)
for name in ('symbols', 'libraries'):
    if (BASE / name).is_dir():
        shutil.copytree(BASE / name, OUTPUT / name)
path = OUTPUT / 'signal_main.kicad_pcb'
shutil.copy2(CANDIDATE / path.name, path)
board = pcbnew.LoadBoard(str(path))
board.BuildConnectivity()
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path), board)
for label, args in (
    ('netlist', ['sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(OUTPUT / 'netlist.xml'), str(OUTPUT / 'signal_main.kicad_sch')]),
    ('erc', ['sch', 'erc', '--severity-all', '--format', 'json', '-o', str(OUTPUT / 'erc.json'), str(OUTPUT / 'signal_main.kicad_sch')]),
    ('drc', ['pcb', 'drc', '--severity-all', '--schematic-parity', '--format', 'json', '-o', str(OUTPUT / 'drc.json'), str(path)]),
):
    result = subprocess.run(['kicad-cli', *args], capture_output=True, text=True, timeout=90)
    (OUTPUT / (label + '.log')).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (label, result.stdout, result.stderr)
drc = json.loads((OUTPUT / 'drc.json').read_text())
erc = json.loads((OUTPUT / 'erc.json').read_text())
old_drc = json.loads((BASE / 'drc.json').read_text())
assert not drc['ignored_checks'] and not erc['ignored_checks']
assert not any(row['violations'] for row in erc['sheets'])
assert drc['schematic_parity'] == old_drc['schematic_parity']

def nets(path):
    tree = ET.parse(path)
    return {net.attrib['name']: sorted((n.attrib['ref'], n.attrib['pin']) for n in net.findall('node'))
            for net in tree.findall('./nets/net')}

assert nets(OUTPUT / 'netlist.xml') == nets(BASE / 'netlist.xml')

def objects(path, fills=False):
    rows = {}
    for node in read_sexpr(path.read_text())[1:]:
        if not isinstance(node, list):
            continue
        uid = children(node, 'uuid')
        if not uid:
            continue
        if not fills and node[0] == 'zone':
            node = [v for v in node if not (isinstance(v, list) and v and v[0] == 'filled_polygon')]
        rows[uid[0][1]] = sexpr(node)
    return rows

before, after = objects(BASE / path.name), objects(path)
assert all(after.get(k) == v for k, v in before.items()), 'old authored object changed'
expected_added = {uid for route in manifest['routes'] for uid in route['segment_uuids']}
assert set(after) - set(before) == expected_added, 'unexpected added objects'
filled_before, filled_after = objects(BASE / path.name, True), objects(path, True)
changed_fills = [k for k in before if filled_before[k] != filled_after[k]]
conn = board.GetConnectivity()
conn.RecalculateRatsnest()
native_opens = conn.GetUnconnectedCount(False)
assert native_opens == len(drc['unconnected_items'])
# Capture actual new copper and actual filled references for independent host audit.
rows = []
for item in board.GetTracks():
    if item.m_Uuid.AsString() not in expected_added:
        continue
    layer = item.GetLayer()
    poly = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(.001), pcbnew.ERROR_OUTSIDE)
    poly.Simplify()
    rows.append({'uuid': item.m_Uuid.AsString(), 'net': item.GetNetname(),
                 'layer': board.GetLayerName(layer), 'polygons': polygons(poly)})
fields = []
for zone in board.Zones():
    if zone.GetIsRuleArea() or zone.GetNetname() != 'LINK_AGND':
        continue
    for name in ('In1.Cu', 'In2.Cu', 'In4.Cu', 'In6.Cu'):
        layer = board.GetLayerID(name)
        if zone.IsOnLayer(layer):
            poly = pcbnew.SHAPE_POLY_SET(zone.GetFilledPolysList(layer))
            poly.Unfracture()
            fields.append({'uuid': zone.m_Uuid.AsString(), 'layer': name, 'polygons': polygons(poly)})
# Every old native connectivity group must survive, and different net labels
# cannot merge except the existing explicit net-tie joins.
old_board = pcbnew.LoadBoard(str(BASE / path.name))
old_board.BuildConnectivity()
old_conn = old_board.GetConnectivity()
old_items = {i.m_Uuid.AsString(): i for i in list(old_board.GetTracks()) + [p for f in old_board.GetFootprints() for p in f.Pads()]}
new_items = {i.m_Uuid.AsString(): i for i in list(board.GetTracks()) + [p for f in board.GetFootprints() for p in f.Pads()]}
checked = set()
for uid, item in old_items.items():
    if uid in checked or item.GetClass() != 'PAD' or not item.GetNetname():
        continue
    old_group = {uid} | {i.m_Uuid.AsString() for i in old_conn.GetConnectedItems(item)}
    new_group = {uid} | {i.m_Uuid.AsString() for i in conn.GetConnectedItems(new_items[uid])}
    assert old_group <= new_group, ('lost original connection', uid)
    checked |= old_group
report = {'native_version': pcbnew.GetBuildVersion(), 'native_opens': native_opens,
          'expected_opens': manifest['expected_opens'], 'violations': drc['violations'],
          'erc_findings': [], 'original_objects_preserved': len(before),
          'original_connectivity_preserved': True, 'changed_filled_zone_uuids': changed_fills,
          'schematic_parity': drc['schematic_parity'], 'added_copper': rows, 'reference_fields': fields,
          'pcb_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [Path(__file__), CANDIDATE / 'routing.json', BASE / path.name]},
          'fabrication_released': False}
(OUTPUT / 'native-review.json').write_text(json.dumps(report, separators=(',', ':')) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('added_copper', 'reference_fields', 'source_sha256')}), flush=True)
assert not drc['violations'], 'native geometry findings'
assert native_opens == manifest['expected_opens'], 'unexpected connectivity result'
