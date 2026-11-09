"""Survey full trace-reference coverage on nets touched by a control pass.

This records existing gaps as well as new copper. It does not qualify layer
transition stitching, timing, EMC, driver loading or complete circuit behavior.
"""
import argparse
import json
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields


def run():
    ap=argparse.ArgumentParser()
    for n in ['capture','candidate','manifest','output']:ap.add_argument('--'+n,required=True)
    args=ap.parse_args()
    assert all(all(x.isalnum() or x in '-_.' for x in v) for v in vars(args).values())
    cp=STAGING/args.capture/'capture.json';mp=STAGING/args.candidate/args.manifest
    c=json.loads(cp.read_text());m=json.loads(mp.read_text())
    for data in [c,m]:
        for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    fields,excluded=anchored_fields(c)
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    fields={l:f.buffer(.0015) for (l,g),f in fields.items() if g==main}
    holes={}
    for o in c['objects']:
        if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    holes={n:unary_union(gs) for n,gs in holes.items()}
    added={u for r in m['routes'] for u in r['segment_uuids']}
    touched={r['net'] for r in m['joins']};rows=[]
    for net in sorted(touched):
        checks=[]
        for o in c['objects']:
            if o['kind']!='PCB_TRACK' or o['net']!=net:continue
            layer,=o['layers'];i=c['copper_layers'].index(layer)
            adjacent=[c['copper_layers'][j] for j in [i-1,i+1] if 0<=j<len(c['copper_layers'])]
            band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(net,Polygon()))
            if band.is_empty:
                checks.append(dict(track_uuid=o['uuid'],layer=layer,added=o['uuid'] in added,own_via_antipad_only=True,fully_referenced=True,uncovered_mm2=0));continue
            options=sorted((band.difference(fields[l]).area,l) for l in adjacent if l in fields)
            missing,reference=options[0] if options else (band.area,None)
            checks.append(dict(track_uuid=o['uuid'],layer=layer,added=o['uuid'] in added,reference_layer=reference,fully_referenced=missing<1e-6,uncovered_mm2=missing))
        rows.append(dict(net=net,native_net_complete=net not in c['open_nets'],track_count=len(checks),unreferenced_tracks=sum(not x['fully_referenced'] for x in checks),new_unreferenced_tracks=sum(x['added'] and not x['fully_referenced'] for x in checks),checks=checks))
    assert not any(r['new_unreferenced_tracks'] for r in rows)
    out=STAGING/args.output;out.mkdir(exist_ok=False)
    sources=[Path(__file__),cp,mp,REPO/'hardware/fabrication/plan_two_board_startup_controls.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},nets=rows,touched_nets=len(rows),complete_touched_nets=sum(r['native_net_complete'] for r in rows),unreferenced_existing_tracks=sum(r['unreferenced_tracks'] for r in rows),new_unreferenced_tracks=0,main_ground_group=main,excluded_unanchored_fragments=excluded,scope='Every native track on each joined net; adjacent main-ground coverage, excluding own via antipads. Layer-transition stitching and electrical qualification remain separate.',fabrication_released=False)
    (out/'survey.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['touched_nets','complete_touched_nets','unreferenced_existing_tracks','new_unreferenced_tracks']}))


if __name__=='__main__':run()
