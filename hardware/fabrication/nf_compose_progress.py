"""Combine only five NF net improvements; retain all other source objects."""
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,native_evidence_errors

ROOT=Path(__file__).resolve().parent
REPLACED={'/N19_WD_ENABLE','/N12_START','/N19_START_DELAY_N'}
ADDITIVE={'/CLAMP_SUPPLY_ENABLE','/N12_ARM_CONDITIONED'}


def copper(n):
    return isinstance(n,list) and n and n[0] in ('segment','via')


def run():
    folders=[ROOT/'staging'/n for n in ('nf-arm-only-native-01','nf-targeted-native-01','nf-compact-native-01')]
    projects=[f/'negative_startup_physical.kicad_pro' for f in folders]
    paths=[p.with_suffix('.kicad_pcb') for p in projects]
    for p in projects:
        assert not native_evidence_errors(p,json.loads((p.parent/'review.json').read_text()))
    original,targeted,compact=[read_sexpr(p.read_text()) for p in paths]
    original_ids={str(first(n,'uuid')[1]) for n in original if copper(n)}
    additions=[n for n in compact if copper(n) and str(first(n,'uuid')[1]) not in original_ids]
    assert additions and all(first(n,'net')[-1] in ADDITIVE for n in additions)
    replacements=[n for n in targeted if copper(n) and first(n,'net')[-1] in REPLACED]
    assert replacements
    result=[n for n in original if not (copper(n) and first(n,'net')[-1] in REPLACED)]+replacements+additions
    identifiers=[str(first(n,'uuid')[1]) for n in result if copper(n)]
    assert len(identifiers)==len(set(identifiers))
    assert [sexpr(n) for n in children(result,'footprint')]==[sexpr(n) for n in children(original,'footprint')]
    output=ROOT/'staging/nf-five-net-composition-01'
    output.mkdir(exist_ok=False)
    pcb=output/paths[0].name
    pcb.write_text(sexpr(result)+'\n')
    inputs=[*paths,*projects,Path(__file__),*[f/'review.json' for f in folders]]
    (output/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),
        replaced_nets=sorted(REPLACED),additive_nets=sorted(ADDITIVE),
        all_other_authored_objects_retained=True,added_copper_objects=len(additions),
        native_checks_pending=True,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':
    run()
