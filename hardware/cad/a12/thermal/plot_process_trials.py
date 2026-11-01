"""CPU-only scientific figure from saved native-copper process scenarios."""

import json

from .generate import OUT, REPO, ROOT, sha


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    report = json.loads((OUT / "u13-process-trials.json").read_text())
    names = ["native_1p6_wall25", "proposed_1p0_wall25", "wall35_current_stack", "wall50_outer85_fine"]
    labels = [
        "Native 1.6mm / assumed 25µm wall",
        "Trial 1.0mm / 25µm wall",
        "Trial 1.6mm / 35µm wall",
        "Trial 1.6mm / 50µm wall +85µm outer Cu",
    ]
    rows = [report["scenarios"][n] for n in names]
    native = json.loads((OUT / "u13-path.json").read_text())
    if native.get("construction_requirements"):
        rows.append(native["finer_grid"])
        labels.append("Actual C50 geometry / required 50µm wall")
    values = []
    for row in rows:
        e = row["unit_heat_energy_decomposition_c_per_w"]
        values.append(
            [
                row["package_theta_jc_c_per_w"],
                e["via_barrels_all_segments"],
                e["sheet_spreading_total"],
                e["tim_bulk_under_actual_bottom_copper"],
                e["peak_above_uniform_source_mean"] + row["aluminum_land_axial_c_per_w"],
            ]
        )
    values = np.array(values)
    fig, ax = plt.subplots(figsize=(11.8, 6.2))
    bottom = np.zeros(len(rows))
    for index, (label, color) in enumerate(
        zip(
            ["Package θJC", "Via barrels", "Cu sheet spreading", "TIM bulk", "EP peak + metal land"],
            ["#65758b", "#ba5239", "#e0a343", "#408c94", "#b29cc5"],
        )
    ):
        ax.barh(np.arange(len(rows)), values[:, index], left=bottom, color=color, label=label)
        bottom += values[:, index]
    for y, (total, row) in enumerate(zip(bottom, rows)):
        ax.text(
            13.4,
            y,
            f"{total:.2f} K/W  |  {row['conditional_junction_at_60c_base_c']:.1f}°C",
            va="center",
            fontsize=9,
        )
    ax.axvline(
        rows[0]["required_total_junction_to_base_at_60c_c_per_w"],
        color="#943e3e",
        linestyle="--",
        linewidth=1.3,
    )
    ax.text(
        11.72,
        -0.65,
        "85°C allocation at 60°C base: 11.718 K/W\nbefore temperature/power uncertainty",
        ha="center",
        fontsize=9,
        color="#943e3e",
    )
    ax.set_yticks(np.arange(len(rows)), labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 16.8)
    ax.set_xlabel("Equivalent junction-to-base thermal resistance (K/W)")
    ax.set_title("U13 heat-path bottleneck and manufacturing-process trials", loc="left", pad=35, fontsize=14)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=9, frameon=False)
    fig.text(
        0.025,
        0.035,
        "2.133384 W IC allocation. First four rows: earlier native copper with declared process overrides; last row: actual C50 layout.\nEnergy shares sum to the distributed-source mean; EP peak is added separately. Contact/material bounds and physical measurements remain missing.\nFabrication process requirements have not been verified by board-specific DFM or received-board microsections; no thermal qualification.",
        fontsize=8,
        color="#485363",
    )
    fig.subplots_adjust(left=0.32, right=0.96, top=0.78, bottom=0.29)
    fig.savefig(OUT / "u13-process-comparison.svg")
    fig.savefig(OUT / "u13-process-comparison.png", dpi=150)
    (OUT / "u13-process-comparison.json").write_text(
        json.dumps(
            dict(
                source_sha256={
                    str(p.relative_to(REPO)): sha(p)
                    for p in [
                        ROOT / "plot_process_trials.py",
                        OUT / "u13-process-trials.json",
                        OUT / "u13-path.json",
                    ]
                },
                evidence_sha256={
                    str(p.relative_to(REPO)): sha(p)
                    for p in [OUT / "u13-process-comparison.svg", OUT / "u13-process-comparison.png"]
                },
                physical_qualification=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
