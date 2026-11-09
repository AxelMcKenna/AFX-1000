"""Locate missing adjacent return coverage at still-open startup logic pads."""
import argparse
import json
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_nf_surface import shape


def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in n) for n in [args.capture,args.output])
    source=STAGING/args.capture/'capture.json';out=STAGING/args.output;assert not out.exists()
    c=json.loads(source.read_text())
    for n,h in c['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    fields,excluded=anchored_fields(c)
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    adjacent={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}
    selected={n for n in c['open_nets'] if ('E28_' in n or n.rsplit('/',1)[-1] in ['ANA_PG','DIG_PG','DIG_PG3_SCHMITT','PWR_ALL_RAILS_ALLOW']) and not n.endswith(('_CT','_SENSE','_DIV'))}
    obstacles={l:[(o,shape(o['layers'][l])) for o in c['objects'] if o['net']!='PWR_AGND' and o['layers'].get(l)] for l in adjacent.values()}
    authored={l:unary_union([shape(z['authored_outline']) for z in c['zones'] if z['layer']==l and z['net']=='PWR_AGND' and any(shape(z['polygons']).intersection(f).area>1e-9 for (fl,gid),f in fields.items() if fl==l and gid==main)]) for l in adjacent.values()}
    rows=[]
    for o in c['objects']:
        if o['kind']!='PAD' or o['net'] not in selected or any(o['drill_mm']):continue
        layer,=o['layers'];reference=adjacent[layer];band=Point(o['position_mm']).buffer(.1)
        missing=band.difference(fields[reference,main].buffer(.0015)).area
        nearby=[]
        if missing>=1e-6:
            for other,g in obstacles[reference]:
                distance=band.distance(g)
                if distance<=.35:
                    nearby.append(dict(uuid=other['uuid'],net=other['net'],kind=other['kind'],ref=other.get('ref'),pin=other.get('pin'),distance_mm=distance))
        rows.append(dict(ref=o['ref'],pin=o['pin'],net=o['net'],pad_uuid=o['uuid'],position_mm=o['position_mm'],layer=layer,
            reference_layer=reference,uncovered_mm2=missing,covered=missing<1e-6,
            authored_main_field_covers_pad_center=authored[reference].covers(band),nearby_reference_layer_copper=nearby))
    blocked=[r for r in rows if not r['covered']]
    sources=[Path(__file__),source,REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},power_opens=c['native_uncapped_opens'],
        selected_open_nets=sorted(selected),pad_access=rows,covered_pads=len(rows)-len(blocked),uncovered_pads=len(blocked),
        excluded_unanchored_fragments=excluded,scope='0.2 mm trace launch at the pad center only; does not prove an escape corridor, load/timing limits or complete routing.',fabrication_released=False)
    out.mkdir();(out/'survey.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pads=len(rows),covered=len(rows)-len(blocked),uncovered=len(blocked),obstructing_objects=len({o['uuid'] for r in blocked for o in r['nearby_reference_layer_copper']}))))


if __name__=='__main__':run()
