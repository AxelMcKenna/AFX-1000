"""Native copper inspection plots for the mounting-aware local-routing pass."""
import json
import subprocess
import sys
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    assert sys.platform=='linux'
    folder=STAGING/'two-board-power-routed-native-04'
    pcb=folder/'power_protection.kicad_pcb'
    report=json.loads((folder/'review.json').read_text())
    assert sha(pcb)==report['artifact_sha256'][pcb.name]
    output=folder/'plots';output.mkdir(exist_ok=False)
    commands=[];artifacts=[]
    for name,layer in [('front','F.Cu'),('back','B.Cu'),*[(f'inner{i}',f'In{i}.Cu') for i in range(1,7)]]:
        target=output/(name+'.svg')
        cmd=['kicad-cli','pcb','export','svg','--layers',layer+',Edge.Cuts','--page-size-mode','2',
             '--mode-single','--exclude-drawing-sheet','--output',str(target),str(pcb)]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        assert p.returncode==0,(cmd,p.stdout,p.stderr)
        commands.append(cmd);artifacts.append(target)
    assert sha(pcb)==report['artifact_sha256'][pcb.name]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),pcb,folder/'review.json']},
        artifact_sha256={p.name:sha(p) for p in artifacts},commands=commands,
        visual_inspection_pending=True,fabrication_released=False)
    (output/'native-plots.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Eight native power-board copper views exported')


if __name__=='__main__':run()
