"""Isolated J29 angle-zero placement with J29-only route replacement."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-fanout-j29"
EXPECTED = "302ec64b2c4d027476de5ac903e76f2ead32a4955f68ef425e9ad21a4147cfd2"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    assert sha(SOURCE / "processor_carrier.kicad_pcb") == EXPECTED
    assert not (ROOT / "processor_carrier.kicad_pcb").exists()
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, ROOT / p.name)
        elif p.is_file() and (
            p.suffix in [".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"]
            or p.name in ["components.json", "bom.csv", "fp-lib-table", "sym-lib-table"]
        ):
            shutil.copy2(p, ROOT / p.name)
    t = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    fp = next(
        f
        for f in children(t, "footprint")
        if any(p[1:3] == ["Reference", "J29"] for p in children(f, "property"))
    )
    oldfp = sexpr(fp)
    first(fp, "at")[1:] = [a(175), a(134), a(0)]
    for p in children(fp, "pad"):
        at = first(p, "at")
        at[1:] = [at[1], at[2], a(0)]
    removed = []
    for q in list(children(t, "segment")):
        net = str(first(q, "net")[1])
        s = list(map(float, first(q, "start")[1:]))
        e = list(map(float, first(q, "end")[1:]))
        raw = net == "/POT_RAW_09" and min(s[0], e[0]) >= 172.5
        avdd = net == "/V3V3_ANALOG" and (
            (s[0] == e[0] == 235.32) or (s[1] == e[1] == 163.7 and min(s[0], e[0]) == 111.37)
        )
        if raw or avdd:
            removed.append(sexpr(q))
            t.remove(q)
    new = []
    for key, s, e, w, layer, net in [
        ("raw-escape", (175, 136.54), (176.5, 136.54), 0.25, "In2.Cu", "POT_RAW_09"),
        ("raw-vertical", (176.5, 136.54), (176.5, 146.5), 0.25, "In2.Cu", "POT_RAW_09"),
        ("raw-anchor", (176.5, 146.5), (172.5, 146.5), 0.25, "In2.Cu", "POT_RAW_09"),
        ("avdd-escape", (175, 139.08), (175, 163.7), 0.4, "F.Cu", "V3V3_ANALOG"),
        ("avdd-trunk", (111.37, 163.7), (229, 163.7), 0.4, "F.Cu", "V3V3_ANALOG"),
    ]:
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-j29-central-" + key))
        q = read_sexpr(
            f'(segment(start {s[0]} {s[1]})(end {e[0]} {e[1]})(width {w})(layer "{layer}")(net "/{net}")(uuid "{uid}"))'
        )
        t.append(q)
        new.append(sexpr(q))
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(t) + "\n")
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    shutil.copyfile(
        SOURCE / "generated/parent-fanout-requirements.json", out / "parent-fanout-requirements.json"
    )
    (out / "design-change.json").write_text(
        json.dumps(
            dict(
                parent_pcb_sha256=EXPECTED,
                candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
                old_J29_footprint=oldfp,
                new_J29_footprint=sexpr(fp),
                removed_segments=removed,
                added_segments=new,
                new_vias=[],
                J29_world_pin1_mm=[105, 76],
                angle_degrees=0,
                foreign_signals_unchanged=True,
                physical_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("removed", len(removed), "added", len(new), "PCB", sha(ROOT / "processor_carrier.kicad_pcb"))


if __name__ == "__main__":
    run()
