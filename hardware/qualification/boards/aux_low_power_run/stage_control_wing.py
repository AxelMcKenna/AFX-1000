"""Stage one bounded control-floorplan alternative; retain the checked parent.

Only the lower edge and U38/C81 poses change. Existing copper, rule areas,
mounting holes, schematic and all other footprints remain exact. Native checks
and a complete new assembly review are required before adopting this layout.
"""

import copy
import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from .route_e28 import WORK, sha


def run():
    source=WORK/"generated/eight-layer-followup/rail_disconnect.kicad_pcb"
    screen=WORK/"generated/control-wing-short-screen.json"
    data=json.loads(screen.read_text())
    assert data["proposed_extension_local_xy_mm"]==[5,54.5,75,60.0]
    assert not data["current_NF_FPC_receiving_box_hits"]
    assert all(r["clear"] for rows in data["nominal_mesh_checks"].values() for r in rows.values())
    assert data["source_sha256"][str(source)]==sha(source)
    out=WORK/"generated/control-wing-placement"
    if out.exists():
        assert not any(out.iterdir()), "Refusing to replace an existing candidate"
    else:
        out.mkdir()
    tree=read_sexpr(source.read_text())
    old=copy.deepcopy(tree)
    copper=[sexpr(n) for n in tree if isinstance(n,list) and n and n[0] in ("segment","via","zone")]
    edge=next(n for n in children(tree,"gr_line") if first(n,"layer")[1]=="Edge.Cuts"
              and list(map(float,first(n,"start")[1:3]))==[256.,154.5]
              and list(map(float,first(n,"end")[1:3]))==[105.,154.5])
    path=[(256.,154.5),(175.,154.5),(175.,160.),(105.,160.),(105.,154.5)]
    additions=[]
    for i,(p,q) in enumerate(zip(path,path[1:])):
        node=copy.deepcopy(edge)
        first(node,"start")[1:]=[a(v) for v in p]
        first(node,"end")[1:]=[a(v) for v in q]
        uid=a(str(uuid.uuid5(uuid.NAMESPACE_URL,f"AX03:wing:{sha(source)}:{i}")))
        if children(node,"uuid"):
            first(node,"uuid")[1]=uid
        else:
            node.append([a("uuid"),uid])
        additions.append(node)
    pos=tree.index(edge)
    tree[pos:pos+1]=additions
    moves={"U38":(166.5,157.,0.),"C81":(170.3,155.6,0.)}
    changes=[]
    for f in children(tree,"footprint"):
        ref=next(p[2] for p in children(f,"property") if p[1]=="Reference")
        if ref in moves:
            at=first(f,"at")
            before=list(map(float,at[1:]))
            at[1:]=[a(v) for v in moves[ref]]
            changes.append(dict(ref=ref,old_at_mm_deg=before,new_at_mm_deg=moves[ref]))
    assert len(changes)==2
    assert copper==[sexpr(n) for n in tree if isinstance(n,list) and n and n[0] in ("segment","via","zone")]
    # Reverse only the declared mutations and require a byte-equivalent tree.
    reverted=copy.deepcopy(tree)
    reverted[pos:pos+len(additions)]=[copy.deepcopy(edge)]
    for f in children(reverted,"footprint"):
        ref=next(p[2] for p in children(f,"property") if p[1]=="Reference")
        for change in changes:
            if ref==change["ref"]:
                first(f,"at")[1:]=[a(v) for v in change["old_at_mm_deg"]]
    # Numeric formatting of the two original poses is restored verbatim too.
    oldfps={next(p[2] for p in children(f,"property") if p[1]=="Reference"):f for f in children(old,"footprint")}
    for f in children(reverted,"footprint"):
        ref=next(p[2] for p in children(f,"property") if p[1]=="Reference")
        if ref in moves:
            first(f,"at")[:]=copy.deepcopy(first(oldfps[ref],"at"))
    assert sexpr(reverted)==sexpr(old)
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"floorplan.json").write_text(json.dumps(dict(source_sha256=sha(source),candidate_sha256=sha(pcb),
        recipe_sha256=sha(Path(__file__)),clearance_screen_sha256=sha(screen),
        outline_extension_local_xy_mm=[5,54.5,75,60],original_depth_mm=54.5,new_depth_mm=60,
        depth_growth_fraction=60/54.5-1,added_area_mm2=70*5.5,
        enclosure_dimensions_unchanged=True,moves=changes,
        all_existing_copper_and_rule_areas_exact=True,other_273_footprint_poses_exact=True,
        mounting_holes_unchanged=True,native_checks_pending=True,
        rerouting_bypass_return_and_full_assembly_review_pending=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Staged 70 x 5.5mm control wing; U38 and C81 moved, copper unchanged")


if __name__=="__main__":
    run()
