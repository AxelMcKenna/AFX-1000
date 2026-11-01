"""Dimensioned CPU plan/elevation and BREP-derived assembly projection."""

import json

from .generate import OUT, ROOT, load, sha


def main():
    import cadquery as cq
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Circle, Rectangle
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    d = load()
    fig = plt.figure(figsize=(16.54, 11.69), layout="constrained")
    grid = fig.add_gridspec(3, 2, height_ratios=[2.3, 1, 0.95])
    ax = fig.add_subplot(grid[0, :])
    ax.set(xlim=(35, 235), ylim=(155, 90), aspect="equal", xlabel="Housing X / mm", ylabel="Housing Y / mm")
    ax.set_title(
        "AFX A12 PB01 — POSITIVE LINKS / prototype only / dimensions in mm\nNominal measured-plane blanks; do not fabricate until receiving, insulation and process holds close",
        loc="left",
        fontsize=13,
    )
    packet = json.loads((OUT / "obstacles.json").read_text())
    for r in packet["boxes"]:
        _, x, y, z, w, h, t, *_ = r
        if x + w < 40 or x > 235 or y + h < 90 or y > 155:
            continue
        if t > 4:
            ax.add_patch(Rectangle((x, y), w, h, facecolor="#e4e8ec", edgecolor="#c3c9cf", lw=0.4))
    for r in packet["cylinders"]:
        _, x, y, z, diam, h = r
        if diam > 6:
            ax.add_patch(Circle((x, y), diam / 2, color="#d5dae0", alpha=0.8))
    colors = {"ANA": "#aa5224", "DIG": "#086e9a"}
    for name, row in d["paths"].items():
        p = np.array(row["points"])
        ax.plot(
            p[:, 0], p[:, 1], color=colors[name], lw=5, alpha=0.8, label=name + " Cu 6.4 wide / 1.2 thick"
        )
        for i, q in enumerate(p):
            ax.plot(q[0], q[1], ".", color="black", ms=2)
            ax.annotate(str(i), (q[0], q[1]), xytext=(3, 4), textcoords="offset points", fontsize=7)
        for q in p[[0, -1]]:
            ax.add_patch(Circle(q[:2], 5, fill=False, color=colors[name], lw=1))
            ax.add_patch(Circle(q[:2], 1.7, fill=False, color="black", lw=0.8))
    for name, q in d["support"]["saddles"].items():
        ax.add_patch(Rectangle((q[0] - 1.25, q[1] - 6.5), 2.5, 13, fill=False, edgecolor="#673a8d", lw=1.3))
    ax.add_patch(Rectangle((163, 117.5), 6, 12, fill=False, edgecolor="#673a8d", lw=1.3))
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.15)
    for col, (name, row) in enumerate(d["paths"].items()):
        p = np.array(row["points"])
        station = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
        a = fig.add_subplot(grid[1, col])
        a.plot(station, p[:, 2], color=colors[name], lw=2)
        a.fill_between(station, p[:, 2], p[:, 2] + 1.2, color=colors[name], alpha=0.2)
        for i, (x, z) in enumerate(zip(station, p[:, 2])):
            a.text(x, z + 0.5, str(i), fontsize=7)
        a.set(
            xlabel="Developed centreline station / mm",
            ylabel="Bottom Z / mm",
            ylim=(9, 27),
            title=f"{name}: length {station[-1]:.1f}; integral machined risers, no formed-sheet claim",
        )
        a.grid(alpha=0.2)
        b = fig.add_subplot(grid[2, col])
        b.axis("off")
        stations = "  ".join(f"{i}:({q[0]:g},{q[1]:g},{q[2]:g})" for i, q in enumerate(p))
        import textwrap

        b.text(
            0,
            1,
            "XYZ station schedule (global housing datum)\n"
            + "\n".join(textwrap.wrap(stations, 90))
            + "\n\nTerminal OD10 (+/−.05), hole3.4 (+/−.05); DIG E28 rear flatX=127.0.\nBulk6.4 (+/−.1), thickness1.2 (+/−.2), edge break≤.05.\nMinimum net normal Cu requirement6mm²; electrical joints measured separately.\nMatch end planes to actual assembled studs; no manual bending.\nAll component mate heights, complete wiring, strength and physical fit unqualified.",
            va="top",
            fontsize=8,
        )
    fig.savefig(OUT / "PB01-dimensioned-plan.svg")
    fig.savefig(OUT / "PB01-dimensioned-plan.png", dpi=140)
    plt.close(fig)
    fig = plt.figure(figsize=(14, 8), layout="constrained")
    a = fig.add_subplot(111, projection="3d")
    for file, color in [
        ("ANA-CU.step", "#bd7842"),
        ("DIG-CU.step", "#3385a3"),
        ("BONDED-PEDESTAL.step", "#a89ac3"),
    ]:
        obj = cq.importers.importStep(str(OUT / file)).val()
        vertices, faces = obj.tessellate(0.12)
        points = np.array([[v.x, v.y, v.z] for v in vertices])
        a.add_collection3d(
            Poly3DCollection(points[np.array(faces)], facecolors=color, edgecolors="none", alpha=0.95)
        )
    for name in d["paths"]:
        for end in (0, 1):
            for half in ("HALF-A", "HALF-B"):
                obj = cq.importers.importStep(str(OUT / f"{name}-CAP{end}-{half}.step")).val()
                vs, fs = obj.tessellate(0.15)
                points = np.array([[v.x, v.y, v.z] for v in vs])
                a.add_collection3d(
                    Poly3DCollection(points[np.array(fs)], facecolors="#decf99", edgecolors="none", alpha=0.9)
                )
    a.set(xlim=(45, 232), ylim=(95, 152), zlim=(0, 30), xlabel="X / mm", ylabel="Y / mm", zlabel="Z / mm")
    a.set_box_aspect((187, 57, 45))
    a.view_init(28, -64)
    a.set_title(
        "PB01 actual STEP geometry — copper, split terminal caps and bonded support\nTape is an assembly process; maximum tape/cap envelopes are separate CAD solids"
    )
    fig.savefig(OUT / "PB01-assembly.png", dpi=150)
    plt.close(fig)
    report = {
        "source_sha256": {
            str(q.relative_to(ROOT)): sha(q)
            for q in [ROOT / "design.json", ROOT / "drawings.py", OUT / "obstacles.json"]
        },
        "visual_approval": False,
        "fabrication_drawing_released": False,
    }
    (OUT / "drawing-report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
