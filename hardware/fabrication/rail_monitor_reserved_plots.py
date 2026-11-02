"""Read-only native inner-plane plots and temporary copper inspection PDFs."""
import json
import subprocess
import sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha, native_evidence_errors

ROOT = Path(__file__).resolve().parent


def run():
    assert sys.platform == 'linux'
    folder = ROOT/'staging/rail-monitor-reserved-closed-native-02'
    project = folder/'rail_monitor.kicad_pro'
    report = json.loads((folder/'review.json').read_text())
    assert not native_evidence_errors(project,report)
    assert report['status']['native_closed']
    pcb = project.with_suffix('.kicad_pcb')
    for name,layers in [('bottom','B.Cu,B.Fab,Edge.Cuts'),('supply','In2.Cu,Edge.Cuts'),('ground','In1.Cu,Edge.Cuts')]:
        pdf = folder/'plots'/f'inspection-{name}.pdf'
        assert not pdf.exists()
        subprocess.run(['kicad-cli','pcb','export','pdf','--layers',layers,'--mode-single','--output',str(pdf),str(pcb)],check=True,timeout=30)
        if name != 'bottom':
            target = folder/'plots'/name
            target.mkdir(exist_ok=False)
            subprocess.run(['kicad-cli','pcb','export','svg','--layers',layers,'--page-size-mode','2','--mode-single','--exclude-drawing-sheet','--output',str(target/f'{name}.svg'),str(pcb)],check=True,timeout=30)
    assert sha(pcb) == report['checked_PCB_sha256']


if __name__ == '__main__':
    run()
