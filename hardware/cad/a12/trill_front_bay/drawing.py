"""Nominal post STEP and source-dimension drawing; no selected thread/material."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run():
    import cadquery as cq
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    r = json.loads((ROOT / "generated/analysis.json").read_text())
    out = ROOT / "generated"
    parts = []
    for x, y in r["mount_centres_mm"]:
        post = cq.Workplane("XY").circle(3.6).extrude(17.3).translate((x, y, 2.7))
        bore = cq.Workplane("XY").circle(2.05 / 2).extrude(4.71).translate((x, y, 15.3))
        parts.append(post.cut(bore).val())
    assembly = cq.Compound.makeCompound(parts)
    assert assembly.isValid() and len(assembly.Solids()) == 2
    cq.exporters.export(assembly, str(out / "posts.step"))
    native = json.loads((out / "verification.json").read_text())["cases"]["posts_geometry"]["statistics"][
        "volume_mm3"
    ]
    analytic = assembly.Volume()
    diff = abs(native - analytic) / analytic
    assert diff < 0.002
    (out / "step-review.json").write_text(
        json.dumps(
            dict(
                valid=True,
                solids=2,
                analytic_nominal_volume_mm3=analytic,
                native_circumscribed_envelope_volume_mm3=native,
                relative_difference=diff,
                native_max_polygon_flat_error_mm=3.6 * (1 - math.cos(math.pi / 128)),
                thread_profile_not_modelled=True,
                material_and_fabrication_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    a = axes[0]
    a.add_patch(Rectangle((13, 153.75), 151, 9.25, fc="#e5c29c", ec="#8d6133", alpha=0.65))
    a.add_patch(Rectangle((82, 158), 53.848, 21.844, fc="none", ec="#557c45", lw=1.6))
    for i, (x, y) in enumerate(r["mount_centres_mm"]):
        a.add_patch(Circle((x, y), 3.6, fc="#9dbfc6", ec="#45626a"))
        a.add_patch(Circle((x, y), 1.6, fc="white", ec="black"))
        a.annotate(
            "H" + str(i + 1), xy=(x, y), xytext=(x + 4, y + 2), fontsize=9, arrowprops=dict(arrowstyle="-")
        )
    a.axhline(185.6, c="#555", ls="--")
    a.text(82, 186.3, "Front inner wall Y185.6", fontsize=8)
    a.annotate(
        "Post edge Y165.322 → growth edge Y163: 2.322 mm gap",
        xy=(130.0871, 165.322),
        xytext=(76, 151),
        fontsize=8,
        arrowprops=dict(arrowstyle="-"),
    )
    a.set(
        xlim=(72, 145),
        ylim=(147, 189),
        xlabel="World X (mm)",
        ylabel="World Y (mm)",
        title="Top: current C3 board over front-bay posts",
    )
    a.set_aspect("equal")
    a.grid(alpha=0.15)
    a = axes[1]
    a.add_patch(Rectangle((-3.6, 2.7), 7.2, 17.3, fc="#9dbfc6", ec="#45626a"))
    a.add_patch(Rectangle((-1.025, 15.3), 2.05, 4.7, fc="white", ec="#45626a"))
    a.add_patch(Rectangle((-5, 20), 10, 1.6, fc="#799c65", ec="#45626a"))
    a.add_patch(Rectangle((-1.6, 20), 3.2, 1.6, fc="white", ec="black"))
    a.add_patch(Rectangle((-3.2, 21.6), 6.4, 2.2, fc="none", ec="#ab7737"))
    a.add_patch(Rectangle((-1.25, 15.6), 2.5, 6, fc="none", ec="#ab7737", ls="--"))
    a.axhline(2.8, c="#555", ls="--")
    a.text(5.7, 2.8, "Floor top2.8; post base2.7", fontsize=8, va="center")
    for z, t in [
        (15.3, "Blind pilot Ø2.05 starts15.3"),
        (20, "PCB seat20.0"),
        (21.6, "PCB top21.6"),
        (23.8, "Head/washer ceiling23.8"),
    ]:
        a.axhline(z, c="#aaa", lw=0.5, ls="--")
        a.text(5.7, z, t, fontsize=8, va="center", bbox=dict(fc="white", ec="none", pad=1))
    a.set(
        xlim=(-7, 24),
        ylim=(1.5, 25.5),
        xlabel="Relative X (mm)",
        ylabel="World Z (mm)",
        title="Section requirement: exact fastener/thread unselected",
    )
    a.grid(alpha=0.15)
    fig.suptitle(
        "TC02 / two insulating floor-post candidates — nominal dimensions, unqualified materials and hardware",
        fontsize=12,
    )
    fig.text(
        0.03,
        0.02,
        "C3 origin[82,158,20]; PCB53.848 ×21.844 ×1.6. Proposed min bore3.1 is an acceptance requirement, not a vendor guarantee.",
        fontsize=9,
    )
    fig.tight_layout(rect=[0, 0.06, 1, 0.92])
    fig.savefig(out / "dimensions.png", dpi=160)
    fig.savefig(out / "dimensions.svg")
    plt.close(fig)
    print(json.dumps(dict(STEP_volume=analytic, relative_native_difference=diff)))


if __name__ == "__main__":
    run()
