"""Dimensioned actual-copper/obstacle drawing, CPU SVG and PNG only."""

import json
import os

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/afx-mpl")

from hardware.cad.a12.thermal.candidates.u10.generate import TIM
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .generate import OUT, ROOT
from .synthesize import CONTACT as METAL


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    tree = read_sexpr((ROOT / "variant/power_p03.kicad_pcb").read_text())
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 7), gridspec_kw={"width_ratios": [1.2, 1]})
    for z in children(tree, "zone"):
        if not children(z, "net") or str(first(z, "net")[1]).lstrip("/") != "RAW_N22":
            continue
        for f in children(z, "filled_polygon"):
            if first(f, "layer")[1] != "B.Cu":
                continue
            xy = [[float(p[1]) - 100, float(p[2]) - 100] for p in children(first(f, "pts"), "xy")]
            ax.add_patch(Polygon(xy, color="#35835a", alpha=0.45))
    for f in children(tree, "footprint"):
        x, y = map(float, first(f, "at")[1:3])
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        if not 186 < x < 200 or not 123 < y < 137:
            continue
        side = first(f, "layer")[1][0]
        if side == "B" or ref in ["U10", "L3", "R17", "C32"]:
            a, b, c, d = [v - 100 for v in courtyard(f, side + ".CrtYd")]
            ax.add_patch(
                Rectangle(
                    (a, b),
                    c - a,
                    d - b,
                    facecolor="#d9adb1" if side == "B" else "none",
                    edgecolor="#90434d" if side == "B" else "#4784a1",
                    linestyle="-" if side == "B" else ":",
                    alpha=0.8,
                )
            )
            ax.text(
                (a + c) / 2,
                (b + d) / 2,
                ref + (" F" if side == "F" else ""),
                fontsize=8,
                ha="center",
                va="center",
            )
    n = json.loads((OUT / "obstacles.json").read_text())["native"]
    for row in n["boxes"]:
        if row[0].startswith("P03_C32_tail"):
            _, x, y, z, w, h, t = row
            ax.add_patch(Rectangle((x - 168, y - 108), w, h, color="#c07b24", alpha=0.5))
            ax.text(x - 168 + w / 2, y - 108 + h / 2, "C32 lead", fontsize=7, ha="center")
    for name, box, color in [("TIM", TIM, "#356ab1"), ("land", METAL, "#222222")]:
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
    for v in children(tree, "via"):
        x, y = map(float, first(v, "at")[1:3])
        if 189 < x < 196 and 126 < y < 133:
            raw = str(first(v, "net")[1]).lstrip("/")
            ax.add_patch(
                Circle(
                    (x - 100, y - 100),
                    float(first(v, "size")[1]) / 2,
                    fill=False,
                    edgecolor="#17683d" if raw == "RAW_N22" else "#a84545",
                    linewidth=0.7,
                )
            )
    ax.annotate(
        "", xy=(90.1, 31.9), xytext=(93.75, 31.9), arrowprops={"arrowstyle": "<->", "color": "#222222"}
    )
    ax.text(91.925, 32.25, "3.65 land / 5.65 TIM width", ha="center", fontsize=8)
    ax.annotate(
        "", xy=(89.6, 27.7), xytext=(89.6, 31.4), arrowprops={"arrowstyle": "<->", "color": "#222222"}
    )
    ax.text(89.25, 29.55, "3.70 land", rotation=90, ha="center", va="center", fontsize=8)
    ax.set(
        xlim=(86, 100),
        ylim=(36, 23),
        aspect="equal",
        xlabel="P03 local X / native X−100 (mm)",
        ylabel="P03 local Y / native Y−100 (mm)",
        title="Actual saved B.Cu and both-face/lead reserves",
    )
    ax.grid(alpha=0.15)
    r = json.loads((OUT / "analysis.json").read_text())
    nom = r["scenarios"][2]["result"]
    sens = r["scenarios"][3]["result"]
    e = nom["unit_heat_energy_decomposition_c_per_w"]
    values = [
        5.5,
        e["via_barrels_all_segments"],
        e["sheet_spreading_total"],
        e["tim_bulk_under_actual_bottom_copper"],
        e["peak_above_uniform_source_mean"],
        nom["aluminum_land_axial_c_per_w"],
        nom["extra_contact_assumed_c_per_w"],
    ]
    labels = [
        "DD package reference",
        "Barrel energy share",
        "Sheet energy share",
        "TIM energy share",
        "EP peak above mean",
        "Al land axial",
        "Assumed interface",
    ]
    bx.barh(
        labels, values, color=["#777777", "#bc833c", "#bc9e48", "#ba585e", "#777777", "#777777", "#777777"]
    )
    for i, v in enumerate(values):
        bx.text(v + 0.3, i, f"{v:.2f}", va="center", fontsize=9)
    bx.invert_yaxis()
    bx.set(
        xlim=(0, 30),
        xlabel="Conditional K/W contribution / 1 W energy share",
        title=f"Nominal path {nom['conditional_total_junction_to_base_c_per_w']:.2f} K/W",
    )
    fig.suptitle("U10 / LT3090IDD — 8 EP vias / stronger actual-copper draft", fontsize=15)
    fig.text(
        0.07,
        0.12,
        "Metal3.65×3.70, topZ5.28; TIM5.65×5.70, nominalgap1.22\nHousingXY = nativeXY+[68,8]; U10 is proposedF194.2,129.3\nGreen actualRAW_N22 Bfill; orange actualTHT lead reserves.",
        fontsize=8,
    )
    fig.text(
        0.56,
        0.12,
        f"At60°C base: nominal {nom['conditional_junction_at_60c_base_c']:.2f}°C; sensitivity {sens['conditional_junction_at_60c_base_c']:.2f}°C\nSensitivity is not a manufacturer enclosure; no guardbanded pass.\n19 electrical opens; measured thermal/pressure/isolation proof missing.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.22, 1, 0.93))
    fig.savefig(OUT / "review.png", dpi=160)
    fig.savefig(OUT / "review.svg")


if __name__ == "__main__":
    main()
