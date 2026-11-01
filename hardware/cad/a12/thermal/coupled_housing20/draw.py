"""Standalone source-loaded thermal diagnostic comparison."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    r = json.load(open(ROOT / "generated/analysis.json"))
    base = np.load(ROOT / "generated/reference-base.npy")
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.7))
    im = axes[0].imshow(base, origin="lower", extent=[0, 334, 0, 188.4], aspect="equal", cmap="inferno")
    fig.colorbar(im, ax=axes[0], label="Conditional base temperature (°C)", shrink=0.7)
    axes[0].set_xlabel("Housing X (mm)")
    axes[0].set_ylabel("Housing Y, front toward +Y (mm)")
    axes[0].set_title("35.43 W, hot cluster, h3, full fin face\nSource-loaded base peak 71.32 °C")
    groups = [(3, 1), (3, 0.5), (2, 1), (2, 0.5)]
    values = []
    for scale in [1, 1.2]:
        values.append(
            [
                next(
                    x["result"]["base_peak_c"]
                    for x in r["loaded_cases"]
                    if x["placement"] == "unplaced_hotcluster"
                    and x["result"]["bottom_h_assumed"] == h
                    and x["result"]["fin_face_fraction_assumed"] == face
                    and x["result"]["heat_scale"] == scale
                )
                for h, face in groups
            ]
        )
    x = np.arange(4)
    width = 0.35
    axes[1].bar(x - width / 2, values[0], width, label="Retained 35.43 W provision", color="#297e8d")
    axes[1].bar(x + width / 2, values[1], width, label="+20% planning heat stress", color="#ed9b40")
    axes[1].axhline(65, ls="--", color="#a11", label="65 °C base planning limit")
    axes[1].set_ylim(40, 89)
    axes[1].set_ylabel("Conditional peak base temperature (°C)")
    axes[1].set_xticks(x, ["h3/full", "h3/half", "h2/full", "h2/half"])
    axes[1].set_title("Coupled cut walls and lid, finite seams\nUniform base temperature is not prescribed")
    axes[1].legend(fontsize=8, loc="upper left")
    fig.suptitle("CH20: actual apertures and source-loaded heat spreading", fontsize=13)
    fig.text(
        0.5,
        0.01,
        "40 °C ambient, k140, 70% exposed cut-wall metal, .1+.1 K/W reference contacts. Assumptions are unaccepted; this is not physical qualification.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    fig.savefig(ROOT / "generated/coupled-comparison.png", dpi=170)
    fig.savefig(ROOT / "generated/coupled-comparison.svg")
    plt.close(fig)


if __name__ == "__main__":
    main()
