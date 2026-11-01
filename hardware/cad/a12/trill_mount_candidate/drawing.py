"""STEP saddle and independently annotated project-dimension drawing."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run():
    import cadquery as cq
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    r = json.loads((ROOT / "report.json").read_text())
    out = ROOT / "generated"

    def box(x, y, z, w, d, h):
        return cq.Workplane("XY").box(w, d, h, centered=(False, False, False)).translate((x, y, z))

    def cyl(x, y, z, d, h):
        return cq.Workplane("XY").circle(d / 2).extrude(h).translate((x, y, z))

    part = None
    solids = [box(70.1, y - 2.9, 24.6, 75.8, 5.8, 1.6) for y in [123, 145]]
    solids += [box(x - 2.9, 120.1, 24.6, 5.8, 27.8, 1.6) for x in [73, 143]]
    solids += [box(73, 131.4, 24.6, 70, 6, 1.6)]
    for m in r["mounts"]:
        x, y = m["world_xy_mm"]
        solids.append(cyl(x, y, 26.2, 5.4, 4.4))
    solids += [cyl(x, y, 26.2, 5.8, 16) for x in [73, 143] for y in [123, 145]]
    for s in solids:
        part = s if part is None else part.union(s)
    for m in r["mounts"]:
        x, y = m["world_xy_mm"]
        part = part.cut(cyl(x, y, 24.5, 3.4, 6.2))
    for x in [73, 143]:
        for y in [123, 145]:
            part = part.cut(cyl(x, y, 26.3, 2.2, 16))
    cq.exporters.export(part, str(out / "saddle.step"))
    volume = part.val().Volume()
    native = json.loads((out / "verification.json").read_text())["cases"]["saddle"]["statistics"][
        "volume_mm3"
    ]
    delta = abs(volume - native) / volume
    assert part.val().isValid() and len(part.solids().vals()) == 1 and delta < 0.002
    (out / "step-review.json").write_text(
        json.dumps(
            dict(
                valid=True,
                connected_solids=1,
                analytic_step_volume_mm3=volume,
                native_faceted_volume_mm3=native,
                relative_volume_difference=delta,
                volume_agreement_limit=0.002,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    for y in [123, 145]:
        ax.add_patch(Rectangle((70.1, y - 2.9), 75.8, 5.8, fc="#b5cdce", ec="#446061"))
    for x in [73, 143]:
        ax.add_patch(Rectangle((x - 2.9, 120.1), 5.8, 27.8, fc="#b5cdce", ec="#446061"))
    ax.add_patch(Rectangle((73, 131.4), 70, 6, fc="#b5cdce", ec="#446061"))
    ax.add_patch(Rectangle((82, 123.5), 53.848, 21.844, fc="none", ec="#527646", lw=1.5))
    for m in r["mounts"]:
        xy = m["world_xy_mm"]
        ax.add_patch(Circle(xy, 2.7, fc="#e5eded", ec="#446061"))
        ax.add_patch(Circle(xy, 1.7, fc="white", ec="black"))
        ax.annotate(
            m["ref"] + " Ø3.2 PCB /3.4 saddle",
            xy,
            xytext=(xy[0] - 12, xy[1] - 6),
            fontsize=7,
            arrowprops={"arrowstyle": "-"},
        )
    for x in [73, 143]:
        for y in [123, 145]:
            ax.add_patch(Circle((x, y), 2.9, fc="#9ab5b5", ec="#446061"))
            ax.add_patch(Circle((x, y), 1.1, fc="white", ec="black"))
    ax.annotate("C3 bounding reserve: 53.848 ×21.844 mm", (100, 145.344), (78, 151), fontsize=8)
    ax.set(
        xlim=(66, 150),
        ylim=(117, 155),
        xlabel="World X (mm)",
        ylabel="World Y (mm)",
        title="Top: actual mounting centres; conservative outline",
    )
    ax.set_aspect("equal")
    ax.grid(alpha=0.15)
    ax = axes[1]
    ax.add_patch(Rectangle((70.1, 24.6), 75.8, 1.6, fc="#b5cdce", ec="#446061"))
    for x in [73, 143]:
        ax.add_patch(Rectangle((x - 2.9, 26.2), 5.8, 16, fc="#9ab5b5", ec="#446061"))
    ax.add_patch(Rectangle((82, 30.6), 53.848, 1.6, fc="#779c65", ec="#446061"))
    for m in r["mounts"]:
        x = m["world_xy_mm"][0]
        ax.add_patch(Rectangle((x - 2.7, 26.2), 5.4, 4.4, fc="#b5cdce", ec="#446061"))
        ax.add_patch(Rectangle((x - 3.2, 32.2), 6.4, 3.2, fc="none", ec="#ab7c33"))
    for z, label in [
        (24.6, "24.6 saddle floor"),
        (30.6, "30.6 PCB seat"),
        (32.2, "32.2 PCB top"),
        (38.6, "38.6 project component ceiling"),
        (42.2, "42.2 backer underside"),
    ]:
        ax.axhline(z, c="#777", lw=0.5, ls="--")
        ax.text(147, z, label, va="center", fontsize=8, bbox=dict(facecolor="white", edgecolor="none", pad=1))
    ax.set(
        xlim=(66, 192),
        ylim=(23, 44),
        xlabel="World X (mm)",
        ylabel="World Z (mm)",
        title="Front: no post through central electrode opening",
    )
    ax.grid(alpha=0.15)
    fig.suptitle(
        "TC01 / C3 insulating saddle candidate — nominal geometry, unqualified hardware", fontsize=12
    )
    fig.text(
        0.03,
        0.015,
        "mm; no fabrication tolerance/strength/capacitance guarantee. Exact polymer, fasteners and backer attachment unresolved.",
        fontsize=9,
    )
    fig.tight_layout(rect=[0, 0.05, 1, 0.93])
    fig.savefig(out / "dimensioned.png", dpi=160)
    fig.savefig(out / "dimensioned.svg")
    plt.close(fig)
    print(json.dumps(dict(volume=volume, delta=delta)))


if __name__ == "__main__":
    run()
