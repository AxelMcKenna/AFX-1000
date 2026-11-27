"""Bind existing board allocations into the unified scene; no design changes."""
import json
import re
from pathlib import Path
from hardware.cad.assembly_workflow.workflow import ROOT, HERE, sha, source_closure


def main():
    capture_path = ROOT/'hardware/cad/two_board_print_01/capture.json'
    mate_path = ROOT/'hardware/cad/two_board_installation_06/r10_interfaces/mate-envelopes.json'
    capture = json.loads(capture_path.read_text())
    mates = json.loads(mate_path.read_text())
    captured_scad = (ROOT/'hardware/cad/two_board_print_01/captured.scad').read_text()
    profiles = json.loads(re.search(r'^board_profiles = (.*);$', captured_scad, re.M)[1])
    assert profiles == [[b['outline'],b['z'],b['holes']] for b in capture['boards']], 'SCAD/PCB capture disagreement'
    assert json.loads(re.search(r'^mounts = (.*);$', captured_scad, re.M)[1]) == capture['mounts']
    replaced = {m['ref'] for m in mates['mates']} | {'D_J1010'}
    rows = [b for b in capture['component_envelopes'] + capture['tail_envelopes'] if b[0] not in replaced]
    target = HERE/'board_allocations.scad'
    target.write_text('// Frozen receiving boxes, excluding explicitly replaced connectors.\nmodule base_component_allocations(){\n' + '\n'.join(
        'translate('+json.dumps([b[1][0], b[1][1], b[2][0]])+')cube('+json.dumps([b[1][2]-b[1][0], b[1][3]-b[1][1], b[2][1]-b[2][0]])+');' for b in rows) + '\n}\n')
    entries = []
    for ident, label in [('main_pcbs','Two main PCB substrates'),('rear_panel','One-piece rear panel'),('button_holders','Atomic switch holders; composite mechanisms own the scene copies'),('lid_bars','Split-lid joining bars; excluded from one-piece scene'),('board_heads','Board screw heads excluding sensor replacements D_H2 and D_H5')]:
        entries.append(dict(id='base_'+ident, source='hardware/cad/assembly_workflow/base.scad',module='base_'+ident,role='installed',category='base',description=label,scene=ident not in ('button_holders','lid_bars'),uncertainty='Captured nominal geometry; physical receiving remains open'))
    entries.append(dict(id='base_component_allocations',source='hardware/cad/assembly_workflow/board_allocations.scad',module='base_component_allocations',role='receiving',category='pcb_population',description='Main-board body/tail receiving boxes excluding seven replaced connector allocations',uncertainty='Provisional heights and courtyard/body allocations; not exact supplier STEP',scene=True))
    sources = {}
    for item in entries:
        source_closure(ROOT/item['source'],sources)
    for path in [capture_path,mate_path,Path(__file__)]:
        sources[str(path.relative_to(ROOT))]=sha(path)
    data = dict(schema_version=1, components=entries, source_sha256=sources,
                selected_variant='one_piece', replaced_allocations=sorted(replaced),
                excluded_scene_duplicates=['base_button_holders','base_lid_bars'],
                intentional_contacts=[dict(components=['base_board_heads','base_main_pcbs'],reason='Mount screw/board seating; no blanket clearance waiver',blanket_pair_exclusion=False)])
    (HERE/'base.json').write_text(json.dumps(data,indent=2)+'\n')


if __name__=='__main__':
    main()
