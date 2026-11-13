"""Bounded changed-workload diagnostic; preserve timeout/crash evidence durably."""
import json,sys
from pathlib import Path
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);script=H/'ldo_local/fill_one.py';src=H/'ldo_local/native-05/authored-fill.kicad_pcb';r=run_recorded(['python3',str(script),str(src),str(OUT)],OUT/'process',90,[script,src]);print(json.dumps(r));assert r['status']=='passed'
