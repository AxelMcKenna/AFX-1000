"""Pack freshly sampled shifted receiving escapes and replay diverse serial exits."""
import copy,json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_joint_escape_packing import pack
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-serial1-source-preparation-inputs-31-02/capture.json';rp=ROOT/'staging/digital-serial1-shifted-target-escape-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in recipe['removed_uuids'] and o.get('ref')!='R3015']+copy.deepcopy(recipe['component_pose']['pads'])
    result=pack(recipe['domains'],limit=512);print('Fresh receiving-end packs',len(result['choices']),'pair counts',result['pair_compatible_counts'],flush=True)
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    serial_index=result['names'].index('serial target');groups={}
    for choice in result['choices']:
        point=recipe['domains']['serial target']['options'][choice['indices'][serial_index]]['point']
        groups.setdefault(tuple(round(v,1) for v in point),[]).append(choice)
    replayed=[]
    for rank in range(max(map(len,groups.values()),default=0)):
        for key,rows in sorted(groups.items(),key=lambda kv:kv[1][0]['cost']):
            if rank<len(rows):replayed.append(rows[rank])
            if len(replayed)>=32:break
        if len(replayed)>=32:break
    for choice in replayed:
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        for r in recipe['data_routes']:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
        for name,index in zip(result['names'],choice['indices']):
            d=recipe['domains'][name];add(screen,d['net'],d['options'][index])
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_joint_escape_packing.py','digital_serial1_joint_escape_survey.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parents[1]/'tests/tooling/test_digital_joint_escape_packing.py']
    out=ROOT/'staging/digital-serial1-shifted-target-pack-01';out.mkdir(exist_ok=False)
    print('Replayed',len(replayed),'packs from',len(groups),'serial exit bins',flush=True)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=recipe['removed_uuids'],packing=result,screen_replayed_choices=replayed,distinct_serial_exit_bins=len(groups),component_pose=recipe['component_pose'],data_routes=recipe['data_routes'],all_screen_replayed_choices_passed=True,global_restorations_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':run()
