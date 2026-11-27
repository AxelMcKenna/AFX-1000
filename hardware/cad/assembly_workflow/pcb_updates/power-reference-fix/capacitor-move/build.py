"""Screen E_C13's moved receiving envelope against the complete selected assembly."""
import copy,json,hashlib
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.assembly_workflow.pcb_updates.r44.build import boxes
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    previous=H/'previous-manifest.json'
    assert not previous.exists(), 'Use new evidence directory for a new stage'
    previous.write_bytes((w.HERE/'current.json').read_bytes())
    data,parts,checks,_=w.load_manifest(previous)
    capture=w.ROOT/data['mechanical_capture'];c=json.loads(capture.read_text())
    rows=c['component_envelopes']+c['tail_envelopes'];old,=[r for r in rows if r[0]=='E_C13']
    assert old==['E_C13',[95.3,126.52,98.7,128.48000000000002],[9.14,11.36]]
    xy=old[1];corners=[(108.275-(y-127.5),129.095+(x-97)) for x in (xy[0],xy[2]) for y in (xy[1],xy[3])]
    moved=['E_C13',[round(min(x for x,y in corners),9),round(min(y for x,y in corners),9),round(max(x for x,y in corners),9),round(max(y for x,y in corners),9)],old[2]]
    assert moved[1]==[107.295,127.395,109.255,130.795]
    excluded=set(json.loads((w.HERE/'base.json').read_text())['replaced_allocations'])
    others=[r for r in rows if r[0]!='E_C13' and r[0] not in excluded]
    scad=H/'probes.scad';scad.write_text(boxes('power_e_c13_moved',[moved])+boxes('power_other_allocations',others))
    native=H.parent/'roundtrip-review.json';r=json.loads(native.read_text());assert r['native_E_C13_physical_change_exactly_three_absolute_angles']
    source=w.ROOT/'hardware/qualification/two_board_aux_current_08/held_cutover/primary/c0805c104k5ractu.pdf'
    paths=[Path(__file__),previous,capture,scad,native,source]
    save(H/'registry.json',dict(schema_version=1,components=[dict(id=n,source=w.relative(scad),module=n,role='receiving',scene=False) for n in ['power_e_c13_moved','power_other_allocations']],source_sha256={w.relative(p):sha(p) for p in paths}))
    candidate=json.loads(previous.read_text());candidate['registries'].append(w.relative(H/'registry.json'))
    obstacles=[n for n in parts if n not in ['base_component_allocations','base_main_pcbs']]+['power_other_allocations']
    new=[dict(id=f'power_e_c13_{i//8+1}',left=['power_e_c13_moved'],right=obstacles[i:i+8],expect='empty') for i in range(0,len(obstacles),8)]
    candidate['checks'].extend(new);save(H/'candidate.json',candidate)
    save(H/'scope.json',dict(old_envelope=old,moved_envelope=moved,prior_roles=len(parts),external_roles=obstacles,new_checks=[x['id'] for x in new],selected=False,new_power_parts_included=False,own_PCB_contact_expected=True,package_max_mm=[2.2,1.45,.88],package_source=w.relative(source),receiving_envelope_preserved=True,physical_qualified=False))
    print('Prepared',len(new),'checks against',len(obstacles),'roles; no power selection')
if __name__=='__main__':main()
