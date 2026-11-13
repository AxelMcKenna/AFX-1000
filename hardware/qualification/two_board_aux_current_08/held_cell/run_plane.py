"""Guarded Linux entry point; preflight before native work, record parent failures too."""
import json,sys
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from hardware.qualification.two_board_aux_current_08.held_cell.preflight import zone_coordinates
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded

def run(h,out):
 h=Path(h);out=Path(out);assert not out.exists() or (out.is_dir() and not any(out.iterdir())),'Preserve previous attempt';plan=json.loads((h/'held_cell/plane-plan-03.json').read_text());tree=read_sexpr((h/'held_cell/authored-03/power_protection.kicad_pcb').read_text());z=next(z for z in children(tree,'zone') if first(z,'uuid')[1]==plan['new_zone_uuid']);assert zone_coordinates(z)==[plan['outline_mm']]
 out.mkdir(exist_ok=True);result=run_recorded([sys.executable,str(h/'held_cell/native_plane.py'),str(h),str(out)],out/'parent-process',timeout=420,input_paths=[h/'held_cell/authored-03/power_protection.kicad_pcb',h/'held_cell/plane-plan-03.json']);assert result['status']=='passed' and all(result['inputs_unchanged'].values()),'Native pipeline failed; inspect parent-process'
if __name__=='__main__':run(*sys.argv[1:])
