"""AP02 dimensioned port/pressure-bay and clamp-height review diagram."""

import json

from .stage import OUT, ROOT, sha, write


def build():
    if (ROOT / "handoff.json").exists() or (OUT / "AP02-layout.png").exists():
        raise RuntimeError("Drawing output is immutable")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    d = json.loads((OUT / "analysis.json").read_text())
    fig, (ax, side) = plt.subplots(1, 2, figsize=(15, 9), gridspec_kw=dict(width_ratios=[2.4, 1]))
    fig.suptitle("AP02 · interior air-path mechanical candidate", x=0.055, ha="left", fontsize=18)
    fig.text(
        0.055,
        0.925,
        "Dimensional/source review only · 10 m³/h target = 8.8 interior + 1.2 base · flow, leakage and temperatures unverified",
        fontsize=10,
    )
    ax.add_patch(
        FancyBboxPatch(
            (0, 0), 334, 188.4, boxstyle="round,pad=0,rounding_size=7", fc="#fafafa", ec="#30383e", lw=1.5
        )
    )
    pins = d["pins"]
    ax.scatter(
        [p[0] for p in pins["kept_centres"]],
        [p[1] for p in pins["kept_centres"]],
        s=5,
        c="#aeb6ba",
        marker="s",
        alpha=0.5,
        label="918 retained pins below plate",
    )
    for b in d["plenum_bays_XY"]:
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec="#2e4c66", lw=2))
    ax.scatter(
        [p[0] for p in pins["removed_centres"]],
        [p[1] for p in pins["removed_centres"]],
        s=15,
        c="#b43c34",
        marker="x",
        label="42 additional whole pins removed",
    )
    for x, y, w, h in [(38, 164, 72, 19), (231.5, 154, 45, 29)]:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0,rounding_size=1",
                fc="#a9ded8",
                ec="#087a72",
                lw=1.2,
                alpha=0.9,
            )
        )
    ax.add_patch(Circle((93.0871, 168.9352), 6, fc="#fafafa", ec="#087a72", lw=1.3))
    for x, y in [[93.0871, 168.9352], [130.0871, 168.922]]:
        ax.add_patch(Circle((x, y), 3.6, fill=False, ec="#a14d9c", lw=1.1))
    ax.add_patch(Rectangle((82, 158), 53.848, 21.844, fill=False, ec="#a14d9c", ls="--", lw=1.5))
    ax.annotate(
        "TC02 board above floor at Z20\n335.27 mm² port projection below it",
        xy=(132, 174),
        xytext=(145, 201),
        fontsize=8,
        color="#873e82",
        arrowprops=dict(arrowstyle="-", color="#873e82"),
    )
    for x, y in d["fan"]["centres"]:
        ax.add_patch(Rectangle((x - 20.25, y - 20.25), 40.5, 40.5, fill=False, ec="#125f93", ls="--", lw=1.1))
        ax.add_patch(Circle((x, y), 18.75, fill=False, ec="#125f93", lw=0.8))
        ax.add_patch(Rectangle((x - 10, 139.5), 20, 2, fc="#d98330", ec="#9c531c"))
        ax.text(x, 134, "6.25 ×10 meter", ha="center", fontsize=7, color="#9c531c")
    for x in [46, 235.5]:
        ax.add_patch(Circle((x, 143), 3, fc="#d9ac67", ec="#7a4f17"))
    for y in [40 + 5.5 * i for i in range(18)]:
        ax.plot([0, 0], [y, y + 4], color="#0875b0", lw=3)
    ax.annotate(
        "18 west-wall slots\n4 ×36, R1.5\nZ5..41 / Y40..137.5\n2557.14 mm² net",
        xy=(0, 90),
        xytext=(-25, 47),
        fontsize=8,
        ha="right",
        color="#075d8a",
        arrowprops=dict(arrowstyle="-", color="#075d8a"),
    )
    for x, y in [[20, 20], [314, 20], [20, 168.4], [314, 168.4]]:
        ax.add_patch(Circle((x, y), 13, fill=False, ec="#62676d", ls=":"))
    ax.plot([34, 300], [0, 0], color="#bc6a25", lw=3)
    ax.text(
        167,
        -12,
        "Retained under-base outlet 266 ×14; isolated from fan bays except meters / sealed interfaces",
        ha="center",
        fontsize=8,
        color="#9c531c",
    )
    ax.text(58, 155, "L: 1258.99", fontsize=8, color="#08665f")
    ax.text(236, 157, "R: 1304.14", fontsize=8, color="#08665f")
    ax.text(
        20,
        215,
        "Port area at floor: 2563.13 mm² net · R6 protected island has 6.825 mm nominal join",
        fontsize=9,
        weight="bold",
    )
    ax.set_xlim(-30, 341)
    ax.set_ylim(-20, 220)
    ax.set_aspect("equal")
    ax.set_xlabel("Global X (mm)")
    ax.set_ylabel("Global Y (rear = 0; front = 188.4)")
    ax.grid(alpha=0.13)
    ax.legend(loc="upper left", fontsize=7, framealpha=0.9)

    side.set_xlim(0, 12)
    side.set_ylim(-39, 8)
    bands = [
        (-6.2, 6.2, "Metal plate / openings", "#aeb8bf"),
        (0, 2.8, "Retained carrier / openings", "#e6e1d7"),
        (-6.7, 0.5, "Top pressure-bay seal", "#efbd7d"),
        (-24.7, 10.4, "Sunon receiving body · CAD 10.4", "#8cbad6"),
        (-14.3, 2.1, "Matched shim · nominal 2.1", "#b4c9dc"),
        (-25.2, 0.5, "Frame-face gasket in recess", "#efbd7d"),
        (-26.2, 1.5, "Tray deck", "#aeb8bf"),
        (-27.7, 1, "Slotted guard", "#ccd6dd"),
        (-26.7, 0.5, "Lower metal washer", "#8a969f"),
        (-28.2, 0.5, "Direct-head seal washer", "#efbd7d"),
        (-31.2, 3, "M3 receiving head", "#8a969f"),
        (-12.2, 0.5, "Upper washer", "#8a969f"),
        (-11.7, 2.6, "Nut receiving gauge", "#8a969f"),
    ]
    for z, h, label, color in bands:
        x = 0 if label in ["Metal plate / openings", "Retained carrier / openings"] else 1
        width = 4 if x == 0 else 2
        side.add_patch(Rectangle((x, z), width, h, fc=color, ec="#4d5961", lw=0.5))
    labels = [
        (1.4, "Carrier top Z2.8"),
        (-3.1, "Base −6.2..0"),
        (-6.45, "Top seal to base"),
        (-10.3, "Nut / tip −8.2"),
        (-13.2, "Shim top −12.2"),
        (-19.5, "Fan + matched shim = 12.5"),
        (-24.95, "Gasket / hard-stop seat −24.7"),
        (-26, "Tray bottom −26.2"),
        (-27.3, "Guard / lower washer"),
        (-28.7, "Head bears on seal directly"),
        (-32.7, "Head bottom −31.2"),
        (-36.8, "Nominal bumper / table plane"),
    ]
    for z, label in labels:
        side.annotate(
            label,
            xy=(3, z),
            xytext=(4.3, z),
            fontsize=8,
            va="center",
            arrowprops=dict(arrowstyle="-", color="#697780", lw=0.7),
        )
    side.axhline(-36.8, color="#30383e", lw=1)
    side.text(0, 5, "Clamp-height schematic", fontsize=10, weight="bold")
    side.text(0.2, -35.7, "5.6 mm nominal head/table gap", fontsize=8, color="#9c531c")
    side.set_xticks([])
    side.set_ylabel("Global Z (mm)")
    side.grid(axis="y", alpha=0.15)
    fig.text(
        0.055,
        0.11,
        "All fan-frame, shim, seal, metering and filled-feedthrough interfaces are receiving requirements. Thin nominal frame land ≈0.6 mm needs\ncustom conversion/registration and actual contact verification; 0.79 mm foam thickness spans0.688..1.171. Seal force, cured wiring, pressure loss,\nflow split, guard protection, structural strength, source power and installed temperatures remain unqualified. This diagram is not a fabrication drawing.",
        fontsize=9,
        color="#8b3c2e",
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.24, wspace=0.18)
    for suffix in ["svg", "png"]:
        fig.savefig(OUT / ("AP02-layout." + suffix), dpi=150, facecolor="white")
    plt.close(fig)
    write(
        OUT / "drawing-provenance.json",
        dict(
            source_sha256={
                "drawing.py": sha(ROOT / "drawing.py"),
                "generated/analysis.json": sha(OUT / "analysis.json"),
                "generated/channel-geometry.json": sha(OUT / "channel-geometry.json"),
            },
            artifact_sha256={n: sha(OUT / n) for n in ["AP02-layout.svg", "AP02-layout.png"]},
            physical_qualified=False,
            fabrication_released=False,
        ),
    )
    print(json.dumps(dict(artifacts=2)))


if __name__ == "__main__":
    build()
