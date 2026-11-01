"""Read-only applicability of actual Seed3 STEP, pin grid and existing EI02 reserves."""

import csv
import hashlib
import json
from pathlib import Path

import cadquery as cq

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
PRIMARY = ROOT / "sources/primary"
BOARD = ROOT.parent / "processor-awg18-ear-fanout-j29-central"
SCENE = REPO / "hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bbox(s):
    b = s.BoundingBox()
    return [b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax]


def box(row):
    return cq.Solid.makeBox(*row[4:7], cq.Vector(*row[1:4]))


def apply(s, plane):
    return s.rotate((0, 0, 0), (0, 0, 1), 90).translate((89.63 + 1.42875, 87.98 - 1.42875, plane))


def run():
    step = PRIMARY / "ES_Daisy_Seed3_Rev5.step"
    pcb = BOARD / "processor_carrier.kicad_pcb"
    inputs = [
        step,
        pcb,
        BOARD / "generated/netlist.xml",
        BOARD / "components.json",
        PRIMARY / "Seed3_pinout.csv",
        PRIMARY / "Daisy_Seed3_datasheet-v2p1p0.pdf",
        SCENE,
        Path(__file__),
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    shape = cq.importers.importStep(str(step)).val()
    solids = shape.Solids()
    assert len(solids) == 445
    native_board = solids[0]
    bb = bbox(native_board)
    assert all(abs(x - y) < 1e-5 for x, y in zip(bb, [0, 0, 0, 18, 51.15, 1.60055]))
    holes = []
    for f in native_board.Faces():
        if f.geomType() != "CYLINDER":
            continue
        c = f._geomAdaptor().Cylinder()
        v = c.Axis().Location()
        if abs(c.Radius() - 0.508) < 1e-7:
            holes.append([v.X(), v.Y()])
    assert len(holes) == 40
    tree = read_sexpr(pcb.read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "U1"] for p in children(f, "property"))
    )
    assert [float(x) for x in first(fp, "at")[1:]] == [159.63, 145.98, -90]
    pads = {str(p[1]): p for p in children(fp, "pad")}
    rows = []
    for pin, p in sorted(pads.items(), key=lambda v: int(v[0])):
        local = [float(x) for x in first(p, "at")[1:3]]
        expected = [local[0] + 1.42875, local[1] + 1.42875]
        closest = min(holes, key=lambda h: sum((a - b) ** 2 for a, b in zip(h, expected)))
        err = max(abs(a - b) for a, b in zip(closest, expected))
        assert err < 0.0001, (pin, err)
        rows.append(
            dict(
                pin=pin,
                carrier_local_mm=local,
                step_hole_axis_xy_mm=closest,
                step_nominal_grid_difference_mm=err,
                carrier_net=first(p, "net")[1],
            )
        )
    csvrows = list(csv.DictReader((PRIMARY / "Seed3_pinout.csv").read_text().splitlines()))
    assert len(csvrows) == 40 and {int(x["PINOUT"]) for x in csvrows} == set(range(1, 41))
    components = json.loads((BOARD / "components.json").read_text())
    u = next(x for x in components if x["ref"] == "U1")
    symbolnames = {str(p["number"]): p["name"] for p in u["pins"]}
    for c in csvrows:
        pin = str(c["PINOUT"])
        name = c["DAISY PIN NAME*"].strip()
        i = int(pin)
        if 1 <= i <= 15:
            assert symbolnames[pin] == f"D{i - 1}" and name == symbolnames[pin]
        elif 22 <= i <= 37:
            assert symbolnames[pin].split("_")[0] == f"D{i - 7}" and f"D{i - 7}" in name
    for pin, expected_net in {
        "20": "/AGND",
        "21": "/V3V3_ANALOG",
        "38": "/V3V3_IO",
        "39": "/SEED_VIN",
        "40": "/AGND",
    }.items():
        assert first(pads[pin], "net")[1] == expected_net
    names = {str(c["PINOUT"]): c["PRIMARY FUNCTION"].strip() for c in csvrows}
    assert (
        names["20"] == "AGND"
        and names["21"] == "+3V3A"
        and names["38"] == "+3V3D"
        and names["39"] == "VIN"
        and names["40"] == "GND"
    )
    line = next(x for x in SCENE.read_text().splitlines() if x.startswith("ui_inherited_envelopes="))
    scene = json.loads(line.split("=", 1)[1].rstrip(";"))
    selected = {r[0]: r for r in scene if r[0] in ["e19_U1", "e19_usb_socket", "e19_usb_plug"]}
    assert len(selected) == 3
    main_box = box(selected["e19_U1"])
    usb_box = box(selected["e19_usb_socket"])
    receiving = main_box.fuse(usb_box)
    # Receiving plane, not a claimed assembled maximum: provisional8.51socket+2.54male housing.
    plane = 19.15
    placed = apply(shape, plane)
    # A solid entirely within an axis-aligned receiving box needs no Boolean.
    # Only solids straddling their union require a real native difference.
    remainder = []
    protrusions = []
    checks = []

    def in_box(bounds, row):
        return all(
            bounds[j] >= row[1 + j] - 1e-7 and bounds[j + 3] <= row[1 + j] + row[4 + j] + 1e-7
            for j in range(3)
        )

    for i, solid in enumerate(placed.Solids()):
        b = bbox(solid)
        if in_box(b, selected["e19_U1"]):
            checks.append(dict(solid=i, proof="entire_native_solid_bbox_inside_U1", outside_mm3=0))
            continue
        protrusion = solid.cut(main_box)
        protrusions.append(protrusion)
        if in_box(b, selected["e19_usb_socket"]):
            checks.append(dict(solid=i, proof="entire_native_solid_bbox_inside_socket", outside_mm3=0))
            continue
        rem = protrusion.cut(usb_box)
        v = rem.Volume()
        remainder.append(v)
        checks.append(dict(solid=i, proof="exact_native_two_box_difference", outside_mm3=v))
        assert v < 1e-6, (i, v)
    assert len(checks) == 445 and sum(remainder) < 1e-6
    old_only = cq.Compound.makeCompound(protrusions)
    assert old_only.Volume() > 1, "Positive control must expose the USBoutsideU1box"
    controls = dict(
        actual_seed_volume_mm3=placed.Volume(),
        per_solid_checks=checks,
        outside_complete_existing_reserve_mm3=sum(remainder),
        outside_U1_box_only_positive_witness_mm3=old_only.Volume(),
    )
    # Deliberate beyond-reserve solid must be detected; no blanket union/empty proof.
    witness = cq.Solid.makeBox(0.2, 0.2, 0.2, cq.Vector(92.9, 94, 22))
    assert witness.cut(receiving).Volume() > 0.0079
    controls["beyond_complete_reserve_positive_witness_mm3"] = witness.cut(receiving).Volume()
    # The full composed existing nominal reserve, not the incomplete U1 box, is the applicability boundary.
    report = dict(
        source_sha256=hashes,
        manufacturer_model="ES_Daisy_Seed3_Rev5",
        datasheet_revision="Seed3v2.1.0",
        manufacturer_revision_not_legacy_SeedRev5=True,
        STEP_solid_count=len(solids),
        STEP_PCB_bounds_mm=bb,
        STEP_all40_hole_axes_xy_mm=holes,
        pin_frame_origin_STEP_mm=[1.42875, 1.42875, 0],
        pin_frame_basis_to_world=[[0, -1, 0], [1, 0, 0], [0, 0, 1]],
        world_pin1_xy_mm=[89.63, 87.98],
        actual40_carrier_pads_match_STEP_grid_within_mm=0.0001,
        pads=rows,
        official_pin_csv=csvrows,
        CSV_pin40_DAISY_name_PG3_disagrees_with_PDF_DGND_but_primary_function_GND=True,
        power_pins_verified=True,
        audio_pins16_19_unused=True,
        current_EI02_reserve_rows=selected,
        receiving_module_PCB_plane_scenario_z_mm=plane,
        receiving_plane_is_not_approved_assembly_max=True,
        actual_STEP_world_bounds_mm=bbox(placed),
        controls=controls,
        nominal_existing_combined_U1_socket_reserve_contains_actual_STEP=True,
        prior_U1_only_gap_claim_superseded=True,
        forced_reserve_extension_required_by_this_nominal_evidence=False,
        nominal_sources_disagree_PCB_length_mm=[51.0, 51.15],
        nominal_sources_disagree_USB_protrusion_mm=[1.55, 1.2800001],
        socket_contact_male_pin_insertion_and_assembly_tolerances_qualified=False,
        regulator_identity_not_proved_by_external_model=True,
        physical_qualified=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    (ROOT / "generated/Seed3-applicability.json").write_text(json.dumps(report, indent=2) + "\n")
    cq.exporters.export(old_only, str(ROOT / "generated/Seed3-outside-U1-only-positive-control.step"))
    cq.exporters.export(placed, str(ROOT / "generated/Seed3-nominal-placed.step"))
    print(
        "Actual40hole match; completeexistingreserve outsidevolume",
        sum(remainder),
        "U1only witness",
        old_only.Volume(),
    )


if __name__ == "__main__":
    run()
