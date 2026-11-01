"""Private ANA26 road and shifted north saddle bolt; terminals and DIG route fixed."""

import copy
import hashlib
import json
import math
from pathlib import Path

from . import caps, generate, support
from .analysis import area_screens

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
OUT = ROOT / "generated"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    import cadquery as cq

    baseline = json.loads((ROOT.parent/"inputs/PB02/design.json").read_text())
    candidate = generate.load()
    assert candidate["revision"] == "PB05-private-ANA26-northbolt6-source-clearance"
    assert not OUT.exists(), "Keep existing generated evidence immutable; use a new trial directory."
    OUT.mkdir(parents=True)
    (ROOT / "design.json").write_text(json.dumps(candidate, indent=2) + "\n")
    sources = [
        Path(__file__),
        ROOT / "design.json",
        generate.ROOT / "design.json",
        generate.ROOT / "generate.py",
        generate.ROOT / "caps.py",
        generate.ROOT / "support.py",
        generate.ROOT / "analysis.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in sources}
    parts = {}
    assembly = []
    for name in ["ANA", "DIG"]:
        copper = generate.shape(candidate, name)
        wrapped = generate.shape(
            candidate,
            name,
            maximum=True,
            wrap=candidate["insulation"]["maximum_build_each_face_allocation_mm"],
        )
        for q in [candidate["paths"][name]["points"][0], candidate["paths"][name]["points"][-1]]:
            wrapped = wrapped.cut(cq.Solid.makeCylinder(5.3, 8, cq.Vector(q[0], q[1], q[2] - 2)))
        envelope = wrapped.fuse(
            *[caps.pieces(candidate, name, i, True)["ENVELOPE"] for i in [0, 1]],
            *[generate.fasteners(candidate, name, i, True) for i in [0, 1]],
        ).clean()
        assert envelope.isValid() and len(envelope.Solids()) == 1
        local = {name + "-CU": copper, name + "-COVERED-ENVELOPE": envelope}
        assembly.append(copper)
        for i in [0, 1]:
            for label, obj in caps.pieces(candidate, name, i).items():
                local[name + "-CAP" + str(i) + "-" + label] = obj
                assembly.append(obj)
            screw = generate.fasteners(candidate, name, i)
            local[name + "-FASTENER" + str(i)] = screw
            assembly.append(screw)
        for label, obj in local.items():
            assert obj.isValid() and len(obj.Solids()) == 1
            cq.exporters.export(obj, str(OUT / (label + ".step")))
            cq.exporters.export(obj, str(OUT / (label + ".stl")), tolerance=0.01, angularTolerance=0.05)
            parts[label] = dict(valid=True, solid_count=1, volume_mm3=obj.Volume())
    supports = support.parts(candidate)
    for label, obj in supports.items():
        assert obj.isValid()
        cq.exporters.export(obj, str(OUT / (label + ".step")))
        cq.exporters.export(obj, str(OUT / (label + ".stl")), tolerance=0.01, angularTolerance=0.05)
        parts[label] = dict(valid=True, solid_count=len(obj.Solids()), volume_mm3=obj.Volume())
    bound_parts = (
        list(support.parts(candidate, True).values())
        + list(support.parts(candidate, True, film_override=0).values())
        + list(supports.values())
    )
    bound = bound_parts[0].fuse(*bound_parts[1:]).clean()
    assert bound.isValid()
    cq.exporters.export(bound, str(OUT / "SUPPORT-ENVELOPE.step"))
    cq.exporters.export(bound, str(OUT / "SUPPORT-ENVELOPE.stl"), tolerance=0.01, angularTolerance=0.05)
    parts["SUPPORT-ENVELOPE"] = dict(valid=True, solid_count=len(bound.Solids()), volume_mm3=bound.Volume())
    assembly.extend(supports.values())
    compound = cq.Compound.makeCompound(assembly)
    cq.exporters.export(compound, str(OUT / "positive-links.step"))
    cq.exporters.export(compound, str(OUT / "positive-links.stl"), tolerance=0.01, angularTolerance=0.05)

    def length(d, name):
        p = d["paths"][name]["points"]
        return math.fsum(math.dist(a, b) for a, b in zip(p, p[1:]))

    assert math.isclose(length(baseline, "DIG") - length(candidate, "DIG"), 0)
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        parts=parts,
        changed_ANA_points=dict(old=baseline["paths"]["ANA"]["points"],new=candidate["paths"]["ANA"]["points"]),
        changed_support=dict(old=baseline["support"],new=candidate["support"]),
        DIG_route_and_all_terminal_ports_unchanged=True,
        source_and_destination_ports_unchanged=True,
        original_DIG_length_mm=length(baseline, "DIG"),
        candidate_DIG_length_mm=length(candidate, "DIG"),
        analytical_minimum_area_mm2=area_screens(candidate),
        native_collision_checks_performed=False,
        normal_sections_or_3d_current_crowding_renewed=False,
        physical_qualified=False,
        complete_link_resistance_verified=False,
        fabrication_released=False,
        artifact_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".step", ".stl"]
        },
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    (OUT / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                parts=len(parts),
                DIG_length_mm=report["candidate_DIG_length_mm"],
                copper_volume_mm3=parts["DIG-CU"]["volume_mm3"],
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
