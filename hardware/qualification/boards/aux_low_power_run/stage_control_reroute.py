"""Restart control routing while freezing the original power/return copper.

The partial six-layer control routes box several pins into inaccessible via
fields. This separate eight-layer trial removes those control tracks/vias and
retains every footprint, power/return conductor, rule area and board outline.
All removed objects are recorded verbatim; no previous signal/noise/timing or
power-integrity acceptance is inherited.
"""

import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision26.layout import POWER_NETS

from .route_e28 import WORK, sha


def run():
    source=WORK/"generated/eight-layer-stage/rail_disconnect.kicad_pcb"
    out=WORK/"generated/eight-control-reroute"
    out.mkdir(exist_ok=False)
    tree=read_sexpr(source.read_text())
    names={str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
    protected=POWER_NETS|{"AGND","V2V5_AUX"}
    removed=[]
    retained=[]
    for node in tree[:]:
        if not isinstance(node,list) or not node or node[0] not in ("segment","via"):
            continue
        net=names[str(first(node,"net")[1])]
        if net not in protected:
            removed.append(dict(net=net,literal=sexpr(node)))
            tree.remove(node)
        else:
            retained.append(dict(net=net,original=sexpr(node)))
            if not children(node,"locked"):
                node.append([a("locked"),a("yes")])
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    for suffix in (".kicad_pro",".kicad_sch"):
        shutil.copyfile(WORK/("rail_disconnect"+suffix),out/("rail_disconnect"+suffix))
    for name in ("fp-lib-table","sym-lib-table"):
        (out/name).write_text((WORK/name).read_text().replace("${KIPRJMOD}/","${KIPRJMOD}/../../"))
    (out/"construction.json").write_text(json.dumps(dict(source_sha256=sha(source),candidate_sha256=sha(pcb),
        recipe_sha256=sha(Path(__file__)),removed_control_objects=removed,retained_power_objects=retained,
        protected_nets=sorted(protected),all_footprints_zones_rule_areas_and_outline_exact=True,
        protected_XY_copper_only_locked_never_moved=True,all_signal_acceptance_invalidated=True,
        fabrication_released=False),indent=2)+"\n")
    print("Staged",len(removed),"control objects for rerouting;",len(retained),"power/return objects frozen")


if __name__=="__main__":
    run()
