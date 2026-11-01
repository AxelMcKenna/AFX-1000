"""Actual E23I2 geometry with explicit, still conditional mated assembly bounds."""

from hardware.cad.input_power import DATUM
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.input_protection.inlet_revision2.generate import ROOT as INLET
from hardware.electronics.output_stage.check_placement import courtyard, transform


def packet(original_data):
    tree = read_sexpr((INLET / "rear_inlet.kicad_pcb").read_text())
    x0, y0, z0 = DATUM
    top = z0 + 1.6
    bodies = []
    unchanged = {"e23_J1", "e23_S1", "e23_S1_actuator"}
    bodies += [
        ["inlet_" + e[0][4:], *e[1:]]
        for e in original_data["envelopes"]
        if e[0] in unchanged or e[0].startswith("e23_H")
    ]
    components = []
    edges = {
        tuple(map(float, first(line, end)[1:3]))
        for line in children(tree, "gr_line")
        if first(line, "layer")[1] == "Edge.Cuts"
        for end in ["start", "end"]
    }
    assert edges == {(100 + x, 100 + y) for x, y in original_data["input_outline"]}, (
        "Rear inlet outline changed"
    )
    mounts = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref.startswith("H"):
            mx, my = map(float, first(fp, "at")[1:3])
            mounts.append((round(x0 + mx - 100, 6), round(y0 + my - 100, 6)))
            continue
        assert first(fp, "layer")[1] == "F.Cu"
        if ref in {"J1", "S1"}:
            expected = {"J1": (140, 110.7, 180), "S1": (154, 101.2, 180)}[ref]
            assert all(abs(float(v) - e) < 1e-6 for v, e in zip(first(fp, "at")[1:4], expected)), (
                "Rear jack/switch moved"
            )
        x, y, xx, yy = courtyard(fp, "F.CrtYd")
        components.append(dict(reference=ref, courtyard_native_mm=[x, y, xx, yy]))
        if ref not in {"J1", "S1"}:
            height = {"F1": 4.31, "J2": 11.0, "J3": 12.31}[ref]
            # Expand the entire side-entry mated assembly before the wire bend.
            # This conservative allocation must be replaced by supplier-tolerance
            # and assembled-harness verification; it is not a measured dimension.
            if ref == "J2":
                at = first(fp, "at")
                assert float(at[1]) == 144 and float(at[2]) == 128 and float(at[3]) == 0
                bx, by, w, d = x0 + 41.5, y0 + 26, 9.5, 24
            else:
                bx, by, w, d = x0 + x - 100 - 0.5, y0 + y - 100 - 0.5, xx - x + 1, yy - y + 1
            bodies.append(
                [
                    "inlet_" + ref,
                    bx,
                    by,
                    top,
                    w,
                    d,
                    height,
                    "Actual E23I2 footprint location with conditional complete mated/height reserve",
                ]
            )
        for pad in children(fp, "pad"):
            if pad[2] not in {"thru_hole", "np_thru_hole"}:
                continue
            x, y = transform(fp, first(pad, "at")[1:3])
            x, y = x0 + x - 100, y0 + y - 100
            height = 4.15 if ref == "J1" else 1.15 if ref == "S1" else 3.15
            width = 1.1 if ref == "S1" else 2.6 if ref == "J1" else 2
            number = str(pad[1]) or str(len(bodies))
            bodies.append(
                [
                    f"inlet_{ref}_lead_{number}",
                    x - width / 2,
                    y - width / 2,
                    z0 - height,
                    width,
                    width,
                    height,
                    "Trimmed terminal/solder/seat allocation; assembly unverified",
                ]
            )
    assert {p["reference"] for p in components} == {"J1", "J2", "J3", "F1", "S1"}
    assert set(mounts) == {
        (round(m[1], 6), round(m[2], 6)) for m in original_data["board_mounts"] if m[0] == "input_power"
    }, "Rear inlet mounting changed"
    return dict(
        board=["input_power", *DATUM, 64, 44, 1.6, "E23I2 passive rear inlet; P03 owns current guard"],
        bodies=bodies,
        components=components,
        physical_fit_verified=False,
    )
