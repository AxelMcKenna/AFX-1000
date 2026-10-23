#!/usr/bin/env python3
"""Export current DRC-checked B1 Gerber/drill drafts for review; no order/upload."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from generate_budget import ROOT,DEST
from check_carrier import sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cli',type=Path,required=True);a=p.parse_args()
    subprocess.run([sys.executable,str(ROOT/'tools/check_budget_pcb.py'),'--check'],check=True)
    board=DEST/'pcb/carrier.kicad_pcb';out=DEST/'pcb/fabrication-draft';out.mkdir(parents=True,exist_ok=True)
    build=ROOT/'build/hardware/budget-native'
    env=dict(os.environ,KICAD_CONFIG_HOME=str(build/'config'),FONTCONFIG_FILE=str(build/'fonts.conf'))
    commands=[['pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts','--output',str(out),str(board)],
              ['pcb','export','drill','--format','excellon','--excellon-units','mm','--excellon-separate-th','--generate-map','--map-format','svg','--output',str(out),str(board)]]
    for command in commands:subprocess.run([str(a.cli),*command],env=env,check=True,capture_output=True,text=True)
    (out/'README.txt').write_text('B1 ENGINEERING REVIEW DRAFT\n100x100mm / four copper layers / 1.6mm nominal FR4\nInner1 GND; Inner2 5V with signal escapes.\nNot a production release. Confirm stackup, exact components, dimensions and assembly fit before prototype fabrication.\nNo order has been placed. Physical audio/fault/thermal qualification is unperformed.\nSee hardware/budget/README.md and pcb/native-check.json for scope.\n')
    files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='export-record.json'}
    (out/'export-record.json').write_text(json.dumps(dict(status='Engineering review draft; not a fabrication release',board_sha256=sha(board),native_record_sha256=sha(DEST/'pcb/native-check.json'),files_sha256=files),indent=2)+'\n')
    print(f'Exported {len(files)} review files; no fabrication order or production approval')


if __name__=='__main__':main()
