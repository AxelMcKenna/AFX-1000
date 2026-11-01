"""CPU review drawing from frozen native points and exact captured hardware meshes."""

import json

from . import review


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    d = review.read(review.OUT / "selected-paths.json")
    fig = plt.figure(figsize=(14, 7))
    ax = fig.add_subplot(121, projection="3d")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    for name, color in [("return", "#a2784b"), ("positive", "#8aa0ab")]:
        raw = (review.ROOT / "inputs" / (name + ".stl")).read_bytes()
        faces = np.frombuffer(raw, dtype=dtype, offset=84)["vertices"]
        centres = faces.mean(axis=1)
        mask = (
            (centres[:, 0] > 155)
            & (centres[:, 0] < 197)
            & (centres[:, 1] > 94)
            & (centres[:, 1] < 133)
            & (centres[:, 2] > 10)
            & (centres[:, 2] < 30)
        )
        ax.add_collection3d(Poly3DCollection(faces[mask], facecolor=color, edgecolor="none", alpha=0.25))
    xy = fig.add_subplot(122)
    for route, color in zip(d["routes"], ["#e16d28", "#222222"]):
        p = np.array(route["native_points_mm"])
        ax.plot(*p.T, color=color, lw=2.8, label=route["net"])
        xy.plot(p[:, 0], p[:, 1], color=color, lw=2, label=route["net"])
        indices = route["native_boundary_indices"]
        for idx in [
            indices["source_initial_straight_end"],
            indices["source_prefix_end"],
            indices["destination_stub_start"],
        ]:
            point = p[idx]
            ax.scatter(*point, c=color, s=16)
            xy.scatter(*point[:2], c=color, s=20)
        xy.annotate("J4 " + route["pin"], p[0, :2], xytext=(-30, 7), textcoords="offset points", fontsize=9)
        xy.annotate("J13 " + route["pin"], p[-1, :2], xytext=(8, -5), textcoords="offset points", fontsize=9)
    n = d["dense_pair_nearest"]
    a = np.array(n["a_point_mm"])
    b = np.array(n["b_point_mm"])
    ax.plot(*np.vstack([a, b]).T, c="#b93c3c", lw=2)
    xy.plot([a[0], b[0]], [a[1], b[1]], c="#b93c3c", ls="--")
    ax.set(
        xlim=(157, 196),
        ylim=(96, 131),
        zlim=(5, 35),
        xlabel="Housing X (mm)",
        ylabel="Housing Y (mm)",
        zlabel="Z (mm)",
        title="Frozen38 mm baseline: native centerlines / hardware context",
    )
    ax.set_box_aspect([39, 35, 30])
    ax.view_init(elev=30, azim=-62)
    ax.legend(loc="upper left", fontsize=9)
    xy.set(
        xlim=(157, 196),
        ylim=(96, 131),
        xlabel="Housing X (mm)",
        ylabel="Housing Y (mm)",
        title="XY projection; crossings are separated in3D",
    )
    xy.set_aspect("equal")
    xy.grid(alpha=0.2)
    xy.legend(loc="upper right")
    xy.text(
        158,
        97.3,
        "Continuous R lower:9.700 /9.709 mm\nNative chord bound<0.000804 mm\nDense extra pair margin≥0.13564 mm\n7 mm receiver stubs; last3.1 mm bare",
        fontsize=9,
        bbox=dict(facecolor="white", alpha=0.9, edgecolor="#aaa"),
    )
    fig.suptitle(
        "EC01 selected source-to-ear pair: continuous-curve certificates +21 native geometry cases",
        fontsize=13,
    )
    fig.text(
        0.04,
        0.025,
        "Centerlines shown, not tube diameter. 85.191 /78.282 mm geometric upper lengths include prefix,7 mm stub and maximum board/tail allocations; cutslack remainsopen.\nForming, MPPE gripping, solder/current/strain/lifetime and physical assembly remain unqualified. H9 vertical drive hits actual DIG copper. Larger-case/control-pose study is separate.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.12, 1, 0.94))
    fig.savefig(review.OUT / "selected-route-review.svg")
    fig.savefig(review.OUT / "selected-route-review.png", dpi=150)
    plt.close(fig)
    (review.OUT / "drawing-inputs.json").write_text(
        json.dumps(
            {
                "source_sha256": {
                    str(p.relative_to(review.ROOT)): review.sha(p)
                    for p in [
                        review.ROOT / "draw.py",
                        review.OUT / "selected-paths.json",
                        review.ROOT / "inputs/return.stl",
                        review.ROOT / "inputs/positive.stl",
                    ]
                }
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
