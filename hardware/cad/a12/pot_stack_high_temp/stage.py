"""HT01 private Alps RK09L1140A5L receiving study from frozen FI01."""

import hashlib
import json
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_forced_air.replay import prepare_rebind
from hardware.cad.a12.thermal.enlarged_base_forced_air.stage import replace_module_body

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
FI = ROOT.parent / "thermal/enlarged_base_forced_air"
MODEL = ROOT / "model"
OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def capture():
    if (ROOT / "handoff.json").exists() or MODEL.exists():
        raise RuntimeError("Capture requires a new destination; sealed/current evidence is never overwritten")
    parent = json.loads((FI / "handoff.json").read_text())
    assert all(sha(FI / n) == h for n, h in parent["files_sha256"].items())
    prepare_rebind(MODEL)
    source = MODEL / "context-derived.scad"
    s = source.read_text()
    replacements = {
        "ps_body": "for(p=ps_centres)translate([p[0],p[1],0])ht_local_body(m);",
        "ps_hardware_max": "ht_hardware();",
        "ps_shaft_max": "ht_shaft();",
        "cp_other_pot_bodies": "for(q=ps_centres)if(q!=p)translate([q[0],q[1],0])ht_local_body();",
    }
    for name, body in replacements.items():
        s = replace_module_body(s, name, lambda unused, body=body: body)
    assert s.count("h=min(10,h-2)+0.1") == 1
    s = s.replace("h=min(10,h-2)+0.1", "h=min(10.8,h-2)+0.1")
    assert s.count("translate([0,0,3]) rotate") == 1
    assert s.count("translate([6,0,3]) rotate") == 1
    s = s.replace("translate([0,0,3]) rotate", "translate([0,0,5]) rotate")
    s = s.replace("translate([6,0,3]) rotate", "translate([6,0,5]) rotate")
    source.write_text(s)
    # Panel bore stays9.5. Only a new named blind lug pocket is added.
    panel = MODEL / "context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"
    p = panel.read_text()
    assert "module ui_lid(){translate([0,0,panel_z])front_panel();}" in p
    p = p.replace(
        "module ui_lid(){translate([0,0,panel_z])front_panel();}",
        "module ht_old_lid(){translate([0,0,panel_z])front_panel();}\n"
        "module ui_lid(){difference(){ht_old_lid();ht_lug_pockets();}}",
    )
    panel.write_text(p)
    copied = {str(p.relative_to(ROOT)): sha(p) for p in MODEL.rglob("*") if p.is_file()}
    drawings = {
        "dimensions": ("/private/tmp/afx-rk09l-15mm.gif", "https://tech.alpsalpine.com/cms.media/product_detail_fig_rk09l_d_222_en_34014d0696.gif"),
        "hardware": ("/private/tmp/afx-rk09l-hardware.gif", "https://tech.alpsalpine.com/cms.media/product_detail_fig_rk09l_c_101_en_acab65d7d7.gif"),
        "mounting": ("/private/tmp/afx-rk09l-mount.gif", "https://tech.alpsalpine.com/cms.media/product_detail_fig_rk09l_d_231_en_08e696475d.gif"),
        "lug": ("/private/tmp/afx-rk09l-bushing.gif", "https://tech.alpsalpine.com/cms.media/product_detail_fig_rk09l_c_1_en_60d88f1440.gif"),
    }
    write(ROOT / "capture.json", dict(
        parent="FI01", parent_handoff_sha256=sha(FI / "handoff.json"), parent_files=len(parent["files_sha256"]),
        all_parent_hashes_checked=True, parent_modified=False,
        original_context_transformation="Private absolute-path rebind, four pot modules, knob inner bore/grub axis, and named panel lug pocket only",
        captured_model_sha256=copied,
        external_manufacturer_drawings={k: dict(external_path=p, sha256=sha(Path(p)), url=u) for k, (p, u) in drawings.items()},
        manufacturer_images_redistributed=False,
    ))
    cfg = json.loads((MODEL / "config.json").read_text())
    write(OUT / "config.json", cfg)
    text = (ROOT / "geometry.scad").read_text()
    (OUT / "checks.scad").write_text("include <" + str(source) + ">\n" + text)
    from .contract import report
    write(OUT / "analysis.json", report())
    print(json.dumps(dict(captured_files=len(copied), parent_handoff_sha256=sha(FI / "handoff.json"))))


if __name__ == "__main__":
    capture()
