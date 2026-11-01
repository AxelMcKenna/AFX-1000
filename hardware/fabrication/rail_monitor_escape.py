"""Replace a necked router escape beside R110 with full-width clearance."""

import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent


def run():
    source = ROOT/"staging/rail-monitor-routed-native-01/rail_monitor.kicad_pcb"
    output = ROOT/"staging/rail-monitor-escape-01"
    assert not output.exists()
    tree = read_sexpr(source.read_text())
    remove = {"c829cc2b-1410-4a5f-ae09-c6841393c48f","3238bb18-6734-4918-906f-d3f4d82badc8",
        "e7178922-3830-44e4-8888-fb452091c865","58c65df9-50a5-4ece-a133-fed6b3368689",
        "bcb00c3c-4ad9-494a-8465-d726df9674b2","8229f6bf-bcd5-49e3-8da9-794c9c41b9b8"}
    selected = [n for n in children(tree,"segment") if str(first(n,"uuid")[1]) in remove]
    assert len(selected) == len(remove)
    assert all(first(n,"net")[-1] == "/V5_COARSE_SENSE" and first(n,"layer")[1] == "F.Cu" for n in selected)
    result = [n for n in tree if n not in selected]
    points = [(60.9125,64),(60.65,64),(60.65,63.55),(60.08,62.98),(59.2,62.98),(58.967,62.9117)]
    for start,end in zip(points,points[1:]):
        ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E13:escape:{sha(source)}:{start}:{end}"))
        result.append([a("segment"),[a("start"),*start],[a("end"),*end],[a("width"),.2],
            [a("layer"),"F.Cu"],[a("net"),"/V5_COARSE_SENSE"],[a("uuid"),ident]])
    output.mkdir()
    pcb = output/source.name
    pcb.write_text(sexpr(result)+"\n")
    (output/"construction.json").write_text(json.dumps(dict(source_sha256={str(source):sha(source),str(Path(__file__)):sha(Path(__file__))},
        candidate_PCB_sha256=sha(pcb),removed_tracks=sorted(remove),replacement_points_mm=points,
        net="/V5_COARSE_SENSE",width_mm=.2,all_other_authored_objects_exact=True,
        native_checks_pending=True,fabrication_released=False),indent=2)+"\n")


if __name__ == "__main__":
    run()
