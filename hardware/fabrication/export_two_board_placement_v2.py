"""Export TB05 and carry forward only the existing internal-land exceptions."""
import json
from pathlib import Path
from hardware.fabrication import export_two_board_placement as parent
from hardware.electronics.common.sexpr import children,read_sexpr,sexpr


def run():
    parent.FOLDER=parent.ROOT/'staging/two-board-placement-05'
    parent.OUT=parent.ROOT/'staging/two-board-placement-cad-02'
    parent.build()
    paths=[Path(__file__)]
    for board,source,refs in [
        ('signal_main',parent.ROOT/'staging/audio-main-controls-06/audio_core.kicad_dru',{'U101':'A_U101','U102':'A_U102','U105':'A_U105','U106':'A_U106'}),
        ('power_protection',parent.REPO/'hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/power_p03.kicad_dru',{'U20':'P_U20','U23':'P_U23'})]:
        text=source.read_text();paths.append(source)
        # Preserve 0.20 general clearance for both new boards. Source-specific
        # same-package exceptions retain their exact 0.15 mm minima and scope.
        begin=text.index('(rule ',text.index('(rule ')+1)
        inherited=text[begin:]
        for old,new in refs.items():inherited=inherited.replace("memberOfFootprint('"+old+"')","memberOfFootprint('"+new+"')")
        target=parent.OUT/(board+'.kicad_dru')
        target.write_text('(version 1)\n(rule "General copper clearance" (constraint clearance (min 0.20mm)))\n'+inherited)
    result=dict(source_sha256={str(p.relative_to(parent.REPO)):parent.sha(p) for p in paths},
        artifact_sha256={p.name:parent.sha(p) for p in parent.OUT.glob('*.kicad_dru')},
        general_clearance_mm=.2,inherited_internal_pad_clearance_mm=.15,
        new_clearance_waivers=False,ignored_rule_categories=[],fabrication_released=False)
    (parent.OUT/'inherited-rules.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':run()
