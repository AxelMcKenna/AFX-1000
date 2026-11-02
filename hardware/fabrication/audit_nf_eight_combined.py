"""Audit the combined eight-layer CT and SS/TMR revision against the selected six-layer board."""
import copy
import json
from pathlib import Path
from shapely.geometry import Point
from hardware.electronics.common.sexpr import a, children, first, read_sexpr
from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import authored, geometry_delta, native_evidence_errors, sha
from hardware.fabrication.audit_single_net import open_counts
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
MOVED = {'C36', 'C38'}
VIA = 'd2790e69-30b9-4c0b-86cb-fd3a942df47c'
ALLOWED = {'/N12_BIAS_CT', '/N12_VIN_VALID_CT', '/N12_BIAS_RESET_N',
           '/N12_PERMIT_D', '/N12_BIAS_SENSE', '/N12_INTVCC', '/NF_NO_FAULT', '/N12_P03_SRC'}
ENDPOINTS = {
    'bf7499a6-796e-45e4-8ad9-c0c4d03bde95': {'start': (18.275, 24.5)},
    '4cb96cf2-0615-4350-9895-ca691a9e929e': {'start': (15.275, 24.5)},
    'baa860c9-69cf-4886-b834-3c28efcf00f1': {'start': (18.275, 27), 'end': (19.725, 27.15)},
    '64fd7125-50ed-4d8b-9f31-99bdcbe224f3': {'start': (15.275, 27)},
    'd9a824d6-0be0-4fa9-bf98-658cc9a91183': {'end': (19.725, 27.15)},
    '9d4cfde3-6b8d-4cb8-ae40-dfe8d748fd13': {'start': (19.725, 27.15)},
}


def verify_geometry(before, after, removed):
    expected = copy.deepcopy(before)
    def layer_map(node):
        if isinstance(node, list): return [layer_map(v) for v in node]
        return 'In6.Cu' if node == 'In4.Cu' else node
    expected = layer_map(expected)
    layers = first(expected, 'layers')
    plane = next(n for n in layers if isinstance(n, list) and n[1] == 'In6.Cu')
    plane[0] = a(14)
    index = layers.index(plane)
    layers[index:index] = [[a(10), 'In4.Cu', a('signal')], [a(12), 'In5.Cu', a('signal')]]
    for f in children(expected, 'footprint'):
        ref = next(p[2] for p in children(f, 'property') if p[1] == 'Reference')
        if ref in MOVED: first(f, 'at')[1] = a(float(first(f, 'at')[1]) - .6)
    old_tracks = {first(n, 'uuid')[1]: n for tag in ['segment','via'] for n in children(before, tag)}
    assert len(removed) == 49 and len({first(n, 'uuid')[1] for n in removed}) == 49
    for node in removed:
        key = first(node, 'uuid')[1]
        assert old_tracks[key] == node and first(node, 'net')[-1] in ALLOWED
        expected.remove(next(n for n in children(expected, node[0]) if first(n, 'uuid')[1] == key))
    for n in children(expected, 'segment'):
        for end, xy in ENDPOINTS.get(first(n, 'uuid')[1], {}).items():
            first(n, end)[1:] = [a(v) for v in xy]
    v = next(v for v in children(expected, 'via') if first(v, 'uuid')[1] == VIA)
    first(v, 'at')[1:] = [a(19.725), a(27.15)]
    delta = geometry_delta(expected, after)
    assert delta['other_root_geometry_exact']
    assert not any(delta['footprint'].values())
    assert not delta['zone']['changed'] and not delta['zone']['removed']
    assert len(delta['zone']['added']) == 12
    old_keepouts = [z for z in children(before, 'zone') if children(z, 'keepout') and children(z, 'layer') and first(z, 'layer')[1] == 'In3.Cu']
    def unlabel(z): return authored([v for v in z if not (isinstance(v, list) and v[0] in {'uuid', 'layer'})])
    zones = {first(z, 'uuid')[1]: z for z in children(after, 'zone')}
    for layer in ['In4.Cu', 'In5.Cu']:
        added = [zones[k] for k in delta['zone']['added'] if first(zones[k], 'layer')[1] == layer]
        assert sorted(map(unlabel, added)) == sorted(map(unlabel, old_keepouts))
    for tag in ['segment', 'via']:
        assert not delta[tag]['changed'] and not delta[tag]['removed']
        new = {first(n, 'uuid')[1]: n for n in children(after, tag)}
        for key in delta[tag]['added']:
            n = new[key]; net = first(n, 'net')[-1]
            assert net in ALLOWED
            if tag == 'segment':
                assert float(first(n, 'width')[1]) >= (.2 if net in {'/N12_BIAS_SENSE', '/N12_INTVCC', '/N12_PERMIT_D', '/NF_NO_FAULT', '/N12_P03_SRC'} else .16)
            else:
                assert float(first(n, 'size')[1]) == .6 and float(first(n, 'drill')[1]) == .3
    return geometry_delta(before, after)


