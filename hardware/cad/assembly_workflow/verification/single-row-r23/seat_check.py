"""Prepare an exact wafer-face seating mask; never exclude the whole board pair."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent

def run():
    contract_path=w.ROOT/'hardware/cad/two_board_installation_06/r23_single_row_mates/mate-contract.json'
    contract=json.loads(contract_path.read_text());direct=json.loads((HERE/'direct-source-check/result.json').read_text())
    assert not direct['runtime_failure'] and not direct['empty']
    m=direct['mesh'];assert m['min_mm'][2]==m['max_mm'][2] and abs(m['min_mm'][2]-8.35)<1e-6
    boxes=[]
    for row in contract['choices']:
        for b in row['male_wafer_receiving_boxes']:
            assert b[2]==8.35;boxes.append([b[0],b[1],8.349999,b[3],b[4],8.350001])
    lines=['use <substrates.scad>','module r23_exact_wafer_seat_mask(){']
    for b in boxes:lines.append('translate('+json.dumps(b[:3])+')cube('+json.dumps([b[i+3]-b[i] for i in range(3)])+');')
    lines+=['}','module r23_substrates_nonseat(){difference(){r23_substrates_with_connector_drills();r23_exact_wafer_seat_mask();}}']
    (HERE/'seat-scoped.scad').write_text('\n'.join(lines)+'\n')
    original=HERE/'base-registry.json';r=json.loads(original.read_text())
    for c in r['components']:
        if c['id']=='r23_substrates':c['source']=w.relative(HERE/'seat-scoped.scad');c['module']='r23_substrates_nonseat'
    r['intentional_contacts'].append({'components':['panel_single_row_mates_r23','r23_substrates'],'reason':'Exact male wafer bottom seats on signal PCB top Z8.35. Frozen original-source and cached mesh witnesses have zero Z thickness. Only these eleven wafer faces receive a +/-0.000001mm numerical band; all tail holes and other substrate surfaces remain checked.','blanket_pair_exclusion':False,'contact_mask_contract':{'source':w.relative(HERE/'seat-scoped.scad'),'module':'r23_exact_wafer_seat_mask','z_mm':[8.349999,8.350001],'boxes_mm':boxes}})
    for f in [original,Path(__file__),contract_path,HERE/'seat-scoped.scad',HERE/'direct-source-check/result.json']:r['source_sha256'][w.relative(f)]=w.sha(f)
    (HERE/'seat-registry.json').write_text(json.dumps(r,indent=2)+'\n')
    candidate=json.loads((HERE/'candidate.json').read_text());candidate['registries'][0]=w.relative(HERE/'seat-registry.json')
    (HERE/'seat-candidate.json').write_text(json.dumps(candidate,indent=2)+'\n');w.load_manifest(HERE/'seat-candidate.json')
    print('Exact11wafer footprints;2nm numerical contact band; all other board geometry preserved')
if __name__=='__main__':run()
