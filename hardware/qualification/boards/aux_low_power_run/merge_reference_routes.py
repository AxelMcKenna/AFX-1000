"""Trial two natively closed reference-net routes in the ten-open candidate.

Only these two control nets are replaced. Native clearances, filled power
connectivity and complete electrical extraction remain required after merging.
"""

import copy
import json
import re
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from .route_e28 import WORK, sha


def run():
    source=WORK/"generated/eight-layer-followup/rail_disconnect.kicad_pcb"
    donor=WORK/"generated/eight-control-continuation-01/imported.kicad_pcb"
    donor_drc=WORK/"generated/native-eight-control-continuation-01/drc.json"
    out=WORK/"generated/reference-merge-trial"
    out.mkdir(exist_ok=False)
    selected={"REF_LOW_OK","REF_LOW_POSITIVE"}
    raw=json.loads(donor_drc.read_text())
    donor_open={re.search(r"\[/([^]]+)\]",r["items"][0]["description"]).group(1) for r in raw["unconnected_items"]}
    assert not selected & donor_open
    tree=read_sexpr(source.read_text())
    other=read_sexpr(donor.read_text())
    names={str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
    codes={name:int(code) for code,name in names.items()}

    def net(node,table):
        value=str(first(node,"net")[1])
        return table.get(value,value.lstrip("/"))

    def poses(board):
        result={}
        for fp in children(board,"footprint"):
            ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
            at=first(fp,"at")
            result[ref]=(str(first(fp,"layer")[1]),round(float(at[1]),6),round(float(at[2]),6),
                         (float(at[3]) if len(at)>3 else 0)%360)
        return result

    assert poses(tree)==poses(other)
    donor_names={str(n[1]):str(n[2]).lstrip("/") for n in children(other,"net")}
    removed=[]
    for node in tree[:]:
        if isinstance(node,list) and node and node[0] in ("segment","via") and net(node,names) in selected:
            removed.append(dict(net=net(node,names),literal=sexpr(node)))
            tree.remove(node)
    count,frozen=len(tree),sexpr(tree)
    ids={str(first(n,"uuid")[1]) for kind in ("segment","via") for n in children(tree,kind)}
    additions=[]
    for kind in ("segment","via"):
        for original in children(other,kind):
            name=net(original,donor_names)
            if name not in selected:
                continue
            node=copy.deepcopy(original)
            uid=str(first(node,"uuid")[1])
            assert uid not in ids
            ids.add(uid)
            first(node,"net")[:]=[a("net"),a(codes[name])]
            tree.append(node)
            additions.append(dict(net=name,literal=sexpr(node)))
    assert selected=={r["net"] for r in additions}
    assert sexpr(tree[:count])==frozen
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"merge.json").write_text(json.dumps(dict(source_sha256=sha(source),donor_sha256=sha(donor),
        donor_native_DRC_sha256=sha(donor_drc),candidate_sha256=sha(pcb),recipe_sha256=sha(Path(__file__)),
        selected_nets=sorted(selected),removed_objects=removed,added_objects=additions,
        all_footprint_poses_exact=True,all_other_original_objects_exact=True,
        native_ERC_DRC_refill_and_power_connectivity_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Staged two reference-net replacements:",len(removed),"old objects;",len(additions),"new objects")


if __name__=="__main__":
    run()
