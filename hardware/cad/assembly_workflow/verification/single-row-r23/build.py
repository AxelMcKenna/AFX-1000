"""Full connector screen with exact own allocations replaced and actual pin holes."""
import copy,json,math
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.assembly_workflow.pcb_updates.r44.build import boxes
HERE=Path(__file__).resolve().parent

def run():
    previous=HERE/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    data,components,checks,_=w.load_manifest(previous)
    cap_path=w.ROOT/data['mechanical_capture'];cap=json.loads(cap_path.read_text())
    audit_path=HERE/'current-board-audit.json';audit=json.loads(audit_path.read_text())
    assert w.sha(w.ROOT/data['boards']['signal'])==audit['board_provenance']['sha256']
    old=json.loads((w.ROOT/'hardware/cad/two_board_installation_06/r23_single_row_mates/board-audit.json').read_text());assert audit['headers']==old['headers']
    own={r['reference'] for r in audit['headers']};assert len(own)==11
    excluded=set(json.loads((w.HERE/'base.json').read_text())['replaced_allocations'])|own
    rows=[r for r in cap['component_envelopes']+cap['tail_envelopes'] if r[0] not in excluded]
    (HERE/'allocations.scad').write_text(boxes('r23_other_component_allocations',rows))
    components['base_component_allocations']['source']=w.relative(HERE/'allocations.scad');components['base_component_allocations']['module']='r23_other_component_allocations'
    lines=['// Diagnostic substrates: retain captured profiles/mount holes; add exactly35 current native connector drills.','module r23_substrates_with_connector_drills(){']
    for board in cap['boards']:
        holes=copy.deepcopy(board['holes'])
        if board['id']=='signal':
            for row in audit['headers']:
                for pad in row['pads']:
                    assert pad['drill_mm']==1 and .34*math.sqrt(2)<pad['drill_mm']/2
                    holes.append(pad['xy_mm']+[pad['drill_mm']])
        lines.append('translate([0,0,'+str(board['z'])+'])linear_extrude('+str(board['thickness'])+')difference(){polygon('+json.dumps(board['outline'])+');')
        lines.extend('translate('+json.dumps(h[:2])+')circle(d='+str(h[2])+');' for h in holes);lines.append('}')
    lines.append('}');(HERE/'substrates.scad').write_text('\n'.join(lines)+'\n')
    bindings=dict(data['_loaded_sources'])
    for f in [Path(__file__),cap_path,audit_path,HERE/'allocations.scad',HERE/'substrates.scad']:bindings[w.relative(f)]=w.sha(f)
    registry={'schema_version':1,'components':list(components.values())+[{'id':'r23_substrates','source':w.relative(HERE/'substrates.scad'),'module':'r23_substrates_with_connector_drills','role':'receiving'}],'source_sha256':bindings,'intentional_contacts':sum((x['intentional_contacts'] for x in data['contracts']),[])}
    (HERE/'base-registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    m=json.loads(previous.read_text());m['registries']=[w.relative(HERE/'base-registry.json'),'hardware/cad/two_board_installation_06/workflow_adapter/single-row-mates-registry.json']
    new='panel_single_row_mates_r23'
    for check in list(m['checks']):
        if check['id'].startswith('r20_signal_'):
            c=copy.deepcopy(check);c['id']=c['id'].replace('r20_signal_','r23_mates_');c['left']=[new]
            c['right']=['r23_substrates' if x=='base_main_pcbs' else x for x in c['right']]
            if c['id'].endswith('base_ground_supports'):c['right'].append('panel_signal_r20_scene2')
            m['checks'].append(c)
    (HERE/'candidate.json').write_text(json.dumps(m,indent=2)+'\n')
    d,c,k,_=w.load_manifest(HERE/'candidate.json');print(len(c),'diagnostic roles;',len(k),'checks')
if __name__=='__main__':run()
