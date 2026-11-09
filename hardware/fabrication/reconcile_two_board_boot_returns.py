"""Model the TPS543620 internal SW bridge without an external routing loop."""
import copy
import json
import math
import shutil
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication.audit_two_board_power_delta import geometry

BASE=STAGING/'two-board-power-buck-local-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2535-buck-local/capture.json'
OUT=STAGING/'two-board-power-boot-return-01'
CHANGES={('P_U20','13'):'P03_D_BOOT_RETURN',('P_C201','2'):'P03_D_BOOT_RETURN',
         ('P_U23','13'):'P03_A_BOOT_RETURN',('P_C221','2'):'P03_A_BOOT_RETURN'}
URL='https://www.ti.com/document-viewer/TPS543620/datasheet/GUID-BAAAA3C0-431A-4B70-AFE1-6FA21FA6A1E5'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(Path(name))==h,name
    objects={o['uuid']:o for o in cap['objects']};retarget={}
    for pair,name in CHANGES.items():
        pads=[o for o in objects.values() if (o.get('ref'),o.get('pin'))==pair]
        assert len(pads)==1
        for uid in cap['all_groups'][pads[0]['group']]:
            o=objects[uid]
            assert o['kind']=='PCB_TRACK' or (o.get('ref'),o.get('pin')) in CHANGES
            retarget[uid]='/P_power_supply/'+name
    sheet=read_sexpr((BASE/'P_power_p03.kicad_sch').read_text())
    for (ref,number),name in CHANGES.items():
        sym=next(s for s in children(sheet,'symbol') if prop(s,'Reference')[2]==ref)
        x,y,angle=map(float,first(sym,'at')[1:]);assert angle==0
        lib=next(s for s in children(first(sheet,'lib_symbols'),'symbol') if s[1]==first(sym,'lib_id')[1])
        pin=next(p for u in children(lib,'symbol') for p in children(u,'pin') if str(first(p,'number')[1])==number)
        px,py=map(float,first(pin,'at')[1:3]);pt=[x+px,y-py]
        wires=[w for w in children(sheet,'wire') if any(math.dist(pt,list(map(float,p[1:3])))<1e-6 for p in children(first(w,'pts'),'xy'))]
        assert len(wires)==1
        other=next(list(map(float,p[1:3])) for p in children(first(wires[0],'pts'),'xy') if math.dist(pt,list(map(float,p[1:3])))>1e-6)
        labels=[l for l in children(sheet,'label') if math.dist(other,list(map(float,first(l,'at')[1:3])))<1e-6]
        assert len(labels)==1 and labels[0][1]==name.replace('BOOT_RETURN','SW')
        labels[0][1]=name
    note=('U20/U23 TPS543620: SW13 is the bootstrap return; SW10 drives the inductor.\n'
          'SW13 and SW10 connect inside each IC (TI SLUSDR5C, Table 5-1).\n'
          'BOOT_RETURN nets terminate only at C201/C221 pin 2 and their IC pin 13;\n'
          'no external bridge to force-SW copper is required by this internal connection.')
    sheet.append([a('text'),note,[a('at'),152.4,2451.1,0],[a('effects'),[a('font'),[a('size'),1.27,1.27]],[a('justify'),a('left')]],
                  [a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,'afx/tbp13/boot-return-note'))]])
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());original=copy.deepcopy(board)
    oldnames={int(n[1]):str(n[2]) for n in children(board,'net')}
    names=set(oldnames.values())|set(retarget.values());names.discard('')
    # Match native_two_board_power's sorted, slash-stripped net IDs BEFORE it
    # assigns pads. Every existing copper object is remapped by net NAME.
    ids={n:i+1 for i,n in enumerate(sorted(names,key=lambda n:n.lstrip('/')))}
    changed_tracks=[]
    for node in board:
        if not isinstance(node,list) or not node:continue
        if node[0] in ['segment','via','arc']:
            n=first(node,'net');uid=str(first(node,'uuid')[1]);name=retarget.get(uid,oldnames[int(n[1])])
            if uid in retarget:changed_tracks.append(uid)
            n[1]=ids[name]
        elif node[0]=='footprint':
            ref=str(prop(node,'Reference')[2])
            for p in children(node,'pad'):
                for n in children(p,'net'):
                    name='/P_power_supply/'+CHANGES[(ref,str(p[1]))] if (ref,str(p[1])) in CHANGES else oldnames[int(n[1])]
                    if name:n[1:]=[ids[name],name]
    assert not children(board,'zone')
    board[:]=[n for n in board if not(isinstance(n,list) and n and n[0]=='net')]
    for name,code in ids.items():board.insert(8,[a('net'),code,name])
    assert geometry(original)==geometry(board)
    OUT.mkdir()
    copied=[]
    for p in BASE.iterdir():
        if p.name in ['libraries','symbols']:
            shutil.copytree(p,OUT/p.name);copied.extend(q for q in p.rglob('*') if q.is_file())
        elif p.suffix in ['.kicad_sch','.kicad_pcb','.kicad_pro','.kicad_dru'] or p.name in ['fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json']:
            shutil.copy2(p,OUT/p.name);copied.append(p)
    (OUT/'P_power_p03.kicad_sch').write_text(sexpr(sheet)+'\n')
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'expected-circuit.json';expected=json.loads(p.read_text())
    for (ref,pin),name in CHANGES.items():expected[ref]['pins'][pin]='P::'+name
    p.write_text(json.dumps(expected,indent=2)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP13';p.write_text(sexpr(root)+'\n')
    report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),CAP,*copied]},
        manufacturer_source=URL,manufacturer_document='SLUSDR5C, Table 5-1, pin 13',
        declared_pin_changes=[dict(ref=r,pin=p,new_net=n) for (r,p),n in CHANGES.items()],
        internal_equivalences=[dict(ref=r,pins=['10','13']) for r in ['P_U20','P_U23']],
        retargeted_tracks=sorted(changed_tracks),all_geometry_unchanged=True,
        predicted_opens=2533,open_reduction_is_internal_pin_model_correction=True,
        connections_routed_this_pass=0,native_validation_pending=True,fabrication_released=False)
    (OUT/'boot-return-change.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(retargeted_tracks=len(changed_tracks),predicted_opens=2533)))

if __name__=='__main__':run()
