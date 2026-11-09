"""Screen local track rework while retaining the original R1013 placement."""
from collections import defaultdict
from shapely.geometry import box
import copy
import json
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT/'staging/digital-led35-dac-pot-inputs-33/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .01
    faces = surface.SIGNAL_LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    net = 'LED_BLANK'
    work = copy.deepcopy(cap)
    pads = [o for o in work['objects'] if o['net'] == net and o['kind'] == 'PAD']
    start = next(o for o in pads if o['ref'] == 'R1013')
    ends = [(f,o['position_mm']) for o in pads if o is not start for f in faces if o['layers'].get(f)]
    crossings = [(o['position_mm'],[f for f in faces if o['layers'].get(f)]) for o in work['objects'] if o['net'] == net and (o['kind'] == 'PCB_VIA' or o['kind'] == 'PAD' and any(o.get('drill_mm',[0,0])))]
    local = box(42,34,49,40)
    groups = defaultdict(list)
    for obj in work['objects']:
        if obj['kind'] == 'PCB_TRACK' and obj['width_mm'] == .2 and obj['net'] != net:
            if any(surface.shape(ps).intersects(local) for ps in obj['layers'].values()):
                groups[obj['net']].append(obj['uuid'])
    results = []
    for omitted_net, ids in sorted(groups.items(), key=lambda row: (len(row[1]),row[0])):
        trial = copy.deepcopy(work)
        trial['objects'] = [o for o in trial['objects'] if o['uuid'] not in ids]
        screen = DigitalViaScreen(trial, signal_layers=faces)
        result = reachability(screen, net, [('B.Cu', start['position_mm'])], ends, faces, existing_crossings=crossings)
        result.update(omitted_net=omitted_net, omitted_track_uuids=ids,
                      additional_omissions_preserve_all_pads_vias_holes_and_power_tracks=True,
                      omitted_net_restoration_not_established=True)
        results.append(result)
        print('LED_BLANK potential after omitting', len(ids), omitted_net, 'tracks:', result['connected'], flush=True)
    paths = [cp, Path(__file__)]+[ROOT/n for n in
             ('digital_xlat_escape_repair.py', 'digital_planned_region_screen.py', 'audit_candidate.py', 'digital_region_reachability.py', 'digital_via_spacing_v2.py',
              'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py', 'nf_minimum_logic.py', 'route_nf_surface.py')]
    result = dict(source_sha256={str(p):sha(p) for p in paths}, results=results, candidate_emitted=False, native_rules_relaxed=False, fabrication_released=False)
    out = ROOT/'staging/digital-blank-local-track-survey-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Completed local track survey', flush=True)


if __name__ == '__main__':
    run()
