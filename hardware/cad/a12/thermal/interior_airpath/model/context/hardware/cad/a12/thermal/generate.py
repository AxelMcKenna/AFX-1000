"""Actual A12-T01 machined solids and integration modules, separate from A11/A12."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated"
P03 = REPO / "hardware/electronics/power_distribution/p03"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load():
    return json.loads((ROOT / "design.json").read_text())


def pin_centres(d):
    feet = d["feet"]["centres"]
    bolts = d["shell_fasteners"]
    answer = []
    for x in range(d["base"]["fin_border"], 334 - d["base"]["fin_border"] + 1, d["base"]["fin_pitch"]):
        for y in range(d["base"]["fin_border"], 157 - d["base"]["fin_border"] + 1, d["base"]["fin_pitch"]):
            if any(math.dist((x, y), c) < 12 for c in feet):
                continue
            if any(math.dist((x, y), c) < 6 for c in bolts):
                continue
            if any(
                math.dist((x, y), c)
                < d["return_support_attachments"]["fin_exclusion_radius"] + math.sqrt(2) * 1.5
                for c in d.get("return_support_attachments", {}).get("centres", [])
            ):
                continue
            answer.append((x, y))
    return answer


def mounts(d):
    return [
        (d["p03_datum"][0] + p[0], d["p03_datum"][1] + p[1])
        for p in d["board_mounts_relative"] + d["proposed_local_mounts_relative"]
    ]


def lands(d):
    result = []
    inset = d["tim"]["metal_land_inset_each_edge"]
    for row in d["thermal_lands"]:
        x, y, w, h = row["cut_relative"]
        x += d["p03_datum"][0]
        y += d["p03_datum"][1]
        site = dict(
            row,
            cut_global=[x, y, w, h],
            metal_global=[x + inset, y + inset, w - 2 * inset, h - 2 * inset],
        )
        if "corner_relief" in row:
            rx, ry = row["corner_relief"]["centre_relative"]
            site["relief_centre_global"] = [rx + d["p03_datum"][0], ry + d["p03_datum"][1]]
        site["metal_contact_area_mm2"] = contact_area(site, "metal")
        site["tim_cut_area_mm2"] = contact_area(site, "cut")
        result.append(site)
    return result


def circle_rect_area(rect, centre, radius):
    """Exact area of an axis-aligned rectangle intersecting a circle."""
    x, y, w, h = rect
    cx, cy = centre
    low, high = max(-radius, x - cx), min(radius, x + w - cx)
    if high <= low:
        return 0.0
    breaks = [low, high]
    for yy in (y - cy, y + h - cy):
        if abs(yy) < radius:
            a = math.sqrt(radius**2 - yy**2)
            breaks += [z for z in (-a, a) if low < z < high]

    def primitive(z):
        return (
            z * math.sqrt(max(0, radius**2 - z**2)) + radius**2 * math.asin(max(-1, min(1, z / radius)))
        ) / 2

    answer = 0.0
    for a, b in zip(sorted(breaks), sorted(breaks)[1:]):
        root = math.sqrt(max(0, radius**2 - ((a + b) / 2) ** 2))
        lower, upper = max(y - cy, -root), min(y + h - cy, root)
        if upper <= lower:
            continue
        upper_integral = (y + h - cy) * (b - a) if y + h - cy < root else primitive(b) - primitive(a)
        lower_integral = (y - cy) * (b - a) if y - cy > -root else -primitive(b) + primitive(a)
        answer += upper_integral - lower_integral
    return answer


def contact_area(site, kind="metal"):
    rect = site[kind + "_global"]
    area = rect[2] * rect[3]
    if "corner_relief" in site:
        radius = site["corner_relief"]["metal_radius_mm" if kind == "metal" else "tim_radius_mm"]
        area -= circle_rect_area(rect, site["relief_centre_global"], radius)
    return area


def contact_contains(site, x, y, kind="metal"):
    rx, ry, w, h = site[kind + "_global"]
    inside = (x >= rx) & (x <= rx + w) & (y >= ry) & (y <= ry + h)
    if "corner_relief" in site:
        cx, cy = site["relief_centre_global"]
        radius = site["corner_relief"]["metal_radius_mm" if kind == "metal" else "tim_radius_mm"]
        inside = inside & ((x - cx) ** 2 + (y - cy) ** 2 >= radius**2)
    return inside


def carrier_windows(d):
    windows = []
    for site in lands(d):
        x, y, w, h = site["metal_global"]
        c = 0.4
        windows.append(
            dict(
                id=site["id"],
                polygon_xy_mm=[
                    [x - c, y - c],
                    [x + w + c, y - c],
                    [x + w + c, y + h + c],
                    [x - c, y + h + c],
                ],
                through_z_mm=[-0.01, 2.81],
                nominal_radial_clearance_mm=c,
            )
        )
        if "corner_relief" in site:
            windows[-1]["subtract_circle"] = dict(
                centre_xy_mm=site["relief_centre_global"],
                radius_mm=site["corner_relief"]["metal_radius_mm"] - c,
            )
            windows[-1]["boolean_operation"] = "rectangle minus circle; separate support window remains"
    return windows


def scad(d):
    b = d["base"]
    z = b["plate_top_z"] - b["plate_thickness"]
    posts = mounts(d)
    sites = lands(d)
    q = json.dumps
    source = f"""// A12-T01 generated from thermal/design.json. No production/physical approval.
