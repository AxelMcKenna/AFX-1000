"""Private access repair: move only H9 and its full-metal exclusion five mm north."""

import hashlib
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-wide"
EXPECTED = "648d09a2483d0be8c33304cec5bfc94d774aed72961ee67dbbd7325bb6b8d58f"


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
    out.mkdir()
    t = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    h9 = next(
        f
        for f in children(t, "footprint")
        if any(p[1:3] == ["Reference", "H9"] for p in children(f, "property"))
    )
    assert list(map(float, first(h9, "at")[1:])) == [252, 155.2]
    before_h9 = sexpr(h9)
    first(h9, "at")[2] = a(150.2)
    ko = next(
        q
        for q in children(t, "zone")
        if children(q, "keepout") and str(first(q, "uuid")[1]) == "ae9d9028-310a-5458-a9e2-6ffd8f76ab30"
    )
    before_ko = sexpr(ko)
    for p in first(first(ko, "polygon"), "pts")[1:]:
        p[2] = a(float(p[2]) - 5)
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(t) + "\n")
    report = dict(
        parent_pcb_sha256=EXPECTED,
        candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        changes=[
            dict(uuid=str(first(h9, "uuid")[1]), before=before_h9, after=sexpr(h9)),
            dict(uuid=str(first(ko, "uuid")[1]), before=before_ko, after=sexpr(ko)),
        ],
        H9_old_native_mm=[252, 155.2],
        H9_new_native_mm=[252, 150.2],
        H9_new_world_mm=[182, 92.2],
        nominal_NPTH_to_top_edge_mm=1.0,
        full_metal_disk_radius_mm=3.8,
        inherited_actual_keepout_min_radius_mm=3.801,
        all_other85_complete_footprints_exact_required=True,
        all77_parts_pinmaps_traces_vias_outline_stackup_exact_required=True,
        original_J1_unfitted_service=True,
        no_new_ports=True,
        nominal_head_and_boss_may_overhang_board_edge=True,
        root_actual_post_tool_and_case_body_check_required=True,
        physical_qualified=False,
        mechanical_fit_passed=False,
        PDN_inherited=False,
        fabrication_released=False,
    )
    (out / "design-change.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["candidate_pcb_sha256"])


if __name__ == "__main__":
    run()
