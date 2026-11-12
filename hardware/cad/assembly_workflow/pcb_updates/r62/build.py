"""Capture only the verified R308 move on top of the existing R303 revision."""
import copy,json
from pathlib import Path
from shapely.geometry import Polygon,box
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness as bridge
from hardware.cad.assembly_workflow.pcb_updates.r44.build import boxes
HERE=Path(__file__).resolve().parent
SIGNAL='hardware/cad/two_board_sensor_05/signal_dac/native-r62/signal_main.kicad_pcb'

def run():
    previous=HERE/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    d,c,_,_=w.load_manifest(previous);parent=w.ROOT/d['mechanical_capture'];old=json.loads(parent.read_text());new=copy.deepcopy(old)
    expected=[{'ref':'A_R308','field':'pose','before':[116.,68.,0,'F.Cu'],'after':[120.5,81.,0,'F.Cu']}]
    delta=bridge.compare(bridge.snapshot(w.ROOT/d['boards']['signal']),bridge.snapshot(w.ROOT/SIGNAL));assert delta==expected,delta
    moved=[]
    for field in ['component_envelopes','tail_envelopes']:
        for row in new[field]:
            if row[0]=='A_R308':row[1]=[v+(4.5 if i%2==0 else 13) for i,v in enumerate(row[1])];moved.append(row)
    assert len(moved)==1 and moved[0][2]==[7.99,11.21]
    for p in list(new['source_sha256']):
        if p.endswith('/signal_main.kicad_pcb'):del new['source_sha256'][p]
    for p in [w.ROOT/SIGNAL,parent,Path(__file__)]:new['source_sha256'][w.relative(p)]=w.sha(p)
    new['mechanical_update']={'parent_capture':w.relative(parent),'parent_mechanical_update':old['mechanical_update'],'exact_incremental_footprint_difference':delta,'body_translation_mm':[4.5,13,0],'all_other_physical_fields_unchanged':True}
    (HERE/'capture.json').write_text(json.dumps(new,indent=2)+'\n')
    excluded=set(json.loads((w.HERE/'base.json').read_text())['replaced_allocations']);rows=[r for r in new['component_envelopes']+new['tail_envelopes'] if r[0] not in excluded]
    (HERE/'allocations.scad').write_text(boxes('base_component_allocations',rows));(HERE/'probes.scad').write_text(boxes('r62_moved_body',moved)+boxes('r62_other_allocations',[r for r in rows if r[0]!='A_R308']))
    bindings=dict(d['_loaded_sources'])
    for p in [HERE/'capture.json',HERE/'allocations.scad',Path(__file__),w.HERE/'verification/coverage-01/candidate.json']:bindings[w.relative(p)]=w.sha(p)
    c['base_component_allocations']['source']=w.relative(HERE/'allocations.scad')
    reg={'schema_version':1,'components':list(c.values()),'source_sha256':bindings,'intentional_contacts':sum((x['intentional_contacts'] for x in d['contracts']),[])}
    (HERE/'registry.json').write_text(json.dumps(reg,indent=2)+'\n')
    selection=json.loads(previous.read_text());selection['registries']=[w.relative(HERE/'registry.json')];selection['boards']['signal']=SIGNAL;selection['mechanical_capture']=w.relative(HERE/'capture.json')
    coverage=json.loads((w.HERE/'verification/coverage-01/candidate.json').read_text())
    selection['checks'] += [q for q in coverage['checks'] if q['id'] in ['coverage_main_population_controls','coverage_main_population_sensor']]
    (HERE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    probe={'schema_version':1,'components':[{'id':n,'source':w.relative(HERE/'probes.scad'),'module':n,'role':'receiving'} for n in ['r62_moved_body','r62_other_allocations']],'source_sha256':{w.relative(HERE/'probes.scad'):w.sha(HERE/'probes.scad')}}
    (HERE/'probe-registry.json').write_text(json.dumps(probe,indent=2)+'\n')
    candidate=copy.deepcopy(selection);candidate['registries'].append(w.relative(HERE/'probe-registry.json'));candidate['checks'].append({'id':'r62_body_other_parts','left':['r62_moved_body'],'right':[n for n in c if n not in ['base_component_allocations','base_main_pcbs']]+['r62_other_allocations'],'expect':'empty'})
    (HERE/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    fresh=bridge.run(w.ROOT,selection['boards'],selection['mechanical_capture']);assert fresh['geometry_fresh'];(HERE/'freshness.json').write_text(json.dumps(fresh,indent=2)+'\n')
    power=next(b for b in new['boards'] if b['id']=='power');area=Polygon(power['outline']).intersection(box(*moved[0][1])).area;assert area==0
    (HERE/'body-proof.json').write_text(json.dumps({'exact_delta':delta,'body':moved[0],'power_board_xy_intersection_mm2':area,'own_signal_substrate_contact_expected':True,'fabrication_released':False},indent=2)+'\n')
    print('Exact R308 capture; R303 preserved; power substrate disjoint;29selected checks plus body probe')
if __name__=='__main__':run()
