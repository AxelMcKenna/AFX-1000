import csv,json,math
from pathlib import Path
from .verify import HERE,sha

def run(root):
 cp=root/'hardware/fabrication/staging/two-board-power-routing-inputs-aux-local-distribution-03/capture.json';bp=HERE.parent/'held_rail/candidate-bom.csv';cap=json.loads(cp.read_text());bom={r['reference']:r for r in csv.DictReader(bp.open())};objects={(o['ref'],o['pin']):o for o in cap['objects'] if o.get('ref')};byid={o['uuid']:o for o in cap['objects']};rows=[]
 for driver,capacitor in [('E_U1','E_C29'),('E_U2','E_C36'),('E_U3','E_C9'),('E_U4','E_C13')]:
  vdd=objects[driver,'1'];gnd=objects[driver,'2'];pos=objects[capacitor,'1'];neg=objects[capacitor,'2'];members=cap['all_groups'][pos['group']];rows.append({'driver':driver,'proposed_local_bypass':capacitor,'value':bom[capacitor]['value'],'MPN':bom[capacitor]['MPN'],'footprint':bom[capacitor]['footprint'],'supply_pad_span_mm':math.dist(vdd['position_mm'],pos['position_mm']),'return_pad_span_mm':math.dist(gnd['position_mm'],neg['position_mm']),'supply_branch_members':members,'supply_branch_pad_contacts':[[byid[u]['ref'],byid[u]['pin']] for u in members if byid[u]['kind']=='PAD'],'supply_branch_same_group_as_driver':pos['group']==vdd['group'],'capacitor_ground_group':neg['group'],'capacitor_ground_group_size':len(cap['all_groups'][neg['group']]),'capacitor_ground_is_main':neg['group']=='00b41082-e346-59e4-aee2-f34d9b87e697','driver_ground_is_main':gnd['group']=='00b41082-e346-59e4-aee2-f34d9b87e697','already_qualified_decoupling':False})
 (HERE/'bypass-audit.json').write_text(json.dumps({'source_sha256':{'capture':sha(cp),'bom':sha(bp)},'rows':rows,'schematic_retarget_performed':False,'finding':'C29/C36 can replace C1/C5 as held-rail bypass assignments only with explicit schematic and complete native supply-branch changes plus return/loop completion; exact capacitor MPNs and effective capacitance still unqualified'},indent=2)+'\n')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
