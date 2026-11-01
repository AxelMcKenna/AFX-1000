"""Source-bound numeric current-courtyard/captured-mesh precheck; no native fit claim."""

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import courtyard
from .u26_band_mesh_screen import contains, hits, triangles
from .u26_band_screen import box_hit, circle_gap

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
WORK = ROOT / "generated/schmitt-all-oc-old-leaf-work"
CP = REPO / "hardware/cad/a12/thermal/enlarged_base_pot"
CTX = CP / "context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"


def main():
    pcb = WORK / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    text = CTX.read_text()

    def arr(n):
        return json.loads(re.search("^" + n + "=(.*);$", text, re.M).group(1))

    datum = next(b[1] for b in arr("ui_native_boards") if b[0] == "E28")
    assert datum == [8, 108.5, 5.0]
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    refs = {f"U{i}" for i in range(36, 43)} | {f"C{i}" for i in range(79, 86)}
    paths = [
        CP / "generated" / (n + ".stl")
        for n in (
            "eb_carrier_geometry",
            "eb_attachment_geometry",
            "eb_metal_geometry",
            "eb_interface_geometry",
            "eb_retained_power_review",
            "ei_controls_geometry",
            "ei_all_ports_geometry",
            "ei_trill_frontbay_geometry",
            "ps_body_geometry",
            "ps_stack",
            "cp_pot_hardware_review",
        )
    ]
    meshes = {p: triangles(p) for p in paths}
    rows = []
    for ref in refs:
        fp = fps[ref]
        side = str(first(fp, "layer")[1])[0]
        xy = courtyard(fp, side + ".CrtYd")
        # Explicit received body/seat allocations; no new native fit inheritance.
        h = 1.5 if ref.startswith("C") else 1.1
        z0, z1 = (5 - h, 5) if side == "B" else (6.62, 6.62 + h)
        box = [xy[0] - 100 + 8, xy[1] - 100 + 108.5, z0, xy[2] - 100 + 8, xy[3] - 100 + 108.5, z1]
        expanded = [box[0] - 0.25, box[1] - 0.25, box[2] - 0.45, box[3] + 0.25, box[4] + 0.25, box[5] + 0.45]
        court_hits = []
        for name, other in fps.items():
            if name == ref or first(other, "layer")[1] != side + ".Cu":
                continue
            try:
                b = courtyard(other, side + ".CrtYd")
            except (ValueError, IndexError):
                continue
            if min(xy[2], b[2]) > max(xy[0], b[0]) + 1e-8 and min(xy[3], b[3]) > max(xy[1], b[1]) + 1e-8:
                court_hits.append(name)
        captured = []
        for b in arr("ui_native_boxes"):
            if b[0].startswith("E28_"):
                continue  # use actual current E28 all courtyards above
            o = [*b[1:4], *[b[i + 1] + b[i + 4] for i in range(3)]]
            if box_hit(expanded, o):
                captured.append(b[0])
        postgaps = [
            circle_gap(
                [box[0] - 0.9, box[1] - 0.9, box[2], box[3] + 0.9, box[4] + 0.9, box[5]],
                c,
                3.6 / math.cos(math.pi / 128),
            )
            for c in arr("tc2_centres")
        ]
        meshrows = {
            str(p.relative_to(REPO)): dict(
                surface_hits=hits(ts, expanded),
                centre_inside=contains(ts, (np.array(expanded[:3]) + expanded[3:]) / 2),
            )
            for p, ts in meshes.items()
        }
        rows.append(
            dict(
                ref=ref,
                face=side,
                box=box,
                expanded=expanded,
                courtyard_hits=court_hits,
                captured_component_hits=captured,
                post_gaps=postgaps,
                mesh_checks=meshrows,
                floor_gap=expanded[2] - 2.8,
            )
        )
    controls = dict(
        floor=contains(meshes[paths[0]], [133, 156, 1]),
        post=contains(meshes[paths[0]], [130.0871, 168.922, 10]),
    )
    failures = [
        r["ref"]
        for r in rows
        if r["courtyard_hits"]
        or r["captured_component_hits"]
        or min(r["post_gaps"]) <= 0
        or r["floor_gap"] < 0
        or any(v["surface_hits"] or v["centre_inside"] for v in r["mesh_checks"].values())
    ]
    hashes = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [pcb, WORK / "components.json", CTX, Path(__file__), *paths]
    }
    result = dict(
        source_sha256=hashes,
        rows=rows,
        controls=controls,
        failures=failures,
        receiving_J12_tail_protrusion_max_mm=0,
        J12_stock_tail_trim_unapproved=False,
        SMT_barrel_fill_cap_and_stencil_accepted=False,
        mated_9mm_envelope_is_receiving_requirement_not_vendor_bound=True,
        full_native_and_physical_qualified=False,
    )
    (WORK / "generated/placement-screen.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                failures=failures,
                details=[
                    {
                        k: r[k]
                        for k in (
                            "ref",
                            "courtyard_hits",
                            "captured_component_hits",
                            "post_gaps",
                            "floor_gap",
                        )
                    }
                    for r in rows
                ],
            ),
            indent=2,
        )
    )
    assert not failures and all(controls.values())


if __name__ == "__main__":
    main()
