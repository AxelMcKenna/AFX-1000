"""Adopt only selected NF logic routes; restore protected source copper exactly."""

import json
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.bypass_import import identity
from hardware.fabrication.routing_nets import is_logic_net

if sys.platform == "linux":
    import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT/"staging/nf-targeted-logic-01"


def copper(node):
    return isinstance(node,list) and node and node[0] in ("segment","via")


def selected(node):
    return copper(node) and is_logic_net(str(first(node,"net")[-1]))


def run():
    assert sys.platform == "linux"
    output = WORK/"logic-merged.kicad_pcb"
    assert not output.exists()
    command = json.loads((WORK/"router-command.json").read_text())
    assert command.get("returncode") == 0 and command["session_exists"]
    session = WORK/"routed.ses"
    assert sha(session) == command["session_sha256"]
    router = json.loads((WORK/"router-result.json").read_text())
    assert router["settings_snapshot"]["autorouter"]["ignore_net_classes"] == ["AFX_PROTECTED"]
    source = WORK/"original.kicad_pcb"
    export = json.loads((WORK/"export.json").read_text())
    assert sha(source) == export["source_PCB_sha256"]
    hashes = {str(p):sha(p) for p in (source,session,WORK/"input.kicad_pcb",WORK/"router-command.json",Path(__file__))}
    text = session.read_text()
    if "(component \n" in text:
        assert text.count("(component \n") == 1
        session = WORK/"adapted-routed.ses"
        adapted = text.replace("(component \n",'(component ""\n')
        if session.exists():
            assert session.read_text() == adapted
        else:
            session.write_text(adapted)
    board = pcbnew.LoadBoard(str(WORK/"input.kicad_pcb"))
    before = identity(board)
    assert len(before) == 267
    assert pcbnew.ImportSpecctraSES(board,str(session))
    after = identity(board)
    assert set(after) == set(before)
    deltas = {ref:dict(before=list(before[ref]),after=list(after[ref])) for ref in before if before[ref] != after[ref]}
    (WORK/"imported-pose-diagnostics.json").write_text(json.dumps(deltas,indent=2)+"\n")
    print("Raw SES placement differences",len(deltas),flush=True)
    for ref in before:
        a,b = before[ref],after[ref]
        assert a[:3] == b[:3] and a[5:] == b[5:],(ref,a,b)
        assert max(abs(a[3]-b[3]),abs(a[4]-b[4])) <= 500,(ref,a,b)
    imported = WORK/"raw-import.kicad_pcb"
    assert pcbnew.SaveBoard(str(imported),board)
    original,routed = [read_sexpr(p.read_text()) for p in (source,imported)]
    protected = [sexpr(n) for n in original if copper(n) and not selected(n)]
    removed = [str(first(n,"uuid")[1]) for n in original if selected(n)]
    result = [n for n in original if not selected(n)]
    inserted,raised = [],[]
    for node in routed:
        if not selected(node):
            continue
        if node[0] == "segment":
            assert str(first(node,"layer")[1]) in ("F.Cu","In2.Cu","In3.Cu","B.Cu")
            width = first(node,"width")
            if float(width[1]) < .16:
                assert float(width[1]) == .15
                raised.append(str(first(node,"uuid")[1]))
                width[1] = .16
        else:
            assert float(first(node,"drill")[1]) >= .3
        inserted.append(node)
    assert inserted
    result.extend(inserted)
    assert [sexpr(n) for n in result if copper(n) and not selected(n)] == protected
    def noncopper(tree):
        return [sexpr(n) for n in tree if not copper(n)]
    assert noncopper(result) == noncopper(original)
    output.write_text(sexpr(result)+"\n")
    assert all(sha(Path(p)) == digest for p,digest in hashes.items())
    (WORK/"logic-merge.json").write_text(json.dumps(dict(source_sha256=hashes,
        output_PCB_sha256=sha(output),protected_copper_objects_exact=len(protected),
        original267_footprints_all_authored_zones_and_other_objects_exact=True,
        removed_logic_copper_UUIDs=removed,imported_logic_copper_objects=len(inserted),
        router_fanout_widths_raised_to_existing_0p16mm_minimum=raised,
        no_project_rule_values_relaxed=True,new_logic_via_plane_clearances_require_PDN_review=True,
        native_checks_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Merged",len(inserted),"logic objects;",len(protected),"protected objects exact; native checks pending")


if __name__ == "__main__":
    run()
