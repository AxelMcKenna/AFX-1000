"""Independent source-footprint/pad/net preservation for the bundled TB05 CAD."""
import copy,json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.two_board_placement import ROOT,REPO,sha


def normalize(fp,netmap,role,exported):
    f=copy.deepcopy(fp);f[1]='LIBRARY_ID_CHECKED_SEPARATELY';first(f,'at')[1:3]=['0','0']
    def walk(node):
        if not isinstance(node,list):return node
        if node and node[0] in ['uuid','path','sheetname','sheetfile']:return None
        if node and node[0]=='net':
            n=str(node[2]) if len(node)>2 else netmap.get(str(node[1]),str(node[1]))
            if exported and n:
                assert n.startswith(role+'::'),('cross-source net merge',n,role)
                n=n[len(role)+2:]
            return ['net',n]
        if len(node)>2 and node[0]=='property' and node[1]=='Reference':node[2]='REF_NORMALIZED'
        result=[]
        for child in node:
            v=walk(child)
            if v is not None:result.append(v)
        return result
    return walk(f)


def check_part(part,pose,before,after,oldnets,newnets,newlib):
    assert str(after[1])==newlib
    assert next(p[2] for p in children(after,'property') if p[1]=='Reference')==part['id']
    assert [float(v) for v in first(after,'at')[1:3]]==[round(v,6) for v in pose['xy']]
    assert normalize(before,oldnets,part['role'],False)==normalize(after,newnets,part['role'],True),part['id']


def run():
    folder=ROOT/'staging/two-board-placement-05';cad=ROOT/'staging/two-board-placement-cad-03';out=ROOT/'staging/two-board-review-01'
    c=json.loads((folder/'capture.json').read_text());p=json.loads((folder/'placement.json').read_text());bundle=json.loads((cad/'library-bundle.json').read_text())
    newlibs={r['ref']:r['new'] for r in bundle['library_identifier_map']};old={};new={};paths=[Path(__file__),folder/'capture.json',folder/'placement.json',cad/'library-bundle.json']
    for role,s in c['sources'].items():
        path=REPO/s['path'];paths.append(path);tree=read_sexpr(path.read_text());nets={str(n[1]):str(n[2]) for n in children(tree,'net')}
        for f in children(tree,'footprint'):old[(role,next(x[2] for x in children(f,'property') if x[1]=='Reference'))]=(f,nets)
    for board in ['signal_main','power_protection']:
        path=cad/(board+'.kicad_pcb');paths.append(path);tree=read_sexpr(path.read_text());nets={str(n[1]):str(n[2]) for n in children(tree,'net')}
        assert not children(tree,'segment') and not children(tree,'via') and not children(tree,'zone')
        for f in children(tree,'footprint'):
            r=next(x[2] for x in children(f,'property') if x[1]=='Reference');assert r not in new;new[r]=(f,nets)
    pads=0
    for part in c['parts']:
        before,oldnets=old[(part['role'],part['ref'])];after,newnets=new[part['id']]
        check_part(part,p['poses'][part['id']],before,after,oldnets,newnets,newlibs.get(part['id'],''));pads+=len(children(before,'pad'))
    # Actual exported source pad mutations must be rejected independently.
    part=next(r for r in c['parts'] if not r['mechanical'] and any(n for _,n,_ in r['pad_nets']))
    before,oldnets=old[(part['role'],part['ref'])];after,newnets=new[part['id']];mutations={}
    for kind in ['missing_pad','wrong_source_net','shifted_placement']:
        bad=copy.deepcopy(after)
        if kind=='missing_pad':bad.remove(children(bad,'pad')[0])
        elif kind=='shifted_placement':first(bad,'at')[1]=float(first(bad,'at')[1])+1
        else:
            pad=next(x for x in children(bad,'pad') if children(x,'net'));net=first(pad,'net');net[2]='OTHER_SOURCE::AGND'
        try:check_part(part,p['poses'][part['id']],before,bad,oldnets,newnets,newlibs[part['id']])
        except AssertionError:mutations[kind]=True
        else:raise AssertionError(('mutation accepted',kind))
    result=dict(source_sha256={str(q.relative_to(REPO)):sha(q) for q in paths},
        exact_preserved_source_footprints=len(c['parts']),exact_preserved_source_pads=pads,
        source_part_values_angles_sides_and_intrinsic_geometry_preserved=True,
        every_source_net_kept_in_its_own_namespace=True,cross_source_nets_joined=False,
        mutation_controls_rejected=mutations,old_copper_inherited=False,
        additional_mechanical_footprints=len(new)-len(c['parts']),electrical_equivalence_of_integrated_unit_claimed=False,
        complete_fit_verified=False,fabrication_released=False)
    target=out/'source-preservation.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':run()
