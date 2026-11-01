"""CPU plot/dimensioned section; no shaded-graphics permission needed."""

import json

from .analyze import OUT, ROOT, read, sha


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Circle, Rectangle

    a = read(OUT / "analysis.json")
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.8), gridspec_kw={"width_ratios": [1, 1.2, 1.2]})
    ax = axes[0]
    ax.add_patch(Rectangle((0, -6.2), 157, 6.2, facecolor="#555", edgecolor="black"))
    for i in range(12):
        ax.add_patch(
            Rectangle((12 + i * 130 / 11, -26.2), 3, 20, facecolor="#666", edgecolor="black", lw=0.5)
        )
    ax.plot([-5, 162], [-28.8, -28.8], color="#86623c", lw=3)
    ax.text(78.5, 4, "6.2 mm plate; top Z0", ha="center", fontsize=9)
    ax.annotate("20 mm fins", xy=(145, -16), xytext=(95, -12), arrowprops={"arrowstyle": "->"}, fontsize=9)
    ax.text(78.5, -37, "Nominal table gap 2.6 mm", ha="center", fontsize=8)
    ax.set(
        xlim=(-5, 162),
        ylim=(-44, 10),
        title="Private lower-fin prototype",
        xlabel="Across depth (mm)",
        ylabel="Z (mm)",
    )
    ax.set_aspect("equal")
    rows = [r for r in a["metal_shell_proposals"] if r["base_prescribed_c"] == 65]
    ys = [rows[0]["bottom_actual_notched_mesh_assumed_capacity_w"]] + [
        r["complete_same_envelope_capacity_screen_w"] for r in rows[:3]
    ]
    labels = [
        "Native bottom\nonly",
        "Metal wrap\nfull walls",
        "Metal wrap\n70% walls",
        "70% walls\n+seam/k case",
    ]
    ax = axes[1]
    ax.bar(range(4), ys, color=["#be5c49", "#508e9a", "#d3a15c", "#ac6846"])
    ax.axhline(a["heat_target_w"], c="#333", ls="--", label="35.4315 W provision")
    for x, y in enumerate(ys):
        ax.text(x, y + 0.4, f"{y:.2f} W", ha="center", fontsize=9)
    ax.set(
        xticks=range(4),
        xticklabels=labels,
        ylim=(0, 42),
        ylabel="Conditional rejected heat at prescribed 65 °C base (W)",
        title="Same external envelope / ambient40 °C",
    )
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    ax = axes[2]
    field = np.load(OUT / "metal-lid-field.npy")
    im = ax.imshow(field, origin="lower", extent=[0, 334, 0, 157], cmap="inferno", vmin=40, vmax=65)
    ax.set(title="Cutout/cap-masked metal lid, 70% walls", xlabel="Housing X (mm)", ylabel="Housing Y (mm)")
    fig.colorbar(im, ax=ax, shrink=0.65, label="Conditional lid temperature (°C)")
    fig.suptitle(
        "FF01: bottom redistribution fails; metal-shell/vent path needs real integration and measurement",
        fontsize=13,
    )
    fig.text(
        0.04,
        0.03,
        "No housing, PCB, fan, heat target or sealed kit changed. Correlations are not installed bounds. The near-table obstacle, ports/seams, airflow, radiation view,\nactual base spreading, every board-to-base path, electrical isolation and full hardware/harness integration remain unqualified.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.13, 1, 0.94))
    fig.savefig(OUT / "feasibility.svg")
    fig.savefig(OUT / "feasibility.png", dpi=150)
    plt.close(fig)
    # Dimensioned plan shows native fin interruption geometry via actual sampled STL edges projection.
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.add_patch(Rectangle((0, 0), 334, 157, facecolor="#ddd", edgecolor="black", lw=1))
    for i in range(12):
        ax.add_patch(Rectangle((12, 12 + i * 130 / 11), 310, 3, facecolor="#555"))
    d = read(
        ROOT
        / "sources/context/hardware/cad/a12/thermal/whole_unit/sources/hardware/cad/a12/thermal/design.json"
    )
    for centres, r in [
        (d["feet"]["centres"], 12),
        (d["shell_fasteners"], 6),
        (d["return_support_attachments"]["centres"], 5),
    ]:
        for p in centres:
            ax.add_patch(Circle(p, r, facecolor="#ddd", edgecolor="#888", lw=0.5))
    for p in d["feet"]["centres"]:
        ax.add_patch(Circle(p, 9, fill=False, edgecolor="#325a8c", lw=0.9))
    ax.annotate("", xy=(0, -8), xytext=(334, -8), arrowprops={"arrowstyle": "<->"})
    ax.text(167, -14, "334 mm", ha="center")
    ax.annotate("", xy=(-9, 0), xytext=(-9, 157), arrowprops={"arrowstyle": "<->"})
    ax.text(-15, 78.5, "157 mm", ha="center", rotation=90)
    ax.text(167, 173, "12 lanes / 3 mm thick / 20 mm deep / 8.818 mm nominal clear gap", ha="center")
    ax.text(
        0,
        -32,
        "Unreleased machining/airflow prototype. Fin span310 mm, across span133 mm; R12 feet / R6 shell-bolt / R5 return-screw reliefs.\nZ−26.2..−6.2 fins; plateZ−6.2..0. Hole/countersink geometry in SCAD/STL. Real prototype has interrupted channels; source correlation needs validation.",
        fontsize=9,
    )
    ax.set(xlim=(-25, 345), ylim=(-45, 185))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "dimensioned-prototype.svg")
    fig.savefig(OUT / "dimensioned-prototype.png", dpi=150)
    plt.close(fig)
    paths = [
        ROOT / "draw.py",
        OUT / "analysis.json",
        OUT / "metal-lid-field.npy",
        OUT / "native-geometry.json",
    ]
    (OUT / "drawing-inputs.json").write_text(
        json.dumps({"source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in paths}}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
