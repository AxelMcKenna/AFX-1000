"""Preserve routed controls for continuation; center only two new ground ends."""

import argparse
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from .route_e28 import WORK, sha


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--parent",default="eight-control-reroute")
    parser.add_argument("--native",default="native-eight-control-reroute")
    parser.add_argument("--next",default="eight-control-continuation-01")
    options=parser.parse_args()
    assert all(all(c.isalnum() or c=="-" for c in name) for name in (options.parent,options.native,options.next))
    assert options.parent.startswith("eight-control-") and options.next.startswith("eight-control-")
    assert options.native.startswith("native-eight-control-")
    parent=WORK/"generated"/options.parent
    source=parent/"imported.kicad_pcb"
    protected_source=WORK/"generated/eight-control-reroute/rail_disconnect.kicad_pcb"
    native=WORK/"generated"/options.native/"drc.json"
    out=WORK/"generated"/options.next
    out.mkdir(exist_ok=False)
    tree=read_sexpr(source.read_text())
    frozen_ids={str(first(n,"uuid")[1]) for kind in ("segment","via") for n in children(read_sexpr(protected_source.read_text()),kind)}
    segments={str(first(n,"uuid")[1]):n for n in children(tree,"segment")}
    vias={str(first(n,"uuid")[1]):n for n in children(tree,"via")}
    raw=json.loads(native.read_text())
    corrections=[]
    errors=[r for r in raw["violations"] if r["severity"]=="error"]
    assert all(r["type"]=="track_not_centered_on_via" for r in errors)
    for row in errors:
        track=next(segments[i["uuid"]] for i in row["items"] if i["uuid"] in segments)
        via=next(vias[i["uuid"]] for i in row["items"] if i["uuid"] in vias)
        assert str(first(track,"uuid")[1]) not in frozen_ids
        xy=list(map(float,first(via,"at")[1:3]))
        old=sexpr(track)
        for key in ("start","end"):
            end=first(track,key)
            if sum((float(end[i+1])-xy[i])**2 for i in (0,1))<.001**2:
                end[1:3]=[a(v) for v in xy]
        corrections.append(dict(before=old,after=sexpr(track),target_via_uuid=str(first(via,"uuid")[1])))
        if first(track,"start")[1:3]==first(track,"end")[1:3]:
            tree.remove(track)
    pcb=out/"rail_disconnect.kicad_pcb"
    pcb.write_text(sexpr(tree)+"\n")
    for suffix in (".kicad_pro",".kicad_sch"):
        shutil.copyfile(parent/("rail_disconnect"+suffix),out/("rail_disconnect"+suffix))
    for name in ("fp-lib-table","sym-lib-table"):
        shutil.copyfile(parent/name,out/name)
    (out/"construction.json").write_text(json.dumps(dict(source_sha256=sha(source),candidate_sha256=sha(pcb),
        native_findings_sha256=sha(native),recipe_sha256=sha(Path(__file__)),new_ground_end_corrections=corrections,
        original_protected_copper_never_edited=True,all_footprints_and_rules_unchanged=True,
        known_unresolved_N19_power_connection=True,native_checks_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Staged isolated routing continuation; only new ground endpoints centered")


if __name__=="__main__":
    run()
