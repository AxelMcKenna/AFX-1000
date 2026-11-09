"""Screen coordinated LED01/02 and LED01/02/03 source escapes on the 27-open board."""
import copy
import json
import math
from pathlib import Path
import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString
from shapely.ops import unary_union
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_joint_escape_packing import pack
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    cp=ROOT/'staging/digital-led16-closed-inputs-27/capture.json'
    cap=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
    surface.WIDTH=layers.WIDTH=.2
    surface.MARGIN=.001
    surface.SIGNAL_LAYERS=FACES
    xx,yy=np.meshgrid(np.arange(4.,8.6001,.05),np.arange(14.,18.5001,.05))
    results=[]
    for name,terminals in [('two outputs',[('/LED/LED_01','6'),('/LED/LED_02','7')]), ('three outputs',[('/LED/LED_01','6'),('/LED/LED_02','7'),('/LED/LED_03','8')])]:
        nets={n for n,p in terminals}
        removed={o['uuid'] for o in cap['objects'] if o['net'] in nets and o['kind'] in ('PCB_TRACK','PCB_VIA')}
        case=dict(removed_uuids=sorted(removed))
        work=copy.deepcopy(cap)
        work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        domains={}
        for net,pin in terminals:
            pad=next(o for o in work['objects'] if o.get('ref')=='U3001' and o.get('pin')==pin)
            assert pad['net']==net and pad['layers'].get('F.Cu')
            start=pad['position_mm']
            free=screen.outline.difference(unary_union([g.buffer(d+.0005,quad_segs=32) for other,g,d in screen.geometry['F.Cu'] if other!=net]))
            via_free=screen.via_outline.difference(screen.obstacles(net))
            mask=contains_xy(free,xx,yy)&contains_xy(via_free,xx,yy)
            points=[(round(x,6),round(y,6)) for x,y in zip(xx[mask],yy[mask])]
            options=[]
            for point in sorted(points,key=lambda p:math.dist(start,p)):
                if not screen.via_legal(net,point):
                    continue
                choices=[p for p in surface.candidate_paths(start,point) if screen.legal(net,'F.Cu',p)]
                if not choices:
                    continue
                path=min(choices,key=lambda p:LineString(p).length)
                options.append(dict(point=point,runs=[('F.Cu',path)],vias=[point],cost=LineString(path).length+2.5))
            domains[net]=dict(net=net,face='F.Cu',start=start,options=options)
            print(name,net,'screened escapes',len(options),flush=True)
        packing=pack(domains,limit=256)
        # Round-robin across LED01 exit bins rather than replaying only one
        # cluster of nearly identical cheap source positions.
        groups={}
        for choice in packing['choices']:
            i=packing['names'].index('/LED/LED_01')
            point=domains['/LED/LED_01']['options'][choice['indices'][i]]['point']
            groups.setdefault(tuple(round(v,1) for v in point),[]).append(choice)
        selected=[]
        for rank in range(max(map(len,groups.values()),default=0)):
            for key,rows in sorted(groups.items(),key=lambda kv:kv[1][0]['cost']):
                if rank<len(rows):
                    selected.append(rows[rank])
                if len(selected)>=32:
                    break
            if len(selected)>=32:
                break
        for choice in selected:
            replay=branch(screen)
            for net,index in zip(packing['names'],choice['indices']):
                add(replay,net,domains[net]['options'][index])
        results.append(dict(case=name,neighbors=[n for n,p in terminals if n!="/LED/LED_01"],removed_uuids=case['removed_uuids'],domains=domains,
                            packing=packing,independently_replayed_choices=selected,led70_exit_bins=len(groups)))
        print(name,'local packs',len(packing['choices']),'replayed',len(selected),flush=True)
    paths=[cp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_joint_escape_packing.py','digital_serial1_joint_escape_survey.py','digital_screen_branch.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parents[1]/'tests/tooling/test_digital_joint_escape_packing.py',ROOT.parents[1]/'tests/tooling/test_digital_screen_branch.py']
    out=ROOT/'staging/digital-led01-source-packing-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},results=results,
        grid_bounds_mm=[4.,14.,8.6,18.5],grid_step_mm=.05,global_restorations_proven=False,
        candidate_emitted=False,native_rules_relaxed=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':
    run()
