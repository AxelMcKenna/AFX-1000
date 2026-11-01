"""Actual saved bottom obstacles and conditional heat-path shares, CPU only."""

import json
import os

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/afx-mpl")

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .baseline import METAL, OUT, ROOT, TIM


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [1.1, 1]})
    tree = read_sexpr((ROOT / "sources/power_p03.kicad_pcb").read_text())
    for zone in children(tree, "zone"):
        if not children(zone, "net") or str(first(zone, "net")[1]).lstrip("/") != "AGND":
            continue
        for fill in children(zone, "filled_polygon"):
            if first(fill, "layer")[1] != "B.Cu":
                continue
            xy = [tuple(float(q) - 100 for q in p[1:3]) for p in children(first(fill, "pts"), "xy")]
            ax.add_patch(Polygon(xy, color="#3d985e", alpha=0.3))
    for f in children(tree, "footprint"):
        if first(f, "layer")[1] != "B.Cu":
            continue
        x, y = map(float, first(f, "at")[1:3])
        if not (117 < x < 135 and 114 < y < 130):
            continue
        box = courtyard(f, "B.CrtYd")
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        a, b, c, d = [v - 100 for v in box]
        ax.add_patch(Rectangle((a, b), c - a, d - b, facecolor="#d7a0a5", edgecolor="#823e49", alpha=0.45))
        ax.text((a + c) / 2, (b + d) / 2, ref, fontsize=8, ha="center", va="center", clip_on=True)
    native, _, _ = json.loads((ROOT / "sources/obstacles.json").read_text())
    for row in native["boxes"]:
        if row[0].startswith("P03_J106_tail"):
            x, y, z, w, h, t = row[1:7]
            ax.add_patch(Rectangle((x - 168, y - 108), w, h, facecolor="#c4781f", alpha=0.65))
    for name, box, color in [("TIM", TIM, "#3b68ba"), ("metal", METAL, "#333333")]:
        a, b, c, d = [v - 100 for v in box]
        ax.add_patch(
            Rectangle(
                (a, b),
                c - a,
                d - b,
                fill=False,
                edgecolor=color,
                linewidth=2,
                linestyle="--" if name == "TIM" else "-",
            )
        )
    for via in children(tree, "via"):
        x, y = map(float, first(via, "at")[1:3])
        if 118 < x < 134 and 115 < y < 128:
            net = str(first(via, "net")[1]).lstrip("/")
            ax.add_patch(
                Circle(
                    (x - 100, y - 100),
                    float(first(via, "size")[1]) / 2,
                    fill=False,
                    edgecolor="#10733b" if net == "AGND" else "#b32936",
                    linewidth=0.8,
                )
            )
    ax.plot(26.25, 20, "k+", markersize=10)
    ax.set(
        xlim=(18, 33),
        ylim=(28, 15),
        aspect="equal",
        xlabel="P03 relative X (mm)",
        ylabel="P03 relative Y (mm)",
        title="Rejected local landing: actual bottom copper/obstacles",
    )
    ax.grid(alpha=0.15)
    report = json.loads((OUT / "analysis.json").read_text())
    r = report["finer_grid"]
    e = r["unit_heat_energy_decomposition_c_per_w"]
    values = [
        14.9,
        e["via_barrels_all_segments"],
        e["sheet_spreading_total"],
        e["tim_bulk_under_actual_bottom_copper"],
        e["peak_above_uniform_source_mean"],
        r["aluminum_land_axial_c_per_w"],
        r["extra_contact_assumed_c_per_w"],
    ]
    names = [
        "DGN package metric",
        "Via energy share",
        "Sheet energy share",
        "TIM energy share",
        "EP peak above mean",
        "Al land axial",
        "Assumed contact",
    ]
    bx.barh(
        names, values, color=["#747474", "#b47b33", "#bf963f", "#ba4d57", "#747474", "#747474", "#747474"]
    )
    for i, v in enumerate(values):
        bx.text(v + 1, i, f"{v:.2f}", va="center", fontsize=9)
    bx.invert_yaxis()
    bx.set(
        xlabel="Conditional K/W contribution / energy share",
        xlim=(0, 125),
        title=f"Local-path screen: {r['conditional_total_junction_to_base_c_per_w']:.2f} K/W",
    )
    fig.text(
        0.07,
        0.07,
        "Blue dashed TIM; black metal; orange J106 tails\nGreen saved B.Cu / AGND vias; red foreign vias",
        fontsize=9,
    )
    fig.text(
        0.55,
        0.045,
        "Shares use the 1 W network energy identity, not independent series resistors.\nPackage/TIM material bounds, contact uncertainty and full-board paths missing.\nNo measured temperature or qualification pass.",
        fontsize=8,
    )
    fig.suptitle("U102 / TPS7A1601DGNR - source-bound rejected baseline", fontsize=14)
    fig.tight_layout(rect=(0, 0.14, 1, 0.95))
    fig.savefig(OUT / "baseline-review.png", dpi=150)
    fig.savefig(OUT / "baseline-review.svg")


if __name__ == "__main__":
    main()
