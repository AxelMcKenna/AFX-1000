"""AP02 fresh private capture of HT01, with actual source-derived air cuts."""

import hashlib
import json
import shutil

from hardware.cad.a12.thermal.enlarged_base_forced_air.stage import replace_module_body

from .plan import FI, HT, ROOT, plan

MODEL = ROOT / "model"
OUT = ROOT / "generated"
REPO = ROOT.parents[4]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2) + "\n")


def body(source, name):
    start = source.index("module " + name + "(")
    begin = source.index("{", start)
    depth = 1
    end = begin + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[begin + 1 : end - 1]


def capture():
    if (ROOT / "handoff.json").exists() or MODEL.exists() or (ROOT / "capture.json").exists():
        raise RuntimeError("Capture refuses an existing or sealed candidate")
    parents = {}
    for name, folder in [
        ("HT01", HT),
        ("FI01", FI),
        ("AP01", ROOT.parent / "air_path_budget"),
        ("SF01", ROOT.parent / "forced_air_sunon"),
    ]:
        h = json.loads((folder / "handoff.json").read_text())
        mapping = h.get("files_sha256", h.get("sha256"))
        assert all(sha(folder / n if (folder / n).exists() else REPO / n) == v for n, v in mapping.items())
        parents[name] = dict(
            folder=str(folder), handoff_sha256=sha(folder / "handoff.json"), files=len(mapping)
        )
    shutil.copytree(HT / "model", MODEL)
    for p in MODEL.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(HT / "model"), str(MODEL)))
    ht_checks = (HT / "generated/checks.scad").read_text().replace(str(HT / "model"), str(MODEL))
    (MODEL / "ht-checks.scad").write_text(ht_checks)
    data = plan()
    for path, prefix in [
        (MODEL / "parts.scad", "eb_part_pins="),
        (MODEL / "context/hardware/cad/a12/thermal/generated/thermal-base.scad", "thermal_pins="),
    ]:
        s = path.read_text()
        line = next(l for l in s.splitlines() if l.startswith(prefix))
        s = s.replace(line, prefix + json.dumps(data["pins"]["kept_centres"]) + ";")
        if prefix == "eb_part_pins=":
            original_part = body(s, "eb_part_metal_base")
            s = replace_module_body(
                s, "eb_part_metal_base", lambda unused: "difference(){ap_old_part_base();ap_port_cuts();}"
            )
            s += "\nmodule ap_old_part_base(){" + original_part + "}\n"
        path.write_text(s)
    metal = MODEL / "context/hardware/cad/a12/thermal/generated/thermal-base.scad"
    s = metal.read_text()
    original = body(s, "thermal_metal_base")
    s = replace_module_body(
        s, "thermal_metal_base", lambda unused: "difference(){ap_old_metal_base();ap_port_cuts();}"
    )
    s += "\nmodule ap_old_metal_base(){" + original + "}\n"
    metal.write_text(s)
    thermal = MODEL / "context/hardware/cad/a12/thermal-integration.scad"
    s = thermal.read_text()
    original = body(s, "retained_thermal_shell")
    s = replace_module_body(
        s,
        "retained_thermal_shell",
        lambda unused: "difference(){ap_old_carrier();ap_port_cuts();ap_exhaust_cuts();}",
    )
    s += "\nmodule ap_old_carrier(){" + original + "}\n"
    thermal.write_text(s)
    s = (MODEL / "context-derived.scad").read_text()
    for name, target in [
        ("fi_tray", "ap_tray"),
        ("fi_guards", "ap_guards"),
        ("fi_fans", "ap_fans_assembly"),
        ("fi_fan_fasteners", "ap_fasteners"),
        ("fi_fan_stress", "ap_fan_stress"),
        ("fi_hardware_stress", "ap_hardware_stress"),
    ]:
        s = replace_module_body(s, name, lambda unused, target=target: target + "();")
    (MODEL / "context-derived.scad").write_text(s)
    oldfa = (FI / "generated/fa-scoped.scad").read_text()
    tray = (
        body(oldfa, "fa_tray")
        .replace("fa_feet", "ap_feet")
        .replace("fa_fans", "ap_fans")
        .replace("fa_round", "ap_round")
    )
    helper = "module ap_source_tray(){$fn=96;" + tray + "}\n"
    (OUT / "source-tray.scad").write_text(helper)
    shutil.copyfile(MODEL / "config.json", OUT / "config.json")
    write(OUT / "analysis.json", data)
    write(
        ROOT / "capture.json",
        dict(
            parents=parents,
            parent_originals_modified=False,
            private_model_sha256={str(p.relative_to(ROOT)): sha(p) for p in MODEL.rglob("*") if p.is_file()},
            scope="Actual floor/plate windows,wholepinremoval,westwallvents,guard,fanshim/sealsandmeteredpressurebaffles; inheritedboard/wireposes unchanged",
        ),
    )
    (OUT / "checks.scad").write_text(
        "include <"
        + str(MODEL / "ht-checks.scad")
        + ">\ninclude <source-tray.scad>\n"
        + (ROOT / "geometry.scad").read_text()
    )
    print(
        json.dumps(
            dict(
                pins_removed=data["pins"]["removed_count"],
                pins_kept=data["pins"]["kept_count"],
                inlet_net=data["inlet"]["nominal_total_net_mm2"],
                exhaust_net=data["exhaust"]["nominal_net_mm2"],
            )
        )
    )


if __name__ == "__main__":
    capture()
