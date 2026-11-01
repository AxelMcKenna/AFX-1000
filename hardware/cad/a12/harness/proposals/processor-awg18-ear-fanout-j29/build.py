"""Private J29 relocation and four exact local route replacements."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-fanout-spaced"
EXPECTED = "e415660388344af08fb372d11ed011381e951cd021a1aa45b913900f0b9784c2"


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
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    t = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    fp = next(
        f
        for f in children(t, "footprint")
        if any(p[1:3] == ["Reference", "J29"] for p in children(f, "property"))
    )
    oldfp = sexpr(fp)
    assert list(map(float, first(fp, "at")[1:])) == [236.5, 157.8]
    first(fp, "at")[1:] = [a(240.4), a(157.8), a(-90)]
    for p in children(fp, "pad"):
        at = first(p, "at")
        at[1:] = [at[1], at[2], a(-90)]
    target = {
        "14aeb7ec-214f-40b0-9af9-af2b543d0f8e",
        "ae0d6d7e-6c33-4a03-bdf9-cbfa49d9d96a",
        "cbec5269-d718-4d20-a8ae-9494900732dd",
        "d7f32aa1-f16d-4065-82be-0d16c7a5e54d",
    }
    removed = []
    for q in list(children(t, "segment")):
        if str(first(q, "uuid")[1]) in target:
            removed.append(sexpr(q))
            t.remove(q)
    assert len(removed) == 4
    new = []
    for key, start, end, width, layer, net in [
        ("raw-escape", (237.86, 157.8), (237.86, 160.25), 0.25, "In2.Cu", "POT_RAW_09"),
        ("raw-anchor", (237.86, 160.25), (230.25, 160.25), 0.25, "In2.Cu", "POT_RAW_09"),
        ("AVDD-escape", (235.32, 157.8), (235.32, 163.7), 0.4, "F.Cu", "V3V3_ANALOG"),
        ("AVDD-trunk", (111.37, 163.7), (235.32, 163.7), 0.4, "F.Cu", "V3V3_ANALOG"),
    ]:
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-j29-relocation-" + key))
        q = read_sexpr(
            f'(segment(start {start[0]} {start[1]})(end {end[0]} {end[1]})(width {width})(layer "{layer}")(net "/{net}")(uuid "{uid}"))'
        )
        t.append(q)
        new.append(sexpr(q))
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(t) + "\n")
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
                all_other87_complete_FP_exact_required=True,
                all79parts_pinmaps_exact_required=True,
                all_quiet_filter_values_nets_poses_exact_required=True,
                H9_newports_and_outline_unchanged_required=True,
                J29_proposed_world_pin1_mm=[170.4, 99.8],
                J29_proposed_angle_degrees=-90,
                complete_PDN_inherited=False,
                mechanical_fit_passed=False,
                physical_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(sha(ROOT / "processor_carrier.kicad_pcb"))


if __name__ == "__main__":
    run()
