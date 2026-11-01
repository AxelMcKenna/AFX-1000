"""Bind real footprint bytes/pad identities, without claiming land acceptance."""

import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.qualification.boards.fan_health.circuit.design import ROOT, sha

LIB = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints")


def review(parts):
    result = []
    for p in parts:
        library, name = p["footprint"].split(":")
        path = (ROOT if library.startswith("RMX_") else LIB) / (library + ".pretty") / (name + ".kicad_mod")
        if not path.is_file():
            raise ValueError("Missing footprint: " + str(path))
        node = read_sexpr(path.read_text())
        pads = {str(n[1]) for n in children(node, "pad") if str(n[1])}
        expected = {str(n["number"]) for n in p["pins"]}
        if pads != expected:
            raise ValueError((p["ref"], pads, expected))
        points = []
        for tag in ("fp_line", "fp_rect"):
            for drawing in children(node, tag):
                if str(first(drawing, "layer")[1]) == "F.CrtYd":
                    for name in ("start", "end"):
                        points.append([float(x) for x in first(drawing, name)[1:3]])
        if not points:
            raise ValueError("No actual front courtyard: " + p["ref"])
        bbox = [
            min(q[0] for q in points),
            min(q[1] for q in points),
            max(q[0] for q in points),
            max(q[1] for q in points),
        ]
        target = ROOT / "sources/footprints" / (library + ".pretty") / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha(target) != sha(path):
            raise ValueError("Captured library changed: " + str(path))
        if not target.exists():
            shutil.copy2(path, target)
        result.append(
            dict(
                ref=p["ref"],
                footprint=p["footprint"],
                sha256=sha(path),
                captured_path=str(target.relative_to(ROOT)),
                pads=sorted(pads),
                expected_pins=sorted(expected),
                courtyard_bbox_mm=bbox,
                courtyard_enclosing_area_mm2=(bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),
                manufacturer_land_pattern_independently_accepted=False,
            )
        )
    area = sum(p["courtyard_enclosing_area_mm2"] for p in result)
    return dict(
        parts=result,
        actual_footprint_pin_sets_match=True,
        summed_enclosing_courtyard_area_mm2=area,
        area_times1p2_mm2=area * 1.2,
        proposed_board_area_mm2=58 * 25,
        placement_or_routing_fit_proven=False,
        courtyard_sum_is_NOT_packing_or_routing_proof=True,
        custom_ABLS_source="ABLS450669RevADp3 5.6x2.1mm lands/9.5mm centres",
        custom_TLP_source="Toshiba11-4M1SRev7p7 package only; ownunapprovedreceivingland",
        sensor_assemblies=[
            dict(
                part="SEMITEC203AT-2",
                quantity=2,
                on_health_PCB=False,
                connection="J2/J3 pin1sensor,pin2GND",
                leads_connector_attachment_qualified=False,
            )
        ],
        fabrication_released=False,
    )


if __name__ == "__main__":
    result = review(json.loads((ROOT / "components.json").read_text()))
    (ROOT / "generated/package-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Actual footprint pin sets:",
        len(result["parts"]),
        "area:",
        result["summed_enclosing_courtyard_area_mm2"],
    )
