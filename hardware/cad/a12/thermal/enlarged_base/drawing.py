"""CPU-only dimensioned review drawing; rendered surfaces retain actual pin count."""

import json
import os

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/afx-eb01-mpl")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

from .stage import OUT


def draw():
    a = json.loads((OUT / "analysis.json").read_text())
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_axes([0.055, 0.42, 0.89, 0.52])
    ax.set_aspect("equal")
    ax.add_patch(
        FancyBboxPatch(
            (0, 0), 334, 188.4, boxstyle="round,pad=0,rounding_size=7", fc="#e0e8eb", ec="#334d59", lw=1.3
        )
    )
    for x, y in a["pins"]["centres"]:
        ax.add_patch(Rectangle((x - 1.5, y - 1.5), 3, 3, fc="#a7b6bb", ec="none"))
    for x, y in a["shell_fasteners"]:
        ax.add_patch(Circle((x, y), 3.3, fc="white", ec="#a23d2b", lw=0.8))
        ax.add_patch(Circle((x, y), 1.7, fc="white", ec="#a23d2b", lw=0.7))
    for x, y in a["foot_axes"]:
        ax.add_patch(Circle((x, y), 9, fill=False, ec="#7a328b", lw=1.2))
        ax.add_patch(Circle((x, y), 3.3, fc="white", ec="#7a328b", lw=0.7))
    for r in a["retained_thermal_lands"]:
        x, y, w, h = r["metal_global"]
        ax.add_patch(Rectangle((x, y), w, h, fc="#ddaa42", ec="#986400", lw=0.8))
        if "corner_relief" in r:
            cx, cy = r["relief_centre_global"]
            ax.add_patch(
                Circle((cx, cy), r["corner_relief"]["metal_radius_mm"], fc="#e0e8eb", ec="#986400", lw=0.7)
            )
    for x, y in a["retained_supports"]:
        ax.add_patch(Circle((x, y), 3, fc="#50a3a1", ec="#286862", lw=0.7))
        ax.add_patch(Circle((x, y), 0.65, fc="white", ec="#286862", lw=0.5))
    for x, y in [[166, 113], [166, 133.125]]:
        ax.add_patch(Circle((x, y), 2.4, fc="white", ec="#215fc2", lw=0.8))
    ax.annotate("334", (334, -10), (167, -10), ha="center", arrowprops=dict(arrowstyle="->"))
    ax.annotate("", (0, -10), (160, -10), arrowprops=dict(arrowstyle="->"))
    ax.annotate(
        "188.4", (-10, 188.4), (-10, 94.2), va="center", rotation=90, arrowprops=dict(arrowstyle="->")
    )
    ax.annotate("", (-10, 0), (-10, 88), arrowprops=dict(arrowstyle="->"))
    ax.text(167, -23, "TOP/UNDERSIDE OVERLAY • coordinates in mm • 1,037 pins shown", ha="center", fontsize=9)
    ax.set_xlim(-20, 350)
    ax.set_ylim(-29, 201)
    ax.invert_yaxis()
    ax.axis("off")
    fig.text(0.06, 0.965, "EB01  Enlarged base + retained-carrier attachments", fontsize=17, weight="bold")
    sx = fig.add_axes([0.06, 0.19, 0.39, 0.19])
    sx.set_aspect("equal")
    sx.add_patch(Rectangle((0, -6.2), 60, 6.2, fc="#b9c5ca", ec="#334d59"))
    for x in [3, 10, 31, 38, 45, 52]:
        sx.add_patch(Rectangle((x, -18.2), 3, 12, fc="#b9c5ca", ec="#334d59", lw=0.7))
    sx.add_patch(Rectangle((12, -25.2), 18, 19, fc="#aaa", ec="#555"))
    sx.add_patch(Rectangle((14.65, -28.8), 12.7, 3.6, fc="#333", ec="#111"))
    sx.plot([21, 21], [-19.2, -6.2], color="white", lw=2)
    sx.plot([21, 21], [-12, 0], color="#a03a2d", lw=2)
    sx.text(62, -2, "plate top Z0 / bottom−6.2", fontsize=8)
    sx.text(62, -12, "3×3 pins; bottom−18.2", fontsize=8)
    sx.text(62, -22, "OD18×19 foot; M3 pilot13 deep", fontsize=8)
    sx.text(62, -28.8, "SJ5312 nominal bottom−28.8", fontsize=8)
    sx.set_xlim(-1, 130)
    sx.set_ylim(-32, 5)
    sx.axis("off")
    fig.text(0.52, 0.365, "NINE LOWER AXES", fontsize=10, weight="bold")
    fig.text(
        0.52,
        0.345,
        "X8 /167 /326 at Y8 /149 /180.4\nM3×16 + Würth03223, nut Z5..7.4\nØ3.4 bore; underside Ø6.6/90°×1.6 CSK",
        fontsize=9,
        va="top",
        linespacing=1.5,
    )
    fig.text(0.52, 0.26, "FOUR FEET", fontsize=10, weight="bold")
    fig.text(
        0.52,
        0.24,
        "(20,20), (314,20), (20,168.4), (314,168.4)\nM3×12; upper Ø6.6/90°×1.6 CSK\nNominal engagement5.8; available thread≥10",
        fontsize=9,
        va="top",
        linespacing=1.5,
    )
    fig.text(
        0.06,
        0.135,
        "RETAINED: four live-node-insulated lands Z5.28; ten P03 supports Z6.3; two return supports at(166,113)/(166,133.125).",
        fontsize=9,
    )
    fig.text(
        0.06,
        0.108,
        "Drawing is a REVIEW REQUIREMENT, not fabrication release. Hole/fit/thread/material/flatness/adhesive and load tests remain unaccepted.",
        fontsize=9,
        color="#9b3028",
    )
    fig.text(
        0.06,
        0.08,
        "Pin gap4 nominal. Minimum blank envelope24.5 thick before workholding allowance. Black anodize provides NO electrical isolation credit.",
        fontsize=9,
    )
    fig.text(
        0.06,
        0.052,
        "No metal walls/lid or forced-air tray adopted. H20 pin count matches; explicit bores/countersinks/supports require a fresh numerical thermal model.",
        fontsize=9,
    )
    fig.savefig(OUT / "EB01-drawing.svg")
    fig.savefig(OUT / "EB01-drawing.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    draw()
