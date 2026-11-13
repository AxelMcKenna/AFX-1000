"""Native schematic/PCB checks with durable bounded process records."""
import sys,json,shutil
from pathlib import Path
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
root=Path(sys.argv[1]);out=Path(sys.argv[2]);src=root/'precision/authored';out.mkdir(exist_ok=True)
for n in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(src/n,out/n)
(out/'libraries').symlink_to(root/'shared_cutover/native-04/libraries',target_is_directory=True)
commands=[('netlist',['sch','export','netlist','--format','kicadxml','--output',str(out/'candidate-netlist.xml'),str(src/'power_protection.kicad_sch')]),('erc',['sch','erc','--format','json','--output',str(out/'candidate-erc.json'),str(src/'power_protection.kicad_sch')]),('drc',['pcb','drc','--format','json','--output',str(out/'drc.json'),str(out/'power_protection.kicad_pcb')])]
for name,args in commands:
 r=run_recorded(['kicad-cli',*args],out/(name+'-process'),180,[src/'power_protection.kicad_sch',out/'power_protection.kicad_pcb']);print(name,r['status'],flush=True);assert r['status']=='passed'
(out/'libraries').unlink();(out/'libraries').symlink_to('../../shared_cutover/native-04/libraries',target_is_directory=True)