def verify_connections(before, after):
    pads = [{(o['ref'], o['pin']): o for o in c['objects'] if o['kind'] == 'PAD'} for c in [before, after]]
    assert pads[0].keys() == pads[1].keys()
    partitions = {}
    for key, pad in pads[0].items():
        assert pad['net'] == pads[1][key]['net']
        # Include the moved bypass pads too: no pre-existing pad relationship may split.
        partitions.setdefault((pad['net'], pad['group']), []).append(key)
    for keys in partitions.values():
        assert len({pads[1][key]['group'] for key in keys}) == 1, keys
    for cap, owner in [('C8', 'U21'), ('C10', 'U20'), ('C35', 'U26'), ('C37', 'U25')]:
        for cp, ip in [('1', '5'), ('2', '2')]:
            x, y = pads[1][cap, cp], pads[1][owner, ip]
            assert x['net'] == y['net'] and x['group'] == y['group']
            if cp == '2': assert x['net'] in {'/N12_P03_SRC', '/N19_P03_SRC'}
    return True


def drill_screen(before, after, capture):
    old = {first(v, 'uuid')[1]: v for v in children(before, 'via')}
    new = {first(v, 'uuid')[1]: v for v in children(after, 'via')}
    pads = [o for o in capture['objects'] if o['kind'] == 'PAD' and not any(o['drill_mm']) and o['layers']]
    polygons = [shape([p for layer in o['layers'].values() for p in layer]) for o in pads]
    rows = []
    moved_rows = []
    for key, node in new.items():
        point = Point([float(v) for v in first(node, 'at')[1:3]])
        radius = float(first(node, 'drill')[1]) / 2
        changed = key not in old or first(old[key], 'at') != first(node, 'at')
        if changed:
            gaps = [point.distance(p) - radius for p in polygons]
            i = min(range(len(gaps)), key=gaps.__getitem__)
            rows.append(dict(uuid=key, new=key not in old, nearest_SMD=f"{pads[i]['ref']}.{pads[i]['pin']}", gap_mm=gaps[i]))
        for pad, polygon in zip(pads, polygons):
            if pad['ref'] in MOVED:
                moved_rows.append(dict(via=key, pad=f"{pad['ref']}.{pad['pin']}", gap_mm=point.distance(polygon)-radius))
    assert len(rows) >= 8 and min(r['gap_mm'] for r in rows) >= .1
    assert min(r['gap_mm'] for r in moved_rows) >= .1
    return dict(new_and_moved_vias=rows, minimum_new_or_moved_via_gap_mm=min(r['gap_mm'] for r in rows),
                closest_via_to_shifted_bypass_land=min(moved_rows, key=lambda r:r['gap_mm']),
                all_other_legacy_vias_qualified=False, mask_stencil_process_accepted=False)


