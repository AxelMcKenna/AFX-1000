"""Standalone scientific summary of the declared heat ledger and plate scenarios."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .ledger import OUT, SOURCES, read


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Rectangle

    ledger = read(OUT / "ledger.json")
    report = read(OUT / "analysis.json")
    fig, axs = plt.subplots(2, 2, figsize=(15, 10.5))
    ax = axs[0, 0]
    classes = {}
    for row in ledger["leaf_heat_rows"]:
        classes[row["category"]] = classes.get(row["category"], 0) + row["watts"]
    ax.bar([0], [ledger["old_supply_only_heatmap_w"]], color="#879bb0", width=0.55)
    bottom = 0
    for label, watts in classes.items():
        ax.bar([1], [watts], bottom=bottom, label=label.replace("_", " "), width=0.55)
        if watts > 2:
            ax.text(
                1, bottom + watts / 2, f"{watts:.2f}", ha="center", va="center", color="white", fontsize=9
            )
        bottom += watts
    ax.set_xticks(
        [0, 1],
        ["Selected supply-loss map\n(incomplete heat scope)", "Whole provisional tree\nno export credit"],
    )
    ax.set(
        ylabel="Internal heat screen (W)",
        title="Declared endpoint power changes the cooling requirement",
        ylim=(0, 40),
    )
    ax.text(0, 11.2, "10.56 W", ha="center", fontsize=10)
    ax.text(1, 36.1, f"{bottom:.2f} W", ha="center", fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)

    ax = axs[0, 1]
    for index, mode in enumerate(["unplaced_uniform", "unplaced_hotcluster"]):
        rows = [
            r["result"]
            for r in report["cases"]
            if r["placement"] == mode and r["result"]["emissivity_assumed"] == 0.8
        ]
        x = np.array([r["h_assumed_w_per_m2k"] for r in rows]) + (index - 0.5) * 0.28
        ax.bar(
            x,
            [r["plate_max_c"] for r in rows],
            width=0.28,
            label="Unplaced load: " + ("uniform" if index == 0 else "hot cluster"),
        )
        for xx, row in zip(x, rows):
            ax.text(xx, row["plate_max_c"] + 1, f"{row['plate_max_c']:.1f}", ha="center", fontsize=9)
    ax.axhline(60, color="#555", ls="--", lw=1, label="60 °C comparison")
    ax.axhline(65, color="#999", ls=":", lw=1, label="65 °C comparison")
    ax.set(
        xticks=[1, 2, 3],
        xlabel="Assumed uniform h (W/m²K); no installed minimum proved",
        ylabel="Conditional peak base (°C)",
        title="Current passive geometry / assumed ε0.8 / ambient40 °C",
        ylim=(40, 152),
    )
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)

    ax = axs[1, 0]
    ax.add_patch(Rectangle((0, 0), 334, 157, fill=False, color="#555"))
    body = read(SOURCES / "hardware/cad/a12/thermal/candidates/u102_stronger/sources/current-body/other.json")
    for b in body["boards"]:
        if b[0] in ["dsp_carrier", "audio_carrier", "led_driver", "input_power", "disconnect_carrier"]:
            ax.add_patch(Rectangle((b[1], b[2]), b[4], b[5], fill=False, edgecolor="#7389a0", lw=1))
            ax.text(b[1] + 1, b[2] + 5, b[0].replace("_carrier", ""), fontsize=7)
    ax.add_patch(Rectangle((168, 108), 160, 45, fill=False, edgecolor="#7389a0", lw=1))
    ax.text(310, 150, "P03", fontsize=8)
    for row in report["source_placements"]["unplaced_hotcluster"]:
        x, y, w, h = row["rect_housing_mm"]
        if row["watts"] > 0.15:
            ax.add_patch(
                Rectangle((x, y), w, h, color="#da8154", alpha=min(0.65, 0.1 + row["watts"] * 0.1), lw=0)
            )
    ax.scatter([277], [116], marker="x", color="#b2182b", s=60)
    ax.annotate(
        "5.61 W unplaced\nhot-cluster scenario",
        (277, 116),
        (205, 35),
        arrowprops=dict(arrowstyle="->", color="#b2182b"),
        fontsize=9,
    )
    ax.set(
        xlim=(-2, 336),
        ylim=(159, -2),
        xlabel="Housing X (mm)",
        ylabel="Housing Y (mm)",
        title="Known board positions + explicit ideal plate injections",
    )
    ax.set_aspect("equal")

    ax = axs[1, 1]
    for index, mode in enumerate(["unplaced_uniform", "unplaced_hotcluster"]):
        rows = [
            r
            for r in report["required_uniform_h"]
            if r["placement"] == mode and r["emissivity_assumed"] == 0.8
        ]
        vals = [sum(r["required_uniform_h_bracket_w_per_m2k"]) / 2 for r in rows]
        x = np.array([0, 1]) + (index - 0.5) * 0.3
        ax.bar(x, vals, width=0.3, label="Unplaced: " + ("uniform" if index == 0 else "hot cluster"))
        for xx, value in zip(x, vals):
            ax.text(xx, value + 0.2, f"{value:.2f}", ha="center", fontsize=9)
    ax.axhline(3, color="#777", ls=":", label="Earlier assumed h3 scenario")
    ax.set(
        xticks=[0, 1],
        xticklabels=["60 °C peak base", "65 °C peak base"],
        ylabel="Required uniform h in this model (W/m²K)",
        title="Same35.43 W screen / ε0.8 / no measurement margin",
        ylim=(0, 19),
    )
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    fig.suptitle("WU01: supply-loss-only temperature is not a whole-unit thermal result", fontsize=17, y=0.98)
    fig.text(
        0.055,
        0.018,
        "All loads, efficiencies,4 A feed and.36 Ω are unverified allocations; no optical/export credit. All-to-metal transfer and uniform h are idealizations.\nNo measured source/base/material/airflow bound; no junction, thermal, fabrication or physical qualification. h is not a fan CFM specification.",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.065, 1, 0.95))
    fig.savefig(OUT / "whole-unit-heat.svg")
    fig.savefig(OUT / "whole-unit-heat.png", dpi=150)
    plt.close(fig)
    (OUT / "drawing-inputs.json").write_text(
        json.dumps(
            dict(
                source_sha256={
                    str(p.relative_to(REPO)): sha(p)
                    for p in [Path(__file__).resolve(), OUT / "ledger.json", OUT / "analysis.json"]
                },
                fabrication_drawing=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
