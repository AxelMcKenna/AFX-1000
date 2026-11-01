"""Standalone conditional thermal comparison; no installation qualification."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    r = json.loads((ROOT / "generated/thermal.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(11.4, 4.7))
    mode = ["unplaced_uniform", "unplaced_hotcluster"]
    old = [x["peak_c"] for x in r["baseline_replay_controls"]]
    retained = [
        next(
            x["result"]["plate_max_c"]
            for x in r["enlarged_base_cases"]
            if x["fin_mode"] == "retained_original_pins" and x["placement"] == m
        )
        for m in mode
    ]
    extended = [x["fine"]["plate_max_c"] for x in r["enlarged_base_refinement"]]
    x = np.arange(3)
    w = 0.33
    axs[0].bar(
        x - w / 2,
        [old[0], retained[0], extended[0]],
        width=w,
        label="Unplaced heat over old footprint",
        color="#227c9d",
    )
    axs[0].bar(
        x + w / 2,
        [old[1], retained[1], extended[1]],
        width=w,
        label="Unplaced heat at hot cluster",
        color="#f2a541",
    )
    axs[0].axhline(65, color="#a33", ls="--", label="65 °C planning limit")
    axs[0].set_xticks(x, ["Original base", "Larger plate\noriginal fins", "Larger plate\nextended fins"])
    axs[0].set_ylim(40, 108)
    axs[0].set_ylabel("Conditional peak plate temperature (°C)")
    axs[0].set_title("Enlarged bottom base alone: still too hot")
    axs[0].legend(fontsize=7, loc="upper right")
    capacities = []
    for h, face in [(2, 0.5), (2, 1), (3, 0.5), (3, 1)]:
        v = next(
            x
            for x in r["isothermal_same_base_conditional_capacity"]
            if x["grid"] == [134, 76]
            and x["base_prescribed_c"] == 65
            and x["bottom_uniform_h_assumed"] == h
            and x["fin_face_fraction"] == face
        )
        capacities.append(v["combined_conditional_capacity_w"])
    axs[1].bar(np.arange(4), capacities, color=["#7a8c99", "#7a8c99", "#438c78", "#438c78"])
    axs[1].axhline(r["heat_target_w"], color="#333", ls="--", label="Retained 35.43 W provision")
    axs[1].axhline(
        1.2 * r["heat_target_w"], color="#a33", ls=":", label="Illustrative +20% capacity objective"
    )
    axs[1].set_xticks(
        np.arange(4), ["h2 / half fin", "h2 / full fin", "h3 / half fin", "h3 / full fin"], rotation=12
    )
    axs[1].set_ylim(0, 49)
    axs[1].set_ylabel("Conditional rejection at prescribed 65 °C base (W)")
    axs[1].set_title("New metal shell + enlarged base: assumption dependent")
    axs[1].legend(fontsize=7, loc="upper left")
    fig.suptitle("334 × 188.4 × 45.6 mm private housing study", fontsize=13)
    fig.text(
        0.5,
        0.01,
        "35.4315 W allocation, 40 °C ambient. Ideal source transfer; h2/h3 are scenarios. New metal shell required. No installed thermal bound or qualification.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.94))
    fig.savefig(ROOT / "generated/comparison.png", dpi=170)
    fig.savefig(ROOT / "generated/comparison.svg")
    plt.close(fig)


if __name__ == "__main__":
    main()
