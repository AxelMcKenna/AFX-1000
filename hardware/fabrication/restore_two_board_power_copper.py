"""Reuse complete source nets only when all their terminals retain one pose.

Never inherit a split net, a plane, an incomplete source net, or copper from a
net with a moved terminal. Native DRC and connectivity checks follow selection.
"""
import argparse
import copy
import json
import shutil
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.integrate_two_board_power import ROLES

BASE=STAGING/'two-board-power-native-10'
CAP=STAGING/'two-board-placement-05/capture.json'


def pad_shape(p):
    return [v for v in p if not(isinstance(v,list) and v and v[0] in ['uuid','net','tstamp','pinfunction','pintype'])]


def name_for(node,names):
    v=first(node,'net')[1]
    return (names[int(v)] if str(v).isdigit() else str(v)).lstrip('/')


def build():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='two-board-power-copper-01')
    parser.add_argument('--reject-native',default=None)
    args=parser.parse_args()
    assert all(c.isalnum() or c in '-_' for c in args.output)
    out=STAGING/args.output; assert not out.exists()
    cap=json.loads(CAP.read_text())
    target=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    assert not any(children(target,t) for t in ['segment','via','arc','zone'])
    fps={str(prop(f,'Reference')[2]):f for f in children(target,'footprint')}
    _,newpins=read_netlist(BASE/'netlist.xml')
    targetnets={str(n[2]).lstrip('/'):(int(n[1]),str(n[2])) for n in children(target,'net')}
    paths=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',BASE/'review.json',
           BASE/'module-cutoff-audit.json',REPO/'hardware/fabrication/integrate_two_board_power.py']
    rejected=set()
    if args.reject_native:
        folder=STAGING/args.reject_native
        ledger=json.loads((folder/'copper-restoration.json').read_text())
        owners={u:row['key'] for row in ledger['selected_nets'] for u in row['target_copper_uuids']}
        drc=json.loads((folder/'drc.json').read_text())
        for violation in drc['violations']:
            matches={owners[i['uuid']] for i in violation.get('items',[]) if i.get('uuid') in owners}
            assert matches,('Non-restored-copper DRC issue',violation)
            rejected.update(matches)
        paths.extend([folder/'copper-restoration.json',folder/'drc.json'])
    selected=[];skipped=Counter()
    for prefix,role in ROLES.items():
        sourcepath=REPO/cap['sources'][role]['path']
        assert sha(sourcepath)==cap['sources'][role]['sha256']
        paths.extend([sourcepath,sourcepath.parent/'netlist.xml'])
        source=read_sexpr(sourcepath.read_text())
        _,oldpins=read_netlist(sourcepath.parent/'netlist.xml')
        oldfps={str(prop(f,'Reference')[2]):f for f in children(source,'footprint')}
        names={int(n[1]):str(n[2]) for n in children(source,'net')}
        nodes=defaultdict(set)
        for node,net in oldpins.items():nodes[net].add(node)
        copper=defaultdict(list)
        for tag in ['segment','via','arc','zone']:
            for item in children(source,tag):
                if not children(item,'net'):continue
                copper[name_for(item,names)].append(item)
        for oldnet,items in sorted(copper.items()):
            key=prefix+':'+oldnet
            if key in rejected:skipped['native_geometry_rejection']+=1;continue
            terminals=nodes.get(oldnet,set())
            if len(terminals)<2:skipped['no_complete_terminal_set']+=1;continue
            if any(v[0]=='zone' for v in items):skipped['contains_zone']+=1;continue
            if any((prefix+'_'+r,p) not in newpins for r,p in terminals):skipped['missing_target_terminal']+=1;continue
            nets={newpins[(prefix+'_'+r,p)] for r,p in terminals}
            if len(nets)!=1:skipped['source_net_split_in_new_circuit']+=1;continue
            translations=set();valid=True
            for ref in {r for r,p in terminals}:
                if ref not in oldfps or prefix+'_'+ref not in fps:valid=False;break
                old,new=oldfps[ref],fps[prefix+'_'+ref]
                if first(old,'layer')[1]!=first(new,'layer')[1]:valid=False;break
                at0,at1=first(old,'at'),first(new,'at')
                angle0=float(at0[3]) if len(at0)>3 else 0
                angle1=float(at1[3]) if len(at1)>3 else 0
                if abs((angle1-angle0+180)%360-180)>1e-6:valid=False;break
                pads0,pads1=[{str(p[1]):pad_shape(p) for p in children(f,'pad') if p[1]} for f in [old,new]]
                if pads0!=pads1:valid=False;break
                translations.add(tuple(round(float(at1[i])-float(at0[i]),6) for i in [1,2]))
            if not valid or len(translations)!=1:skipped['changed_terminal_pose_or_land']+=1;continue
            delta=next(iter(translations));net=next(iter(nets));code,fullname=targetnets[net]
            objects=[]
            def transform(node):
                if not isinstance(node,list) or not node:return
                if node[0] in ['start','end','mid','at','xy']:
                    node[1:3]=[round(float(node[i+1])+delta[i],6) for i in range(2)]
                elif node[0] in ['uuid','tstamp']:
                    node[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPC:'+prefix+':'+str(node[1])))
                elif node[0]=='net':node[1]=code
                elif node[0]=='net_name':node[1]=fullname
                for child in node:
                    if isinstance(child,list):transform(child)
            for original in items:
                item=copy.deepcopy(original);transform(item);target.append(item)
                objects.append(str(first(item,'uuid')[1]))
            selected.append(dict(key=key,role=role,source_net=oldnet,target_net=net,
                translation_mm=delta,terminals=sorted([[prefix+'_'+r,p] for r,p in terminals]),
                counts=dict(Counter(str(i[0]) for i in items)),target_copper_uuids=objects))
    assert selected,'No eligible source copper'
    shutil.copytree(STAGING/'two-board-power-integration-10',out)
    dest=out/'power_protection.kicad_pcb';dest.write_text(sexpr(target)+'\n')
    ledger=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},selected_nets=selected,
        excluded_after_native_DRC=sorted(rejected),skipped_net_reasons=dict(skipped),
        copper_counts=dict(Counter(str(i[0]) for i in target if isinstance(i,list) and i and i[0] in ['segment','via','arc'])),
        existing_footprints_changed=False,source_layer_names_retained=True,planes_restored=False,
        native_geometry_and_connection_validation_pending=True,stack_approved=False,fabrication_released=False)
    (out/'copper-restoration.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print(json.dumps(dict(selected_nets=len(selected),by_role=dict(Counter(r['role'] for r in selected)),
        counts=ledger['copper_counts'],skipped=skipped),indent=2))


if __name__=='__main__':build()
