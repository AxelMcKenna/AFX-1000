"""Read-only native plots for an unselected eight-layer feasibility trial."""
import json
import subprocess
import sys
from pathlib import Path
from hardware.fabrication.audit_candidate import native_evidence_errors, sha


def run():
    assert sys.platform == 'linux'
    folder = Path(__file__).resolve().parent/'staging/nf-eight-cell-native-02'
    project = folder/'negative_startup_physical.kicad_pro'
    review = json.loads((folder/'review.json').read_text())
    assert not native_evidence_errors(project, review)
    pcb = project.with_suffix('.kicad_pcb'); out = folder/'plots'; out.mkdir(exist_ok=True)
    for name, layers in [('front','F.Cu,F.Fab,Edge.Cuts'), ('back','B.Cu,B.Fab,Edge.Cuts'),
                         ('ground','In1.Cu,Edge.Cuts'), ('new-in4','In4.Cu,Edge.Cuts'),
                         ('new-in5','In5.Cu,Edge.Cuts'), ('aux-in6','In6.Cu,Edge.Cuts')]:
        target = out/f'{name}.pdf'; assert not target.exists()
        subprocess.run(['kicad-cli','pcb','export','pdf','--layers',layers,'--mode-single','--output',str(target),str(pcb)],check=True,timeout=30)
    assert sha(pcb) == review['checked_PCB_sha256']


if __name__ == '__main__': run()
