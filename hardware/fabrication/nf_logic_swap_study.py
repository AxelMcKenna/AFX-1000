"""Distance-only study of identical gate-package site swaps; no CAD mutation.

A geometric spanning-tree estimate ignores obstacles, existing copper, layer
transitions and electrical constraints. It selects a rework experiment only.
"""
import argparse,itertools,json,math
from collections import defaultdict
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent

def mst_length(points):
    points=sorted(set(points))
    if len(points)<2:return 0.
    seen={0};total=0.
    while len(seen)<len(points):
        distance,index=min((math.dist(points[i],points[j]),i) for i in range(len(points)) if i not in seen for j in seen)
        total+=distance;seen.add(index)
    return total

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--label',required=True);args=ap.parse_args()
    assert all(v and all(c.isalnum() or c in '-_' for c in v) for v in vars(args).values())
    path=ROOT/'staging'/args.capture/'capture.json';capture=json.loads(path.read_text());assert all(sha(Path(p))==h for p,h in capture['source_sha256'].items())
    source=next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text())
    parts={}
    for f in children(board,'footprint'):
        props={p[1]:p[2] for p in children(f,'property')}
        if props['Value']=='SN74HCS08PWR':parts[props['Reference']]=dict(value=props['Value'],footprint=str(f[1]),layer=first(f,'layer')[1],pose=first(f,'at')[1:])
    pads={(o['ref'],o['pin']):o for o in capture['objects'] if o['kind']=='PAD'};by_net=defaultdict(list)
    for k,p in pads.items():
        if p['net'] not in ['/AGND','/AUX2V6']:by_net[p['net']].append(k)
    baseline={n:mst_length([tuple(pads[k]['position_mm']) for k in keys]) for n,keys in by_net.items()}
    rows=[]
    for left,right in itertools.combinations(sorted(parts),2):
        if (parts[left]['footprint'],parts[left]['layer'])!=(parts[right]['footprint'],parts[right]['layer']):continue
        assert {p for r,p in pads if r==left}=={p for r,p in pads if r==right}
        # Standard power-pin assignments are unchanged at both physical sites.
        assert pads[left,'7']['net']==pads[right,'7']['net']=='/AGND'
        assert pads[left,'14']['net']==pads[right,'14']['net']=='/AUX2V6'
        def moved(key):
            ref,pin=key;return tuple(pads[(right if ref==left else left if ref==right else ref,pin)]['position_mm'])
        nets={pads[k]['net'] for k in pads if k[0] in [left,right]}-{'/AGND','/AUX2V6'}
        per_net=[]
        for net in sorted(nets):
            after=mst_length([moved(k) for k in by_net[net]])
            per_net.append(dict(net=net,before_mm=baseline[net],after_mm=after,delta_mm=after-baseline[net]))
        old=sum(r['before_mm'] for r in per_net);new=sum(r['after_mm'] for r in per_net)
        rows.append(dict(refs=[left,right],before_mm=old,after_mm=new,delta_mm=new-old,per_net=per_net))
    rows.sort(key=lambda r:r['delta_mm']);out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False)
    data=dict(source_sha256={str(p):sha(p) for p in [path,source,Path(__file__)]},metric='Sum of Euclidean minimum spanning trees over all pad centers on affected non-power nets',parts=parts,ranked_swaps=rows,best_pair=rows[0]['refs'],best_saving_mm=-rows[0]['delta_mm'],existing_copper_or_component_poses_modified=False,existing_copper_rework_accounted_for=False,actual_routability_verified=False,electrical_benefit_qualified=False,manufacturing_qualified=False,required_next_steps=['Explicitly inventory all affected pin escape copper and preserve both sites power/ground assignments','Trial the swap in a separate candidate and reroute or remove vacated signal branches','Verify all original non-reworked geometry, pad nets, retained pad connections and native DRC/ERC/parity','Inspect clock/qualifier return paths, route lengths and local bypass assignment before selecting'],fabrication_released=False)
    (out/'study.json').write_text(json.dumps(data,indent=2)+'\n')
    print('Best identical-package pair:',rows[0]['refs'],'estimated savings mm:',-rows[0]['delta_mm'])

if __name__=='__main__':run()