def removed_from_source(before):
    ct=ROOT/'staging/nf-ct-cell-prepare-01/construction.json'
    repairs=ROOT/'staging/nf-eight-conflict-prepared-01/construction.json'
    source_ids={first(n,'uuid')[1] for tag in ['segment','via'] for n in children(before,tag)}
    nodes=json.loads(ct.read_text())['removed_segments']
    nodes += [n for n in json.loads(repairs.read_text())['removed_route_objects'] if first(n,'uuid')[1] in source_ids]
    return nodes,[ct,repairs]


def run():
    folders=[ROOT/'staging'/n for n in ['nf-softstart-cell-native-02','nf-eight-combined-native-02']]
    projects=[f/'negative_startup_physical.kicad_pro' for f in folders]
    for p in projects:
        r=json.loads((p.parent/'review.json').read_text());assert not native_evidence_errors(p,r)
        assert r['status']['counts']['violations']==r['status']['counts']['schematic_parity']==0
        assert r['status']['counts']['erc']==2
    assert sha(projects[0])==sha(projects[1])
    boards=[read_sexpr(p.with_suffix('.kicad_pcb').read_text()) for p in projects]
    removed,receipts=removed_from_source(boards[0]);delta=verify_geometry(*boards,removed)
    parts=[netlist(f/'netlist.xml') for f in folders]
    assert parts[0][1]==parts[1][1] and parts[0][0].keys()==parts[1][0].keys()
    assert all(parts[0][0][r].findtext(k)==parts[1][0][r].findtext(k) for r in parts[0][0] for k in ['value','footprint'])
    paths=[ROOT/'staging'/n/'capture.json' for n in ['nf-softstart-cell-inputs-163','nf-eight-combined-inputs-161']]
    captures=[json.loads(p.read_text()) for p in paths]
    for c,p in zip(captures,projects):
        assert all(sha(Path(k))==h for k,h in c['source_sha256'].items())
        assert str(p.with_suffix('.kicad_pcb')) in c['source_sha256']
    verify_connections(*captures)
    # In addition to all four CT cells, the newer SS/TMR cells must stay complete.
    pads={(o['ref'],o['pin']):o for o in captures[1]['objects'] if o['kind']=='PAD'}
    for cap,pin in [('C53','19'),('C54','20')]:
        assert pads[cap,'1']['net']==pads['U23',pin]['net'] and pads[cap,'1']['group']==pads['U23',pin]['group']
        assert pads[cap,'2']['net']==pads['U23','23']['net']=='/N12_P03_SRC' and pads[cap,'2']['group']==pads['U23','23']['group']
    counts=[open_counts(json.loads((f/'drc.json').read_text())) for f in folders]
    assert (sum(counts[0].values()),sum(counts[1].values()))==(163,161)
    assert all(counts[1][n]<=counts[0][n] for n in counts[0].keys()|counts[1].keys())
    drilling=drill_screen(*boards,captures[1])
    inputs=[Path(__file__),ROOT/'audit_candidate.py',ROOT/'audit_single_net.py',ROOT/'route_nf_surface.py',*receipts,*paths,*projects,*[p.with_suffix('.kicad_pcb') for p in projects],*[f/n for f in folders for n in ['review.json','drc.json','erc.json','netlist.xml']]]
    output=folders[1]/'combined-cell-audit.json';assert not output.exists()
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},geometry_delta=delta,
        all_previous_pad_connections_preserved=True,circuit_and_project_rules_exact=True,
        all_four_CT_and_both_SS_TMR_cells_connected=True,local_reference_groups_preserved=True,
        no_per_net_regressions=True,opens_before=163,opens_after=161,drill_screen=drilling,
        original_outline_and_nominal_thickness_exact=True,old_AUX_plane_mapped_to_In6=True,
        new_signal_layers=['In4.Cu','In5.Cu'],matching_keepouts_extended=True,
        material_stack_accepted=False,timing_noise_PDN_and_receiving_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Verified combined trial: 163 -> 161, all previous pad connections preserved; minimum drill gap',drilling['minimum_new_or_moved_via_gap_mm'])


if __name__=='__main__':run()

