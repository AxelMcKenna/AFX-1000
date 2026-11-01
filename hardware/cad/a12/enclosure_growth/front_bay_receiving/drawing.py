"""Dimensioned CPU review of actual source-derived receiving geometry."""

import json
from pathlib import Path

from .capture import ROOT, sha


def build():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle

    out = ROOT / "generated"
    target = out / "receiving-datums-final.svg"
    if target.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("New drawing required")
    d = json.loads((out / "coherent-receiving-model.json").read_text())
    c = json.loads((out / "interface-final.json").read_text())
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.25])
    front = fig.add_subplot(gs[0, :])
    top = fig.add_subplot(gs[1, :2])
    side = fig.add_subplot(gs[1, 2])
    colors = {"NF233": "#d48726", "FPC84": "#217ca5"}
    for b in d["boards"]:
        x, y, z = b["origin"]
        w, h = b["size"]
        color = colors[b["id"]]
        front.add_patch(Rectangle((x, z), w, h, fill=False, edgecolor=color, lw=2))
        front.text(x + w / 2, z + h + 1, b["id"] + f"  {w:g} × {h:g}", ha="center", color=color)
        top.add_patch(Rectangle((x, 180.5), w, 1.76, facecolor=color, alpha=0.5))
        top.text(x + w / 2, 177, b["id"], ha="center", color=color)
    for row in d["boxes"]:
        n, x, y, z, w, depth, h = row
        front.add_patch(
            Rectangle((x, z), w, h, facecolor=colors[n.split("_")[0]], edgecolor="none", alpha=0.32)
        )
    for m in c["mounting"]:
        x = m["world_X"]
        H = m["board_top_Z"]
        for z in [3.5, H - 1.2]:
            front.add_patch(Rectangle((x - 3, z), 6, 1.2, color="#43318f"))
        front.axvline(x, ls=":", lw=0.7, color="#43318f")
        front.text(x, 0, f"{x:g}", ha="center", fontsize=8)
        top.add_patch(Rectangle((x - 3, 179.9), 6, 6.3, fill=False, edgecolor="#43318f"))
        top.plot(x, 184, "o", ms=3, color="#43318f")
    front.set(
        xlim=(5, 330),
        ylim=(-2, 49),
        xlabel="World X / mm   ·   mount centres marked",
        ylabel="World Z / mm",
        title="FR01 · 317 actual source component records; conditional assembled receiving prisms",
    )
    top.add_patch(Rectangle((2.8, 185.6), 328.4, 2.8, facecolor="#888888", alpha=0.4))
    top.axhline(183.8, ls=":", color="gray")
    top.text(250, 184.2, "Upper seat Y183.8 only Z41.6–43.6", fontsize=8)
    top.set(
        xlim=(5, 330),
        ylim=(173, 189),
        xlabel="World X / mm",
        ylabel="World Y / mm",
        title="Front-wall mounting · existing board XY preserved · screw axes Y184.0",
    )
    m = c["mounting"][0]
    H = m["board_top_Z"]
    side.add_patch(Rectangle((185.6, 2.8), 2.8, 40.8, fc="#bbbbbb"))
    side.add_patch(Rectangle((183.8, 41.6), 1.8, 2, fc="#bbbbbb"))
    side.add_patch(Rectangle((184.3, 2.8), 1.9, H - 0.95 - 2.8, fc="#8c7bb5"))
    side.add_patch(Rectangle((182.5, 35.5), 3.7, H - 0.95 - 35.5, fc="#8c7bb5"))
    side.add_patch(Rectangle((180.5, 3.5), 1.6, 39, fc=colors["NF233"]))
    side.add_patch(Polygon(m["keeper_section_YZ"], fc="#54408c", alpha=0.9))
    side.add_patch(Rectangle((180.5, 43.6), 7.9, 2, fc="#999999", alpha=0.7))
    side.add_patch(Rectangle((182.95, 35.8), 2.1, 10.2, fc="#cccccc"))
    side.add_patch(Rectangle((181.5, 45.6), 5, 0.4, fc="gray"))
    side.add_patch(Rectangle((182, 46), 4, 2.1, fc="#777777"))
    side.text(176.7, 30, "Front\n−Y", fontsize=9)
    side.text(183.9, 50, "M2-class receiving\nnot a thread/torque approval", ha="center", fontsize=8)
    side.annotate("0.2 nominal top gap", (181.5, 42.6), (174, 40), arrowprops={"arrowstyle": "-"}, fontsize=8)
    side.annotate(
        "2.0 channel; matched shim", (182.2, 38), (173.8, 35), arrowprops={"arrowstyle": "-"}, fontsize=8
    )
    side.annotate(
        "0.2 local wall pocket",
        (185.7, 42),
        (188, 37),
        arrowprops={"arrowstyle": "-"},
        fontsize=8,
        ha="right",
    )
    side.set(
        xlim=(173, 190),
        ylim=(33, 52),
        xlabel="World Y / mm",
        ylabel="World Z / mm",
        title="NF upper keeper section · X210",
    )
    for ax in [front, top, side]:
        ax.grid(alpha=0.15)
        ax.set_aspect("equal", adjustable="box")
    fig.text(
        0.03,
        0.015,
        "Receiving requirements only. NF unknown-connector clash remains OPEN. No copper keepout, polymer, screw/thread, full harness or thermal qualification.",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(target)
    fig.savefig(out / "receiving-datums-final.png", dpi=150)
    (out / "drawing-final.json").write_text(
        json.dumps(
            dict(
                source_sha256={
                    str(p): sha(p)
                    for p in [Path(__file__), out / "coherent-receiving-model.json", out / "interface-final.json"]
                },
                artifact_sha256={str(p): sha(p) for p in [target, out / "receiving-datums-final.png"]},
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    build()
