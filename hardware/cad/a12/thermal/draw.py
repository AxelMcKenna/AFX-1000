"""Dimensioned vector fabrication/assembly drawing; dimensions are authoritative."""

from html import escape

from .generate import OUT, lands, load, mounts, pin_centres


def main():
    d = load()
    b = d["base"]
    bottom = b["plate_top_z"] - b["plate_thickness"]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1660" viewBox="0 0 1400 1660">',
        '<rect width="1400" height="1660" fill="white"/>',
        "<style>text{font-family:Arial,sans-serif;fill:#17202a} .dim{font-size:15px} .note{font-size:17px} .title{font-size:26px;font-weight:bold} .line{fill:none;stroke:#17202a;stroke-width:1.4}</style>",
    ]

    def text(x, y, s, cls="note"):
        svg.append(f'<text x="{x}" y="{y}" class="{cls}">{escape(s)}</text>')

    def line(x1, y1, x2, y2, color="#17202a"):
        svg.append(f'<path d="M{x1},{y1}L{x2},{y2}" stroke="{color}" fill="none"/>')

    text(42, 43, "AFX-A12-T01-BASE / FOOT — external thermal base", "title")
    text(42, 73, "DESIGN CANDIDATE — NOT FABRICATION RELEASED — all dimensions mm")
    text(42, 102, "6061-T6/T651 • STEP is nominal solid • threads are drawing callouts • no scale from print")
    scale = 3.6
    ox = 95
    oy = 160

    def rect(x, y, w, h, fill="none", stroke="#17202a", rx=0):
        svg.append(
            f'<rect x="{ox + x * scale}" y="{oy + y * scale}" width="{w * scale}" height="{h * scale}" rx="{rx * scale}" fill="{fill}" stroke="{stroke}"/>'
        )

    def circle(x, y, r, fill="none", stroke="#17202a"):
        svg.append(
            f'<circle cx="{ox + x * scale}" cy="{oy + y * scale}" r="{r * scale}" fill="{fill}" stroke="{stroke}"/>'
        )

    rect(0, 0, 334, 157, "#f2f4f4", rx=7)
    for x, y in pin_centres(d):
        rect(x - 1.5, y - 1.5, 3, 3, "#d5d8dc", "#b3b6b7")
    rect(206.5, 40.5, 81, 33, "#e8daef", rx=1)
    for x, y in d["shell_fasteners"]:
        circle(x, y, 3)
        circle(x, y, 1.7)
    for x, y in d["return_support_attachments"]["centres"]:
        circle(x, y, 2.4, stroke="#8e44ad")
        circle(x, y, 1.2)
    for x, y in d["feet"]["centres"]:
        circle(x, y, 9, stroke="#2e86c1")
        circle(x, y, 3)
        circle(x, y, 1.7)
    for x, y in mounts(d):
        circle(x, y, 3, "#d4efdf")
        circle(x, y, 0.65)
    for site in lands(d):
        for kind, fill in (("cut", "#fadbd8"), ("metal", "#f5b7b1")):
            x, y, w, h = site[kind + "_global"]
            if "corner_relief" not in site:
                rect(x, y, w, h, fill, "#c0392b")
                continue
            cx, cy = site["relief_centre_global"]
            radius = site["corner_relief"]["metal_radius_mm" if kind == "metal" else "tim_radius_mm"]
            tag = site["id"] + kind
            ax, ay, ww, hh = ox + x * scale, oy + y * scale, w * scale, h * scale
            ccx, ccy, rr = ox + cx * scale, oy + cy * scale, radius * scale
            svg.append(
                f'<defs><clipPath id="{tag}"><rect x="{ax}" y="{ay}" width="{ww}" height="{hh}"/></clipPath></defs>'
            )
            svg.append(
                f'<path clip-path="url(#{tag})" d="M{ax},{ay}h{ww}v{hh}h{-ww}Z M{ccx - rr},{ccy}a{rr},{rr} 0 1,0 {2 * rr},0a{rr},{rr} 0 1,0 {-2 * rr},0Z" fill-rule="evenodd" fill="{fill}" stroke="#c0392b"/>'
            )
    line(ox, oy - 22, ox + 334 * scale, oy - 22)
    line(ox, oy - 30, ox, oy)
    line(ox + 334 * scale, oy - 30, ox + 334 * scale, oy)
    text(ox + 155 * scale, oy - 30, "334 ±0.10", "dim")
    line(ox - 28, oy, ox - 28, oy + 157 * scale)
    line(ox - 37, oy, ox, oy)
    line(ox - 37, oy + 157 * scale, ox, oy + 157 * scale)
    text(12, oy + 75 * scale, "157", "dim")
    text(95, 750, "TOP VIEW: red = isolated TIM/metal lands; green = M1.6 supports; blue = underside feet.")
    text(
        95,
        776,
        "Grey pin outlines shown through plate for location only. P03 board datum (168,108), bottom z6.30–6.70.",
    )
    # Section schematic at enlarged vertical scale, dimensions explicitly labelled.
    sx = 95
    sy = 980
    zs = 12

    def section_rect(x, z, w, h, fill):
        svg.append(
            f'<rect x="{sx + x}" y="{sy - (z + h) * zs}" width="{w}" height="{h * zs}" fill="{fill}" stroke="#17202a"/>'
        )

    section_rect(0, bottom, 1198, b["plate_thickness"], "#b3b6b7")
    for xx, ww in [(0, 720), (870, 160), (1090, 108)]:
        section_rect(xx, 0, ww, 2.8, "#f9e79f")
    for x in range(20, 1170, 40):
        section_rect(x, bottom - b["fin_height"], 12, b["fin_height"], "#b3b6b7")
    section_rect(740, b["plate_top_z"], 95, b["thermal_land_top_z"] - b["plate_top_z"], "#b3b6b7")
    section_rect(728, b["thermal_land_top_z"], 119, 6.5 - b["thermal_land_top_z"], "#f5b7b1")
    section_rect(1050, b["plate_top_z"], 30, 6.3 - b["plate_top_z"], "#b3b6b7")
    section_rect(1050, 6.3, 30, 0.2, "#82e0aa")
    section_rect(700, 6.5, 420, 1.6, "#2874a6")
    section_rect(36, bottom - 19, 65, 19, "#b3b6b7")
    section_rect(45, bottom - 22.6, 46, 3.6, "#566573")
    text(
        95,
        800,
        "SECTION SCHEMATIC (Z exaggerated): integral lands and supports; TIM separates every hot node.",
    )
    text(95, 829, "Metal top0; bottom−6.20; fin tips−18.20; nominal table−28.80; top panel +38.00.")
    text(
        95,
        855,
        "6.20 plate /12.00 pins /19.00 feet +3.60 bumper. Nominal overall height66.80; fin air gap10.60.",
    )
    y = 1340
    rows = [
        "CNC: ±0.10 general; thermal-land/support faces ±0.03 to shared datum; Ra≤1.6µm; no burrs/sharp pad edges.",
        "Black anodize exposed metal; MASK TIM lands + support/shim faces. Anodize/solder mask give NO isolation credit.",
        "6 shell holes: Ø3.4,Ø6.6/90° CSK UNDERSIDE,M3×16. 4 feet: same CSK TOP,M3×12. Retain plastic carrier with local windows.",
        "10 PCB posts: Ø6; M1.6×0.35 blind, ≥2.5 usable thread; Ø1.3 drill3.6 deep. PTS A91201604,4mm; equal OD6/ID2.3 shims.",
        "4 FOOT parts: Ø18×19, M3×0.5 usable10,Ø2.5 drill13 from upper face; lower SJ5312 bumper Ø12.7×3.6. Verify loaded height.",
        "TIM: Henkel2195667,TGP6000ULM1.524±10%. Cut to schedule; ≤0.03 thickness spread across set; natural tack only.",
        "Measure pad thickness, select equal0..0.40 shims by0.05 steps; target20%compression. Local measured10..30%allocation.",
        "See fabrication-schedule.json for all XY datums, pads, pin centres, tolerances and assembly holds. No AGND/chassis bond.",
        "U13 metal local[101,2.2]..[117,14.2], minusR4.8 at(117,4); TIM[100,1.2]..[118,15.2], minusR3.8 atsamecentre.",
        "U13 floorwindow metalrectangle+.40 onalledges, minusR4.4 atsamecentre; separateØ6.8 supportwindow preserves1.0web.",
    ]
    for row in rows:
        text(42, y, row, "dim")
        y += 29
    svg.append("</svg>")
    (OUT / "fabrication-drawing.svg").write_text("\n".join(svg) + "\n")
    import json

    schedule = dict(
        units="mm",
        origin="Enclosure XY origin;z0 original shell underside datum; all XY dimensions use native +Y convention",
        base_part=d["base"]["part_number"],
        base_envelope=[334, 157, 6.2],
        corner_radius=7,
        plate_bottom_z=bottom,
        plate_top_z=b["plate_top_z"],
        fin_tip_z=bottom - b["fin_height"],
        pin_width=3,
        pin_height=12,
        pin_pitch=7,
        pin_centres=pin_centres(d),
        thermal_land_top_z=b["thermal_land_top_z"],
        sites=lands(d),
        pcb_support_xy=mounts(d),
        pcb_support_top_z=6.3,
        pcb_support_diameter=6,
        pcb_support_thread="M1.6x0.35 blind; minimum2.5 usable thread; tap drillØ1.3,3.6 deep fromtop. Bottom web must remain unbroken.",
        pcb_support_shim=dict(
            part="AFX-A12-T01-SHIM",
            material="PEEK or stainless; measuredflat",
            od=6,
            id=2.3,
            available_total_heights=[i * 0.05 for i in range(9)],
            same_height_at_all_supports=True,
        ),
        return_support_attachments=d["return_support_attachments"],
        shell_retaining_xy=d["shell_fasteners"],
        shell_hole=dict(
            through=3.4,
            csk_diameter=6.6,
            angle=90,
            csk_face="underside",
            screw="Accu SPK-M3-16-A2",
            nut="Wurth03223 DIN934,A2,5.5AFx2.4 listed; actuallot tolerances and A12 retention require approval",
        ),
        feet=d["feet"],
        foot_hole=dict(through=3.4, csk_diameter=6.6, angle=90, csk_face="upper"),
        output_floor_pocket=dict(
            x=206.5,
            y=40.5,
            w=81,
            h=33,
            corner_r=1,
            bottom_z=1.6,
            scope="Retained plastic carrier only; no metal pocket atZ0",
        ),
        general_tolerance=0.10,
        thermal_datum_tolerance=0.03,
        thermal_finish_ra_um=1.6,
        material=d["base"]["construction"],
        surface_finish=d["base"]["external_finish"],
        masking=d["base"]["contact_finish"],
        nominal_assembly_height=66.8,
        nominal_fins_table_clearance=10.6,
        typical_mass_from_cad="See cad-verification.json, includes base only; four feet add~52g",
        minimum_material_properties_certified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (OUT / "fabrication-schedule.json").write_text(json.dumps(schedule, indent=2) + "\n")


if __name__ == "__main__":
    main()
