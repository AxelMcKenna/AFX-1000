"""Short real R93 input link and contained ground barrel after placement screen."""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr
from ..routing.check import point_segment
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u28-run-pulldown-placement-work"
WORK = ROOT / "generated/u28-run-pulldown-routed-work"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    router = Router(tree)
    assert legal_line(router, "POWER_RUN", 5, (77, 52.2), (77, 51), 0.2)
    point = (78.825, 52.2)
    conflicts = []
    for g in router.geometry:
        if g["net"] == "AGND" and (g["kind"] in ("rect", "line") or g.get("through")):
            continue
        if g["kind"] == "line":
            distance = point_segment(point, g["start"], g["end"]) - g["width"] / 2
            need = 0.52
        elif g["kind"] == "via":
            distance = math.dist(point, g["xy"]) - g["radius"]
            need = 0.26 if g["net"] == "AGND" else 0.52
        else:
            distance = math.hypot(*[max(abs(point[i] - g["xy"][i]) - g["size"][i] / 2, 0) for i in (0, 1)])
            need = 0.52
        if distance < need - 1e-8:
            conflicts.append(dict(shape=g, distance=distance, requirement=need))
    assert not conflicts, conflicts
    track = read_sexpr(
        f'(segment (start 177 152.2) (end 177 151) (width .2) (layer "B.Cu") (net {router.nets["POWER_RUN"]}) (uuid {uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E28:R93-signal:" + digest)}))'
    )
    via = read_sexpr(
        f'(via (at 178.825 152.2) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {router.nets["AGND"]}) (uuid {uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E28:R93-ground:" + digest)}))'
    )
    tree.extend((track, via))
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    result = dict(
        source_pcb_sha256=digest,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        signal_track=sexpr(track),
        ground_via=sexpr(via),
        actual_foreign_pad_track_and_drill_conflicts=conflicts,
        no_other_objects_changed=True,
        filled_capped_via_planarity_assembly_and_process_accepted=False,
        native_and_PDN_pending=True,
        qualified=False,
    )
    (WORK / "generated/R93-local-fanout.json").write_text(json.dumps(result, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
