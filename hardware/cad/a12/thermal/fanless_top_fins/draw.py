"""Software-rendered actual native finned lid plus conditional thermal cases."""

import json
import re

from .analyze import OUT, ROOT, read, sha


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    a = read(OUT / "analysis.json")
    pts = np.array(
        [
            [float(v) for v in row]
            for row in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", (OUT / "lid-with-fins.stl").read_text())
        ]
    )
    tris = pts.reshape(-1, 3, 3)
    fig = plt.figure(figsize=(14, 6.5))
    ax = fig.add_subplot(121, projection="3d")
    colors = ["#768a95" if tri[:, 2].max() > 38.001 else "#c5cdd0" for tri in tris]
    ax.add_collection3d(Poly3DCollection(tris, facecolor=colors, edgecolor="none", alpha=1))
    ax.set(
        xlim=(0, 334),
        ylim=(0, 157),
        zlim=(34, 59),
        xlabel="Housing X (mm)",
        ylabel="Housing Y (mm)",
        zlabel="Z (mm)",
        title="Actual private native lid +18 mm perimeter fins",
    )
    ax.set_box_aspect([334, 157, 70])
    ax.view_init(elev=32, azim=-67)
    ax = fig.add_subplot(122)
    rows = [r for r in a["cases"] if r["base_prescribed_c"] == 65]
    ys = [r["total_conditional_rejection_w"] for r in rows]
    labels = [
        "Full walls\nzero seam",
        "70%walls\nzero seam",
        "70%,k140\nR=.05",
        "70%,k140\nR=.10",
        "70%,k140\nR=.20",
        "R=.20\nhalf fin faces",
    ]
    ax.bar(range(len(rows)), ys, color=["#558d96", "#619fa5", "#b4a365", "#b98d59", "#b96c50", "#ac574f"])
    ax.axhline(35.4315458763, c="#333", ls="--", label="Retained35.4315 W")
    for i, v in enumerate(ys):
        ax.text(i, v + 0.4, f"{v:.2f}", ha="center", fontsize=9)
    ax.set(
        xticks=range(len(rows)),
        xticklabels=labels,
        ylim=(0, 47),
        ylabel="Conditional heat rejection at65 °C base /40 °C ambient (W)",
        title="Actual fin area in coupled wall/lid conduction model",
    )
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=8)
    fig.suptitle(
        "FF02: upward fins use existing control-height envelope; installed cooling remains unqualified",
        fontsize=13,
    )
    fig.text(
        0.04,
        0.035,
        "Native model includes inherited lid apertures; controls are omitted from this view. Fin topZ56 vs nominal controltopZ58.8.\nNo added fin radiation credit. Finger/service access, actual plume preheat, seams, finish, table, source heat paths and physical tests remain open.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.12, 1, 0.93))
    fig.savefig(OUT / "finned-lid-study.svg")
    fig.savefig(OUT / "finned-lid-study.png", dpi=150)
    plt.close(fig)
    (OUT / "drawing-inputs.json").write_text(
        json.dumps(
            {
                "source_sha256": {
                    str(p.relative_to(ROOT.parent)): sha(p)
                    for p in [ROOT / "draw.py", OUT / "analysis.json", OUT / "lid-with-fins.stl"]
                }
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
