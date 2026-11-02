"""Read-only native copper plots for the local watchdog placement review."""
import json
import subprocess
import sys
from pathlib import Path
from hardware.fabrication.audit_candidate import native_evidence_errors,sha


def run():
    assert sys.platform=='linux'
    folder=Path(__file__).resolve().parent/'staging/nf-watchdog-routed-native-02'
    project=folder/'negative_startup_physical.kicad_pro'
    report=json.loads((folder/'review.json').read_text())
    assert not native_evidence_errors(project,report)
    pcb=project.with_suffix('.kicad_pcb');out=folder/'plots';out.mkdir(exist_ok=True)
    for name,layers in [('front','F.Cu,F.Fab,Edge.Cuts'),('back','B.Cu,B.Fab,Edge.Cuts'),('ground','In1.Cu,Edge.Cuts')]:
        assert not (out/f'{name}.pdf').exists()
        subprocess.run(['kicad-cli','pcb','export','pdf','--layers',layers,'--mode-single','--output',str(out/f'{name}.pdf'),str(pcb)],check=True,timeout=30)
    assert sha(pcb)==report['checked_PCB_sha256']


if __name__=='__main__':run()
