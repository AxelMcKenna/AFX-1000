"""Stage the alternate receiver pose without changing the original candidate."""

import json
from pathlib import Path

from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

from .route_e28 import WORK, sha


def ref(fp):
    return next(p[2] for p in children(fp,"property") if p[1]=="Reference")


def run():
    source = WORK / "rail_disconnect.kicad_pcb"
    digest = sha(source)
    tree = read_sexpr(source.read_text())
    report = json.loads((WORK / "generated/direct-placement-search.json").read_text())
    poses = report["best"][0]["poses"]
    parts = {c["ref"]:c for c in json.loads((WORK / "components.json").read_text())}
    nets = {str(n[2]).lstrip("/"):int(n[1]) for n in children(tree,"net")}
    nc = "unconnected-(U43-NC-Pad1)"
    preserved = [sexpr(f) for f in children(tree,"footprint") if ref(f) not in poses]
    tree[:] = [f for f in tree if not (isinstance(f,list) and f and f[0]=="footprint" and ref(f) in poses)]
    for name,p in poses.items():
        c = parts[name]
        lib = WORK / ("RMX_E28.pretty/AX03_DCK0005A.kicad_mod" if name=="U43" else "RMX_E28.pretty/AX03_C0603.kicad_mod")
        fp = placed_footprint(dict(c,value=c["part"],mpn=c["part"],nets={q["number"]:q["net"] or nc for q in c["pins"]}),
                              (p[0]-100,p[1]-100,p[2],p[3]),lib,nets,namespace="rmx:E28:AX03:")
        if name=="U43":
            first(next(p for p in children(fp,"pad") if p[1]=="1"),"net")[2] = nc
        tree.append(fp)
    assert [sexpr(f) for f in children(tree,"footprint") if ref(f) not in poses] == preserved
    out = WORK / "generated/receiver-direct-pose"
    out.mkdir(exist_ok=False)
    pcb = out / source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out / "placement.json").write_text(json.dumps(dict(source_sha256=digest,candidate_sha256=sha(pcb),
        recipe_sha256=sha(Path(__file__)),poses=poses,only_U43_C86_replaced=True,
        no_existing_copper_or_rules_changed=True,native_checks_pending=True),indent=2)+"\n")
    assert sha(source)==digest


if __name__=="__main__":
    run()
