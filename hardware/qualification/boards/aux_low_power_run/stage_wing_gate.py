"""Move U11 and its underside bypass into the already-cleared control wing.

Retain the eight-open parent, every copper object, outline, hole and rule area.
Only these two poses change; placement and new connections require native review.
"""

import copy
import json
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from .route_e28 import WORK, sha


def run():
    source=WORK/"generated/control-wing-return-smoothed/rail_disconnect.kicad_pcb"
    native=WORK/"generated/native-control-wing-return/review.json"
    screen=WORK/"generated/control-wing-gate-clearance.json"
    data=json.loads(screen.read_text())
    assert "underside_component_space" in data["nominal_mesh_checks"]
    assert not data["current_NF_FPC_receiving_box_hits"]
    assert all(row["clear"] for rows in data["nominal_mesh_checks"].values() for row in rows.values())
    review=json.loads(native.read_text())
    assert review["uncapped_missing_connections"]==8 and review["source_sha256"][str(source)]==sha(source)
    out=WORK/"generated/wing-gate-placement"
    out.mkdir(exist_ok=False)
    tree=read_sexpr(source.read_text())
    old=copy.deepcopy(tree)
    moves={"U11":(125.5,157.2,0.),"C79":(129.75,155.25,0.)}
    changes=[]
    old_poses={}
    for fp in children(tree,"footprint"):
        ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
        if ref not in moves:
            continue
        at=first(fp,"at")
        old_poses[ref]=copy.deepcopy(at)
        changes.append(dict(ref=ref,old_at_mm_deg=list(map(float,at[1:])),new_at_mm_deg=moves[ref],layer=first(fp,"layer")[1]))
        at[1:]=[a(v) for v in moves[ref]]
    assert len(changes)==2
    reverse=copy.deepcopy(tree)
    for fp in children(reverse,"footprint"):
        ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
        if ref in moves:
            first(fp,"at")[:]=old_poses[ref]
    assert sexpr(reverse)==sexpr(old)
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"placement.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in (source,native,screen,Path(__file__))},
        candidate_sha256=sha(pcb),moves=changes,other_273_poses_exact=True,
        all_copper_outline_holes_and_rules_exact=True,schematic_unchanged=True,
        native_checks_and_rerouting_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Moved U11/C79 into the existing wing; all copper, holes and outline retained")


if __name__=="__main__":
    run()
