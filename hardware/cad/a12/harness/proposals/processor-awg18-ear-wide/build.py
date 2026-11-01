"""Private wider E19 ear; preserve all86 footprints and routed objects."""

import hashlib
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-supported"
EXPECTED = "27563a7ac2e4049029d8caa007c9b0627ebbe120c415ccb59bc7ed34dd0ec33e"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    assert sha(SOURCE / "processor_carrier.kicad_pcb") == EXPECTED
    assert not (ROOT / "processor_carrier.kicad_pcb").exists()
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, ROOT / p.name, dirs_exist_ok=True)
        elif p.is_file() and (
            p.suffix in [".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"]
            or p.name in ["components.json", "bom.csv", "fp-lib-table", "sym-lib-table"]
        ):
            shutil.copy2(p, ROOT / p.name)
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    t = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    edges = [q for q in children(t, "gr_line") if first(q, "layer")[1] == "Edge.Cuts"]
    changes = []
    for q in edges:
        old = sexpr(q)
        for name in ["start", "end"]:
            point = first(q, name)
            if float(point[2]) == 153:
                point[2] = a(148)
        if sexpr(q) != old:
            changes.append(dict(uuid=str(first(q, "uuid")[1]), before=old, after=sexpr(q)))
    assert len(changes) == 3
    zonechanges = []
    for q in children(t, "zone"):
        if not children(q, "net") or first(q, "net")[1] != "/AGND":
            continue
        if not children(q, "layer") or first(q, "layer")[1] != "In1.Cu":
            continue
        if not children(q, "priority") or str(first(q, "priority")[1]) != "1":
            continue
        old = sexpr(q)
        pts = first(first(q, "polygon"), "pts")
        assert [list(map(float, p[1:])) for p in pts[1:]] == [
            [248, 153.5],
            [263, 153.5],
            [263, 164.5],
            [248, 164.5],
        ]
        pts[1][2] = a(148)
        pts[2][2] = a(148)
        zonechanges.append(dict(uuid=str(first(q, "uuid")[1]), before=old, after=sexpr(q)))
    assert len(zonechanges) == 1
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(t) + "\n")
    report = dict(
        parent_source_sha256=EXPECTED,
        candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        edge_changes=changes,
        zone_changes=zonechanges,
        world_outline_mm=[[30, 42], [180, 42], [180, 90], [194, 90], [194, 107], [30, 107]],
        added_world_xy_mm=[180, 90, 194, 95],
        added_area_mm2=70,
        actual_unchanged_positive_priority1_contract_native_xy=[143, 119, 262, 164],
        changed_AGND_In1_priority1_contract_native_xy=[248, 148, 263, 164.5],
        all_86_complete_footprints_unchanged_required=True,
        all_tracks_vias_unchanged_required=True,
        all_77_part_pinmaps_unchanged_required=True,
        all_stackup_and_H9_keepout_unchanged_required=True,
        no_new_ports=True,
        physical_qualified=False,
        PDN_result_inherited=False,
        mechanical_fit_passed=False,
        fabrication_released=False,
    )
    (out / "design-change.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["candidate_pcb_sha256"])


if __name__ == "__main__":
    run()
