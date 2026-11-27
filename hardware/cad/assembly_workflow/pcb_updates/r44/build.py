"""Translate exactly the verified R303 receiving box; preserve frozen CAD sources."""
import copy,json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness as bridge
HERE=Path(__file__).resolve().parent
SIGNAL='hardware/cad/two_board_sensor_05/signal_dac/native-r44/signal_main.kicad_pcb'
ORIGINAL='hardware/cad/two_board_print_01/capture.json'

def boxes(module,rows):
    return 'module '+module+'(){\n'+''.join('translate('+json.dumps([xy[0],xy[1],z[0]])+')cube('+json.dumps([xy[2]-xy[0],xy[3]-xy[1],z[1]-z[0]])+');\n' for _,xy,z in rows)+'}\n'

def run():
    old=json.loads((w.ROOT/ORIGINAL).read_text());new=copy.deepcopy(old)
    baseline=next(p for p in old['source_sha256'] if p.endswith('/signal_main.kicad_pcb'))
    assert w.sha(w.ROOT/baseline)==old['source_sha256'][baseline]
    delta=bridge.compare(bridge.snapshot(w.ROOT/baseline),bridge.snapshot(w.ROOT/SIGNAL))
    assert delta==[{'ref':'A_R303','field':'pose','before':[120.,73.,0,'F.Cu'],'after':[109.,82.5,0,'F.Cu']}],delta
    moved=[]
    for field in ['component_envelopes','tail_envelopes']:
        for row in new[field]:
            if row[0]=='A_R303':
                row[1]=[v+(-11 if i%2==0 else 9.5) for i,v in enumerate(row[1])];moved.append(row)
    assert len(moved)==1
    new['source_sha256'].pop(baseline);new['source_sha256'][SIGNAL]=w.sha(w.ROOT/SIGNAL)
    new['source_sha256'][ORIGINAL]=w.sha(w.ROOT/ORIGINAL)
    new['source_sha256'][w.relative(Path(__file__))]=w.sha(Path(__file__))
    new['mechanical_update']={'exact_footprint_difference':delta,'body_translation_mm':[-11,9.5,0],'unchanged_package_side_orientation_height':True,'frozen_structural_sources_unchanged':True}
    (HERE/'capture.json').write_text(json.dumps(new,indent=2)+'\n')
    base=json.loads((w.HERE/'base.json').read_text());excluded=set(base['replaced_allocations'])
    rows=[r for r in new['component_envelopes']+new['tail_envelopes'] if r[0] not in excluded]
    (HERE/'allocations.scad').write_text(boxes('base_component_allocations',rows))
    (HERE/'probes.scad').write_text(boxes('r44_moved_body',moved)+boxes('r44_other_allocations',[r for r in rows if r[0]!='A_R303']))
    # Parent selection is captured once so later promotion does not self-bind.
    previous=HERE/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    d,c,_,_=w.load_manifest(previous)
    bindings=dict(d['_loaded_sources'])
    for p in [HERE/'capture.json',HERE/'allocations.scad',Path(__file__)]:bindings[w.relative(p)]=w.sha(p)
    c['base_component_allocations']['source']=w.relative(HERE/'allocations.scad')
    contacts=sum([x['intentional_contacts'] for x in d['contracts']],[])
    reg={'schema_version':1,'components':list(c.values()),'source_sha256':bindings,'intentional_contacts':contacts}
    (HERE/'registry.json').write_text(json.dumps(reg,indent=2)+'\n')
    manifest=json.loads(previous.read_text());manifest['registries']=[w.relative(HERE/'registry.json')];manifest['boards']['signal']=SIGNAL;manifest['mechanical_capture']=w.relative(HERE/'capture.json')
    (HERE/'selection.json').write_text(json.dumps(manifest,indent=2)+'\n')
    probes={'schema_version':1,'components':[{'id':n,'source':w.relative(HERE/'probes.scad'),'module':n,'role':'receiving'} for n in ['r44_moved_body','r44_other_allocations']],'source_sha256':{w.relative(HERE/'probes.scad'):w.sha(HERE/'probes.scad')}}
    (HERE/'probe-registry.json').write_text(json.dumps(probes,indent=2)+'\n')
    manifest['registries'].append(w.relative(HERE/'probe-registry.json'))
    manifest['checks']=[{'id':'r44_body_other_parts','left':['r44_moved_body'],'right':[n for n in c if n not in ['base_component_allocations','base_main_pcbs']]+['r44_other_allocations'],'expect':'empty'}]
    (HERE/'candidate.json').write_text(json.dumps(manifest,indent=2)+'\n')
    result=bridge.run(w.ROOT,manifest['boards'],manifest['mechanical_capture']);assert result['geometry_fresh'],result
    (HERE/'freshness.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Exact R303 translation captured; all other footprint physical fields unchanged')
if __name__=='__main__':run()
