"""Build the reviewed zero-argument adapter without modifying frozen geometry."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=HERE.parent
rows=[]
def add(name,src,body,role='installed',category='control',uncertainty='Frozen project geometry; supplier tolerances and physical assembly remain unqualified.'):
    rows.append(dict(id='controls_'+name,source=str((HERE/'controls.scad').relative_to(ROOT)),module='controls_'+name,role=role,category=category,description=name.replace('_',' '),uncertainty=uncertainty,delegate_source=src,delegate_body=body))
add('display','display.scad','tbh04_display_installed(); tbh04_fasteners();')
add('display_wiring','display.scad','tbh04_wire_reserve();','receiving')
add('selectors','selectors.scad','tbh04_selector_brackets(); tbh04_selector_pcbs(); tbh04_selector_bodies(); tbh04_selector_leads(); tbh04_selector_fasteners();')
add('selector_wiring','selectors.scad','tbh04_selector_wiring();','receiving')
add('selector_motion','selectors.scad','tbh04_selector_motion();','motion')
for name in ['meters','banks']:
    src='led_follow_on/'+name+'.scad'
    add(name,src,' '.join('tbh05_'+name+'_'+x+'();' for x in ['frames','boards','emitters','fasteners']))
    add(name+'_lenses',src,'tbh05_'+name+'_lenses();')
    add(name+'_wiring',src,'tbh05_'+name+'_wires();','receiving')
add('ring','ring_follow_on/ring.scad','tbh06_pose(){tbh06_frame(); tbh06_board(); tbh06_emitters(); tbh06_resistors(); tbh06_fasteners();}')
add('ring_lens','ring_follow_on/ring.scad','tbh06_pose()tbh06_lens();')
add('ring_wiring','ring_follow_on/ring.scad','tbh06_pose()tbh06_wires();','receiving')
add('button_indicators','button_follow_on/buttons.scad','tbh07_boards_installed(); tbh07_emitters(); tbh07_solder(); tbh07_shims(); tbh07_fasteners();')
add('button_wiring','button_follow_on/buttons.scad','tbh07_wires();','receiving')
add('button_motion','led_follow_on/button_motion.scad','tbh05_button_motion_native();','motion')
add('lid','button_follow_on/buttons.scad','translate([0,0,43.6])tbh07_lid_variant();',category='printed_part')
add('guide','connected_guide.scad','translate([0,0,42.2])tbh07_connected_guide_variant();',category='printed_part')
add('knobs','pot_follow_on/knobs.scad','tbh04_pot_knobs_installed();',category='printed_part')
add('pot_hardware','pot_follow_on/knobs.scad','tbh04_pot_panel_hardware();')
add('pot_shafts','pot_follow_on/knobs.scad','tbh04_pot_shafts_max();','receiving',uncertainty='Maximum shaft/bushing receiving envelope for selected 25 mm shaft candidate, not an installed solid.')
add('pot_body','pot_follow_on/body_receiving.scad','tbh04_pot_body_receiving();','receiving',uncertainty='Project 16 x 16 mm allocation; exact center-detent procurement and supplier body qualification remain open.')
for name,delegate in [('keycaps','keys'),('switches','switches'),('retaining_clips','clips')]:
    add(name,'workflow_adapter/key_scope.scad','controls_'+delegate+'_delegate();',category='printed_part' if name!='switches' else 'purchased_part_reference',uncertainty='Frozen 29-key geometry.' if name!='switches' else 'Frozen switch case/plunger reference; terminals are not modeled; not supplier STEP.')
add('button_mechanisms','workflow_adapter/key_scope.scad','controls_mechanisms_delegate();',category='mechanism_reference',uncertainty='Frozen full 29-button rest-state mechanism: holders, clips, switch references, spring rings and compliant pucks. Spring/compliance and supplier tolerances unqualified.')
add('touch_backer','workflow_adapter/key_scope.scad','controls_touch_backer_delegate();',category='printed_part')
add('touch_lens','workflow_adapter/key_scope.scad','controls_touch_lens_delegate();',category='printed_part')
capture_path=BASE.parent/'two_board_print_01/capture.json'
capture=json.loads(capture_path.read_text())
touch=next(x for x in capture['context'] if x['id']=='touch_module_body_and_tail_reserve')
x0,y0,x1,y1=touch['xy'];z0,z1=touch['z']
(HERE/'touch_reserve.scad').write_text('// Generated directly from capture.json context touch_module_body_and_tail_reserve.\nmodule controls_touch_reserve_delegate(){translate('+json.dumps([x0,y0,z0])+')cube('+json.dumps([x1-x0,y1-y0,z1-z0])+');}\n')
add('touch_module_receiving','workflow_adapter/touch_reserve.scad','controls_touch_reserve_delegate();','receiving',uncertainty='Frozen captured module body/tail allocation only; no selected physical touch PCB is asserted.')
rows[-1]['capture_binding']={'source':str(capture_path.relative_to(ROOT)),'context_id':touch['id'],'xy':touch['xy'],'z':touch['z']}
for row in rows:row['scene']=row['role']=='installed' and row['id'] not in ['controls_switches','controls_retaining_clips']
imports=sorted({x['delegate_source'] for x in rows})
scad='// Generated adapters: no top-level geometry. World frame millimetres.\n'+''.join('use <../'+x+'>\n' for x in imports)
scad+='\n'+''.join('module '+x['module']+'(){'+x['delegate_body']+'}\n' for x in rows)
(HERE/'controls.scad').write_text(scad)
closure={}
def visit(p):
    p=p.resolve(); key=str(p.relative_to(ROOT))
    if key in closure:return
    closure[key]=hashlib.sha256(p.read_bytes()).hexdigest()
    if p.suffix=='.scad':
        for rel in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()):visit(p.parent/rel)
visit(HERE/'controls.scad')
visit(capture_path)
visit(BASE.parent/'a11/assembly.scad')
active=json.loads((BASE/'active-controls.json').read_text())
assembly=json.loads((BASE/'panel_electrical/assembly-manifest.json').read_text())
for path in ['active-controls.json','panel_electrical/assembly-manifest.json','panel_electrical/assembly-native-r3/review.json','panel_electrical/assembly-native-r3/functional-review.json']:
    visit(BASE/path)
for b in active['boards']:visit(BASE/b['path'])
for p in sorted((BASE/'panel_electrical/assembly').rglob('*')):
    if p.is_file():visit(p)
r=dict(schema_version=1,coordinate_frame='housing world coordinates, mm',fabrication_released=False,components=rows,source_sha256=closure,
 intentional_contacts=[dict(components=['controls_lid','controls_button_indicators'],reason='Indicator top shims seat at lid underside Z43.6; verify contact faces, not blanket overlap permission.',evidence='button_follow_on/buttons.scad:tbh07_shims'),dict(components=['controls_guide','controls_button_indicators'],reason='Indicator boards seat on final guide at Z42.9; retain seating contact while testing interference.',evidence='connected_guide.scad:buttons_down_retention_final')],
 pcb_inventory=dict(physical_instances=34,distinct_designs=12,designs=active['boards'],instances=assembly['passive_board_instances'],paths_relative_to=str(BASE.relative_to(ROOT))),
 panel_electrical=dict(project=str((BASE/'panel_electrical/assembly/panel.kicad_pro').relative_to(ROOT)),schematic=str((BASE/'panel_electrical/assembly/panel.kicad_sch').relative_to(ROOT)),channels=96,fabrication_released=False),
 limitations=['Installed means modeled installed state, not measured or purchased hardware.','Pot bodies, shaft maxima, wire reservations and motion are excluded from default installed geometry.','No duplicate generic captured control boxes or PCB substrates from another assembly may be added.','Full button mechanism includes holders/clips/switches/springs/pucks once; atomic switches/clips have scene=false and root holders must also have scene=false.','Legacy bank/meter/ring combined installed unions omit solder; adapter preserves that omission and adds their separately defined physical lenses.'])
(HERE/'registry.json').write_text(json.dumps(r,indent=2)+'\n')
