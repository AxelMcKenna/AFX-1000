"""Derive translated supplementary nominal mates without altering AP03 parts."""

from .stage import OUT, PARENT, ROOT, require_parent, sha, write


def build():
    if (ROOT/"mating.scad").exists() or (ROOT/"handoff.json").exists():
        raise RuntimeError("Existing interface fixture cannot be overwritten")
    require_parent()
    changes={}
    for name in ["mating.py","mating.scad","mating_guards.scad","mating_audit.py",
                 "guard_domain_audit.py","seated_stage.py","seated_mating.py"]:
        original=(PARENT/name).read_text()
        s=original.replace("AP02","AP03")
        if name=="mating.scad":
            s=s.replace("[74.3,138.985,-9.1]","[74.3,133.985,-9.1]")
            s=s.replace("[49.8,142.8,","[49.8,137.8,")
            s=s.replace("[87.8,141.485,-15.2]","[88.8,136.485,-15.2]")
            s=s.replace("[87.8,142.005,-15.2]","[88.8,137.005,-15.2]")
        if name=="mating_guards.scad":
            s=s.replace("y=[139,144]","y=[134,139]")
            s=s.replace("mg_Y(141.5);mg_Y(142)","mg_Y(136.5);mg_Y(137)")
            s=s.replace("mg_Y(142);mg_Y(144)","mg_Y(137);mg_Y(139)")
            s=s.replace("[x,142-mg,-10]","[x,137-mg,-10]")
        if name=="mating_audit.py":
            s=s.replace("from .port_boundary_audit import distance", "from hardware.cad.a12.thermal.interior_airpath.port_boundary_audit import distance")
            s=s.replace("(1, [139, 144])","(1, [134, 139])")
            s=s.replace("(1, [141.5, 142])","(1, [136.5, 137])")
            s=s.replace("(1, [142, 144])","(1, [137, 139])")
            s=s.replace("1, [142, 144])","1, [137, 139])")
        if name=="seated_stage.py":
            s=s.replace("[x,142,-10]","[x,137,-10]")
        (ROOT/name).write_text(s)
        changes[name]=dict(parent_sha256=sha(PARENT/name),derived_sha256=sha(ROOT/name))
    write(OUT/"interface-derivation.json",dict(source_sha256={"interfaces_stage.py":sha(ROOT/"interfaces_stage.py")},
          copied_source_and_derived=changes,original_parts_modified=False,
          reason="Translate only rear-wall contact datums and controls5mm; meter-border controls move to the retained outer edge beyond the larger aperture.",
          masks_are_proposed_test_only_pending_actual_raw_facet_audit=True))


if __name__=="__main__":
    build()
