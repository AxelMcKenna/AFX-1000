"""Author the TBP73 short AUX join from the pad-aware current-board screen."""
import json
from pathlib import Path
from hardware.fabrication import route_two_board_aux_local_distribution as build
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.electronics.common.sexpr import read_sexpr,first,sexpr

def run():
    build.BASE=STAGING/'two-board-power-aux-ground-reuse-native-01'
    build.CAP=STAGING/'two-board-power-routing-inputs-aux-ground-reuse-01/capture.json'
    build.PLAN=STAGING/'two-board-aux-local-distribution-plan-06/plan.json'
    build.OUT=STAGING/'two-board-power-aux-local-distribution-03'
    build.run()
    p=build.OUT/'power_protection.kicad_sch';tree=read_sexpr(p.read_text());first(first(tree,'title_block'),'rev')[1]='TBP73-CANDIDATE';p.write_text(sexpr(tree)+'\n')
    p=build.OUT/'aux-local-distribution-routing.json';data=json.loads(p.read_text())
    data['source_sha256'][str(Path(__file__).relative_to(REPO))]=sha(Path(__file__))
    data['source_sha256']['hardware/fabrication/plan_two_board_aux_local_distribution_v6.py']=sha(REPO/'hardware/fabrication/plan_two_board_aux_local_distribution_v6.py')
    p.write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':run()
