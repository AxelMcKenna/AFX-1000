"""Review-only FF01 same-envelope downward-fin and exact-aperture lid prototypes."""

import json
from pathlib import Path

from .analyze import DESIGN, OUT, ROOT, read, sha


def main():
    d = read(DESIGN)
    source = (
        """// FF01 PRIVATE feasibility prototype; not a fabricated or adopted enclosure.
// Changes only owned artifacts. Kept nominal external footprint334x157 and baseZ-6.2..0.
include <../sources/context/hardware/cad/a11/generated/layout.scad>
include <../sources/context/hardware/cad/a11/housing.scad>
part="bottom";
module exclusions(){
 for(p=FEET)translate(p)circle(r=12,$fn=96);
 for(p=BOLTS)translate(p)circle(r=6,$fn=96);
 for(p=RETURNS)translate(p)circle(r=5,$fn=96);
}
module fin_footprints(){difference(){union(){for(i=[0:11])translate([12,12+i*(133-3)/11])square([310,3]);}exclusions();}}
module plate_shape(){rounded_rect(334,157,7);}
module bottom(){difference(){union(){translate([0,0,-6.2])linear_extrude(6.2)plate_shape();translate([0,0,-26.2])linear_extrude(20)fin_footprints();}
for(p=FEET){translate([p[0],p[1],-6.21])cylinder(d=3.4,h=6.22,$fn=64);translate([p[0],p[1],-1.6])cylinder(d1=3.4,d2=6.6,h=1.61,$fn=64);}
for(p=BOLTS){translate([p[0],p[1],-6.21])cylinder(d=3.4,h=6.22,$fn=64);translate([p[0],p[1],-6.21])cylinder(d1=6.6,d2=3.4,h=1.61,$fn=64);}
for(p=RETURNS){translate([p[0],p[1],-6.21])cylinder(d=2.4,h=6.22,$fn=64);translate([p[0],p[1],-6.21])cylinder(d1=4.8,d2=2.4,h=1.21,$fn=64);}
}}
// Exact inherited panel apertures; no new structural/electrical/seam proof.
module lid(){translate([0,0,36])linear_extrude(2)panel_2d();}
if(part=="bottom")bottom();
if(part=="lid")render()lid();
if(part=="assembly"){bottom();lid();}
""".replace("FEET", json.dumps(d["feet"]["centres"]))
        .replace("BOLTS", json.dumps(d["shell_fasteners"]))
        .replace("RETURNS", json.dumps(d["return_support_attachments"]["centres"]))
    )
    (OUT / "prototype.scad").write_text(source)
    a = dict(
        part_scope="External lower plate/fin geometry and separate exact-aperture2mm lid ONLY; no complete-case/harness integration",
        base_z=[-6.2, 0],
        fin_z=[-26.2, -6.2],
        table_z=-28.8,
        nominal_table_gap_mm=2.6,
        feet_max_loaded_compression_bound=None,
        fin_lanes=12,
        fin_thickness_mm=3,
        fin_length_before_exclusions_mm=310,
        across_span_mm=133,
        nominal_clear_gap_mm=(133 - 12 * 3) / 11,
        foot_exclusion_r_mm=12,
        shell_bolt_exclusion_r_mm=6,
        return_exclusion_r_mm=5,
        analytic_fullspan_array_has_more_area_than_actual_notched_prototype=True,
        native_geometry_qualified=False,
        no_frozen_source_edits=True,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [Path(__file__).resolve(), DESIGN, OUT / "prototype.scad"]
        },
    )
    (OUT / "geometry-contract.json").write_text(json.dumps(a, indent=2) + "\n")


if __name__ == "__main__":
    main()
