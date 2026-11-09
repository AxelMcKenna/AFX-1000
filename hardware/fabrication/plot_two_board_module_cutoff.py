"""Export the actual native TBP10 module-protection schematic for review."""
import json
import subprocess
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    folder=STAGING/'two-board-power-native-10'
    source=folder/'G_module_input.kicad_sch'
    target=folder/'plots-module';target.mkdir(exist_ok=False)
    before=sha(source)
    cmd=['kicad-cli','sch','export','svg','-o',str(target),str(source)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert sha(source)==before
    record=dict(source_sha256={str(f.relative_to(REPO)):sha(f) for f in [Path(__file__),source]},command=cmd,
        artifact_sha256={f.name:sha(f) for f in target.glob('*.svg')},
        note='Direct sheet export; full-hierarchy netlist is authoritative for references and connectivity.')
    (target/'native-plot.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Actual TBP10 module sheet exported')


if __name__=='__main__':run()
