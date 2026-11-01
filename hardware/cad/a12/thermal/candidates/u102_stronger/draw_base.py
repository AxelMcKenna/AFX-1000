"""CPU-rendered source-bound plate-assumption diagnostic; no empirical cooling claim."""

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/afx-mpl")
ROOT = Path(__file__).resolve().parent


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    report = json.loads((ROOT / "generated/base-model-audit.json").read_text())
    cases = report["cases"]
    x = np.arange(len(cases))
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.bar(
        x - 0.18, [r["plate_max_c"] for r in cases], width=0.36, label="Global plate peak", color="#a4493b"
    )
    ax.bar(
        x + 0.18,
        [r["local_3x3mm_source_projections"]["U102"]["local_peak_in_3x3mm_projection_c"] for r in cases],
        width=0.36,
        label="U102 plate projection",
        color="#457aa0",
    )
    for i, row in enumerate(cases):
        ax.text(i - 0.18, row["plate_max_c"] + 0.5, f"{row['plate_max_c']:.1f}", ha="center", fontsize=9)
    ax.axhline(60, color="#555", linestyle="--", linewidth=1, label="60 °C scenario allocation")
    ax.axhline(65, color="#888", linestyle=":", linewidth=1, label="65 °C comparison")
    ax.set_xticks(x, [f"h={r['h_assumed_w_per_m2k']}, ε={r['emissivity_assumed']}" for r in cases])
    ax.set(
        ylim=(40, 81),
        ylabel="Conditional base temperature (°C)",
        xlabel="Assumed uniform h (W/m²K) and emissivity; not measured",
        title="T01 base model: 60–65 °C is not a physical upper bound",
    )
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    fig.text(
        0.1,
        0.10,
        "Exact captured model replay: assumed ambient40 °C, supply-loss provision10.558 W, radiation view factor0.5.\nDigital12 W + analog1.255 W are delivered output allocations, not measured heat; bipolar/auxiliary loads also exist.\nTheir heat partition into the enclosure/base is unbounded. No installed airflow, finish, source-power or temperature qualification.",
        fontsize=9,
    )
    fig.subplots_adjust(bottom=0.27, top=0.88, left=0.1, right=0.96)
    fig.savefig(ROOT / "generated/base-assumptions.svg")
    fig.savefig(ROOT / "generated/base-assumptions.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