thermal_pins={q(pin_centres(d))};
thermal_mounts={q(posts)};
thermal_feet_xy={q(d["feet"]["centres"])};
thermal_shell_bolts={q(d["shell_fasteners"])};
thermal_return_supports={q(d.get("return_support_attachments", {}).get("centres", []))};
thermal_sites={q([r["metal_global"] for r in sites])};
thermal_tim_cuts={q([r["cut_global"] for r in sites])};
thermal_reliefs={q([[*r["relief_centre_global"], r["corner_relief"]["metal_radius_mm"], r["corner_relief"]["tim_radius_mm"]] if "corner_relief" in r else [0, 0, 0, 0] for r in sites])};
module thermal_site(i,kind=0,expand=0){{r=kind==0?thermal_sites[i]:thermal_tim_cuts[i];c=thermal_reliefs[i];difference(){{translate([r[0]-expand,r[1]-expand])square([r[2]+2*expand,r[3]+2*expand]);if(c[2]>0)translate([c[0],c[1]])circle(r=(kind==0?c[2]:c[3])-expand,$fn=256);}}}}
module thermal_round_rect(w,h,r){{hull()for(x=[r,w-r],y=[r,h-r])translate([x,y])circle(r=r,$fn=64);}}
module thermal_metal_base(){{difference(){{union(){{
 translate([0,0,{z}])linear_extrude({b["plate_thickness"]})thermal_round_rect(334,157,7);
 for(p=thermal_pins)translate([p[0]-1.5,p[1]-1.5,{z - b["fin_height"]}])cube([3,3,{b["fin_height"]}]);
 for(i=[0:len(thermal_sites)-1])translate([0,0,{b["plate_top_z"]}])linear_extrude({b["thermal_land_top_z"] - b["plate_top_z"]})thermal_site(i);
 for(p=thermal_mounts)translate([p[0],p[1],{b["plate_top_z"]}])cylinder(d=6,h={b["board_support_top_z"] - b["plate_top_z"]},$fn=48);
 }}
 translate([206.5,40.5,1.6])linear_extrude(2)thermal_round_rect(81,33,1);
 for(p=thermal_shell_bolts){{translate([p[0],p[1],{z - 0.1}])cylinder(d=3.4,h={b["plate_thickness"] + 0.2},$fn=48);translate([p[0],p[1],{z}])cylinder(d1=6.6,d2=3.4,h=1.6,$fn=64);}}
 for(p=thermal_feet_xy){{translate([p[0],p[1],{z - 0.1}])cylinder(d=3.4,h={b["plate_thickness"] + 0.2},$fn=48);translate([p[0],p[1],{b["plate_top_z"] - 1.6}])cylinder(d1=3.4,d2=6.6,h=1.6,$fn=64);}}
 for(p=thermal_mounts)translate([p[0],p[1],2.7])cylinder(d=1.3,h=3.7,$fn=32); // tap drill3.6 deep; >=2.5 usable M1.6 thread is a drawing callout
 for(p=thermal_return_supports){{translate([p[0],p[1],{z - 0.1}])cylinder(d=2.4,h={b["plate_thickness"] + 0.2},$fn=48);translate([p[0],p[1],{z}])cylinder(d1=4.8,d2=2.4,h=1.2,$fn=64);}}
}}}}
module thermal_pads(board_z=6.5){{color([.55,.55,.55])for(i=[0:len(thermal_tim_cuts)-1])translate([0,0,{b["thermal_land_top_z"]}])linear_extrude(board_z-{b["thermal_land_top_z"]})thermal_site(i,1);}}
module thermal_shims(height=.2){{for(p=thermal_mounts)translate([p[0],p[1],6.3])difference(){{cylinder(d=6,h=height,$fn=48);translate([0,0,-.01])cylinder(d=2.3,h=height+.02,$fn=32);}}}}
module thermal_feet(){{for(p=thermal_feet_xy){{color([.25,.25,.25])translate([p[0],p[1],{z - d["feet"]["height"]}])cylinder(d=18,h={d["feet"]["height"]},$fn=64);color([.1,.1,.1])translate([p[0],p[1],{z - d["feet"]["height"] - 3.6}])cylinder(d=12.7,h=3.6,$fn=64);}}}}
// Retain the complete structural plastic carrier except these local windows.
module thermal_floor_cut(){{for(i=[0:len(thermal_sites)-1])translate([0,0,-.01])linear_extrude(2.82)thermal_site(i,0,.4);for(p=thermal_mounts)translate([p[0],p[1],-.01])cylinder(d=6.8,h=6.8,$fn=64);for(p=thermal_return_supports)translate([p[0],p[1],-.01])cylinder(d=3.5,h=2.82,$fn=64);}}
// Proposed A12-only captured M3 nuts in the six existing lid bosses; root must integrate/recheck the shell.
module thermal_shell_nut_pockets(){{for(p=thermal_shell_bolts)translate([p[0],p[1],5.0])cylinder(d=5.7/cos(30),h=2.6,$fn=6);}}
module thermal_shell_nut_slots(){{for(p=thermal_shell_bolts)translate([p[0]-2.85,p[1]<78?p[1]:p[1]-6,5])cube([5.7,6,2.6]);}}
module thermal_assembly(){{color([.15,.15,.15])thermal_metal_base();thermal_pads();thermal_shims();thermal_feet();}}
"""
    (OUT / "thermal-base.scad").write_text(source)
    (OUT / "preview.scad").write_text(
        'include <thermal-base.scad>\npart="assembly";\nif(part=="assembly")thermal_assembly();\nif(part=="base")thermal_metal_base();\n'
    )


def cadquery_export(d):
    from importlib.metadata import version

    import cadquery as cq

    b = d["base"]
    bottom = b["plate_top_z"] - b["plate_thickness"]
    base = (
        cq.Workplane("XY")
        .box(334, 157, b["plate_thickness"], centered=(False, False, False))
        .translate((0, 0, bottom))
        .edges("|Z")
        .fillet(7)
        .val()
    )
    solids = []
    for x, y in pin_centres(d):
        solids.append(
            cq.Solid.makeBox(3, 3, b["fin_height"], cq.Vector(x - 1.5, y - 1.5, bottom - b["fin_height"]))
        )
    for r in lands(d):
        x, y, w, h = r["metal_global"]
        land = cq.Solid.makeBox(
            w, h, b["thermal_land_top_z"] - b["plate_top_z"], cq.Vector(x, y, b["plate_top_z"])
        )
        if "corner_relief" in r:
            cx, cy = r["relief_centre_global"]
            land = land.cut(
                cq.Solid.makeCylinder(
                    r["corner_relief"]["metal_radius_mm"],
                    b["thermal_land_top_z"] + 0.2,
                    cq.Vector(cx, cy, -0.1),
                )
            )
        solids.append(land)
    for x, y in mounts(d):
        solids.append(
            cq.Solid.makeCylinder(
                3, b["board_support_top_z"] - b["plate_top_z"], cq.Vector(x, y, b["plate_top_z"])
            )
        )
    base = base.fuse(*solids).clean()
    pocket = (
        cq.Workplane("XY")
        .box(81, 33, 2, centered=(False, False, False))
        .translate((206.5, 40.5, 1.6))
        .edges("|Z")
        .fillet(1)
        .val()
    )
    cuts = [pocket]
    for x, y in d["shell_fasteners"]:
        cuts += [
            cq.Solid.makeCylinder(1.7, b["plate_thickness"] + 0.2, cq.Vector(x, y, bottom - 0.1)),
            cq.Solid.makeCone(3.3, 1.7, 1.6, cq.Vector(x, y, bottom)),
        ]
    for x, y in d["feet"]["centres"]:
        cuts += [
            cq.Solid.makeCylinder(1.7, b["plate_thickness"] + 0.2, cq.Vector(x, y, bottom - 0.1)),
            cq.Solid.makeCone(1.7, 3.3, 1.6, cq.Vector(x, y, b["plate_top_z"] - 1.6)),
        ]
    for x, y in mounts(d):
        cuts.append(cq.Solid.makeCylinder(0.65, 3.7, cq.Vector(x, y, 2.7)))
    for x, y in d.get("return_support_attachments", {}).get("centres", []):
        cuts.extend(
            [
                cq.Solid.makeCylinder(1.2, b["plate_thickness"] + 0.2, cq.Vector(x, y, bottom - 0.1)),
                cq.Solid.makeCone(2.4, 1.2, 1.2, cq.Vector(x, y, bottom)),
            ]
        )
    base = base.cut(*cuts).clean()
    assert base.isValid() and len(base.Solids()) == 1
    cq.exporters.export(base, str(OUT / "AFX-A12-T01-BASE.step"))
    cq.exporters.export(base, str(OUT / "AFX-A12-T01-BASE.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(
        base,
        str(OUT / "base-isometric.svg"),
        opt={
            "width": 1200,
            "height": 650,
            "projectionDir": (1, -1, -1),
            "showHidden": False,
            "strokeWidth": 0.3,
        },
    )
    reimport = cq.importers.importStep(str(OUT / "AFX-A12-T01-BASE.step")).val()
    assert reimport.isValid() and abs(reimport.Volume() - base.Volume()) < 0.001
    # Separate fabricated foot, represented by exact cylinder and blind tap-drill.
    foot = (
        cq.Solid.makeCylinder(9, d["feet"]["height"])
        .cut(cq.Solid.makeCylinder(1.25, 13, cq.Vector(0, 0, d["feet"]["height"] - 13)))
        .clean()
    )
    assert foot.isValid()
    cq.exporters.export(foot, str(OUT / "AFX-A12-T01-FOOT.step"))
    record = dict(
        cadquery_version=version("cadquery"),
        ocp_version=version("cadquery-ocp"),
        base_solid_valid=True,
        base_solid_count=1,
        step_roundtrip_volume_matches=True,
        base_volume_mm3=base.Volume(),
        base_mass_typical_kg=base.Volume() * 2.7e-6,
        base_surface_area_mm2=base.Area(),
        fin_count=len(pin_centres(d)),
        foot_solid_valid=foot.isValid(),
        foot_mass_typical_kg=foot.Volume() * 2.7e-6,
        threads_are_callouts_not_helical_brep=True,
        physical_fit_verified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    (OUT / "cad-verification.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    OUT.mkdir(exist_ok=True)
    d = load()
    scad(d)
    record = cadquery_export(d)
    bottom = d["base"]["plate_top_z"] - d["base"]["plate_thickness"]
    footbottom = bottom - d["feet"]["height"] - d["feet"]["bumper_nominal_height"]
    (OUT / "interface.json").write_text(
        json.dumps(
            dict(
                revision=d["revision"],
                base_top_z=d["base"]["plate_top_z"],
                base_bottom_z=bottom,
                fin_bottom_z=bottom - d["base"]["fin_height"],
                nominal_foot_bottom_z=footbottom,
                assembled_housing_height_nominal_mm=38 - footbottom,
                nominal_fin_to_table_clearance_mm=d["feet"]["height"]
                + d["feet"]["bumper_nominal_height"]
                - d["base"]["fin_height"],
                p03_board_bottom_adjustable_z_mm=[6.3, 6.7],
                thermal_land_top_z=d["base"]["thermal_land_top_z"],
                thermal_land_tim_cuts=lands(d),
                board_mounts_global_mm=mounts(d),
                retained_structural_carrier_z_mm=[0, 2.8],
                local_rectangular_carrier_windows=carrier_windows(d),
                local_support_windows=dict(
                    centres=mounts(d),
                    diameter=6.8,
                    z_range=[-0.01, 6.79],
                    scope="Remove old P03 posts locally; retain all other carrier and standoff connections",
                ),
                shell_retaining_hardware=dict(
                    screw="Accu SPK-M3-16-A2",
                    quantity=6,
                    clearance_diameter=3.4,
                    countersink_diameter=6.6,
                    countersink_angle=90,
                    countersink_face="Metal underside",
                    metal_underside_z=bottom,
                    nominal_screw_tip_z=bottom + 16,
                    nut="Wurth03223 DIN934 A2,M3,5.5AF,2.4mm listed height; captured atZ5..7.6;lot tolerance approval open",
                    retained_plastic_bore_diameter=3.4,
                    physical_retention_and_clearance_verified=False,
                ),
                return_support_attachments=d.get("return_support_attachments", {}),
                support_electrical_keepout=dict(
                    p03_native_rule_radius_mm=3.7,
                    metal_radius_mm=3,
                    nominal_radial_margin_mm=0.7,
                    all_six_copper_layers=True,
                    pad_via_track_and_filled_zone_exclusion_required=True,
                    solder_mask_insulation_credit=False,
                    actual_native_copper_extraction_verified=False,
                ),
                root_integration="Retain original plastic floor/carrier and its standoff connections. Subtract ONLY thermal_floor_cut() local shaped land windows and Ø6.8 P03 support/post windows. Add metal beneath atZ0, pads, equal shims and feet. Apply six M3x16 attachments and proposed nut pockets/slots only after shell review. A11 untouched.",
                shell_retaining_hardware_stack_physically_verified=False,
                quiet_ground_bond="none;floating CHASSIS",
                physical_fit_verified=False,
                thermal_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
